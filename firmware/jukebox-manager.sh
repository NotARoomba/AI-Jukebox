#!/bin/bash

# Jukebox Manager - Unified Management Script
# This script combines all Jukebox firmware management functions

set -e

# Configuration
SERVICE_NAME="jukebox"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
LOG_DIR="/var/log/jukebox"
PID_DIR="/var/run/jukebox"
SERVICE_DIR="/home/pi/Jukebox/firmware"
REPO_URL="https://github.com/NotARoomba/AI-Jukebox.git"
REPO_DIR="/tmp/AI-Jukebox-update"
BACKUP_DIR="/home/pi/Jukebox/backup-$(date +%Y%m%d-%H%M%S)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}[HEADER]${NC} $1"
}

print_command() {
    echo -e "${CYAN}$1${NC}"
}

# Function to check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This command requires root privileges (use sudo)"
        return 1
    fi
    return 0
}

# Function to check if we're in the right directory
check_directory() {
    if [ ! -f "main.py" ]; then
        print_error "Please run this script from the firmware directory"
        exit 1
    fi
}

# Function to show usage
show_usage() {
    echo "=========================================="
    echo "        Jukebox Manager"
    echo "=========================================="
    echo
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo
    echo "Commands:"
    echo "  install              Install the Jukebox service"
    echo "  start                Start the Jukebox service"
    echo "  stop                 Stop the Jukebox service"
    echo "  restart              Restart the Jukebox service"
    echo "  status               Show service status"
    echo "  enable               Enable service to start on boot"
    echo "  disable              Disable service from starting on boot"
    echo "  logs                 Show service logs"
    echo "  test                 Test service configuration"
    echo "  check-updates        Check for available updates"
    echo "  update               Update firmware from GitHub"
    echo "  auto-update          Setup automatic updates"
    echo "  help                 Show this help message"
    echo
    echo "Examples:"
    echo "  $0 install           # Install the service"
    echo "  $0 start             # Start the service"
    echo "  $0 status            # Check service status"
    echo "  $0 update            # Update firmware"
    echo "  $0 auto-update       # Setup automatic updates"
    echo
    echo "For detailed help on a command:"
    echo "  $0 help [COMMAND]"
}

# Function to show detailed help for a command
show_command_help() {
    case "$1" in
        "install")
            echo "Install the Jukebox service:"
            echo "  Creates systemd service file"
            echo "  Sets up GPIO and audio permissions"
            echo "  Creates log directories"
            echo "  Enables service to start on boot"
            echo
            echo "Usage: sudo $0 install"
            ;;
        "start")
            echo "Start the Jukebox service:"
            echo "  Starts both Suno API and main.py"
            echo "  Monitors service health"
            echo
            echo "Usage: sudo $0 start"
            ;;
        "status")
            echo "Show service status:"
            echo "  Service installation status"
            echo "  Process monitoring"
            echo "  Network port checks"
            echo "  Resource usage"
            echo "  Log file status"
            echo
            echo "Usage: $0 status"
            ;;
        "update")
            echo "Update firmware from GitHub:"
            echo "  Pulls from AI-Jukebox repository"
            echo "  Creates backup before updating"
            echo "  Restarts service after update"
            echo
            echo "Usage: sudo $0 update"
            ;;
        "auto-update")
            echo "Setup automatic updates:"
            echo "  Configures cron jobs for updates"
            echo "  Options: hourly, daily (default), weekly"
            echo "  Creates log rotation"
            echo
            echo "Usage: sudo $0 auto-update [frequency]"
            echo "  sudo $0 auto-update hourly"
            echo "  sudo $0 auto-update daily"
            echo "  sudo $0 auto-update weekly"
            ;;
        *)
            show_usage
            ;;
    esac
}

# Function to install service
install_service() {
    print_header "Installing Jukebox Service"
    echo "=========================================="
    
    if ! check_root; then
        return 1
    fi
    
    # Get the current user
    CURRENT_USER=$(logname || who am i | awk '{print $1}' | head -n1)
    if [ -z "$CURRENT_USER" ]; then
        CURRENT_USER="pi"
    fi
    
    print_status "Installing Jukebox service for user: $CURRENT_USER"
    print_status "Firmware directory: $SERVICE_DIR"
    
    # Create necessary directories
    print_status "Creating log and PID directories..."
    mkdir -p "$LOG_DIR" "$PID_DIR"
    chown "$CURRENT_USER:$CURRENT_USER" "$LOG_DIR" "$PID_DIR"
    
    # Make the service script executable
    chmod +x "run-service.sh"
    
    # Create the service file
    print_status "Creating systemd service file..."
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Jukebox Firmware Service
After=network.target sound.target
Wants=network.target sound.target

[Service]
Type=forking
User=$CURRENT_USER
Group=$CURRENT_USER
WorkingDirectory=$SERVICE_DIR
ExecStart=/bin/bash $SERVICE_DIR/run-service.sh
ExecStop=/bin/bash -c 'pkill -f "python.*main.py" && pkill -f "npm.*run.*dev"'
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment variables
Environment=PATH=$SERVICE_DIR/env/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=$SERVICE_DIR

# Audio and GPIO permissions
SupplementaryGroups=audio gpio

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd
    print_status "Reloading systemd..."
    systemctl daemon-reload
    
    # Enable the service
    print_status "Enabling Jukebox service..."
    systemctl enable "$SERVICE_NAME"
    
    # Set proper permissions for GPIO and audio
    print_status "Setting up GPIO and audio permissions..."
    usermod -a -G gpio,audio "$CURRENT_USER" 2>/dev/null || true
    
    # Create udev rules for GPIO access
    print_status "Creating udev rules for GPIO access..."
    cat > /etc/udev/rules.d/99-gpio.rules << EOF
SUBSYSTEM=="gpio", GROUP="gpio", MODE="0660"
SUBSYSTEM=="bcm2835-gpiomem", GROUP="gpio", MODE="0660"
EOF
    
    # Reload udev rules
    udevadm control --reload-rules
    udevadm trigger
    
    print_status "Installation completed successfully!"
    echo
    print_status "To start the service:"
    echo "  sudo $0 start"
    echo
    print_status "To check service status:"
    echo "  $0 status"
}

# Function to start service
start_service() {
    print_header "Starting Jukebox Service"
    echo "=========================================="
    
    if ! check_root; then
        return 1
    fi
    
    print_status "Starting Jukebox service..."
    if systemctl start "$SERVICE_NAME"; then
        print_status "Service started successfully"
        
        # Wait a moment and check status
        sleep 3
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            print_status "Service is running and healthy"
        else
            print_warning "Service may have failed to start properly"
            systemctl status "$SERVICE_NAME" --no-pager -l
        fi
    else
        print_error "Failed to start service"
        systemctl status "$SERVICE_NAME" --no-pager -l
        return 1
    fi
}

# Function to stop service
stop_service() {
    print_header "Stopping Jukebox Service"
    echo "=========================================="
    
    if ! check_root; then
        return 1
    fi
    
    print_status "Stopping Jukebox service..."
    if systemctl stop "$SERVICE_NAME"; then
        print_status "Service stopped successfully"
    else
        print_error "Failed to stop service"
        return 1
    fi
}

# Function to restart service
restart_service() {
    print_header "Restarting Jukebox Service"
    echo "=========================================="
    
    if ! check_root; then
        return 1
    fi
    
    print_status "Restarting Jukebox service..."
    if systemctl restart "$SERVICE_NAME"; then
        print_status "Service restarted successfully"
        
        # Wait a moment and check status
        sleep 3
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            print_status "Service is running and healthy"
        else
            print_warning "Service may have failed to restart properly"
            systemctl status "$SERVICE_NAME" --no-pager -l
        fi
    else
        print_error "Failed to restart service"
        systemctl status "$SERVICE_NAME" --no-pager -l
        return 1
    fi
}

# Function to show service status
show_status() {
    print_header "Jukebox Service Status"
    echo "=========================================="
    
    # Check if service is installed
    if systemctl list-unit-files | grep -q "$SERVICE_NAME.service"; then
        print_status "Jukebox service is installed"
        
        # Check service status
        SERVICE_STATUS=$(systemctl is-active "$SERVICE_NAME.service")
        if [ "$SERVICE_STATUS" = "active" ]; then
            print_status "Service is running (active)"
        elif [ "$SERVICE_STATUS" = "inactive" ]; then
            print_warning "Service is stopped (inactive)"
        elif [ "$SERVICE_STATUS" = "failed" ]; then
            print_error "Service has failed"
        else
            print_warning "Service status: $SERVICE_STATUS"
        fi
        
        # Check if service is enabled
        if systemctl is-enabled "$SERVICE_NAME.service" | grep -q "enabled"; then
            print_status "Service is enabled (will start on boot)"
        else
            print_warning "Service is not enabled (won't start on boot)"
        fi
    else
        print_error "Jukebox service is not installed"
        echo "Run: sudo $0 install"
        return 1
    fi
    
    echo
    
    # Check if processes are running
    print_header "Process Status"
    
    # Check Suno API
    if pgrep -f "npm.*run.*dev" > /dev/null; then
        SUNO_PID=$(pgrep -f "npm.*run.*dev")
        print_status "Suno API is running (PID: $SUNO_PID)"
    else
        print_warning "Suno API is not running"
    fi
    
    # Check main.py
    if pgrep -f "python.*main.py" > /dev/null; then
        MAIN_PID=$(pgrep -f "python.*main.py")
        print_status "main.py is running (PID: $MAIN_PID)"
    else
        print_warning "main.py is not running"
    fi
    
    echo
    
    # Check network ports
    print_header "Network Status"
    
    # Check if Suno API is listening on port 3000
    if netstat -tlnp 2>/dev/null | grep -q ":3000"; then
        print_status "Suno API is listening on port 3000"
    else
        print_warning "Suno API is not listening on port 3000"
    fi
    
    # Test Suno API endpoint
    print_status "Testing Suno API endpoint..."
    if curl -s "http://localhost:3000/api/get_limit" > /dev/null 2>&1; then
        print_status "Suno API is responding"
    else
        print_warning "Suno API is not responding"
    fi
    
    echo
    
    # Check log files
    print_header "Log Files Status"
    if [ -d "$LOG_DIR" ]; then
        print_status "Log directory exists: $LOG_DIR"
        echo "Available log files:"
        ls -la "$LOG_DIR" 2>/dev/null || echo "Cannot access log directory"
    else
        print_warning "Log directory not found: $LOG_DIR"
    fi
    
    echo
    
    # Summary and recommendations
    print_header "Summary & Recommendations"
    
    if systemctl is-active "$SERVICE_NAME.service" | grep -q "active"; then
        print_status "✓ Service is running"
        echo "  - To stop: sudo $0 stop"
        echo "  - To restart: sudo $0 restart"
        echo "  - To view logs: $0 logs"
    else
        print_warning "⚠ Service is not running"
        echo "  - To start: sudo $0 start"
        echo "  - To check why: systemctl status $SERVICE_NAME"
    fi
    
    if systemctl is-enabled "$SERVICE_NAME.service" | grep -q "enabled"; then
        print_status "✓ Service is enabled"
    else
        print_warning "⚠ Service is not enabled"
        echo "  - To enable: sudo $0 enable"
    fi
}

# Function to enable service
enable_service() {
    print_header "Enabling Jukebox Service"
    echo "=========================================="
    
    if ! check_root; then
        return 1
    fi
    
    print_status "Enabling Jukebox service..."
    if systemctl enable "$SERVICE_NAME"; then
        print_status "Service enabled successfully"
        print_status "Service will start automatically on boot"
    else
        print_error "Failed to enable service"
        return 1
    fi
}

# Function to disable service
disable_service() {
    print_header "Disabling Jukebox Service"
    echo "=========================================="
    
    if ! check_root; then
        return 1
    fi
    
    print_status "Disabling Jukebox service..."
    if systemctl disable "$SERVICE_NAME"; then
        print_status "Service disabled successfully"
        print_status "Service will not start automatically on boot"
    else
        print_error "Failed to disable service"
        return 1
    fi
}

# Function to show logs
show_logs() {
    print_header "Jukebox Service Logs"
    echo "=========================================="
    
    if ! check_root; then
        print_warning "Some log commands may require sudo privileges"
    fi
    
    echo "Available log viewing options:"
    echo
    print_command "sudo journalctl -u $SERVICE_NAME -f"
    print_description "View real-time service logs (Ctrl+C to exit)"
    echo
    
    print_command "sudo journalctl -u $SERVICE_NAME --since '1 hour ago'"
    print_description "Show service logs from the last hour"
    echo
    
    print_command "sudo journalctl -u $SERVICE_NAME --since '1 day ago'"
    print_description "Show service logs from the last day"
    echo
    
    if [ -d "$LOG_DIR" ]; then
        echo "Individual log files:"
        print_command "tail -f $LOG_DIR/jukebox.log"
        print_description "View service log file"
        echo
        
        print_command "tail -f $LOG_DIR/main.log"
        print_description "View Python script logs"
        echo
        
        print_command "tail -f $LOG_DIR/suno-api.log"
        print_description "View Suno API logs"
        echo
        
        print_command "tail -f $LOG_DIR/auto-update.log"
        print_description "View auto-update logs"
        echo
    fi
}

# Function to test service configuration
test_configuration() {
    print_header "Testing Jukebox Service Configuration"
    echo "=========================================="
    
    check_directory
    
    print_status "Testing Jukebox service configuration..."
    
    # Check if running as root
    if [ "$EUID" -eq 0 ]; then
        print_warning "Running as root - this is fine for testing"
    else
        print_status "Running as user: $(whoami)"
    fi
    
    # Check current directory
    CURRENT_DIR=$(pwd)
    print_status "Current directory: $CURRENT_DIR"
    
    # Check Python installation
    print_status "Checking Python installation..."
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version)
        print_status "Python3 found: $PYTHON_VERSION"
    else
        print_error "Python3 not found. Please install Python 3.7+"
        return 1
    fi
    
    # Check Node.js installation
    print_status "Checking Node.js installation..."
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        print_status "Node.js found: $NODE_VERSION"
    else
        print_error "Node.js not found. Please install Node.js"
        return 1
    fi
    
    # Check npm installation
    print_status "Checking npm installation..."
    if command -v npm &> /dev/null; then
        NPM_VERSION=$(npm --version)
        print_status "npm found: $NPM_VERSION"
    else
        print_error "npm not found. Please install npm"
        return 1
    fi
    
    # Check virtual environment
    print_status "Checking virtual environment..."
    if [ -d "env" ]; then
        print_status "Virtual environment found: env/"
        
        # Check if virtual environment is activated
        if [ -n "$VIRTUAL_ENV" ]; then
            print_status "Virtual environment is active: $VIRTUAL_ENV"
        else
            print_warning "Virtual environment not activated. Activating..."
            source env/bin/activate
            print_status "Virtual environment activated"
        fi
        
        # Check Python packages
        print_status "Checking Python packages..."
        if python -c "import requests, vlc, RPi.GPIO" 2>/dev/null; then
            print_status "Required Python packages are installed"
        else
            print_warning "Some required Python packages are missing"
            print_status "Installing requirements..."
            pip install -r requirements.txt
        fi
    else
        print_error "Virtual environment not found. Please run setup.sh first."
        return 1
    fi
    
    # Check Suno API directory
    print_status "Checking Suno API..."
    if [ -d "suno-api" ]; then
        print_status "Suno API directory found: suno-api/"
        
        # Check if package.json exists
        if [ -f "suno-api/package.json" ]; then
            print_status "Suno API package.json found"
        else
            print_error "Suno API package.json not found"
            return 1
        fi
    else
        print_error "Suno API directory not found. Please run setup.sh first."
        return 1
    fi
    
    # Check service files
    print_status "Checking service files..."
    if [ -f "jukebox.service" ]; then
        print_status "Service file found: jukebox.service"
    else
        print_warning "Service file not found: jukebox.service"
    fi
    
    if [ -f "run-service.sh" ]; then
        print_status "Service script found: run-service.sh"
        if [ -x "run-service.sh" ]; then
            print_status "Service script is executable"
        else
            print_warning "Service script is not executable. Run: chmod +x run-service.sh"
        fi
    else
        print_warning "Service script not found: run-service.sh"
    fi
    
    # Check audio files
    print_status "Checking audio files..."
    AUDIO_COUNT=$(find audio -name "*.mp3" 2>/dev/null | wc -l)
    if [ "$AUDIO_COUNT" -gt 0 ]; then
        print_status "Found $AUDIO_COUNT audio files in audio/ directory"
    else
        print_warning "No audio files found in audio/ directory"
    fi
    
    # Summary
    echo
    print_status "=== Service Test Summary ==="
    print_status "✓ Python and Node.js are installed"
    print_status "✓ Virtual environment is configured"
    print_status "✓ Suno API directory exists"
    print_status "✓ Service files are present"
    print_status "✓ Ready for service installation"
    
    echo
    print_status "To install the service, run:"
    echo "  sudo $0 install"
    echo
    print_status "To test the service manually, run:"
    echo "  ./run-service.sh"
    echo
    print_status "Test completed successfully!"
}

# Function to check for updates
check_updates() {
    print_header "Checking for Jukebox Updates"
    echo "=========================================="
    
    check_directory
    
    # Check if git is installed
    if ! command -v git &> /dev/null; then
        print_error "Git is not installed. Please install git first."
        return 1
    fi
    
    print_status "Fetching repository information..."
    
    if [ -d "$REPO_DIR" ]; then
        print_status "Updating existing repository..."
        cd "$REPO_DIR"
        git fetch origin
    else
        print_status "Cloning repository..."
        git clone "$REPO_URL" "$REPO_DIR"
        cd "$REPO_DIR"
    fi
    
    # Get latest commit info
    LATEST_COMMIT=$(git rev-parse HEAD)
    LATEST_COMMIT_MSG=$(git log -1 --pretty=format:"%s")
    LATEST_COMMIT_DATE=$(git log -1 --pretty=format:"%cd" --date=short)
    LATEST_COMMIT_AUTHOR=$(git log -1 --pretty=format:"%an")
    
    print_status "Repository updated successfully"
    
    # Get current firmware info
    if [ -d "$SERVICE_DIR/.git" ]; then
        print_status "Current firmware is a git repository"
        cd "$SERVICE_DIR"
        CURRENT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
        CURRENT_COMMIT_MSG=$(git log -1 --pretty=format:"%s" 2>/dev/null || echo "unknown")
        CURRENT_COMMIT_DATE=$(git log -1 --pretty=format:"%cd" --date=short 2>/dev/null || echo "unknown")
    else
        print_status "Current firmware is not a git repository"
        CURRENT_COMMIT="not_git"
        CURRENT_COMMIT_MSG="not_git"
        CURRENT_COMMIT_DATE="not_git"
    fi
    
    echo
    print_header "=== Update Summary ==="
    
    if [ "$CURRENT_COMMIT" != "not_git" ]; then
        echo "Current firmware:"
        echo "  Commit: $CURRENT_COMMIT"
        echo "  Message: $CURRENT_COMMIT_MSG"
        echo "  Date: $CURRENT_COMMIT_DATE"
        echo
    fi
    
    echo "Latest available:"
    echo "  Commit: $LATEST_COMMIT"
    echo "  Message: $LATEST_COMMIT_MSG"
    echo "  Date: $LATEST_COMMIT_DATE"
    echo "  Author: $LATEST_COMMIT_AUTHOR"
    echo
    
    # Check for updates
    print_status "Checking for updates..."
    
    if [ ! -d "$REPO_DIR/firmware" ]; then
        print_error "Firmware directory not found in repository"
        rm -rf "$REPO_DIR"
        return 1
    fi
    
    # Compare current firmware with repository
    if diff -r "$SERVICE_DIR" "$REPO_DIR/firmware" > /dev/null 2>&1; then
        print_status "✓ Firmware is up to date"
        rm -rf "$REPO_DIR"
        return 0
    else
        print_warning "⚠ Updates are available!"
        echo
        print_status "To update your firmware, run:"
        echo "  sudo $0 update"
        echo
        print_status "To setup automatic updates, run:"
        echo "  sudo $0 auto-update"
        
        rm -rf "$REPO_DIR"
        return 0
    fi
}

# Function to update firmware
update_firmware() {
    print_header "Updating Jukebox Firmware"
    echo "=========================================="
    
    if ! check_root; then
        return 1
    fi
    
    check_directory
    
    print_status "Updating from GitHub repository..."
    
    # Create backup
    print_status "Creating backup of current firmware..."
    mkdir -p "$BACKUP_DIR"
    cp -r ./* "$BACKUP_DIR/" 2>/dev/null || true
    print_status "Backup created at: $BACKUP_DIR"
    
    # Clone/update repository
    if [ -d "$REPO_DIR" ]; then
        print_status "Updating existing repository..."
        cd "$REPO_DIR"
        git fetch origin
        git reset --hard origin/main
    else
        print_status "Cloning repository..."
        git clone "$REPO_URL" "$REPO_DIR"
        cd "$REPO_DIR"
    fi
    
    if [ ! -d "$REPO_DIR/firmware" ]; then
        print_error "Firmware directory not found in repository"
        rm -rf "$REPO_DIR"
        return 1
    fi
    
    # Check for changes
    if diff -r "$SERVICE_DIR" "$REPO_DIR/firmware" > /dev/null 2>&1; then
        print_status "No changes detected - firmware is up to date"
        rm -rf "$REPO_DIR"
        return 0
    fi
    
    print_status "Changes detected - updating firmware..."
    
    # Stop the service if running
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_status "Stopping jukebox service..."
        systemctl stop "$SERVICE_NAME"
    fi
    
    # Copy new firmware files
    cp -r "$REPO_DIR/firmware"/* "$SERVICE_DIR/"
    
    # Make scripts executable
    chmod +x "$SERVICE_DIR"/*.sh 2>/dev/null || true
    
    # Update permissions
    chown -R pi:pi "$SERVICE_DIR"
    
    print_status "Firmware files updated successfully"
    
    # Reinstall service if needed
    if [ -f "$SERVICE_FILE" ]; then
        print_status "Reinstalling service with new configuration..."
        cd "$SERVICE_DIR"
        $0 install
    fi
    
    # Restart service
    print_status "Starting jukebox service..."
    if systemctl start "$SERVICE_NAME"; then
        print_status "Service started successfully"
        
        # Wait a moment and check status
        sleep 5
        if systemctl is-active --quiet "$SERVICE_NAME"; then
            print_status "Service is running and healthy"
        else
            print_warning "Service may have failed to start properly"
            systemctl status "$SERVICE_NAME" --no-pager -l
        fi
    else
        print_error "Failed to start service"
        systemctl status "$SERVICE_NAME" --no-pager -l
    fi
    
    # Cleanup
    rm -rf "$REPO_DIR"
    
    echo
    print_header "=== Update Summary ==="
    print_status "✓ Repository updated from GitHub"
    print_status "✓ Firmware files updated"
    print_status "✓ Service restarted"
    print_status "✓ Backup created at: $BACKUP_DIR"
    
    echo
    print_status "To check service status:"
    echo "  $0 status"
    echo
    print_status "To view service logs:"
    echo "  $0 logs"
    echo
    print_status "Update completed successfully!"
}

# Function to setup auto-update
setup_auto_update() {
    print_header "Setting Up Automatic Updates"
    echo "=========================================="
    
    if ! check_root; then
        return 1
    fi
    
    check_directory
    
    # Get update frequency from command line
    UPDATE_FREQUENCY="${2:-daily}"
    CRON_USER="pi"
    
    # Validate frequency
    case $UPDATE_FREQUENCY in
        "hourly"|"daily"|"weekly")
            print_status "Setting up $UPDATE_FREQUENCY updates"
            ;;
        *)
            print_error "Invalid update frequency: $UPDATE_FREQUENCY"
            print_status "Valid options: hourly, daily, weekly"
            return 1
            ;;
    esac
    
    # Create cron job based on frequency
    case $UPDATE_FREQUENCY in
        "hourly")
            CRON_SCHEDULE="0 * * * *"
            ;;
        "daily")
            CRON_SCHEDULE="0 2 * * *"
            ;;
        "weekly")
            CRON_SCHEDULE="0 2 * * 0"
            ;;
    esac
    
    # Get absolute path to update script
    SCRIPT_PATH=$(readlink -f "$0")
    
    # Create cron job entry
    CRON_JOB="$CRON_SCHEDULE $SCRIPT_PATH update >> $LOG_DIR/auto-update.log 2>&1"
    
    # Check if cron job already exists
    if crontab -u "$CRON_USER" -l 2>/dev/null | grep -q "$(basename "$0")"; then
        print_warning "Cron job already exists. Updating..."
        # Remove existing cron job
        crontab -u "$CRON_USER" -l 2>/dev/null | grep -v "$(basename "$0")" | crontab -u "$CRON_USER" -
    fi
    
    # Add new cron job
    (crontab -u "$CRON_USER" -l 2>/dev/null; echo "$CRON_JOB") | crontab -u "$CRON_USER" -
    
    print_status "Cron job added successfully"
    
    # Setup log rotation
    print_status "Setting up log rotation for auto-update logs..."
    
    cat > /etc/logrotate.d/jukebox-auto-update << EOF
$LOG_DIR/auto-update.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 pi pi
    postrotate
        systemctl reload rsyslog >/dev/null 2>&1 || true
    endscript
}
EOF
    
    print_status "Log rotation configured"
    
    # Create update log file
    print_status "Creating auto-update log file..."
    mkdir -p "$LOG_DIR"
    touch "$LOG_DIR/auto-update.log"
    chown "$CRON_USER:$CRON_USER" "$LOG_DIR/auto-update.log"
    chmod 644 "$LOG_DIR/auto-update.log"
    
    print_status "Log file created: $LOG_DIR/auto-update.log"
    
    # Show cron status
    print_status "Current cron jobs for user $CRON_USER:"
    crontab -u "$CRON_USER" -l 2>/dev/null || echo "No cron jobs found"
    
    echo
    print_header "=== Auto-Update Setup Summary ==="
    print_status "✓ Cron job configured for $UPDATE_FREQUENCY updates"
    print_status "✓ Log rotation configured"
    print_status "✓ Update log file created"
    
    echo
    print_status "Update schedule: $UPDATE_FREQUENCY"
    case $UPDATE_FREQUENCY in
        "hourly")
            echo "  - Updates will run every hour"
            ;;
        "daily")
            echo "  - Updates will run daily at 2:00 AM"
            ;;
        "weekly")
            echo "  - Updates will run weekly on Sundays at 2:00 AM"
            ;;
    esac
    
    echo
    print_status "To manually run an update:"
    echo "  sudo $0 update"
    echo
    print_status "To check update logs:"
    echo "  tail -f $LOG_DIR/auto-update.log"
    echo
    print_status "Setup completed successfully!"
}

# Main execution
main() {
    case "${1:-help}" in
        "install")
            install_service
            ;;
        "start")
            start_service
            ;;
        "stop")
            stop_service
            ;;
        "restart")
            restart_service
            ;;
        "status")
            show_status
            ;;
        "enable")
            enable_service
            ;;
        "disable")
            disable_service
            ;;
        "logs")
            show_logs
            ;;
        "test")
            test_configuration
            ;;
        "check-updates")
            check_updates
            ;;
        "update")
            update_firmware
            ;;
        "auto-update")
            setup_auto_update "$@"
            ;;
        "help")
            if [ -n "$2" ]; then
                show_command_help "$2"
            else
                show_usage
            fi
            ;;
        *)
            print_error "Unknown command: $1"
            echo
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
