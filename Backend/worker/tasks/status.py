from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from redis import Redis

from shared.config import get_settings
from shared.enums import TaskStatus

settings = get_settings()
redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


def update_task_status(
    task_id: str,
    status: TaskStatus,
    error: Optional[str] = None,
    progress: Optional[float] = None,
    download_speed: Optional[str] = None,
    eta: Optional[str] = None,
) -> None:
    """Persist the latest task status snapshot in Redis."""
    task_data = redis_client.get(f"task:{task_id}")
    if not task_data:
        return

    data = json.loads(task_data)
    data["status"] = status.value
    if error:
        data["error"] = error
    if progress is not None:
        data["progress"] = progress
    if download_speed:
        data["download_speed"] = download_speed
    if eta:
        data["eta"] = eta

    if status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
        data["completed_at"] = datetime.utcnow().isoformat()
        data["progress"] = None
        data["download_speed"] = None
        data["eta"] = None

    redis_client.setex(f"task:{task_id}", 86400, json.dumps(data))
