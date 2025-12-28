from fastapi import APIRouter
from redis import Redis
from shared.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check():
    try:
        redis_client = Redis.from_url(settings.redis_url)
        redis_client.ping()
        redis_status = "healthy"
    except Exception:
        redis_status = "unhealthy"

    return {
        "status": "ok" if redis_status == "healthy" else "degraded",
        "redis": redis_status
    }
