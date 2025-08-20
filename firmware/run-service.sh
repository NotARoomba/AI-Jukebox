#!/bin/bash

# Jukebox Firmware Service Script
# This script is designed to run as a systemd service

set -e

# Configuration
LOG_DIR="/var/log/jukebox"
PID_DIR="/var/run/jukebox"
SERVICE_DIR="/home/pi/Jukebox/firmware"
SUNO_DIR="$SERVICE_DIR/suno-api"

# Create necessary directories
mkdir -p "$LOG_DIR" "$PID_DIR"

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_DIR/jukebox.log"
}

# Cleanup function
cleanup() {
    log "Shutting down Jukebox service..."
    
    # Stop Python process
    if [ -f "$PID_DIR/main.pid" ]; then
        PID=$(cat "$PID_DIR/main.pid")
        if kill -0 "$PID" 2>/dev/null; then
            log "Stopping main.py (PID: $PID)"
            kill "$PID"
            wait "$PID" 2>/dev/null || true
        fi
        rm -f "$PID_DIR/main.pid"
    fi
    
    # Stop Suno API
    if [ -f "$PID_DIR/suno.pid" ]; then
        PID=$(cat "$PID_DIR/suno.pid")
        if kill -0 "$PID" 2>/dev/null; then
            log "Stopping Suno API (PID: $PID)"
            kill "$PID"
            wait "$PID" 2>/dev/null || true
        fi
        rm -f "$PID_DIR/suno.pid"
    fi
    
    log "Jukebox service stopped"
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Change to service directory
cd "$SERVICE_DIR" || {
    log "ERROR: Cannot change to service directory $SERVICE_DIR"
    exit 1
}

# Check if virtual environment exists
if [ ! -d "env" ]; then
    log "ERROR: Virtual environment not found. Please run setup.sh first."
    exit 1
fi

# Check if Suno API directory exists
if [ ! -d "$SUNO_DIR" ]; then
    log "ERROR: Suno API directory not found. Please run setup.sh first."
    exit 1
fi

log "Starting Jukebox service..."

# Start Suno API
log "Starting Suno API..."
cd "$SUNO_DIR"
npm install --silent > "$LOG_DIR/suno-install.log" 2>&1
npm run dev > "$LOG_DIR/suno-api.log" 2>&1 &
SUNO_PID=$!
echo "$SUNO_PID" > "$PID_DIR/suno.pid"
log "Suno API started with PID: $SUNO_PID"

# Wait a moment for Suno API to start
sleep 5

# Check if Suno API is running
if ! kill -0 "$SUNO_PID" 2>/dev/null; then
    log "ERROR: Suno API failed to start"
    exit 1
fi

# Test Suno API endpoint
for i in {1..30}; do
    if curl -s "http://localhost:3000/api/get_limit" > /dev/null 2>&1; then
        log "Suno API is responding on http://localhost:3000"
        break
    fi
    if [ $i -eq 30 ]; then
        log "ERROR: Suno API is not responding after 30 attempts"
        exit 1
    fi
    sleep 2
done

# Return to service directory
cd "$SERVICE_DIR"

# Activate virtual environment and start main.py
log "Starting main.py..."
source env/bin/activate
python main.py > "$LOG_DIR/main.log" 2>&1 &
MAIN_PID=$!
echo "$MAIN_PID" > "$PID_DIR/main.pid"
log "main.py started with PID: $MAIN_PID"

log "Jukebox service is running"
log "Suno API: http://localhost:3000"
log "Check logs in: $LOG_DIR"

# Wait for processes
wait
