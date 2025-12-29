from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from shared.config import get_settings
from web.api.v1 import jobs, health
import os

app = FastAPI(
    title="Transloader Engine API Hey there!!! 😃",
    version="1.0.0",
    description="Asynchronous file transfer service"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
async def root():
    """Redirect to dashboard"""
    from fastapi.responses import FileResponse
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
