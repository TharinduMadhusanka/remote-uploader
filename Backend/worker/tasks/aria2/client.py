from __future__ import annotations

from typing import Optional

import aria2p

from shared.config import get_settings

settings = get_settings()

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