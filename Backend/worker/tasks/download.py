from pathlib import Path
import shutil
import zipfile

from celery import Task
import httpx

from worker.celery_app import app
from shared.config import get_settings
from shared.enums import TaskStatus
from worker.tasks.upload import upload_to_webdav
from worker.tasks.status import update_task_status
from worker.tasks.aria2.direct_download import download_file_aria2, download_with_httpx
from worker.tasks.aria2.torrent_download import download_torrent_aria2, sanitize_filename

settings = get_settings()

class DownloadTask(Task):
    autoretry_for = (httpx.HTTPError, ConnectionError)
    retry_kwargs = {"max_retries": settings.max_retries}
    retry_backoff = True

# check whether direct link or torrent/magnet
def link_type(url: str) -> str:
    if url.startswith("magnet:"):
        return "magnet"
    elif url.endswith(".torrent"):
        return "torrent"
    elif url.startswith("http://") or url.startswith("https://") :
        return "direct"
    else:
        return "unknown"

@app.task(bind=True, base=DownloadTask, name="worker.tasks.download.process_download")
def process_download(self, task_id: str, url: str, filename: str):
    """Process download using aria2 with httpx fallback."""
    task_dir = Path(settings.storage_path) / task_id
    task_dir.mkdir(parents=True, exist_ok=True)  # Both containers run as same user
    filepath = task_dir / filename

    # check link type
    l_type = link_type(url)

    if l_type == "direct":
        print(f"Processing direct link download for task {task_id}")

        try:
            update_task_status(task_id, TaskStatus.DOWNLOADING, progress=0)

            # Try aria2 first
            aria2_success = download_file_aria2(task_id, url, filepath)

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

    elif l_type in ['magnet', 'torrent']:
        '''Process magnet/torrent link download using aria2'''
        print(f"Processing {l_type} link download for task {task_id}")
        
        try:
            update_task_status(task_id, TaskStatus.DOWNLOADING, progress=0)
            
            is_magnet = (l_type == 'magnet')
            success, downloaded_files, torrent_name = download_torrent_aria2(task_id, url, task_dir, is_magnet)
            
            if not success or not downloaded_files:
                raise Exception(f"{l_type} download failed")
            
            update_task_status(task_id, TaskStatus.UPLOADING, progress=100)
            
            # Determine final filename
            if filename and filename != f"download_{task_id[:8]}":
                # User provided a custom filename
                final_name = filename
            elif torrent_name:
                # Use torrent's actual name
                final_name = sanitize_filename(torrent_name)
            else:
                # Fallback to task ID
                final_name = f"torrent_{task_id[:8]}"
            
            # Handle single or multiple files
            if len(downloaded_files) == 1:
                # Single file - upload directly
                file_to_upload = downloaded_files[0]
                # Preserve original extension if exists
                original_ext = file_to_upload.suffix
                if original_ext and not final_name.endswith(original_ext):
                    upload_filename = f"{final_name}{original_ext}"
                else:
                    upload_filename = final_name
                upload_to_webdav(file_to_upload, upload_filename)
            else:
                # Multiple files - create zip archive
                zip_path = task_dir / f"{final_name}.zip"
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in downloaded_files:
                        # Preserve relative path structure
                        arcname = file_path.relative_to(task_dir)
                        zipf.write(file_path, arcname)
                
                upload_to_webdav(zip_path, f"{final_name}.zip")
            
            update_task_status(task_id, TaskStatus.COMPLETED)
            
        except Exception as e:
            error_msg = str(e)
            update_task_status(task_id, TaskStatus.FAILED, error=error_msg)
            raise
            
        finally:
            if task_dir.exists():
                shutil.rmtree(task_dir, ignore_errors=True)
    
    else:
        error_msg = f"Unsupported URL type: {l_type}"
        update_task_status(task_id, TaskStatus.FAILED, error=error_msg)
        raise ValueError(error_msg)