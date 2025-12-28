from celery import Task
from worker.celery_app import app
from shared.config import get_settings
from shared.enums import TaskStatus
from redis import Redis
import httpx
import json
from pathlib import Path
from datetime import datetime
from worker.tasks.upload import upload_to_webdav
import shutil

settings = get_settings()
redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


def update_task_status(task_id: str, status: TaskStatus, error: str = None):
    task_data = redis_client.get(f"task:{task_id}")
    if task_data:
        data = json.loads(task_data)
        data["status"] = status.value
        if error:
            data["error"] = error
        if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            data["completed_at"] = datetime.utcnow().isoformat()
        redis_client.setex(f"task:{task_id}", 86400, json.dumps(data))


class DownloadTask(Task):
    autoretry_for = (httpx.HTTPError, ConnectionError)
    retry_kwargs = {"max_retries": settings.max_retries}
    retry_backoff = True


@app.task(bind=True, base=DownloadTask, name="worker.tasks.download.process_download")
def process_download(self, task_id: str, url: str, filename: str):
    task_dir = Path(settings.storage_path) / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    filepath = task_dir / filename

    try:
        update_task_status(task_id, TaskStatus.DOWNLOADING)

        with httpx.Client(timeout=settings.download_timeout, follow_redirects=True) as client:
            with client.stream("GET", url) as response:
                response.raise_for_status()

                content_length = response.headers.get("content-length")
                if content_length:
                    size_gb = int(content_length) / (1024 ** 3)
                    if size_gb > settings.max_file_size_gb:
                        raise ValueError(
                            f"File size {size_gb:.2f}GB exceeds limit of {settings.max_file_size_gb}GB")

                with open(filepath, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)

        update_task_status(task_id, TaskStatus.UPLOADING)

        upload_to_webdav(filepath, filename)

        update_task_status(task_id, TaskStatus.COMPLETED)

    except Exception as e:
        error_msg = str(e)
        update_task_status(task_id, TaskStatus.FAILED, error_msg)
        raise

    finally:
        if task_dir.exists():
            shutil.rmtree(task_dir, ignore_errors=True)
