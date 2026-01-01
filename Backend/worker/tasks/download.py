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
import aria2p
import time
from typing import Optional

settings = get_settings()
redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


def update_task_status(
    task_id: str,
    status: TaskStatus,
    error: str = None,
    progress: float = None,
    download_speed: str = None,
    eta: str = None
):
    """Update task status in Redis with optional progress information."""
    task_data = redis_client.get(f"task:{task_id}")
    if task_data:
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
        if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            data["completed_at"] = datetime.utcnow().isoformat()
            # Clear progress info on completion
            data["progress"] = None
            data["download_speed"] = None
            data["eta"] = None
        redis_client.setex(f"task:{task_id}", 86400, json.dumps(data))


def get_aria2_client() -> Optional[aria2p.API]:
    """Initialize and return aria2 RPC client, or None if unavailable."""
    try:
        # Parse the aria2 RPC URL to extract host and port
        # Expected format: http://aria2:6800/jsonrpc
        # Strip any protocol prefix
        url_clean = settings.aria2_rpc_url.replace("http://", "").replace("https://", "")
        host_port = url_clean.split("/")[0]
        
        if ":" in host_port:
            host, port_str = host_port.split(":", 1)
            port = int(port_str)
        else:
            host = host_port
            port = 6800
        
        # Always use HTTP (not HTTPS) for local aria2 RPC connection
        aria2 = aria2p.API(
            aria2p.Client(
                host=f"http://{host}",
                port=port,
                secret=settings.aria2_rpc_secret
            )
        )
        
        # Test connection
        aria2.get_global_options()
        print(f"aria2 connected successfully to {host}:{port}")
        return aria2
    except Exception as e:
        print(f"aria2 connection failed to {settings.aria2_rpc_url}: {e}")
        return None


def format_speed(speed_bytes: int) -> str:
    """Format speed in bytes/sec to human readable string."""
    if speed_bytes < 1024:
        return f"{speed_bytes} B/s"
    elif speed_bytes < 1024 ** 2:
        return f"{speed_bytes / 1024:.2f} KB/s"
    elif speed_bytes < 1024 ** 3:
        return f"{speed_bytes / (1024 ** 2):.2f} MB/s"
    else:
        return f"{speed_bytes / (1024 ** 3):.2f} GB/s"


def format_time(seconds: int) -> str:
    """Format seconds to human readable time string."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def download_with_aria2(task_id: str, url: str, filepath: Path) -> bool:
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


class DownloadTask(Task):
    autoretry_for = (httpx.HTTPError, ConnectionError)
    retry_kwargs = {"max_retries": settings.max_retries}
    retry_backoff = True


@app.task(bind=True, base=DownloadTask, name="worker.tasks.download.process_download")
def process_download(self, task_id: str, url: str, filename: str):
    """Process download using aria2 with httpx fallback."""
    task_dir = Path(settings.storage_path) / task_id
    task_dir.mkdir(parents=True, exist_ok=True)  # Both containers run as same user
    filepath = task_dir / filename

    try:
        update_task_status(task_id, TaskStatus.DOWNLOADING, progress=0)

        # Try aria2 first
        aria2_success = download_with_aria2(task_id, url, filepath)

        # Fallback to httpx if aria2 fails and fallback is enabled
        if not aria2_success:
            if settings.aria2_enable_fallback:
                print(f"aria2 failed for {task_id}, falling back to httpx")
                download_with_httpx(task_id, url, filepath)
            else:
                raise Exception("aria2 download failed and fallback is disabled")

        # Verify file was downloaded
        if not filepath.exists() or filepath.stat().st_size == 0:
            raise Exception("Downloaded file is missing or empty")

        update_task_status(task_id, TaskStatus.UPLOADING, progress=100)

        upload_to_webdav(filepath, filename)

        update_task_status(task_id, TaskStatus.COMPLETED)

    except Exception as e:
        error_msg = str(e)
        update_task_status(task_id, TaskStatus.FAILED, error=error_msg)
        raise

    finally:
        if task_dir.exists():
            shutil.rmtree(task_dir, ignore_errors=True)
