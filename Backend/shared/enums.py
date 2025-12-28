from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    DOWNLOADING = "DOWNLOADING"
    UPLOADING = "UPLOADING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
