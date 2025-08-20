# Jukebox Firmware Service Installation

This guide explains how to install the Jukebox firmware as a systemd service on Linux (Raspberry Pi) that will automatically start on boot and run in the background.

## Overview

The Jukebox firmware consists of two main components:

1. **Suno API Server** - A Node.js server that generates AI music
2. **Main Python Script** - Handles RFID card reading and audio playback

## Prerequisites

Before installing the service, ensure you have:

- Python 3.7+ installed
- Node.js and npm installed
- All dependencies installed (run `setup.sh` first)
- Virtual environment created (`env` folder)
- Suno API cloned (`suno-api` folder)

## Installation

### 1. Install the Service

Run the unified management script as root:

```bash
sudo chmod +x jukebox-manager.sh
sudo ./jukebox-manager.sh install
```

This script will:

- Create the systemd service file
- Set up proper permissions for GPIO and audio
- Create log directories
- Enable the service to start on boot

### 2. Service Management

**Start the service:**

```bash
sudo systemctl start jukebox
```

**Stop the service:**

```bash
sudo systemctl stop jukebox
```

**Check service status:**

```bash
sudo systemctl status jukebox
```

**View service logs:**

```bash
sudo journalctl -u jukebox -f
```

**View individual log files:**

```bash
tail -f /var/log/jukebox/jukebox.log
tail -f /var/log/jukebox/main.log
tail -f /var/log/jukebox/suno-api.log
```

### 3. Service Configuration

The service file is located at `/etc/systemd/system/jukebox.service`

Key features:

- Automatically restarts if it crashes
- Runs as the `pi` user (or your current user)
- Has proper GPIO and audio permissions
- Logs to both systemd journal and individual log files

## Manual Service Scripts

If you prefer to run the service manually or troubleshoot:

```bash
chmod +x run-service.sh
./run-service.sh
```

## Unified Management

All service management functions are now consolidated into a single script:

```bash
chmod +x jukebox-manager.sh

# Install the service
sudo ./jukebox-manager.sh install

# Start the service
sudo ./jukebox-manager.sh start

# Check status
./jukebox-manager.sh status

# View logs
./jukebox-manager.sh logs

# Test configuration
./jukebox-manager.sh test

# Check for updates
./jukebox-manager.sh check-updates

# Update firmware
sudo ./jukebox-manager.sh update

# Setup auto-updates
sudo ./jukebox-manager.sh auto-update

# Get help
./jukebox-manager.sh help
```

## Testing and Monitoring

### Test Service Configuration

Before installing the service, test your setup:

```bash
chmod +x jukebox-manager.sh
./jukebox-manager.sh test
```

This script will verify:

- Python and Node.js installations
- Virtual environment setup
- Required packages
- Suno API configuration
- Service file presence

### Check Service Status

Monitor your service with:

```bash
./jukebox-manager.sh status
```

This script provides:

- Service installation status
- Process monitoring
- Network port checks
- Resource usage
- Log file status

## Auto-Updates from GitHub

The Jukebox firmware can automatically update from the [AI-Jukebox repository](https://github.com/NotARoomba/AI-Jukebox) on GitHub.

### Check for Updates

Check if updates are available:

```bash
chmod +x jukebox-manager.sh
./jukebox-manager.sh check-updates
```

### Manual Update

Update firmware manually:

```bash
sudo ./jukebox-manager.sh update
```

### Setup Automatic Updates

Configure automatic updates (recommended):

```bash
sudo ./jukebox-manager.sh auto-update
```

**Update Frequencies:**

- **Daily** (default): Updates at 2:00 AM daily
- **Weekly**: Updates on Sundays at 2:00 AM
- **Hourly**: Updates every hour

**Examples:**

```bash
# Setup daily updates (default)
sudo ./jukebox-manager.sh auto-update

# Setup hourly updates
sudo ./jukebox-manager.sh auto-update hourly

# Setup weekly updates
sudo ./jukebox-manager.sh auto-update weekly
```

**Auto-update Features:**

- Automatically pulls from GitHub repository
- Creates backups before updating
- Restarts service after updates
- Logs all update activities
- Configurable update frequency
- Safe rollback with backups

## Troubleshooting

### Common Issues

1. **Service fails to start**

   - Check if virtual environment exists
   - Verify Suno API directory exists
   - Check log files for specific errors

2. **Permission denied errors**

   - Ensure the service is running as the correct user
   - Check GPIO and audio group memberships
   - Verify file permissions

3. **Audio not working**

   - Check if VLC is installed
   - Verify audio device configuration
   - Check volume settings

4. **RFID not working**
   - Ensure SPI is enabled
   - Check GPIO permissions
   - Verify hardware connections

### Log Locations

- System logs: `sudo journalctl -u jukebox`
- Service logs: `/var/log/jukebox/`

### Debug Mode

To run in debug mode without the service:

```bash
# Terminal 1: Start Suno API
cd suno-api
npm run dev

# Terminal 2: Start main script
source env/bin/activate
python main.py
```

## Quick Reference

**Essential Commands:**

```bash
# Install and start service
sudo ./jukebox-manager.sh install
sudo ./jukebox-manager.sh start

# Check status and logs
./jukebox-manager.sh status
./jukebox-manager.sh logs

# Update firmware
./jukebox-manager.sh check-updates
sudo ./jukebox-manager.sh update

# Setup auto-updates
sudo ./jukebox-manager.sh auto-update

# Get help
./jukebox-manager.sh help
```

## Service Files Explained

- **`jukebox.service`** - systemd service definition
- **`run-service.sh`** - Service execution script
- **`jukebox-manager.sh`** - **Unified management script** (combines all functions)
- **`requirements.txt`** - Python dependencies

## Uninstalling the Service

```bash
sudo systemctl stop jukebox
sudo systemctl disable jukebox
sudo rm /etc/systemd/system/jukebox.service
sudo systemctl daemon-reload
```

## Support

If you encounter issues:

1. Check the log files for error messages
2. Verify all prerequisites are met
3. Test components individually
4. Check hardware connections and permissions

The service is designed to be robust and will automatically restart if it encounters errors, ensuring your Jukebox continues to work reliably.
