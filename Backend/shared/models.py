from pydantic import BaseModel, HttpUrl, Field
from typing import Optional
from datetime import datetime
from .enums import TaskStatus


class JobSubmit(BaseModel):
    url: HttpUrl
    rename_to: Optional[str] = None


class JobResponse(BaseModel):
    id: str
    status: TaskStatus
    url: str
    filename: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class JobList(BaseModel):
    jobs: list[JobResponse]
    total: int
