# Setup Guide

This guide reflects the current codebase and environment model.

## System Requirements

- Python `3.8+`
- PostgreSQL `12+`
- Linux or Raspberry Pi OS
- enough disk for logs, PostgreSQL, and optional YOLO model downloads

Optional hardware:

- ESP32-CAM or other IP cameras for Heimdall
- BLE scanners/beacons for Atmos

## 1. Clone And Install

```bash
git clone <your-repo-url> integrity
cd integrity
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Create Databases

The current code expects these logical DB namespaces:

- `events`
- `queue`
- `rasbhari`
- `notifications`
- `thoughts`

Example:

```sql
CREATE DATABASE rasbhari_events;
CREATE DATABASE rasbhari_queue;
CREATE DATABASE rasbhari_main;
CREATE DATABASE rasbhari_notifications;
CREATE DATABASE rasbhari_thoughts;
```

## 3. Configure Environment

```bash
cp .env.example .env
```

Fill in:

- `EVENTS_POSTGRES_*`
- `QUEUE_POSTGRES_*`
- `RASBHARI_POSTGRES_*`
- `NOTIFICATIONS_POSTGRES_*`
- `THOUGHTS_POSTGRES_*`
- `LOG_DIR`
- `SERVER_FILES_FOLDER`

Optional:

- `NTFY_TOPIC`
- `SENDGRID_API_KEY`
- `COURIER_SENDER_EMAIL`
- `COURIER_RECEIVER_EMAIL`
- `OPEN_WEBUI_URL`
- `FLASK_SECRET_KEY`

## 4. Start Rasbhari

```bash
python server.py
```

Open:

- `http://localhost:5000/`

## 5. Verify

### Verify events

```bash
curl -X POST http://localhost:5000/events/ \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "setup:test",
    "description": "Rasbhari setup verification",
    "tags": "notification"
  }'
```

### Verify skills

```bash
curl -X POST http://localhost:5000/skills/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Python",
    "total_xp": 0,
    "requirement": "Complete 5 Python practice sessions"
  }'
```

## Optional Components

### Courier

Works with ntfy.sh by default.

For email delivery also set:

- `SENDGRID_API_KEY`
- `COURIER_SENDER_EMAIL`
- `COURIER_RECEIVER_EMAIL`

### Heimdall

Requires:

- camera devices enabled for `Heimdall`
- working `device.url` values
- `ultralytics` runtime dependencies

### Atmos

Requires:

- at least three devices with `coordinates`
- `device.url` endpoints returning BLE RSSI JSON

## Notes

- Queue processors checkpoint progress in `queue.queuestats`.
- The dashboard home page includes reliability cards and a universal timeline.
- Dashboard layout customization is persisted in browser local storage, not in PostgreSQL.
