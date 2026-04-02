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
- See [docs/AI.md](docs/AI.md) for how the assistant uses these values inside the Rasbhari command pipeline
- `FLASK_SECRET_KEY` should be set explicitly outside local development

## Logging

- `LOG_DIR`

Gabru writes:

- `main.log`
- `warnings.log`
- `exceptions.log`
- one log file per logger, for example `Courier.log`

## Backups

- `RASBHARI_BACKUP_DIR`
- `RASBHARI_BACKUP_RETENTION_DAYS`

Notes:

- `scripts/backup_rasbhari_postgres.sh` uses these values
- `RASBHARI_BACKUP_DIR` should point to persistent storage on the Raspberry Pi
- `RASBHARI_BACKUP_RETENTION_DAYS` controls how long timestamped backup directories are retained before pruning
- See [backup-restore.md](backup-restore.md) for the full workflow

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
SERVER_FILES_FOLDER=/tmp/rasbhari/files
SERVER_PORT=5000
SERVER_DEBUG=False
FLASK_SECRET_KEY=replace-me
NTFY_BASE_URL=https://ntfy.sh
NTFY_TOPIC=rasbhari-alerts
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_COMMAND_MODEL=qwen2.5:7b-instruct
OLLAMA_TIMEOUT_SECONDS=20
RASBHARI_VERSION=
```
