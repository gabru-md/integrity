# Rasbhari

Rasbhari is an event-driven personal operating system for Raspberry Pi and lightweight Linux hosts. It combines a Flask dashboard, PostgreSQL-backed services, and background workers to track activities, projects, promises, notifications, devices, and skill progression.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1%2B-green)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-12%2B-blue)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](license.md)

## What It Does

- Stores everything important as events.
- Uses queue processors to react to those events in the background.
- Exposes CRUD-style apps for core domains such as projects, promises, activities, and skills.
- Includes user-facing instructions inside each app UI so non-developers can understand the meaning of fields and terms.
- Provides a dashboard with reliability cards, pinned widgets, drag reordering, action-first controls, and a universal timeline.
- Runs comfortably on a Raspberry Pi while staying inspectable and hackable.

## Current Apps

Rasbhari currently registers these apps in [server.py](/Users/manish/PycharmProjects/integrity/server.py):

- `Blogs`
- `Promises`
- `Events`
- `Thoughts`
- `Devices`
- `Projects`
- `Activities`
- `Skills`

See [apps/README.md](apps/README.md) for details.

## Current Background Processes

Rasbhari currently uses these background processes:

- `Courier`
- `PromiseProcessor`
- `ProjectUpdater`
- `SkillXPProcessor`
- `Atmos`
- `Heimdall`

See [processes/README.md](processes/README.md) for details.

## Dashboard

The dashboard is now a control surface rather than a passive summary page. The home page includes:

- `Reliability` row for processes, queue backlog, notifications, devices, and event flow
- `Pinned` widgets section
- drag reorder for the remaining widgets
- action-first widget controls such as quick event logging, thought capture, skill practice logging, and activity triggering
- a `Universal Timeline` that merges skills, projects, notifications, and recent events

Widget pinning, collapsing, and ordering are persisted locally in the browser.

Each app home page also includes an `Instructions` block for end users. These in-app explanations are intentionally separate from developer docs and should explain what an app does, what important terms mean, and how to fill in the main fields.

## Architecture

```text
Dashboard / Web UI
    -> Flask Server and App blueprints
    -> Services and Pydantic models
    -> PostgreSQL databases
    -> Background processes and queue processors
    -> Events emitted back into the system
```

Key building blocks:

- `gabru/flask/` for server, app, model, and template helpers
- `gabru/db/` for DB connections and CRUD services
- `gabru/process.py` for daemon-style workers
- `gabru/qprocessor/` for database-backed queue processors

See [gabru/readme.md](gabru/readme.md) for the framework-level view.

## Databases

The current code uses these database namespaces:

- `events` for event history
- `queue` for queue processor progress (`queuestats`)
- `rasbhari` for most app data
- `notifications` for sent notification history
- `thoughts` for thoughts

Environment variable naming follows the `DBNAME_POSTGRES_*` pattern. See [ENVIRONMENT.md](ENVIRONMENT.md) and [.env.example](.env.example).

## Quick Start

### 1. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Create PostgreSQL databases

```sql
CREATE DATABASE rasbhari_events;
CREATE DATABASE rasbhari_queue;
CREATE DATABASE rasbhari_main;
CREATE DATABASE rasbhari_notifications;
CREATE DATABASE rasbhari_thoughts;
```

### 3. Configure environment

```bash
cp .env.example .env
```

Minimum required values:

- all `EVENTS_*`, `QUEUE_*`, `RASBHARI_*`, `NOTIFICATIONS_*`, and `THOUGHTS_*` DB variables
- `LOG_DIR`
- `SERVER_FILES_FOLDER`

Optional but useful:

- `NTFY_TOPIC`
- `SENDGRID_API_KEY`
- `COURIER_SENDER_EMAIL`
- `COURIER_RECEIVER_EMAIL`
- `OPEN_WEBUI_URL`
- `FLASK_SECRET_KEY`

### 4. Run the server

```bash
python server.py
```

Open `http://localhost:5000`.

## First Useful Tests

### Log an event

```bash
curl -X POST http://localhost:5000/events/ \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "learning:session",
    "description": "Read one chapter",
    "tags": "#python"
  }'
```

### Create a skill

```bash
curl -X POST http://localhost:5000/skills/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Python",
    "tag_key": "python",
    "aliases": ["py"],
    "total_xp": 0,
    "requirement": "Complete 5 Python practice sessions"
  }'
```

Once `SkillXPProcessor` is running, `#python` events award XP to the `Python` skill. Level-ups emit `skill:level_up` events, create skill history entries, and trigger Courier notifications because they are tagged with `notification`.

For multi-word skills, use a stable `tag_key`. Example:

- name: `Counter Strike`
- tag_key: `counterstrike`
- aliases: `["counter-strike", "cs2"]`

## Queue Processing Notes

Queue processors now checkpoint progress in batches:

- state is stored in the `queue.queuestats` table
- progress is flushed every 10 consumed items by default
- progress is also flushed when the queue becomes idle

This keeps replay windows bounded without turning every consumed event into a database write.

## Documentation Map

- [apps/README.md](apps/README.md)
- [processes/README.md](processes/README.md)
- [gabru/readme.md](gabru/readme.md)
- [gabru/flask/README.md](gabru/flask/README.md)
- [gabru/qprocessor/README.md](gabru/qprocessor/README.md)
- [SETUP.md](SETUP.md)
- [ENVIRONMENT.md](ENVIRONMENT.md)

## Notes

- The `chat` route redirects to `OPEN_WEBUI_URL` when configured.
- Notifications go to ntfy.sh by default; add the `email` tag to route through SendGrid instead.
- Some older docs used names like `Contracts` or `Shortcuts`; those are not part of the current registered application set.
