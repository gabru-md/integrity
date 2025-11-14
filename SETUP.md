# Rasbhari Setup Guide

This guide will walk you through the complete setup process for Rasbhari, from system preparation to running your first automation.

## Table of Contents

- [System Requirements](#system-requirements)
- [Hardware Setup](#hardware-setup)
- [Software Installation](#software-installation)
- [Database Configuration](#database-configuration)
- [Environment Configuration](#environment-configuration)
- [Running the Server](#running-the-server)
- [Verification](#verification)
- [Optional Components](#optional-components)
- [Troubleshooting](#troubleshooting)
- [Next Steps](#next-steps)

## System Requirements

### Hardware Requirements

**Minimum Configuration:**
- Raspberry Pi 3B+ (1GB RAM)
- 16GB MicroSD card (Class 10)
- 5V/2.5A power supply
- Network connection (Ethernet or WiFi)

**Recommended Configuration:**
- Raspberry Pi 4 (2GB+ RAM)
- 32GB+ MicroSD card (Class 10 or A1/A2)
- 5V/3A USB-C power supply
- Ethernet connection (for stability)

**Optional Hardware:**
- ESP32-CAM modules (for Heimdall visual monitoring)
- BLE beacons (for Atmos location tracking)
- ESP32/Arduino boards (for custom sensors)

### Software Requirements

- **Operating System**: Raspberry Pi OS (64-bit recommended) or any Debian-based Linux
- **Python**: Version 3.8 or higher
- **PostgreSQL**: Version 12 or higher
- **Git**: For cloning the repository
- **Internet Connection**: For package installation and external APIs

## Hardware Setup

### 1. Prepare Raspberry Pi

**A. Flash Raspberry Pi OS:**

1. Download [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
2. Insert MicroSD card into your computer
3. Open Raspberry Pi Imager
4. Choose OS: **Raspberry Pi OS (64-bit)** recommended
5. Choose Storage: Select your MicroSD card
6. Click ⚙️ (Advanced Options):
   - Set hostname: `rasbhari.local`
   - Enable SSH
   - Set username and password
   - Configure WiFi (if needed)
   - Set timezone
7. Write and wait for completion

**B. Boot and Connect:**

1. Insert MicroSD into Raspberry Pi
2. Connect power, ethernet (or use WiFi)
3. Wait 2-3 minutes for first boot
4. Find IP address:
   ```bash
   # On your computer
   ping rasbhari.local
   # Or check your router's DHCP table
   ```
5. SSH into Raspberry Pi:
   ```bash
   ssh pi@rasbhari.local
   # Or: ssh pi@<IP_ADDRESS>
   ```

### 2. Update System

```bash
# Update package lists
sudo apt update

# Upgrade installed packages
sudo apt upgrade -y

# Reboot if kernel was updated
sudo reboot
```

After reboot, reconnect via SSH.

## Software Installation

### 1. Install System Dependencies

```bash
# Install Python 3 and development tools
sudo apt install -y python3 python3-pip python3-dev python3-venv

# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Install Git
sudo apt install -y git

# Install system libraries for Python packages
sudo apt install -y \
    libpq-dev \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-setuptools

# For Heimdall (computer vision)
sudo apt install -y \
    libopencv-dev \
    python3-opencv \
    libatlas-base-dev

# For system monitoring (optional)
sudo apt install -y htop
```

### 2. Verify Installations

```bash
# Check Python version (should be 3.8+)
python3 --version

# Check PostgreSQL (should be running)
sudo systemctl status postgresql

# Check Git
git --version
```

### 3. Clone Rasbhari Repository

```bash
# Navigate to home directory
cd ~

# Clone repository
git clone https://github.com/yourusername/rasbhari.git

# Enter project directory
cd rasbhari

# Verify contents
ls -la
```

### 4. Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Your prompt should now show (venv)
```

**Note**: Always activate the virtual environment before running Rasbhari:
```bash
cd ~/rasbhari
source venv/bin/activate
```

To make this automatic, add to `~/.bashrc`:
```bash
echo 'cd ~/rasbhari && source venv/bin/activate' >> ~/.bashrc
```

### 5. Install Python Dependencies

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# This may take 10-20 minutes on Raspberry Pi
```

**If installation fails:**
- For numpy/scipy errors: `sudo apt install -y python3-numpy python3-scipy`
- For opencv errors: Use system package: `sudo apt install -y python3-opencv`
- For memory issues: Add swap space (see Troubleshooting)

## Database Configuration

### 1. Configure PostgreSQL

**A. Set PostgreSQL Password:**

```bash
# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL prompt:
ALTER USER postgres WITH PASSWORD 'your_secure_password';
\q
```

**B. Enable Local Connections:**

Edit PostgreSQL configuration:
```bash
sudo nano /etc/postgresql/*/main/pg_hba.conf
```

Find this line:
```
local   all             postgres                                peer
```

Change to:
```
local   all             postgres                                md5
```

Restart PostgreSQL:
```bash
sudo systemctl restart postgresql
```

### 2. Create Databases

```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Create databases
CREATE DATABASE rasbhari_events;
CREATE DATABASE rasbhari_contracts;
CREATE DATABASE rasbhari_queue;
CREATE DATABASE rasbhari_main;
CREATE DATABASE rasbhari_notifications;
CREATE DATABASE rasbhari_thoughts;

# Verify databases were created
\l

# Exit
\q
```

### 3. Create Database User (Optional but Recommended)

```bash
sudo -u postgres psql

# Create user
CREATE USER rasbhari WITH PASSWORD 'your_secure_password';

# Grant privileges on all databases
GRANT ALL PRIVILEGES ON DATABASE rasbhari_events TO rasbhari;
GRANT ALL PRIVILEGES ON DATABASE rasbhari_contracts TO rasbhari;
GRANT ALL PRIVILEGES ON DATABASE rasbhari_queue TO rasbhari;
GRANT ALL PRIVILEGES ON DATABASE rasbhari_main TO rasbhari;
GRANT ALL PRIVILEGES ON DATABASE rasbhari_notifications TO rasbhari;
GRANT ALL PRIVILEGES ON DATABASE rasbhari_thoughts TO rasbhari;

\q
```

## Environment Configuration

### 1. Create Environment File

```bash
# Copy example file
cp .env.example .env

# Edit configuration
nano .env
```

### 2. Configure Database Connections

Edit `.env` file with your database credentials:

```bash
# Events Database
EVENTS_POSTGRES_DB=rasbhari_events
EVENTS_POSTGRES_USER=rasbhari
EVENTS_POSTGRES_PASSWORD=your_secure_password
EVENTS_POSTGRES_HOST=localhost
EVENTS_POSTGRES_PORT=5432

# Contracts Database
CONTRACTS_POSTGRES_DB=rasbhari_contracts
CONTRACTS_POSTGRES_USER=rasbhari
CONTRACTS_POSTGRES_PASSWORD=your_secure_password
CONTRACTS_POSTGRES_HOST=localhost
CONTRACTS_POSTGRES_PORT=5432

# Queue Database
QUEUE_POSTGRES_DB=rasbhari_queue
QUEUE_POSTGRES_USER=rasbhari
QUEUE_POSTGRES_PASSWORD=your_secure_password
QUEUE_POSTGRES_HOST=localhost
QUEUE_POSTGRES_PORT=5432

# Main Database
RASBHARI_POSTGRES_DB=rasbhari_main
RASBHARI_POSTGRES_USER=rasbhari
RASBHARI_POSTGRES_PASSWORD=your_secure_password
RASBHARI_POSTGRES_HOST=localhost
RASBHARI_POSTGRES_PORT=5432

# Notifications Database
NOTIFICATIONS_POSTGRES_DB=rasbhari_notifications
NOTIFICATIONS_POSTGRES_USER=rasbhari
NOTIFICATIONS_POSTGRES_PASSWORD=your_secure_password
NOTIFICATIONS_POSTGRES_HOST=localhost
NOTIFICATIONS_POSTGRES_PORT=5432

# Thoughts Database
THOUGHTS_POSTGRES_DB=rasbhari_thoughts
THOUGHTS_POSTGRES_USER=rasbhari
THOUGHTS_POSTGRES_PASSWORD=your_secure_password
THOUGHTS_POSTGRES_HOST=localhost
THOUGHTS_POSTGRES_PORT=5432
```

### 3. Configure Server Settings

```bash
# Server Configuration
SERVER_DEBUG=False
SERVER_PORT=5000

# File Storage
SERVER_FILES_FOLDER=/home/pi/rasbhari/files

# Logging
LOG_DIR=/home/pi/rasbhari/logs

# Rasbhari URL (for shortcuts)
RASBHARI_LOCAL_URL=rasbhari.local:5000
```

### 4. Create Required Directories

```bash
# Create files directory
mkdir -p ~/rasbhari/files

# Create logs directory
mkdir -p ~/rasbhari/logs

# Set permissions
chmod 755 ~/rasbhari/files
chmod 755 ~/rasbhari/logs
```

### 5. Configure External Services (Optional)

**SendGrid (for email notifications):**
```bash
COURIER_SENDER_EMAIL=your-email@example.com
COURIER_RECEIVER_EMAIL=recipient@example.com
SENDGRID_API_KEY=SG.your_sendgrid_api_key_here
```

Get SendGrid API key: https://sendgrid.com/

**Apple Signing Server (for iOS shortcuts):**
```bash
APPLE_SIGNING_SERVER_URL=your-macbook.local
APPLE_SIGNING_SERVER_PORT=5001
```

See [Optional Components](#optional-components) for setup details.

## Running the Server

### 1. Initial Database Setup

Tables are created automatically on first run by each service's `_create_table()` method.

### 2. Start the Server

```bash
# Ensure you're in the project directory with venv activated
cd ~/rasbhari
source venv/bin/activate

# Run the server
python server.py
```

You should see output like:
```
INFO - Connected to PostgreSQL database.
INFO - EventsDB - Connected to PostgreSQL database.
INFO - ContractsDB - Connected to PostgreSQL database.
...
 * Running on http://0.0.0.0:5000
```

### 3. Access the Dashboard

Open a web browser and navigate to:
```
http://rasbhari.local:5000
```

Or use the IP address:
```
http://<raspberry-pi-ip>:5000
```

## Verification

### 1. Check Web Interface

Navigate to `http://rasbhari.local:5000`

You should see:
- Dashboard with widgets
- Navigation to Apps, Processes
- No errors in browser console

### 2. Test API Endpoints

Create your first event:
```bash
curl -X POST http://rasbhari.local:5000/events/ \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "system:startup",
    "description": "Rasbhari started successfully",
    "tags": ["system", "test"]
  }'
```

Expected response:
```json
{"message": "Events created successfully"}
```

Retrieve events:
```bash
curl http://rasbhari.local:5000/events/
```

### 3. Check Logs

```bash
# View main log
tail -f ~/rasbhari/logs/main.log

# View specific component logs
tail -f ~/rasbhari/logs/Events.log
tail -f ~/rasbhari/logs/Sentinel.log
```

### 4. Check Database

```bash
sudo -u postgres psql rasbhari_events

# In PostgreSQL:
SELECT * FROM events LIMIT 5;
\q
```

### 5. Check Processes

Navigate to `http://rasbhari.local:5000/processes`

You should see:
- List of registered processes
- Status (enabled/disabled, running/stopped)
- Ability to start/stop processes

## Optional Components

### 1. SendGrid Email Notifications

**Setup:**

1. Sign up at https://sendgrid.com/ (free tier available)
2. Create API key with "Mail Send" permissions
3. Verify sender email address
4. Add to `.env`:
   ```bash
   SENDGRID_API_KEY=SG.your_api_key
   COURIER_SENDER_EMAIL=verified@example.com
   COURIER_RECEIVER_EMAIL=your@email.com
   ```
5. Enable Courier process in `apps/events.py`:
   ```python
   events_app.register_process(Courier, enabled=True)
   ```

**Test:**
```bash
curl -X POST http://rasbhari.local:5000/events/ \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "test:notification",
    "description": "Test email notification",
    "tags": ["notification", "test"]
  }'
```

### 2. iOS Shortcuts Integration

**Requirements:**
- iPhone or iWatch
- macOS computer (for signing)
- Same network as Raspberry Pi

**Setup Apple Signing Server (on macOS):**

```bash
# On your Mac
cd ~/rasbhari/util
python apple-signing-server.py
```

**Configure in `.env`:**
```bash
APPLE_SIGNING_SERVER_URL=your-macbook.local
APPLE_SIGNING_SERVER_PORT=5001
```

**Create and Sign Shortcuts:**
1. Navigate to `http://rasbhari.local:5000/shortcuts/home`
2. Create a new shortcut
3. Click "Sign" to sign with Apple server
4. Download the signed `.shortcut` file
5. Open on iPhone/iWatch and install

### 3. Heimdall (Visual Monitoring)

**Requirements:**
- ESP32-CAM module(s)
- YOLO model (downloaded automatically)

**Setup ESP32-CAM:**
1. Flash ESP32-CAM with camera server firmware
2. Configure WiFi settings
3. Add device in Rasbhari:
   ```bash
   curl -X POST http://rasbhari.local:5000/devices/ \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Front Door Camera",
       "type": "ESP32-CAM",
       "url": "http://esp32cam-ip/stream",
       "location": "entrance",
       "enabled_for": ["Heimdall"]
     }'
   ```
4. Enable Heimdall in `apps/devices.py`:
   ```python
   devices_app.register_process(Heimdall, enabled=True)
   ```

**Note**: First run downloads YOLO model (~10MB), may take a few minutes.

### 4. Atmos (Location Tracking)

**Requirements:**
- 3+ BLE beacon devices
- Known beacon positions (X, Y coordinates)

**Setup:**
1. Place BLE beacons in known locations
2. Configure beacon positions in code
3. Enable Atmos in `apps/devices.py`:
   ```python
   devices_app.register_process(Atmos, enabled=True)
   ```

### 5. Auto-Start on Boot

Create systemd service:

```bash
sudo nano /etc/systemd/system/rasbhari.service
```

Add:
```ini
[Unit]
Description=Rasbhari Automation System
After=network.target postgresql.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/rasbhari
Environment="PATH=/home/pi/rasbhari/venv/bin"
ExecStart=/home/pi/rasbhari/venv/bin/python /home/pi/rasbhari/server.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start
sudo systemctl enable rasbhari

# Start now
sudo systemctl start rasbhari

# Check status
sudo systemctl status rasbhari

# View logs
sudo journalctl -u rasbhari -f
```

## Troubleshooting

### Installation Issues

**Problem: pip install fails with memory error**

Solution: Increase swap space
```bash
# Stop swap
sudo dphys-swapfile swapoff

# Edit config
sudo nano /etc/dphys-swapfile
# Change: CONF_SWAPSIZE=100
# To: CONF_SWAPSIZE=1024

# Recreate and restart
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Retry installation
pip install -r requirements.txt
```

**Problem: PostgreSQL installation fails**

Solution:
```bash
# Add PostgreSQL repository
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update
sudo apt install postgresql-12
```

**Problem: Python version too old**

Solution on Raspberry Pi OS:
```bash
# Install Python 3.9 from deadsnakes PPA
sudo apt install software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.9 python3.9-venv python3.9-dev
```

### Database Issues

**Problem: Can't connect to PostgreSQL**

Solutions:
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Start if stopped
sudo systemctl start postgresql

# Check port
sudo ss -tlnp | grep 5432

# Check logs
sudo tail /var/log/postgresql/postgresql-*-main.log
```

**Problem: Password authentication failed**

Solution:
```bash
# Reset postgres password
sudo -u postgres psql
ALTER USER postgres WITH PASSWORD 'newpassword';
\q

# Update .env file with new password
nano .env
```

**Problem: Database doesn't exist**

Solution:
```bash
# List databases
sudo -u postgres psql -l

# Create missing database
sudo -u postgres psql
CREATE DATABASE rasbhari_events;
\q
```

### Server Issues

**Problem: Port 5000 already in use**

Solutions:
```bash
# Find process using port
sudo lsof -ti:5000

# Kill process
sudo kill -9 $(sudo lsof -ti:5000)

# Or change port in .env
nano .env
# Set: SERVER_PORT=5001
```

**Problem: Server starts but shows errors**

Check logs:
```bash
# Main log
tail -50 ~/rasbhari/logs/main.log

# Warnings
tail -50 ~/rasbhari/logs/warnings.log

# Exceptions
tail -50 ~/rasbhari/logs/exceptions.log
```

**Problem: Can't access from other devices**

Solutions:
```bash
# Check firewall
sudo ufw status

# Allow port if UFW is enabled
sudo ufw allow 5000

# Check server is listening on all interfaces (0.0.0.0)
sudo ss -tlnp | grep 5000
```

### Process Issues

**Problem: Process not starting**

Checks:
1. Is process enabled in code? Check `enabled=True`
2. Is ProcessManager started? Check `start_process_manager()` in server
3. Check logs: `tail -f ~/rasbhari/logs/<ProcessName>.log`
4. Check database: Process needs corresponding database

**Problem: Process crashes repeatedly**

Solutions:
```bash
# Check exception log
tail -50 ~/rasbhari/logs/exceptions.log

# Check process-specific log
tail -50 ~/rasbhari/logs/Sentinel.log

# Restart server
sudo systemctl restart rasbhari
```

### Performance Issues

**Problem: Server slow or unresponsive**

Solutions:
```bash
# Check system resources
htop

# Check database performance
sudo -u postgres psql
SELECT * FROM pg_stat_activity;

# Vacuum databases
VACUUM ANALYZE;
\q

# Clear old logs
find ~/rasbhari/logs -name "*.log" -type f -mtime +30 -delete
```

**Problem: High memory usage**

Solutions:
```bash
# Disable unused processes
# Edit apps/*.py files, set enabled=False

# Reduce batch sizes in QueueProcessors
# Edit process files, set max_queue_size=5

# Restart server
sudo systemctl restart rasbhari
```

## Next Steps

### 1. Learn the Framework

- Read [Gabru Framework Guide](gabru/readme.md)
- Understand [Apps](apps/README.md) and [Processes](processes/)
- Explore [QueueProcessor](gabru/qprocessor/README.md)

### 2. Create Your First App

Follow the tutorial: [Creating a New App](apps/README.md#creating-a-new-app)

Example: Todo list, habit tracker, sensor logger

### 3. Create Your First Process

Follow the tutorial: [QueueProcessor Guide](gabru/qprocessor/README.md)

Example: Custom notifications, data aggregation

### 4. Integrate Hardware

- Set up ESP32-CAM for monitoring
- Deploy BLE beacons for tracking
- Connect sensors via ESP32/Arduino

### 5. Set Up Automations

- Create contracts for behavioral monitoring
- Configure iOS shortcuts
- Set up email notifications

### 6. Monitor and Maintain

- Check logs regularly: `~/rasbhari/logs/`
- Monitor database size: `sudo -u postgres psql -l`
- Keep system updated: `sudo apt update && sudo apt upgrade`
- Backup databases periodically

## Getting Help

### Documentation
- [Main README](readme.md)
- [Gabru Framework](gabru/readme.md)
- [Apps Guide](apps/README.md)
- [Process Documentation](processes/)

### Community
- Open an issue on GitHub
- Check existing issues for solutions

### Logs Location
- **Main logs**: `~/rasbhari/logs/main.log`
- **Warnings**: `~/rasbhari/logs/warnings.log`
- **Exceptions**: `~/rasbhari/logs/exceptions.log`
- **Component logs**: `~/rasbhari/logs/<ComponentName>.log`

---

**Congratulations!** 🎉 You've successfully set up Rasbhari!

For questions or issues, please check the logs first, then consult the documentation or open a GitHub issue.
