#!/bin/bash

# Snippets Service Management Script
# This script helps install, start, stop, and manage the Snippets services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

function print_error() {
    echo -e "${RED}✗ $1${NC}"
}

function print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

function require_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        print_error "Docker is not installed or not in PATH."
        print_info "Install Docker, then retry."
        exit 1
    fi
}

function require_nginx() {
    if ! command -v nginx >/dev/null 2>&1; then
        print_error "Nginx is not installed or not in PATH."
        print_info "Install Nginx, then retry."
        exit 1
    fi
}

function check_redis() {
    print_info "Checking Redis (Docker container: redis)..."
    require_docker

    # Is container running?
    if docker ps --format '{{.Names}}' | grep -qx "redis"; then
        # Optional: verify port is reachable locally
        if command -v redis-cli >/dev/null 2>&1; then
            if redis-cli -h 127.0.0.1 -p 6379 ping >/dev/null 2>&1; then
                print_success "Redis container is running and reachable on 127.0.0.1:6379"
                return 0
            else
                print_error "Redis container is running but not responding on 127.0.0.1:6379"
                print_info "Check container logs: $0 logs redis"
                return 1
            fi
        else
            print_success "Redis container is running (redis-cli not found; skipping ping check)"
            return 0
        fi
    else
        print_error "Redis container is not running"
        return 1
    fi
}

function ensure_redis() {
    require_docker

    if check_redis; then
        return 0
    fi

    print_info "Ensuring Redis container exists and is running..."

    # If container exists (stopped), start it
    if docker ps -a --format '{{.Names}}' | grep -qx "redis"; then
        print_info "Starting existing Redis container..."
        docker start redis >/dev/null
        print_success "Redis container started"
    else
        print_info "Creating and starting Redis container..."
        docker run -d -p 6379:6379 --name redis redis:latest >/dev/null
        print_success "Redis container created and started"
    fi

    # Re-check
    if check_redis; then
        return 0
    else
        print_error "Redis container still not healthy."
        print_info "Try: docker logs redis"
        return 1
    fi
}

function install_services() {
    print_info "Installing Snippets services..."

    # Ensure Redis is running
    ensure_redis

    # Copy service files to systemd directory
    print_info "Copying service files to /etc/systemd/system/..."
    sudo cp "$SCRIPT_DIR/snippets-celery.service" /etc/systemd/system/
    sudo cp "$SCRIPT_DIR/snippets-beat.service" /etc/systemd/system/
    sudo cp "$SCRIPT_DIR/snippets-api.service" /etc/systemd/system/
    sudo cp "$SCRIPT_DIR/snippets-frontend.service" /etc/systemd/system/

    # Configure nginx reverse proxy
    require_nginx
    sudo mkdir -p /etc/nginx/conf.d
    sudo cp "$SCRIPT_DIR/nginx-snippets-dev.conf" /etc/nginx/conf.d/snippets-dev.conf
    print_info "Configuring Nginx reverse proxy..."
    if sudo systemctl is-active --quiet nginx; then
        sudo systemctl reload nginx
    else
        sudo systemctl start nginx
    fi

    # Reload systemd daemon
    print_info "Reloading systemd daemon..."
    sudo systemctl daemon-reload

    # Enable services to start on boot
    print_info "Enabling services to start on boot..."
    sudo systemctl enable snippets-celery.service
    sudo systemctl enable snippets-beat.service
    sudo systemctl enable snippets-api.service
    sudo systemctl enable snippets-frontend.service

    print_success "Services installed successfully!"

    # Start services after installation
    start_services
}

function uninstall_services() {
    print_info "Uninstalling Snippets services..."

    # Stop services
    sudo systemctl stop snippets-celery.service 2>/dev/null || true
    sudo systemctl stop snippets-beat.service 2>/dev/null || true
    sudo systemctl stop snippets-api.service 2>/dev/null || true
    sudo systemctl stop snippets-frontend.service 2>/dev/null || true

    # Disable services
    sudo systemctl disable snippets-celery.service 2>/dev/null || true
    sudo systemctl disable snippets-beat.service 2>/dev/null || true
    sudo systemctl disable snippets-api.service 2>/dev/null || true
    sudo systemctl disable snippets-frontend.service 2>/dev/null || true

    # Remove service files
    sudo rm -f /etc/systemd/system/snippets-celery.service
    sudo rm -f /etc/systemd/system/snippets-beat.service
    sudo rm -f /etc/systemd/system/snippets-api.service
    sudo rm -f /etc/systemd/system/snippets-frontend.service
    sudo rm -f /etc/nginx/conf.d/snippets-dev.conf

    # Reload systemd daemon
    sudo systemctl daemon-reload

    if command -v nginx >/dev/null 2>&1; then
        if sudo systemctl is-active --quiet nginx; then
            sudo systemctl reload nginx
        fi
    fi

    print_success "Services uninstalled successfully!"
}

function start_services() {
    print_info "Starting Snippets services..."

    # Ensure Redis is running
    ensure_redis

    # Start Nginx reverse proxy
    if command -v nginx >/dev/null 2>&1; then
        print_info "Starting Nginx reverse proxy..."
        sudo systemctl start nginx
        print_success "Nginx started"
    fi

    # Start Celery worker
    print_info "Starting Celery worker..."
    sudo systemctl start snippets-celery.service
    print_success "Celery worker started"

    # Start Celery Beat scheduler
    print_info "Starting Celery Beat scheduler..."
    sudo systemctl start snippets-beat.service
    print_success "Celery Beat scheduler started"

    # Start FastAPI application
    print_info "Starting FastAPI application..."
    sudo systemctl start snippets-api.service
    print_success "FastAPI application started"

    # Start Frontend application
    print_info "Starting Frontend application..."
    sudo systemctl start snippets-frontend.service
    print_success "Frontend application started"

    print_success "All services started successfully!"
}

function stop_services() {
    print_info "Stopping Snippets services..."

    # Stop Frontend application
    print_info "Stopping Frontend application..."
    sudo systemctl stop snippets-frontend.service
    print_success "Frontend application stopped"

    # Stop FastAPI application
    print_info "Stopping FastAPI application..."
    sudo systemctl stop snippets-api.service
    print_success "FastAPI application stopped"

    # Stop Celery worker
    print_info "Stopping Celery worker..."
    sudo systemctl stop snippets-celery.service
    print_success "Celery worker stopped"

    # Stop Celery Beat scheduler
    print_info "Stopping Celery Beat scheduler..."
    sudo systemctl stop snippets-beat.service
    print_success "Celery Beat scheduler stopped"

    print_success "All services stopped successfully!"
}

function restart_services() {
    print_info "Restarting Snippets services..."
    stop_services
    sleep 2
    start_services
}

function status_services() {
    print_info "Checking service status..."
    echo ""

    echo "=== Redis (Docker) Status ==="
    if command -v docker >/dev/null 2>&1; then
        docker ps -a --filter "name=^/redis$" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || true
        echo ""
        echo "--- Redis logs (last 30 lines) ---"
        docker logs --tail 30 redis 2>/dev/null || true
    else
        echo "Docker not installed."
    fi
    echo ""

    echo "=== Celery Worker Status ==="
    systemctl status snippets-celery.service --no-pager || true
    echo ""

    echo "=== Celery Beat Scheduler Status ==="
    systemctl status snippets-beat.service --no-pager || true
    echo ""

    echo "=== FastAPI Application Status ==="
    systemctl status snippets-api.service --no-pager || true
    echo ""

    echo "=== Frontend Application Status ==="
    systemctl status snippets-frontend.service --no-pager || true
}

function show_logs() {
    SERVICE=$1
    if [ -z "$SERVICE" ]; then
        print_error "Please specify a service: celery or api or frontend or redis"
        exit 1
    fi

    case $SERVICE in
        celery)
            sudo journalctl -u snippets-celery.service -f
            ;;
        beat)
            sudo journalctl -u snippets-beat.service -f
            ;;
        api)
            sudo journalctl -u snippets-api.service -f
            ;;
        frontend)
            sudo journalctl -u snippets-frontend.service -f
            ;;
        redis)
            require_docker
            docker logs -f redis
            ;;
        *)
        print_error "Unknown service: $SERVICE"
        print_info "Available services: celery, beat, api, frontend, redis"
        exit 1
        ;;
    esac
}

function show_help() {
    cat << EOF
Snippets Service Management Script

Usage: $0 [command]

Commands:
    install     Install and enable services to start on boot
    uninstall   Stop, disable, and remove services
    start       Start all services
    stop        Stop all services
    restart     Restart all services
    status      Show status of all services
    logs        Show logs for a specific service (celery|beat|api|frontend|redis)
    help        Show this help message

Notes:
    - Redis is managed via Docker container named: redis
    - Redis run command used if container does not exist:
      docker run -d -p 6379:6379 --name redis redis:latest

Examples:
    $0 install          # Install services
    $0 start            # Start all services
    $0 logs celery      # Show Celery worker logs
    $0 logs beat        # Show Celery Beat logs
    $0 logs frontend    # Show Frontend logs
    $0 logs redis       # Show Redis container logs
    $0 status           # Check status of all services

EOF
}

# Main script logic
case "${1:-}" in
    install)
        install_services
        ;;
    uninstall)
        uninstall_services
        ;;
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        status_services
        ;;
    logs)
        show_logs "$2"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: ${1:-}"
        echo ""
        show_help
        exit 1
        ;;
esac
