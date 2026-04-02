# Rasbhari Setup Guide

Rasbhari is a modular, event-driven Application OS built on the Gabru Framework. This guide will help you set up the environment from scratch.

## 1. System Requirements

- **Python**: `3.14+`
- **uv**: package and project manager (replaces pip/venv)
- **PostgreSQL**: `12+`
- **OS**: Linux (Ubuntu/Debian/Raspberry Pi OS) or macOS.

## 2. Quick Start with Docker (recommended)

The fastest way to get Rasbhari running locally is with Docker Compose — it handles Postgres setup, database creation, and the app in one command.

```bash
docker compose up --build
```

This will:
- Start a Postgres 16 container and create all 5 databases automatically
- Build and start the Rasbhari app on `http://localhost:5000`
- Persist database data in a named Docker volume (`postgres_data`)

To override env vars (e.g. `FLASK_SECRET_KEY`, `NTFY_TOPIC`), uncomment the relevant lines in `docker-compose.yml` or pass them via shell:

```bash
FLASK_SECRET_KEY=my-secret docker compose up
```

To stop and remove containers (data volume is preserved):

```bash
docker compose down
```

---

## 3. Manual Installation

### 3.1 System Requirements

- **Python**: `3.14+`
- **uv**: `1.0+` — install via `curl -LsSf https://astral.sh/uv/install.sh | sh` (macOS/Linux)
- **PostgreSQL**: `12+`
- **OS**: Linux (Ubuntu/Debian/Raspberry Pi OS) or macOS.

### 3.2 Install dependencies

```bash
# Clone the repository
git clone <your-repo-url> integrity
cd integrity

# uv creates the venv and installs all dependencies from uv.lock
uv sync
```

uv will automatically use the Python version specified in `.python-version` (`3.14`). To run any command inside the managed environment use `uv run`:

```bash
uv run python server.py
```

### 3.3 Database Configuration

Rasbhari uses a multi-tenant database architecture. You need to create 5 distinct databases:

```sql
-- Run these as postgres superuser
CREATE DATABASE rasbhari;
CREATE DATABASE events;
CREATE DATABASE queue;
CREATE DATABASE notifications;
CREATE DATABASE thoughts;
```

### 3.4 Environment Setup

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

#### Essential Variables to Set:
- **DB Settings**: Update `*_POSTGRES_DB`, `*_POSTGRES_USER`, and `*_POSTGRES_PASSWORD` for all 5 databases.
- **Security**: Set a strong `FLASK_SECRET_KEY`.
- **Paths**: Set `LOG_DIR` and `SERVER_FILES_FOLDER` to valid absolute paths.
- **Backups**: Set `RASBHARI_BACKUP_DIR` to persistent storage and review [backup-restore.md](backup-restore.md).

## 4. First Run & User Approval

1. **Start the server**:
   ```bash
   uv run python server.py
   ```
2. **Create your account**:
   - Navigate to `http://localhost:5000/signup`.
   - The first user created in the system is automatically considered an admin.
3. **Approval Flow**:
   - Subsequent users who sign up will see a "Pending Approval" message.
   - Admins can approve users via the database (setting `is_active = True` in the `users` table) or via the Admin dashboard (if enabled).

### Claiming Existing Events
If you have events that were created before user-scoping was enabled, run this SQL to associate them with your account:
```sql
UPDATE events SET user_id = (SELECT id FROM users WHERE username = 'your_username') WHERE user_id IS NULL;
```

## 5. Deploying to fly.io

### 5.1 Prerequisites

```bash
brew install flyctl       # macOS
fly auth login
```

### 5.2 Create the app and postgres instance

```bash
# Create the app (skips the launch wizard)
fly launch --no-deploy

# Create a fly-managed postgres cluster in Amsterdam
fly postgres create --name rasbhari-db --region ams

# Connect to postgres and create the four additional databases
fly postgres connect -a rasbhari-db
```

Inside the psql session:

```sql
CREATE DATABASE events;
CREATE DATABASE queue;
CREATE DATABASE notifications;
CREATE DATABASE thoughts;
\q
```

### 5.3 Set secrets

All sensitive values are injected as secrets so they never appear in `fly.toml`.
Replace the placeholder values below with the connection details from `fly postgres create` output.

```bash
fly secrets set \
  FLASK_SECRET_KEY="replace-with-strong-key" \
  RASBHARI_POSTGRES_DB="rasbhari" \
  RASBHARI_POSTGRES_USER="postgres" \
  RASBHARI_POSTGRES_PASSWORD="<pg-password>" \
  RASBHARI_POSTGRES_HOST="rasbhari-db.flycast" \
  EVENTS_POSTGRES_DB="events" \
  EVENTS_POSTGRES_USER="postgres" \
  EVENTS_POSTGRES_PASSWORD="<pg-password>" \
  EVENTS_POSTGRES_HOST="rasbhari-db.flycast" \
  QUEUE_POSTGRES_DB="queue" \
  QUEUE_POSTGRES_USER="postgres" \
  QUEUE_POSTGRES_PASSWORD="<pg-password>" \
  QUEUE_POSTGRES_HOST="rasbhari-db.flycast" \
  NOTIFICATIONS_POSTGRES_DB="notifications" \
  NOTIFICATIONS_POSTGRES_USER="postgres" \
  NOTIFICATIONS_POSTGRES_PASSWORD="<pg-password>" \
  NOTIFICATIONS_POSTGRES_HOST="rasbhari-db.flycast" \
  THOUGHTS_POSTGRES_DB="thoughts" \
  THOUGHTS_POSTGRES_USER="postgres" \
  THOUGHTS_POSTGRES_PASSWORD="<pg-password>" \
  THOUGHTS_POSTGRES_HOST="rasbhari-db.flycast"
```

### 5.4 Deploy

```bash
fly deploy
```

The app will be available at `https://rasbhari.fly.dev`. A persistent volume (`rasbhari_data`) is automatically created for logs and uploaded files at `/data`.

---

## 6. Public Access (Optional)

To access your Rasbhari instance from outside your local network using ngrok:

1. Install ngrok: `brew install ngrok/ngrok/ngrok` (macOS) or follow Linux instructions.
2. Authenticate: `ngrok config add-authtoken <YOUR_TOKEN>`
3. Start tunnel: `ngrok http 5000`

## 7. Backups And Restore

If you are running Rasbhari on a Raspberry Pi or any long-lived personal host, define a real PostgreSQL backup path before you rely on the system remotely.

Recommended backup command:

```bash
./scripts/backup_rasbhari_postgres.sh
```

Recommended env:

```bash
RASBHARI_BACKUP_DIR=/var/backups/rasbhari
RASBHARI_BACKUP_RETENTION_DAYS=14
```

The full workflow, including restore steps and verification, is documented in [backup-restore.md](backup-restore.md).

## 8. Verification

### Test Event Creation
```bash
curl -X POST http://localhost:5000/events/ \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "system:ping",
    "description": "Rasbhari Heartbeat",
    "tags": "setup, test"
  }'
```

---
**Note**: Rasbhari is designed for the **Gabru Framework**. For architectural details, refer to `agents.md`.
