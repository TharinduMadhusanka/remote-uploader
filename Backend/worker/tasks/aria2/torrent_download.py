# imports
import time
from pathlib import Path
from typing import Optional

from shared.config import get_settings
from shared.enums import TaskStatus

from worker.tasks.status import update_task_status

from .client import get_aria2_client, format_speed, format_time

settings = get_settings()

def get_torrent_name(download) -> Optional[str]:
    """Extract torrent name from aria2 download object."""
    try:
        # Try to get the name from bittorrent info
        if hasattr(download, 'bittorrent') and download.bittorrent:
            bt_info = download.bittorrent
            if hasattr(bt_info, 'info') and bt_info.info:
                name = getattr(bt_info.info, 'name', None)
                if name:
                    return name
        
        # Fallback: check if files exist and use parent directory name
        if download.files:
            first_file = Path(download.files[0].path)
            # If file is in a subdirectory, use that directory name
            relative_to_dir = first_file.relative_to(download.dir)
            if len(relative_to_dir.parts) > 1:
                return relative_to_dir.parts[0]
            # Otherwise use the filename without extension
            return first_file.stem
        
        return None
    except Exception as e:
        print(f"Error extracting torrent name: {e}")
        return None

def derive_torrent_name(task_dir: Path, downloaded_files: list[Path]) -> str:
    """Derive a sensible base name for a torrent when user didn't provide one.

    - Single file: use the file's name
    - Multiple files: try to use the top-level folder name; fallback to task dir name
    """
    if not downloaded_files:
        return task_dir.name

    if len(downloaded_files) == 1:
        return downloaded_files[0].name

    roots: list[str] = []
    for p in downloaded_files:
        try:
            rel = p.relative_to(task_dir)
            root = rel.parts[0] if rel.parts else p.name
        except Exception:
            root = p.name
        if root not in roots:
            roots.append(root)

    if roots:
        return roots[0]

    return task_dir.name


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing/replacing invalid characters."""
    # Replace spaces and special characters
    filename = filename.replace(' ', '_')
    # Remove characters that might cause issues
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '')
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    return filename

def download_torrent_aria2(task_id: str, url: str, download_dir: Path, is_magnet: bool = False) -> tuple[bool, list[Path], Optional[str]]:
    """
    Download torrent or magnet link using aria2.
    Returns (success, list of downloaded file paths, torrent_name).
    """
    aria2 = get_aria2_client()
    if not aria2:
        print(f"aria2 client unavailable for task {task_id}")
        return False, [], None

    try:
        options = {
            "dir": str(download_dir),
            "max-connection-per-server": str(settings.aria2_max_connections),
            "split": str(settings.aria2_split),
            "continue": "true",
            "max-tries": str(settings.max_retries),
            "bt-max-peers": "50",
            "seed-time": "0",  # Don't seed after download
            "follow-torrent": "true",
        }

        print(f"aria2 starting {'magnet' if is_magnet else 'torrent'} download: {url}")
        
        if is_magnet:
            download = aria2.add_magnet(url, options=options)
        else:
            download = aria2.add_torrent(url, options=options)
            
        print(f"aria2 torrent added, GID: {download.gid}")

        # Monitor initial download progress (magnet metadata or direct torrent)
        while not download.is_complete:
            download.update()

            if download.has_failed:
                error_msg = download.error_message or "Unknown aria2 error"
                print(f"aria2 torrent download failed: {error_msg}")
                update_task_status(task_id, TaskStatus.FAILED, error=error_msg)
                return False, [], None

            if download.total_length > 0:
                progress = (download.completed_length / download.total_length) * 100
                speed = format_speed(download.download_speed)

                if download.download_speed > 0:
                    remaining_bytes = download.total_length - download.completed_length
                    eta_seconds = remaining_bytes // download.download_speed
                    eta = format_time(eta_seconds)
                else:
                    eta = "calculating..."

                num_seeders = getattr(download, 'num_seeders', 0)
                connections = getattr(download, 'connections', 0)

                print(f"Progress: {progress:.1f}% | Speed: {speed} | Peers: {connections} | Seeders: {num_seeders}")

                update_task_status(
                    task_id,
                    TaskStatus.DOWNLOADING,
                    progress=round(progress, 2),
                    download_speed=f"{speed} ({connections} peers)",
                    eta=eta
                )

            time.sleep(2)

        download.update()

        if download.is_complete and not download.has_failed:
            downloaded_files: list[Path] = []
            torrent_name = None
            
            # Get torrent name early if available
            torrent_name = get_torrent_name(download)
            
            # Collect files from current download
            for file in download.files:
                file_path = Path(file.path)
                if file_path.exists():
                    downloaded_files.append(file_path)

            # Handle magnet links that spawn a new download after metadata
            if is_magnet and len(downloaded_files) == 0:
                print("Magnet metadata stage complete; locating auto-spawned torrent download")

                spawned = None
                wait_deadline = time.time() + 30
                
                while time.time() < wait_deadline and spawned is None:
                    try:
                        download.update()
                    except Exception:
                        pass

                    spawned_ids = getattr(download, 'followed_by_ids', None) or []
                    if spawned_ids:
                        try:
                            spawned = aria2.get_download(spawned_ids[0])
                        except Exception:
                            spawned = None

                    if spawned is None:
                        try:
                            for d in aria2.get_downloads():
                                if d.gid != download.gid and d.dir == str(download_dir):
                                    spawned = d
                                    break
                        except Exception:
                            pass

                    if spawned is None:
                        time.sleep(1)

                if spawned is None:
                    print("No spawned torrent detected after metadata; no files to download")
                    return False, [], torrent_name
                else:
                    # Get torrent name from spawned download if not already set
                    if not torrent_name:
                        torrent_name = get_torrent_name(spawned)
                    
                    # Track spawned download progress
                    while not spawned.is_complete:
                        spawned.update()

                        if spawned.has_failed:
                            error_msg = spawned.error_message or "Spawned torrent download failed"
                            print(f"aria2 spawned torrent failed: {error_msg}")
                            update_task_status(task_id, TaskStatus.FAILED, error=error_msg)
                            return False, [], torrent_name

                        if spawned.total_length > 0:
                            progress = (spawned.completed_length / spawned.total_length) * 100
                            speed = format_speed(spawned.download_speed)

                            if spawned.download_speed > 0:
                                remaining_bytes = spawned.total_length - spawned.completed_length
                                eta_seconds = remaining_bytes // spawned.download_speed
                                eta = format_time(eta_seconds)
                            else:
                                eta = "calculating..."

                            num_seeders = getattr(spawned, 'num_seeders', 0)
                            connections = getattr(spawned, 'connections', 0)

                            print(f"Progress: {progress:.1f}% | Speed: {speed} | Peers: {connections} | Seeders: {num_seeders}")

                            update_task_status(
                                task_id,
                                TaskStatus.DOWNLOADING,
                                progress=round(progress, 2),
                                download_speed=f"{speed} ({connections} peers)",
                                eta=eta
                            )

                        time.sleep(2)

                    spawned.update()
                    # Collect files from spawned download
                    for f in spawned.files:
                        fpath = Path(f.path)
                        if fpath.exists():
                            downloaded_files.append(fpath)

            print(f"aria2 torrent download completed: {len(downloaded_files)} files (name: {torrent_name})")
            return (len(downloaded_files) > 0), downloaded_files, torrent_name
        else:
            error_msg = download.error_message or "Torrent download failed"
            print(f"aria2 torrent failed: {error_msg}")
            update_task_status(task_id, TaskStatus.FAILED, error=error_msg)
            return False, [], None

    except Exception as e:
        print(f"aria2 torrent exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False, [], None