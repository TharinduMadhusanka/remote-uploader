import time
from pathlib import Path

import httpx

from shared.config import get_settings
from shared.enums import TaskStatus

from worker.tasks.status import update_task_status

from .client import get_aria2_client, format_speed, format_time

settings = get_settings()

def download_file_aria2(task_id: str, url: str, filepath: Path) -> bool:
    """
    Download file using aria2. Returns True on success, False on failure.
    Updates progress in Redis during download.
    """
    aria2 = get_aria2_client()
    if not aria2:
        print(f"aria2 client unavailable for task {task_id}")
        return False

    try:
        # Add download with aria2 options
        options = {
            "dir": str(filepath.parent),
            "out": filepath.name,
            "max-connection-per-server": str(settings.aria2_max_connections),
            "split": str(settings.aria2_split),
            "continue": "true",
            "max-tries": str(settings.max_retries),
            "retry-wait": "3",
            "timeout": "60",
            "allow-overwrite": "true",
        }

        print(f"aria2 starting download: {url} -> {filepath}")
        download = aria2.add_uris([url], options=options)
        print(f"aria2 download added, GID: {download.gid}")

        # Monitor download progress
        while not download.is_complete:
            download.update()

            if download.has_failed:
                error_msg = download.error_message or "Unknown aria2 error"
                print(f"aria2 download failed: {error_msg}")
                update_task_status(task_id, TaskStatus.FAILED, error=error_msg)
                return False

            # Calculate progress
            if download.total_length > 0:
                progress = (download.completed_length / download.total_length) * 100
                speed = format_speed(download.download_speed)
                
                # Calculate ETA
                if download.download_speed > 0:
                    remaining_bytes = download.total_length - download.completed_length
                    eta_seconds = remaining_bytes // download.download_speed
                    eta = format_time(eta_seconds)
                else:
                    eta = "calculating..."

                # Log progress for debugging
                print(f"Progress: {progress:.1f}% | Speed: {speed} | ETA: {eta}")

                update_task_status(
                    task_id,
                    TaskStatus.DOWNLOADING,
                    progress=round(progress, 2),
                    download_speed=speed,
                    eta=eta
                )

            time.sleep(1)  # Update every second

        # Refresh to get final status
        download.update()

        if download.is_complete and not download.has_failed:
            print(f"aria2 download completed successfully: {filepath}")
            return True
        else:
            error_msg = download.error_message or "Download failed"
            print(f"aria2 download failed after completion check: {error_msg}")
            update_task_status(task_id, TaskStatus.FAILED, error=error_msg)
            return False

    except Exception as e:
        print(f"aria2 download exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def download_with_httpx(task_id: str, url: str, filepath: Path):
    """Fallback download method using httpx."""
    update_task_status(task_id, TaskStatus.DOWNLOADING, progress=0)

    with httpx.Client(timeout=settings.download_timeout, follow_redirects=True) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()

            content_length = response.headers.get("content-length")
            if content_length:
                size_gb = int(content_length) / (1024 ** 3)
                if size_gb > settings.max_file_size_gb:
                    raise ValueError(
                        f"File size {size_gb:.2f}GB exceeds limit of {settings.max_file_size_gb}GB")

            downloaded = 0
            total = int(content_length) if content_length else None

            with open(filepath, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Update progress every 1MB
                    if total and downloaded % (1024 * 1024) == 0:
                        progress = (downloaded / total) * 100
                        update_task_status(
                            task_id,
                            TaskStatus.DOWNLOADING,
                            progress=round(progress, 2)
                        )
