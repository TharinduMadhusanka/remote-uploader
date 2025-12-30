# Transloader Engine - GitHub Copilot Instructions

## Project Overview

This is an asynchronous file transfer service (Transloader Engine) that downloads files from URLs and uploads them to WebDAV storage (Nextcloud). The architecture uses FastAPI for the web API, Celery for task queue management, and Redis for task state management.

## Architecture

- **Web Service**: FastAPI application handling API requests
- **Worker Service**: Celery workers processing download/upload tasks
- **Storage**: Redis for task queue and state management
- **Deployment**: Docker Compose for containerized services

## Code Style & Conventions

### General Python
- Use Python 3.11+ features
- Follow PEP 8 style guidelines
- Use type hints for all function parameters and return values
- Use descriptive variable names
- Keep functions focused and single-purpose
- Use async/await for I/O operations in FastAPI routes

### Import Organization
```python
# Standard library imports
import os
from pathlib import Path

# Third-party imports
from fastapi import FastAPI, HTTPException
from celery import Task
from redis import Redis

# Local imports
from shared.config import get_settings
from shared.models import JobResponse
from shared.enums import TaskStatus
```

### Models & Schemas
- Use Pydantic models for all request/response schemas
- Place shared models in `shared/models.py`
- Use enums for status fields (defined in `shared/enums.py`)
- Use `HttpUrl` type for URL validation
- Use `Optional[]` for nullable fields
- Use descriptive field names with `Field()` for validation

### Configuration
- Use Pydantic Settings for configuration (`shared/config.py`)
- All config values should have type hints
- Use `@lru_cache()` for settings singleton
- Environment variables via `.env` file
- Use `get_settings()` function to access configuration

### API Development
- Use FastAPI routers in `web/api/v1/`
- Prefix all API routes with `/api/v1`
- Use dependency injection for API key authentication
- Return appropriate HTTP status codes
- Use Pydantic models for request/response validation
- Add descriptive tags to routers
- Include error handling with HTTPException

### Example API Route Pattern
```python
@router.post("/jobs", response_model=JobResponse, status_code=201)
async def create_job(job: JobSubmit, api_key: str = Depends(verify_api_key)):
    # Implementation
    pass
```

### Celery Tasks
- Define tasks in `worker/tasks/` directory
- Use `@app.task(bind=True)` for tasks that need self reference
- Implement custom Task classes for retry logic
- Use `autoretry_for` for automatic retry on specific exceptions
- Update task status in Redis throughout task lifecycle
- Clean up temporary files in `finally` blocks
- Use `task_id` as primary identifier for tracking

### Task Status Management
- Use `TaskStatus` enum for all status values
- Store task data in Redis with 24-hour expiration
- Update status at each major step (PENDING → DOWNLOADING → UPLOADING → COMPLETED/FAILED)
- Include timestamps for created_at and completed_at
- Store error messages in task data when tasks fail

### Error Handling
- Use try-except blocks around risky operations
- Update task status to FAILED on errors
- Store error messages in Redis task data
- Log errors with context
- Clean up resources in finally blocks
- Raise exceptions after updating status for Celery retry mechanism

### File Handling
- Use `pathlib.Path` for file operations
- Create task-specific directories: `storage_path / task_id`
- Check file size limits before downloading
- Use streaming for large file downloads
- Clean up temporary files after upload completion
- Use `shutil.rmtree()` with `ignore_errors=True` for cleanup

### Redis Operations
- Use `redis_client.get()` and `redis_client.setex()` for task data
- Store task data as JSON strings
- Set expiration (86400 seconds = 24 hours) on all task keys
- Use key pattern: `task:{task_id}`
- Parse JSON when reading task data

### Security
- Require API key for all job-related endpoints (except health check)
- Use header-based authentication: `X-API-Key`
- Validate URLs to prevent SSRF attacks (add private IP checking)
- Implement file size limits
- Use environment variables for sensitive credentials
- Never commit `.env` files

### Docker & Deployment
- Use multi-stage builds when possible
- Keep Dockerfiles minimal and efficient
- Use `requirements.txt` for Python dependencies
- Define services in `docker-compose.yml`
- Use health checks for all services
- Mount volumes for persistent data and temporary storage

### Testing
- Write unit tests for business logic
- Use pytest for testing
- Mock external services (Redis, WebDAV)
- Test error handling paths
- Test retry mechanisms

## Common Patterns

### Creating a New Task
1. Define task in `worker/tasks/`
2. Use appropriate base class with retry logic
3. Update status throughout execution
4. Handle errors and update status
5. Clean up resources in finally block

### Adding a New API Endpoint
1. Create route in appropriate module in `web/api/v1/`
2. Define Pydantic models for request/response
3. Add router to main.py with appropriate prefix and tags
4. Apply authentication dependency if needed
5. Return appropriate response model

### Adding Configuration
1. Add field to Settings class in `shared/config.py`
2. Add default value or mark as required
3. Document in `.env.example`
4. Access via `get_settings()`

## File Structure Rules
- Shared code goes in `shared/` (models, config, enums)
- Web API code goes in `web/api/v1/`
- Celery tasks go in `worker/tasks/`
- Static files (HTML, JS) go in `web/static/`
- Each service has its own Dockerfile and requirements.txt

## Dependencies
- **Web**: FastAPI, uvicorn, pydantic-settings, redis
- **Worker**: Celery, httpx, webdavclient3
- **Shared**: Pydantic models and configuration

## Do Not
- Do not use synchronous I/O in FastAPI routes
- Do not commit sensitive credentials
- Do not store large files permanently (clean up after processing)
- Do not skip status updates in task execution
- Do not forget to set Redis key expiration
- Do not use bare except clauses
- Do not skip type hints
- Do not hardcode URLs or credentials

## Documentation
- Add docstrings to complex functions
- Document non-obvious business logic
- Keep README.md updated with new features
- Document environment variables in comments
- Use descriptive commit messages

## When Adding Features
1. Consider impact on both web and worker services
2. Update shared models if needed
3. Add appropriate error handling
4. Update task status tracking if applicable
5. Test with Docker Compose
6. Update documentation

## Helpful Commands
```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f [service-name]

# Rebuild after code changes
docker-compose up -d --build

# Stop services
docker-compose down

# Run tests
pytest

# Format code
black .
```

## copilot-instructions.md
- if the project change architecture or design or anyother important thing,, need to update this file accordingly.
