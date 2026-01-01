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
    progress: Optional[float] = Field(None, description="Download progress percentage (0-100)")
    download_speed: Optional[str] = Field(None, description="Current download speed (e.g., '2.5 MB/s')")
    eta: Optional[str] = Field(None, description="Estimated time remaining")


class JobList(BaseModel):
    jobs: list[JobResponse]
    total: int
