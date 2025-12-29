# 🚀 Transloader Engine

Asynchronous file transfer service with WebDAV support (Phase 1).

## Features

- ✅ Async download/upload pipeline
- ✅ API-based job submission
- ✅ Redis queue + Celery workers
- ✅ WebDAV (Nextcloud) integration
- ✅ Private IP protection
- ✅ Auto-retry on failure
- ✅ Job history (last 100 jobs)

## Quick Start

### 1. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
nano .env
```

### 2. Start Services

```bash
# Build and start all containers
docker-compose up -d

# Check logs
docker-compose logs -f
```

### 3. Test API

```bash
# Health check (no auth required)
curl http://localhost:8000/api/v1/health

# Submit job (requires API key)
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "X-API-Key: your-secret-api-key-change-this" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/file.zip"}'

# Check status
curl http://localhost:8000/api/v1/jobs/{job_id} \
  -H "X-API-Key: your-secret-api-key-change-this"

# List all jobs
curl http://localhost:8000/api/v1/jobs \
  -H "X-API-Key: your-secret-api-key-change-this"
```

## API Reference

### Authentication
All endpoints (except `/health`) require API key:
```
X-API-Key: your-secret-key
```

### Endpoints

#### `POST /api/v1/jobs`
Submit new download job.

**Request:**
```json
{
  "url": "https://example.com/video.mp4",
  "rename_to": "my-video.mp4"  // optional
}
```

**Response (201):**
```json
{
  "id": "abc-123",
  "status": "PENDING",
  "url": "https://example.com/video.mp4",
  "filename": "my-video.mp4",
  "created_at": "2024-12-27T10:30:00Z",
  "completed_at": null,
  "error": null
}
```

#### `GET /api/v1/jobs/{id}`
Get job status.

**Response (200):**
```json
{
  "id": "abc-123",
  "status": "COMPLETED",
  "url": "https://example.com/video.mp4",
  "filename": "my-video.mp4",
  "created_at": "2024-12-27T10:30:00Z",
  "completed_at": "2024-12-27T10:35:00Z",
  "error": null
}
```

#### `GET /api/v1/jobs?status=COMPLETED&limit=20`
List jobs (last 100 stored).

**Response (200):**
```json
{
  "jobs": [...],
  "total": 15
}
```

#### `DELETE /api/v1/jobs/{id}`
Cancel pending/running job.

**Response (200):**
```json
{
  "message": "Job cancelled"
}
```

#### `GET /api/v1/health`
Health check (no auth required).

**Response (200):**
```json
{
  "status": "ok",
  "redis": "healthy"
}
```

## Job Status Flow

```
PENDING → DOWNLOADING → UPLOADING → COMPLETED
             ↓              ↓
          FAILED         FAILED
```

## Architecture

```
User → FastAPI → Redis Queue → Celery Worker → WebDAV
                                      ↓
                              Temp Storage (auto-cleanup)
```

## Configuration

Edit `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `API_KEY` | API authentication key | Required |
| `NEXTCLOUD_USERNAME` | WebDAV username | Required |
| `NEXTCLOUD_PASSWORD` | WebDAV password | Required |
| `WEBDAV_URL` | WebDAV endpoint | Required |
| `MAX_FILE_SIZE_GB` | Max file size limit | 5 |
| `CELERY_WORKER_CONCURRENCY` | Parallel downloads | 2 |
| `DOWNLOAD_TIMEOUT` | Download timeout (seconds) | 3600 |
| `MAX_RETRIES` | Auto-retry attempts | 3 |

## Folder Structure

```
transloader-engine/
├── docker-compose.yml
├── .env
├── shared/              # Shared code (web + worker)
│   ├── config.py
│   ├── enums.py
│   └── models.py
├── web/                 # FastAPI service
│   ├── Dockerfile
│   ├── main.py
│   └── api/v1/
├── worker/              # Celery worker
│   ├── Dockerfile
│   ├── celery_app.py
│   └── tasks/
└── storage/             # Temp downloads (auto-cleanup)
```

## Development

```bash
# Rebuild after code changes
docker-compose up -d --build

# View worker logs
docker-compose logs -f worker

# View API logs
docker-compose logs -f web

# Stop all services
docker-compose down

# Stop and remove volumes (clears Redis data)
docker-compose down -v
```

## Troubleshooting

### Job stuck in PENDING
- Check worker logs: `docker-compose logs worker`
- Verify Redis connection: `curl http://localhost:8000/api/v1/health`

### WebDAV upload fails
- Verify credentials in `.env`
- Check WebDAV URL format (should end with `/`)
- Test WebDAV connection manually

### Out of disk space
- Temp files are auto-deleted after upload
- Check storage: `docker-compose exec worker df -h`

## Next Phase (Future)

- [ ] Telegram upload support
- [ ] Google Drive integration
- [ ] S3 upload support
- [ ] Progress tracking (download %)
- [ ] Web UI dashboard
- [ ] PostgreSQL persistence
- [ ] Multi-worker support
- [ ] Resume incomplete downloads

## License

MIT


## How to use

ssh -i "privatekey" -L 8000:localhost:8000 usename@serverip