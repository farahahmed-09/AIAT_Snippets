# Systemd Service Files

This directory contains systemd service files and management scripts for running the Snippets application as background services.

## Services

### 1. `snippets-celery.service`

- **Description**: Celery worker for background task processing
- **Dependencies**: Redis Docker container (managed by the script)
- **Queues**: `main-queue`, `video-queue`
- **Log Location**: `/var/log/celery/snippets-celery.log`
- **PID File**: `/var/run/celery/snippets-celery.pid`

### 2. `snippets-beat.service`

- **Description**: Celery Beat scheduler for periodic tasks
- **Dependencies**: Redis, Celery worker
- **Scheduled Tasks**: Storage cleanup (2 AM), Cache maintenance (3 AM)
- **Logs**: Viewable via `journalctl -u snippets-beat.service`

### 3. `snippets-api.service`

- **Description**: FastAPI application server
- **Port**: 8000
- **Dependencies**: Redis Docker container (managed by the script)
- **Optional**: Celery worker (for background tasks)

### 4. `snippets-frontend.service`

- **Description**: Frontend (Vite dev server)
- **Port**: 5173 (internal)
- **Dependencies**: Node.js/npm

## Quick Start

### Install and Start Services

```bash
# Make the management script executable (already done)
chmod +x systemd/manage-services.sh

# Install services (requires sudo)
./systemd/manage-services.sh install

# Start all services
./systemd/manage-services.sh start

# Check status
./systemd/manage-services.sh status
```

The install step also configures Nginx using `systemd/nginx-snippets-dev.conf`
and reloads the Nginx service.

### Access the Application

Once services are running:

- **Frontend**: http://localhost:1107 (via Nginx reverse proxy)
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Management Commands

### Service Control

```bash
# Start services
./systemd/manage-services.sh start

# Stop services
./systemd/manage-services.sh stop

# Restart services
./systemd/manage-services.sh restart

# Check status
./systemd/manage-services.sh status
```

### View Logs

```bash
# Celery worker logs
./systemd/manage-services.sh logs celery

# FastAPI application logs
./systemd/manage-services.sh logs api

# Frontend logs
./systemd/manage-services.sh logs frontend

# Redis logs
./systemd/manage-services.sh logs redis
```

### Uninstall Services

```bash
# Stop, disable, and remove all services
./systemd/manage-services.sh uninstall
```

## Service Behavior

### Auto-Start on Boot

All services are configured to start automatically when the system boots.

### Auto-Restart

Services will automatically restart if they crash or fail.

### Dependency Management

- Celery worker requires Redis to be running
- FastAPI application requires Redis to be running
- If Redis is down, Celery and the API will error until Redis is back

## Troubleshooting

### Check Service Status

```bash
# Individual service status
sudo systemctl status snippets-celery.service
sudo systemctl status snippets-api.service
sudo systemctl status snippets-frontend.service
docker ps -a --filter "name=^/redis$"
```

### View Recent Logs

```bash
# Last 50 lines of Celery logs
sudo journalctl -u snippets-celery.service -n 50

# Last 50 lines of API logs
sudo journalctl -u snippets-api.service -n 50

# Follow logs in real-time
sudo journalctl -u snippets-api.service -f
```

### Manually Start/Stop Services

```bash
# Start individual service
sudo systemctl start snippets-celery.service
sudo systemctl start snippets-api.service
sudo systemctl start snippets-frontend.service

# Stop individual service
sudo systemctl stop snippets-celery.service
sudo systemctl stop snippets-api.service
sudo systemctl stop snippets-frontend.service

# Restart individual service
sudo systemctl restart snippets-celery.service
sudo systemctl restart snippets-api.service
sudo systemctl restart snippets-frontend.service
```

### Reload Service Configuration

If you modify the service files:

```bash
# Copy updated files
sudo cp systemd/snippets-celery.service /etc/systemd/system/
sudo cp systemd/snippets-api.service /etc/systemd/system/
sudo cp systemd/snippets-frontend.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Restart services
./systemd/manage-services.sh restart
```

### Check Redis Connection

```bash
# Test Redis connection
redis-cli -p 6379 ping

# Should return: PONG
```

## File Locations

- **Service Files**: `/etc/systemd/system/snippets-*.service`
- **Celery Logs**: `/var/log/celery/snippets-celery.log`
- **Celery PID**: `/var/run/celery/snippets-celery.pid`
- **API Logs**: View with `journalctl -u snippets-api.service`

## Requirements

- **User**: `sprints-rd` (services run as this user)
- **Conda Environment**: `snippets` at `/mnt/conda_env/snippets`
- **Project Directory**: `/home/sprints-rd/AIAT_Snippets`
- **Docker**: Required for the Redis container
- **Node.js/npm**: Required for the frontend service
- **Nginx**: Required for reverse proxy on port 1107
- **Redis**: Docker container named `redis` running on port 6379

## Notes

- Services run as the `sprints-rd` user
- The Celery worker runs in detached mode
- Logs are automatically rotated by systemd
- All services have automatic restart enabled
- Nginx config is installed to `/etc/nginx/conf.d/snippets-dev.conf` for dev proxying
