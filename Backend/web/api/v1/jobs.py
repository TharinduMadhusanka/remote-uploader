from fastapi import APIRouter, HTTPException, Query
from celery import Celery
from redis import Redis
from shared.models import JobSubmit, JobResponse, JobList
from shared.enums import TaskStatus
from shared.config import get_settings
from datetime import datetime
import json
import uuid
import re

router = APIRouter()
settings = get_settings()

celery_app = Celery("transloader", broker=settings.redis_url,
                    backend=settings.redis_url)
redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


def is_private_ip(url: str) -> bool:
    """Block private IP ranges for security"""
    private_patterns = [
        r'127\.\d+\.\d+\.\d+',
        r'192\.168\.\d+\.\d+',
        r'10\.\d+\.\d+\.\d+',
        r'172\.(1[6-9]|2[0-9]|3[0-1])\.\d+\.\d+',
        r'localhost'
    ]
    return any(re.search(pattern, url.lower()) for pattern in private_patterns)


@router.post("/jobs", response_model=JobResponse, status_code=201)
async def submit_job(job: JobSubmit):
    url_str = str(job.url)

    if is_private_ip(url_str):
        raise HTTPException(status_code=400, detail="Private IPs not allowed")

    task_id = str(uuid.uuid4())

    filename = job.rename_to if job.rename_to else url_str.split(
        '/')[-1].split('?')[0]
    if not filename:
        filename = f"download_{task_id[:8]}"

    created_at = datetime.utcnow()

    task_data = {
        "id": task_id,
        "status": TaskStatus.PENDING.value,
        "url": url_str,
        "filename": filename,
        "created_at": created_at.isoformat(),
        "completed_at": None,
        "error": None
    }

    redis_client.setex(f"task:{task_id}", 86400, json.dumps(task_data))
    redis_client.lpush("task_ids", task_id)
    redis_client.ltrim("task_ids", 0, 99)

    celery_app.send_task(
        "worker.tasks.download.process_download",
        args=[task_id, url_str, filename],
        task_id=task_id
    )

    response_payload = {**task_data, "created_at": created_at}

    return JobResponse(**response_payload)


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    task_data = redis_client.get(f"task:{job_id}")

    if not task_data:
        raise HTTPException(status_code=404, detail="Job not found")

    data = json.loads(task_data)
    data["created_at"] = datetime.fromisoformat(data["created_at"])
    if data["completed_at"]:
        data["completed_at"] = datetime.fromisoformat(data["completed_at"])

    return JobResponse(**data)


@router.get("/jobs", response_model=JobList)
async def list_jobs(
    status: TaskStatus = Query(None),
    limit: int = Query(20, ge=1, le=100)
):
    task_ids = redis_client.lrange("task_ids", 0, limit - 1)
    jobs = []

    for task_id in task_ids:
        task_data = redis_client.get(f"task:{task_id}")
        if task_data:
            data = json.loads(task_data)
            if status is None or data["status"] == status.value:
                data["created_at"] = datetime.fromisoformat(data["created_at"])
                if data["completed_at"]:
                    data["completed_at"] = datetime.fromisoformat(
                        data["completed_at"])
                jobs.append(JobResponse(**data))

    return JobList(jobs=jobs, total=len(jobs))


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    task_data = redis_client.get(f"task:{job_id}")

    if not task_data:
        raise HTTPException(status_code=404, detail="Job not found")

    data = json.loads(task_data)

    # If job is active (pending, downloading, uploading), cancel it first
    if data["status"] not in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
        celery_app.control.revoke(job_id, terminate=True)

    # Remove from Redis completely
    redis_client.delete(f"task:{job_id}")

    # Remove from the task_ids list
    redis_client.lrem("task_ids", 0, job_id)

    return {"message": "Job deleted successfully"}
