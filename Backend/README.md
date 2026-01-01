# 🚀 Transloader Engine

Asynchronous file transfer service with WebDAV support and aria2 powered downloads.

## Features

- ✅ Async download/upload pipeline with **aria2** multi-connection downloads
- ✅ API-based job submission
- ✅ Redis queue + Celery workers
- ✅ WebDAV (Nextcloud) integration
- ✅ **Real-time progress tracking** (%, speed, ETA)
- ✅ **BitTorrent & magnet link support**
- ✅ **Auto-resume capability**
- ✅ Private IP protection
- ✅ Auto-retry on failure
- ✅ Job history (last 100 jobs)
- ✅ Automatic fallback to httpx if aria2 unavailable

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
  "status": "DOWNLOADING",
  "url": "https://example.com/video.mp4",
  "filename": "my-video.mp4",
  "created_at": "2024-12-27T10:30:00Z",
  "completed_at": null,
  "error": null,
  "progress": 45.67,
  "download_speed": "12.5 MB/s",
  "eta": "2m 15s"
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
                              aria2 (multi-connection)
                                      ↓
                              Temp Storage (auto-cleanup)
```

**Services:**
- **web**: FastAPI application (API server)
- **worker**: Celery workers (download/upload processing)
- **redis**: Task queue and state storage
- **aria2**: Download daemon with RPC interface
ARIA2_RPC_SECRET` | aria2 RPC authentication | `change-me-aria2-secret` |
| `ARIA2_MAX_CONNECTIONS` | Connections per download | 16 |
| `ARIA2_SPLIT` | Pieces to split each download | 16 |
| `ARIA2_MAX_CONCURRENT_DOWNLOADS` | Parallel downloads | 5 |
| `NEXTCLOUD_USERNAME` | WebDAV username | Required |
| `NEXTCLOUD_PASSWORD` | WebDAV password | Required |
| `WEBDAV_URL` | WebDAV endpoint | Required |
| `MAX_FILE_SIZE_GB` | Max file size limit | 5 |
| `CELERY_WORKER_CONCURRENCY` | Parallel worker
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

### aria2 connection issues
- Check aria2 service: `docker-compose logs aria2`
- Verify RPC_SECRET matches in `.env`
- System will fallback to httpx automatically

### WebDAV upload fails
- Verify credentials in `.env`
- Check WebDAV URL format (should end with `/`)
- Test WebDAV connection manually

### Slow downloads
- Increase `ARIA2_MAX_CONNECTIONS` (up to 16)
- Increase `ARIA2_SPLIT` for large files
- Check network bandwidth limits
x] ~~Progress tracking (download %)~~ ✅ Implemented
- [x] ~~Resume incomplete downloads~~ ✅ Implemented
- [x] ~~BitTorrent support~~ ✅ Implemented
- [ ] Web UI dashboard
- [ ] PostgreSQL persistence
- [ ] Multi-worker scaling
## Advanced: BitTorrent Downloads

aria2 automatically handles torrent files and magnet links:

```bash
# Submit torrent file URL
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/file.torrent"}'

# Submit magnet link
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"url": "magnet:?xt=urn:btih:..."}'
``

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