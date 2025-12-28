from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import JSONResponse
from shared.config import get_settings
from web.api.v1 import jobs, health

app = FastAPI(
    title="Transloader Engine API",
    version="1.0.0",
    description="Asynchronous file transfer service"
)

settings = get_settings()


async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


# Include routers
app.include_router(
    health.router,
    prefix="/api/v1",
    tags=["health"]
)

app.include_router(
    jobs.router,
    prefix="/api/v1",
    tags=["jobs"],
    dependencies=[Depends(verify_api_key)]
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
