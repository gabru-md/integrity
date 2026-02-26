# Environment Variables Reference

This document provides a complete reference for all environment variables used in Rasbhari. These variables are configured in the `.env` file at the project root.

## Table of Contents

- [Quick Start](#quick-start)
- [Database Configuration](#database-configuration)
- [Server Configuration](#server-configuration)
- [Notification Services](#notification-services)
- [Apple Integration](#apple-integration)
- [System Paths](#system-paths)
- [Optional Services](#optional-services)
- [Environment Files](#environment-files)
- [Security Best Practices](#security-best-practices)
- [Examples](#examples)

## Quick Start

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit with your configuration:
   ```bash
   nano .env
   ```

3. Required variables (minimum setup):
   - All `*_POSTGRES_*` variables
   - `LOG_DIR`
   - `SERVER_FILES_FOLDER`

4. Optional variables:
   - SendGrid configuration (for notifications)
   - Apple signing server (for iOS shortcuts)

## Database Configuration

Rasbhari uses multiple PostgreSQL databases for different concerns. Each database requires its own set of connection parameters.

### Pattern

All database variables follow this naming pattern:
```
{DATABASE_NAME}_POSTGRES_{PARAMETER}
```

### Events Database

**Purpose**: Stores all system events (backbone of event-driven architecture)

| Variable | Type | Required | Description | Example |
|----------|------|----------|-------------|---------|
| `EVENTS_POSTGRES_DB` | string | Yes | Database name | `rasbhari_events` |
| `EVENTS_POSTGRES_USER` | string | Yes | Database username | `rasbhari` or `postgres` |
| `EVENTS_POSTGRES_PASSWORD` | string | Yes | Database password | `secure_password_123` |
| `EVENTS_POSTGRES_HOST` | string | Yes | Database host | `localhost` or `192.168.1.100` |
| `EVENTS_POSTGRES_PORT` | integer | Yes | Database port | `5432` |

**Notes:**
- Partitioned table for performance with large event volumes
- Most frequently accessed database
- Consider dedicated disk/SSD for production

### Contracts Database

**Purpose**: Stores behavioral contracts and validation rules

| Variable | Type | Required | Description | Example |
|----------|------|----------|-------------|---------|
| `CONTRACTS_POSTGRES_DB` | string | Yes | Database name | `rasbhari_contracts` |
| `CONTRACTS_POSTGRES_USER` | string | Yes | Database username | `rasbhari` |
| `CONTRACTS_POSTGRES_PASSWORD` | string | Yes | Database password | `secure_password_123` |
| `CONTRACTS_POSTGRES_HOST` | string | Yes | Database host | `localhost` |
| `CONTRACTS_POSTGRES_PORT` | integer | Yes | Database port | `5432` |

**Notes:**
- Used by Sentinel and SentinelOC processes
- Low write volume, high read volume during validation

### Queue Database

**Purpose**: Tracks queue processing progress for all QueueProcessors

| Variable | Type | Required | Description | Example |
|----------|------|----------|-------------|---------|
| `QUEUE_POSTGRES_DB` | string | Yes | Database name | `rasbhari_queue` |
| `QUEUE_POSTGRES_USER` | string | Yes | Database username | `rasbhari` |
| `QUEUE_POSTGRES_PASSWORD` | string | Yes | Database password | `secure_password_123` |
| `QUEUE_POSTGRES_HOST` | string | Yes | Database host | `localhost` |
| `QUEUE_POSTGRES_PORT` | integer | Yes | Database port | `5432` |

**Notes:**
- Contains `queuestats` table
- Frequently updated by all QueueProcessors
- Small database (one row per processor)

### Main Database

**Purpose**: Primary database for general application data

| Variable | Type | Required | Description | Example |
|----------|------|----------|-------------|---------|
| `RASBHARI_POSTGRES_DB` | string | Yes | Database name | `rasbhari_main` |
| `RASBHARI_POSTGRES_USER` | string | Yes | Database username | `rasbhari` |
| `RASBHARI_POSTGRES_PASSWORD` | string | Yes | Database password | `secure_password_123` |
| `RASBHARI_POSTGRES_HOST` | string | Yes | Database host | `localhost` |
| `RASBHARI_POSTGRES_PORT` | integer | Yes | Database port | `5432` |

**Notes:**
- Used by various apps for general data storage
- Can be merged with other databases if desired

### Notifications Database

**Purpose**: Stores notification history and templates

| Variable | Type | Required | Description | Example |
|----------|------|----------|-------------|---------|
| `NOTIFICATIONS_POSTGRES_DB` | string | Yes | Database name | `rasbhari_notifications` |
| `NOTIFICATIONS_POSTGRES_USER` | string | Yes | Database username | `rasbhari` |
| `NOTIFICATIONS_POSTGRES_PASSWORD` | string | Yes | Database password | `secure_password_123` |
| `NOTIFICATIONS_POSTGRES_HOST` | string | Yes | Database host | `localhost` |
| `NOTIFICATIONS_POSTGRES_PORT` | integer | Yes | Database port | `5432` |

**Notes:**
- Used by Courier process
- Tracks sent notifications to prevent duplicates

### Thoughts Database

**Purpose**: Stores personal notes and thoughts

| Variable | Type | Required | Description | Example |
|----------|------|----------|-------------|---------|
| `THOUGHTS_POSTGRES_DB` | string | Yes | Database name | `rasbhari_thoughts` |
| `THOUGHTS_POSTGRES_USER` | string | Yes | Database username | `rasbhari` |
| `THOUGHTS_POSTGRES_PASSWORD` | string | Yes | Database password | `secure_password_123` |
| `THOUGHTS_POSTGRES_HOST` | string | Yes | Database host | `localhost` |
| `THOUGHTS_POSTGRES_PORT` | integer | Yes | Database port | `5432` |

**Notes:**
- Used by Thoughts app
- Can be merged with main database if preferred

### Database Best Practices

**Security:**
- Use strong passwords (16+ characters, mixed case, numbers, symbols)
- Different passwords for production vs development
- Never commit `.env` file to version control

**User Management:**
- Create dedicated `rasbhari` user instead of using `postgres`
- Grant only necessary privileges
- Use `md5` authentication for local connections

**Connection Pooling:**
- All databases on same host: Use `localhost`
- Remote databases: Use IP address or hostname
- Default port `5432` unless changed in PostgreSQL config

**Consolidation:**
If running on resource-constrained hardware, you can use fewer databases:
```bash
# Minimal setup (3 databases)
EVENTS_POSTGRES_DB=rasbhari_events      # Keep separate (large volume)
QUEUE_POSTGRES_DB=rasbhari_queue        # Keep separate (critical for recovery)
RASBHARI_POSTGRES_DB=rasbhari_main      # Merge contracts, notifications, thoughts
```

## Server Configuration

### SERVER_DEBUG

**Purpose**: Enable Flask debug mode

| Value | Type | Default | Description |
|-------|------|---------|-------------|
| `True` | boolean | `False` | Enable debug mode (auto-reload, detailed errors) |
| `False` | boolean | - | Production mode (recommended) |

**Examples:**
```bash
# Development
SERVER_DEBUG=True

# Production (recommended)
SERVER_DEBUG=False
```

**Notes:**
- Never use `True` in production
- Debug mode exposes sensitive information
- Auto-reloads server on code changes

### SERVER_PORT

**Purpose**: Port number for Flask web server

| Value | Type | Default | Description |
|-------|------|---------|-------------|
| `1024-65535` | integer | `5000` | Port to listen on |

**Examples:**
```bash
# Default
SERVER_PORT=5000

# Alternative (avoid conflicts)
SERVER_PORT=8080
```

**Notes:**
- Default: `5000`
- Must be available (not used by another service)
- Ports below 1024 require root privileges
- Update firewall rules if changed

## Notification Services

### SendGrid Email Configuration

**Purpose**: Send email notifications via SendGrid API

| Variable | Type | Required | Description | Example |
|----------|------|----------|-------------|---------|
| `SENDGRID_API_KEY` | string | Optional* | SendGrid API key | `SG.xxxxxxxxxxx` |
| `COURIER_SENDER_EMAIL` | string | Optional* | Verified sender email | `noreply@yourdomain.com` |
| `COURIER_RECEIVER_EMAIL` | string | Optional* | Default recipient email | `you@example.com` |

\* Required only if using Courier process for email notifications

**Setup:**
1. Sign up at https://sendgrid.com/ (free tier: 100 emails/day)
2. Create API key with "Mail Send" permissions
3. Verify sender email in SendGrid dashboard
4. Add to `.env`

**Examples:**
```bash
SENDGRID_API_KEY=SG.abcdefghijklmnopqrstuvwxyz1234567890
COURIER_SENDER_EMAIL=rasbhari@yourdomain.com
COURIER_RECEIVER_EMAIL=your-email@gmail.com
```

**Notes:**
- Free tier sufficient for personal use
- Sender email must be verified in SendGrid
- Can use same email for sender and receiver
- Courier process must be enabled to use

**Testing:**
```bash
# Create notification event
curl -X POST http://localhost:5000/events/ \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "test:notification",
    "description": "Test email",
    "tags": ["notification"]
  }'
```

## Apple Integration

### Apple Signing Server

**Purpose**: Sign iOS shortcuts for installation on iPhone/iWatch

| Variable | Type | Required | Description | Example |
|----------|------|----------|-------------|---------|
| `APPLE_SIGNING_SERVER_URL` | string | Optional* | macOS server hostname/IP | `macbook.local` |
| `APPLE_SIGNING_SERVER_PORT` | integer | Optional* | Server port | `5001` |

\* Required only if using iOS shortcuts functionality

**Setup:**
1. On macOS computer, run: `python util/apple-signing-server.py`
2. Note the hostname/IP and port
3. Add to `.env` on Raspberry Pi

**Examples:**
```bash
# Using hostname
APPLE_SIGNING_SERVER_URL=macbook.local
APPLE_SIGNING_SERVER_PORT=5001

# Using IP address
APPLE_SIGNING_SERVER_URL=192.168.1.50
APPLE_SIGNING_SERVER_PORT=5001
```

**Notes:**
- Mac and Raspberry Pi must be on same network
- Mac must be running signing server when creating shortcuts
- Only needed during shortcut creation (not for runtime)
- Shortcuts require Apple Developer certificate on Mac

## System Paths

### LOG_DIR

**Purpose**: Directory for all log files

| Value | Type | Required | Description | Example |
|-------|------|---------|-------------|---------|
| Absolute path | string | Yes | Directory for logs | `/home/pi/rasbhari/logs` |

**Examples:**
```bash
# Raspberry Pi
LOG_DIR=/home/pi/rasbhari/logs

# Generic Linux
LOG_DIR=/var/log/rasbhari

# Development
LOG_DIR=/tmp/rasbhari-logs
```

**Log Files Created:**
- `main.log` - All INFO+ messages from all components
- `warnings.log` - WARNING+ messages only
- `exceptions.log` - ERROR+ messages with stack traces
- `{ComponentName}.log` - Component-specific logs

**Notes:**
- Directory must exist before starting server
- Create with: `mkdir -p /home/pi/rasbhari/logs`
- Ensure write permissions: `chmod 755 /home/pi/rasbhari/logs`
- Logs rotate automatically (Python logging)
- Monitor disk space: `du -sh /home/pi/rasbhari/logs`

### SERVER_FILES_FOLDER

**Purpose**: Directory for file uploads and downloads

| Value | Type | Required | Description | Example |
|-------|------|---------|-------------|---------|
| Absolute path | string | Yes | Directory for files | `/home/pi/rasbhari/files` |

**Examples:**
```bash
# Raspberry Pi
SERVER_FILES_FOLDER=/home/pi/rasbhari/files

# Generic Linux
SERVER_FILES_FOLDER=/var/lib/rasbhari/files

# Development
SERVER_FILES_FOLDER=/tmp/rasbhari-files
```

**Used By:**
- Shortcuts app (stores `.shortcut` files)
- File download endpoint (`/download/<filename>`)
- Any custom apps that handle file uploads

**Notes:**
- Directory must exist before starting server
- Create with: `mkdir -p /home/pi/rasbhari/files`
- Ensure write permissions: `chmod 755 /home/pi/rasbhari/files`
- Clean up old files periodically

### RASBHARI_LOCAL_URL

**Purpose**: Base URL for accessing Rasbhari server

| Value | Type | Required | Description | Example |
|-------|------|---------|-------------|---------|
| hostname:port | string | Yes | Server URL | `rasbhari.local:5000` |

**Examples:**
```bash
# Using hostname
RASBHARI_LOCAL_URL=rasbhari.local:5000

# Using IP address
RASBHARI_LOCAL_URL=192.168.1.100:5000

# Custom port
RASBHARI_LOCAL_URL=rasbhari.local:8080
```

**Used By:**
- Shortcuts app (generates callback URLs)
- iOS shortcuts (for triggering events)
- External integrations

**Notes:**
- Must be accessible from devices that will use shortcuts
- Use `.local` hostname if mDNS is available
- Use IP address if hostname doesn't resolve

## Optional Services

### Heimdall Configuration

**Purpose**: Visual monitoring with object detection

Variables are configured in code, not `.env`. See `processes/heimdall/` for configuration.

**Optional Environment:**
```bash
# YOLO model path (auto-downloaded if not set)
YOLO_MODEL_PATH=/home/pi/rasbhari/models/yolo11n.pt
```

### Atmos Configuration

**Purpose**: BLE-based location tracking

Variables are configured in code, not `.env`. See `processes/atmos/` for configuration.

## Environment Files

### Production (.env)

```bash
# Database Configuration
EVENTS_POSTGRES_DB=rasbhari_events
EVENTS_POSTGRES_USER=rasbhari
EVENTS_POSTGRES_PASSWORD=prod_secure_password_123
EVENTS_POSTGRES_HOST=localhost
EVENTS_POSTGRES_PORT=5432

CONTRACTS_POSTGRES_DB=rasbhari_contracts
CONTRACTS_POSTGRES_USER=rasbhari
CONTRACTS_POSTGRES_PASSWORD=prod_secure_password_123
CONTRACTS_POSTGRES_HOST=localhost
CONTRACTS_POSTGRES_PORT=5432

QUEUE_POSTGRES_DB=rasbhari_queue
QUEUE_POSTGRES_USER=rasbhari
QUEUE_POSTGRES_PASSWORD=prod_secure_password_123
QUEUE_POSTGRES_HOST=localhost
QUEUE_POSTGRES_PORT=5432

RASBHARI_POSTGRES_DB=rasbhari_main
RASBHARI_POSTGRES_USER=rasbhari
RASBHARI_POSTGRES_PASSWORD=prod_secure_password_123
RASBHARI_POSTGRES_HOST=localhost
RASBHARI_POSTGRES_PORT=5432

NOTIFICATIONS_POSTGRES_DB=rasbhari_notifications
NOTIFICATIONS_POSTGRES_USER=rasbhari
NOTIFICATIONS_POSTGRES_PASSWORD=prod_secure_password_123
NOTIFICATIONS_POSTGRES_HOST=localhost
NOTIFICATIONS_POSTGRES_PORT=5432

THOUGHTS_POSTGRES_DB=rasbhari_thoughts
THOUGHTS_POSTGRES_USER=rasbhari
THOUGHTS_POSTGRES_PASSWORD=prod_secure_password_123
THOUGHTS_POSTGRES_HOST=localhost
THOUGHTS_POSTGRES_PORT=5432

# Server Configuration
SERVER_DEBUG=False
SERVER_PORT=5000

# Paths
LOG_DIR=/home/pi/rasbhari/logs
SERVER_FILES_FOLDER=/home/pi/rasbhari/files
RASBHARI_LOCAL_URL=rasbhari.local:5000

# SendGrid (Optional)
SENDGRID_API_KEY=SG.your_production_api_key_here
COURIER_SENDER_EMAIL=rasbhari@yourdomain.com
COURIER_RECEIVER_EMAIL=your-email@example.com

# Apple Signing (Optional)
APPLE_SIGNING_SERVER_URL=macbook.local
APPLE_SIGNING_SERVER_PORT=5001
```

### Development (.env.dev)

```bash
# Database Configuration (use 'postgres' user for dev)
EVENTS_POSTGRES_DB=rasbhari_events_dev
EVENTS_POSTGRES_USER=postgres
EVENTS_POSTGRES_PASSWORD=dev_password
EVENTS_POSTGRES_HOST=localhost
EVENTS_POSTGRES_PORT=5432

CONTRACTS_POSTGRES_DB=rasbhari_contracts_dev
CONTRACTS_POSTGRES_USER=postgres
CONTRACTS_POSTGRES_PASSWORD=dev_password
CONTRACTS_POSTGRES_HOST=localhost
CONTRACTS_POSTGRES_PORT=5432

QUEUE_POSTGRES_DB=rasbhari_queue_dev
QUEUE_POSTGRES_USER=postgres
QUEUE_POSTGRES_PASSWORD=dev_password
QUEUE_POSTGRES_HOST=localhost
QUEUE_POSTGRES_PORT=5432

RASBHARI_POSTGRES_DB=rasbhari_main_dev
RASBHARI_POSTGRES_USER=postgres
RASBHARI_POSTGRES_PASSWORD=dev_password
RASBHARI_POSTGRES_HOST=localhost
RASBHARI_POSTGRES_PORT=5432

NOTIFICATIONS_POSTGRES_DB=rasbhari_notifications_dev
NOTIFICATIONS_POSTGRES_USER=postgres
NOTIFICATIONS_POSTGRES_PASSWORD=dev_password
NOTIFICATIONS_POSTGRES_HOST=localhost
NOTIFICATIONS_POSTGRES_PORT=5432

THOUGHTS_POSTGRES_DB=rasbhari_thoughts_dev
THOUGHTS_POSTGRES_USER=postgres
THOUGHTS_POSTGRES_PASSWORD=dev_password
THOUGHTS_POSTGRES_HOST=localhost
THOUGHTS_POSTGRES_PORT=5432

# Server Configuration
SERVER_DEBUG=True
SERVER_PORT=5000

# Paths
LOG_DIR=/tmp/rasbhari-logs
SERVER_FILES_FOLDER=/tmp/rasbhari-files
RASBHARI_LOCAL_URL=localhost:5000

# SendGrid (use test mode)
SENDGRID_API_KEY=SG.test_api_key
COURIER_SENDER_EMAIL=test@example.com
COURIER_RECEIVER_EMAIL=developer@example.com

# Apple Signing (local Mac)
APPLE_SIGNING_SERVER_URL=localhost
APPLE_SIGNING_SERVER_PORT=5001
```

### Testing (.env.test)

```bash
# Use in-memory or test databases
EVENTS_POSTGRES_DB=rasbhari_test_events
EVENTS_POSTGRES_USER=postgres
EVENTS_POSTGRES_PASSWORD=test
EVENTS_POSTGRES_HOST=localhost
EVENTS_POSTGRES_PORT=5432

# ... (minimal config for testing)

SERVER_DEBUG=True
SERVER_PORT=5001  # Different port to avoid conflicts
LOG_DIR=/tmp/rasbhari-test-logs
SERVER_FILES_FOLDER=/tmp/rasbhari-test-files
```

## Security Best Practices

### Password Security

❌ **Bad:**
```bash
EVENTS_POSTGRES_PASSWORD=password123
EVENTS_POSTGRES_PASSWORD=rasbhari
```

✅ **Good:**
```bash
EVENTS_POSTGRES_PASSWORD=r@5Bh4r1_Ev3nT5_sEcUr3_P@ssW0rD_2024!
```

**Guidelines:**
- Minimum 16 characters
- Mix of uppercase, lowercase, numbers, symbols
- Unique per environment (dev vs prod)
- Use password manager or generator

### API Key Security

❌ **Bad:**
```bash
# Don't commit .env file
git add .env
```

✅ **Good:**
```bash
# Add to .gitignore
echo ".env" >> .gitignore

# Only commit .env.example
git add .env.example
```

### File Permissions

```bash
# Restrict .env to owner only
chmod 600 .env

# Verify
ls -la .env
# Should show: -rw------- (600)
```

### Environment Separation

Use different `.env` files per environment:

```bash
# Development
ln -sf .env.dev .env

# Production
ln -sf .env.prod .env

# Testing
ln -sf .env.test .env
```

### Secrets Management

For production deployments, consider:

1. **Environment variables** (not files):
   ```bash
   export EVENTS_POSTGRES_PASSWORD="secure_pass"
   python server.py
   ```

2. **Secret management tools**:
   - HashiCorp Vault
   - AWS Secrets Manager
   - Azure Key Vault

3. **Docker secrets** (if using containers):
   ```yaml
   services:
     rasbhari:
       secrets:
         - db_password
   secrets:
     db_password:
       external: true
   ```

## Examples

### Minimal Setup

```bash
# Required variables only
EVENTS_POSTGRES_DB=rasbhari_events
EVENTS_POSTGRES_USER=rasbhari
EVENTS_POSTGRES_PASSWORD=your_password
EVENTS_POSTGRES_HOST=localhost
EVENTS_POSTGRES_PORT=5432

QUEUE_POSTGRES_DB=rasbhari_queue
QUEUE_POSTGRES_USER=rasbhari
QUEUE_POSTGRES_PASSWORD=your_password
QUEUE_POSTGRES_HOST=localhost
QUEUE_POSTGRES_PORT=5432

RASBHARI_POSTGRES_DB=rasbhari_main
RASBHARI_POSTGRES_USER=rasbhari
RASBHARI_POSTGRES_PASSWORD=your_password
RASBHARI_POSTGRES_HOST=localhost
RASBHARI_POSTGRES_PORT=5432

LOG_DIR=/home/pi/rasbhari/logs
SERVER_FILES_FOLDER=/home/pi/rasbhari/files
RASBHARI_LOCAL_URL=rasbhari.local:5000
```

### Full Setup with All Features

See "Production (.env)" example above.

### Remote Database

```bash
# Database on separate server
EVENTS_POSTGRES_DB=rasbhari_events
EVENTS_POSTGRES_USER=rasbhari
EVENTS_POSTGRES_PASSWORD=your_password
EVENTS_POSTGRES_HOST=192.168.1.200  # Database server IP
EVENTS_POSTGRES_PORT=5432

# ... (same for other databases)
```

### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'
services:
  rasbhari:
    build: .
    environment:
      - EVENTS_POSTGRES_DB=rasbhari_events
      - EVENTS_POSTGRES_USER=rasbhari
      - EVENTS_POSTGRES_PASSWORD=${DB_PASSWORD}
      - EVENTS_POSTGRES_HOST=db
      - EVENTS_POSTGRES_PORT=5432
      # ... (other variables)
    depends_on:
      - db

  db:
    image: postgres:14
    environment:
      - POSTGRES_PASSWORD=${DB_PASSWORD}
```

```bash
# .env for docker-compose
DB_PASSWORD=secure_password_123
```

## Troubleshooting

### Variable Not Loading

**Problem**: Changes to `.env` not taking effect

**Solutions:**
```bash
# Restart server
python server.py

# Or if using systemd:
sudo systemctl restart rasbhari

# Verify variable is set:
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('SERVER_PORT'))"
```

### Database Connection Failed

**Problem**: "could not connect to server"

**Check:**
```bash
# Verify variables are set correctly
cat .env | grep POSTGRES

# Test database connection manually
psql -U rasbhari -d rasbhari_events -h localhost
```

### Wrong File Path

**Problem**: "FileNotFoundError: [Errno 2] No such file or directory"

**Check:**
```bash
# Verify directories exist
ls -la $LOG_DIR
ls -la $SERVER_FILES_FOLDER

# Create if missing
mkdir -p ~/rasbhari/logs
mkdir -p ~/rasbhari/files
```

## Related Documentation

- [Setup Guide](SETUP.md) - Complete installation instructions
- [Main README](readme.md) - Project overview
- [.env.example](.env.example) - Template file

---

**Need help?** Check the logs in `$LOG_DIR` or open an issue on GitHub.
