from webdav3.client import Client
from shared.config import get_settings
from pathlib import Path

settings = get_settings()


def upload_to_webdav(filepath: Path, filename: str):
    options = {
        'webdav_hostname': settings.webdav_url,
        'webdav_login': settings.nextcloud_username,
        'webdav_password': settings.nextcloud_password,
        'webdav_timeout': 3600
    }

    client = Client(options)
    client.verify = True

    remote_path = filename

    client.upload_sync(remote_path=remote_path, local_path=str(filepath))
