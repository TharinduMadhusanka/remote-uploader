# Setup Instructions

## Initial Setup

### 1. Configure Environment
```bash
cp .env.example .env
# Edit .env with your credentials
nano .env
```

### 2. Start Services
```bash
docker compose up -d --build
```

**That's it!** No manual permission fixes needed.

### 3. Verify Health
```bash
# Check all services are running
docker compose ps

# Should show all services as "Up" and redis/aria2 as "healthy"
```

## Why This Solution Works

The system uses **Docker-managed volumes** instead of bind mounts:
- `storage_data` volume: Automatically created and managed by Docker
- Docker handles all permissions internally
- Both aria2 and worker run as UID 1000 and share the volume seamlessly

**Benefits:**
✅ Zero manual permission configuration  
✅ Works identically on any OS (Linux, Mac, Windows)  
✅ Production-ready and cloud-compatible  
✅ Survives container restarts  
✅ Can be backed up with docker commands  

Both **aria2** and **worker** containers run as the same user (UID 1000):
- aria2 configured with `PUID=1000` and `PGID=1000`
- worker Dockerfile creates and switches to `appuser` with UID 1000
- docker-compose sets `user: "1000:1000"` for worker

This ensures:
✅ No permission conflicts when sharing storage volume  
✅ Both containers can read/write downloaded files  
✅ Secure (non-root)  
✅ Works on any cloud provider or home server  
✅ Scalable for multiple workers

## Troubleshooting

### aria2 Connection Failed

Check aria2 service is healthy:
```bash
docker compose ps aria2
docker compose logs aria2
```

### Worker Can't Connect to aria2

Verify network connectivity:
```bash
docker compose exec worker ping -c 2 aria2
```

## Volume Management

### Backup Storage Data
```bash
# Create backup of storage volume
docker run --rm -v backend_storage_data:/data -v $(pwd):/backup alpine tar czf /backup/storage-backup.tar.gz -C /data .
```

### Restore Storage Data
```bash
# Restore from backup
docker run --rm -v backend_storage_data:/data -v $(pwd):/backup alpine tar xzf /backup/storage-backup.tar.gz -C /data
```

### Inspect Volume
```bash
# See wheres**: Docker-managed volumes work identically in cloud
   - ECS: Use EFS or EBS volumes mapped to volume names
   - Kubernetes: Use PersistentVolumeClaims
   - Cloud Run: Not suitable (stateless), use Cloud Storage
   
2. **Environment variables**: Set via cloud secrets manager
3. **Networking**: Ensure containers can communicate (default works)
4. **Scaling**: Can run multiple worker containers sharing same volumes

Example for AWS ECS:
```json
{
  "volumes": [{
    "name": "storage_data",
    "efsVolumeConfiguration": {
      "fileSystemId": "fs-xxxxx"
    }
  }]
}
```

Example for Kubernetes:
```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: storage-data
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 100Gi
```
docker compose down -v  # Remove volumes
```

## Cloud Deployment Notes

When deploying to cloud (AWS, GCP, Azure, etc.):

1. **Volume permissions**: Ensure mounted volumes have permissions for UID 1000
2. **Environment variables**: Set all required vars in `.env` or cloud secrets
3. **Networking**: Ensure containers can communicate (default Docker network works)
4. **Storage**: Consider using persistent volumes/EBS/Cloud Storage for `/app/storage`

Example for AWS ECS or similar:
- Use EFS or EBS volume mounted to `/app/storage`
- Set volume permissions: `sudo chown -R 1000:1000 /mnt/efs/storage`
- Configure task definition to run containers as UID 1000
