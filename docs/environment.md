# Environment Variables Reference

This file documents the variables currently used by the codebase.

## Database Variables

Each `DB("<name>")` call maps to:

```text
<NAME>_POSTGRES_DB
<NAME>_POSTGRES_USER
<NAME>_POSTGRES_PASSWORD
<NAME>_POSTGRES_HOST
<NAME>_POSTGRES_PORT
```

Hosted demo shortcut:

- `DATABASE_URL`

If a specific `<NAME>_POSTGRES_*` block is unset, Rasbhari falls back to `DATABASE_URL`.
This is useful for temporary hosted deployments on platforms like Render where one PostgreSQL database is enough for a public trial instance.
In that mode, all Rasbhari tables live in the same PostgreSQL database.

## Databases Currently Used

### Events

Used by `EventService`.

- `EVENTS_POSTGRES_DB`
- `EVENTS_POSTGRES_USER`
- `EVENTS_POSTGRES_PASSWORD`
- `EVENTS_POSTGRES_HOST`
- `EVENTS_POSTGRES_PORT`

### Queue

Used by `QueueService` for `queuestats`.

- `QUEUE_POSTGRES_DB`
- `QUEUE_POSTGRES_USER`
- `QUEUE_POSTGRES_PASSWORD`
- `QUEUE_POSTGRES_HOST`
- `QUEUE_POSTGRES_PORT`

### Rasbhari

Used by most app data:

- activities
- blogs
- devices
- projects
- promises
- skills
- skill history
- timeline items

Variables:

- `RASBHARI_POSTGRES_DB`
- `RASBHARI_POSTGRES_USER`
- `RASBHARI_POSTGRES_PASSWORD`
- `RASBHARI_POSTGRES_HOST`
- `RASBHARI_POSTGRES_PORT`

### Notifications

Used by `NotificationService`.

- `NOTIFICATIONS_POSTGRES_DB`
- `NOTIFICATIONS_POSTGRES_USER`
- `NOTIFICATIONS_POSTGRES_PASSWORD`
- `NOTIFICATIONS_POSTGRES_HOST`
- `NOTIFICATIONS_POSTGRES_PORT`

### Thoughts

Used by `ThoughtService`.

- `THOUGHTS_POSTGRES_DB`
- `THOUGHTS_POSTGRES_USER`
- `THOUGHTS_POSTGRES_PASSWORD`
- `THOUGHTS_POSTGRES_HOST`
- `THOUGHTS_POSTGRES_PORT`

## Server Variables

- `SERVER_DEBUG`
- `SERVER_PORT`
- `PORT`
- `RASBHARI_DISABLE_PROCESSES`
- `SERVER_FILES_FOLDER`
- `FLASK_SECRET_KEY`
- `OPEN_WEBUI_URL`
- `OLLAMA_BASE_URL`
- `OLLAMA_COMMAND_MODEL`
- `OLLAMA_TIMEOUT_SECONDS`
- `RASBHARI_VERSION`

Sandbox note:

- the disposable test instance uses the same variable names in a dedicated `.env.test`
- see [testing-sandbox.md](testing-sandbox.md) and [.env.test.example](../.env.test.example)

Notes:

- `/chat` redirects to `OPEN_WEBUI_URL`
- `/assistant/command` uses `OLLAMA_BASE_URL` and `OLLAMA_COMMAND_MODEL`
- `RASBHARI_VERSION` can be set explicitly in deployments that do not ship `.git`; otherwise Rasbhari falls back to the current git commit when available
- hosted platforms like Render and Koyeb commonly inject `PORT`; Rasbhari now uses `PORT` first and falls back to `SERVER_PORT`
- set `RASBHARI_DISABLE_PROCESSES=true` for a secondary UI-only instance that points at the same database while the Raspberry Pi keeps running the background processors
- See [docs/AI.md](docs/AI.md) for how the assistant uses these values inside the Rasbhari command pipeline
- `FLASK_SECRET_KEY` should be set explicitly outside local development

## Logging

- `LOG_DIR`
  Optional. If unset, Rasbhari falls back to stdout/stderr logging, which is suitable for platforms like Render.

## rTV Torrent Diagnostics

- `RTV_METADATA_TIMEOUT_SECONDS`
- `RTV_METADATA_PROBE_TIMEOUT_SECONDS`
- `RTV_LISTEN_INTERFACES`
- `RTV_OUTGOING_INTERFACE`

Notes:

- `RTV_METADATA_TIMEOUT_SECONDS` controls how long full metadata resolution waits.
- `RTV_METADATA_PROBE_TIMEOUT_SECONDS` controls the short debug probe window.
- `RTV_LISTEN_INTERFACES` controls the libtorrent listen bind string.
- `RTV_OUTGOING_INTERFACE` can force libtorrent to use a specific LAN interface if it keeps announcing from loopback.

Gabru writes:

- `main.log`
- `warnings.log`
- `exceptions.log`
- one log file per logger, for example `Courier.log`

## Backups

- `RASBHARI_BACKUP_DIR`
- `RASBHARI_BACKUP_RETENTION_DAYS`
- `RASBHARI_BACKUP_SCRIPT`
- `RASBHARI_BACKUP_INTERVAL_SECONDS`
- `RASBHARI_BACKUP_POLL_SECONDS`
- `RASBHARI_BACKUP_STATUS_FILE`

Notes:

- `scripts/backup_rasbhari_postgres.sh` uses these values
- `RASBHARI_BACKUP_DIR` should point to persistent storage on the Raspberry Pi
- `RASBHARI_BACKUP_RETENTION_DAYS` controls how long timestamped backup directories are retained before pruning
- `BackupScheduler` can run the existing backup script from inside Rasbhari's process manager using `RASBHARI_BACKUP_INTERVAL_SECONDS`
- `RASBHARI_BACKUP_STATUS_FILE` stores the last success or failure snapshot surfaced in the admin and process views
- See [backup-restore.md](backup-restore.md) for the full workflow

## Admin Updates

- `RASBHARI_UPDATE_REPO_DIR`
- `RASBHARI_UPDATE_SCRIPT`
- `RASBHARI_UPDATE_REMOTE`
- `RASBHARI_UPDATE_BRANCH`
- `RASBHARI_UPDATE_SERVICE_NAME`
- `RASBHARI_UPDATE_HEALTHCHECK_URL`
- `RASBHARI_UPDATE_VALIDATION_CMD`
- `RASBHARI_UPDATE_HEALTHCHECK_ATTEMPTS`
- `RASBHARI_UPDATE_HEALTHCHECK_DELAY_SECONDS`

Notes:

- The admin control plane uses these values to compare the current local commit with the latest remote commit and to trigger a deterministic host-side update flow.
- `RASBHARI_UPDATE_SCRIPT` should point at `scripts/update_rasbhari_host.sh` inside the deployed repo unless you intentionally wrap it with your own host script.
- The update script refuses to run when the repo working tree is dirty, but chmod-only mode flips on scripts are ignored so accidental execute-bit changes do not block deployment.
- The script fetches the target branch, validates the checkout, restarts the configured service, and rolls back to the previous commit if the health check fails.
- `RASBHARI_UPDATE_VALIDATION_CMD` runs inside the repo directory before restart; keep it lightweight and deterministic for Raspberry Pi use.

## Courier / Notifications

- `NTFY_BASE_URL`
- `NTFY_TOPIC`
- `COURIER_SENDER_EMAIL`
- `COURIER_RECEIVER_EMAIL`
- `SENDGRID_API_KEY`

Notes:

- ntfy.sh is the default delivery path
- `NTFY_BASE_URL` lets you point Courier to a self-hosted ntfy instance
- SendGrid is only used when the event has the `email` tag
- Courier classifies notifications as `urgent`, `today`, `review`, `suggestion`, `digest`, or `system` using `notification_class:<class>` tags

## Example Minimal Local Setup

```bash
EVENTS_POSTGRES_DB=rasbhari_events
EVENTS_POSTGRES_USER=postgres
EVENTS_POSTGRES_PASSWORD=postgres
EVENTS_POSTGRES_HOST=localhost
EVENTS_POSTGRES_PORT=5432

QUEUE_POSTGRES_DB=rasbhari_queue
QUEUE_POSTGRES_USER=postgres
QUEUE_POSTGRES_PASSWORD=postgres
QUEUE_POSTGRES_HOST=localhost
QUEUE_POSTGRES_PORT=5432

RASBHARI_POSTGRES_DB=rasbhari_main
RASBHARI_POSTGRES_USER=postgres
RASBHARI_POSTGRES_PASSWORD=postgres
RASBHARI_POSTGRES_HOST=localhost
RASBHARI_POSTGRES_PORT=5432

NOTIFICATIONS_POSTGRES_DB=rasbhari_notifications
NOTIFICATIONS_POSTGRES_USER=postgres
NOTIFICATIONS_POSTGRES_PASSWORD=postgres
NOTIFICATIONS_POSTGRES_HOST=localhost
NOTIFICATIONS_POSTGRES_PORT=5432

THOUGHTS_POSTGRES_DB=rasbhari_thoughts
THOUGHTS_POSTGRES_USER=postgres
THOUGHTS_POSTGRES_PASSWORD=postgres
THOUGHTS_POSTGRES_HOST=localhost
THOUGHTS_POSTGRES_PORT=5432

LOG_DIR=/tmp/rasbhari/logs
RASBHARI_BACKUP_DIR=/var/backups/rasbhari
RASBHARI_BACKUP_RETENTION_DAYS=14
RASBHARI_BACKUP_SCRIPT=~/Desktop/apps/integrity/scripts/backup_rasbhari_postgres.sh
RASBHARI_BACKUP_INTERVAL_SECONDS=7200
RASBHARI_BACKUP_POLL_SECONDS=60
RASBHARI_BACKUP_STATUS_FILE=/tmp/rasbhari/files/rasbhari-backup-status.json
RASBHARI_UPDATE_REPO_DIR=~/Desktop/apps/integrity
RASBHARI_UPDATE_SCRIPT=~/Desktop/apps/integrity/scripts/update_rasbhari_host.sh
RASBHARI_UPDATE_REMOTE=origin
RASBHARI_UPDATE_BRANCH=main
RASBHARI_UPDATE_SERVICE_NAME=rasbhari
RASBHARI_UPDATE_HEALTHCHECK_URL=http://127.0.0.1:5000/login
RASBHARI_UPDATE_VALIDATION_CMD=python3 -m py_compile server.py
RASBHARI_UPDATE_HEALTHCHECK_ATTEMPTS=12
RASBHARI_UPDATE_HEALTHCHECK_DELAY_SECONDS=5
SERVER_FILES_FOLDER=/tmp/rasbhari/files
SERVER_PORT=5000
SERVER_DEBUG=False
RASBHARI_DISABLE_PROCESSES=False
FLASK_SECRET_KEY=replace-me
NTFY_BASE_URL=https://ntfy.sh
NTFY_TOPIC=rasbhari-alerts
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_COMMAND_MODEL=qwen2.5:7b-instruct
OLLAMA_TIMEOUT_SECONDS=20
RASBHARI_VERSION=
```
