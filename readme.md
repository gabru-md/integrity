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
- Generates daily, weekly, and monthly behavioral mirror reports from current activity, thought, project, and skill signals.
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
- `Connections`
- `Reports`
- `Users`
- `Network-Signatures`

See [apps/README.md](apps/README.md) for details.

## Current Background Processes

Rasbhari currently uses these background processes:

- `Courier`
- `PromiseProcessor`
- `ProjectUpdater`
- `SkillXPProcessor`
- `ReportProcessor`
- `Atmos`
- `Heimdall`
- `NetworkSniffer`

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

The admin `Processes` page also includes dependency health cards for configured external services such as OpenWebUI, ntfy, and SendGrid so operator mistakes and external outages are easier to spot.

The `Reports` app adds a local-first behavioral mirror. It currently computes:

- an `Integrity Score`
- `Stalled Intent` detection for active projects without matching progress signals
- neglected relationships based on connection cadence and last contact
- social balance based on interactions logged inside the Connections ledger
- event-weighted tag allocation
- skill XP earned from matched tagged events
- unfinished loop heuristics based on start/finish event patterns
- mood hints from thought keywords

If no connections are configured yet, the report explicitly marks social balance as a data gap instead of inventing certainty.

## Authentication, Signup, and Ownership

Rasbhari supports real sign-in accounts and a managed signup flow.

- **Signup & Approval**: New users can request access via the `/signup` page. These accounts are created in a pending state (`is_approved=False`) and cannot log in until an administrator approves them in the `Users` app.
- **Admin Creation**: Users created directly by administrators through the `Users` dashboard are automatically approved.
- **API Keys**: Every user also gets a generated 5-character `api_key`. Protected routes accept `X-API-Key: <key>` and `Authorization: ApiKey <key>`. Users can rotate their own key from `/users/profile`.
- **Data Ownership**: Every personal record is owned by a specific `user_id`.
- **Permissions**: Normal users can only read and write their own app data. Admin users can access system panels like `Processes`, `Devices`, and `Users`.
- **Private Data**: Admin access does not automatically bypass private data ownership checks.
- **Global Processes**: Global processes still run once for the whole system, but they process user-scoped work items by `user_id`.

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
  -H "X-API-Key: YOUR5K" \
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
  -H "X-API-Key: YOUR5K" \
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

### Create a connection

```bash
curl -X POST http://localhost:5000/connections/ \
  -H "X-API-Key: YOUR5K" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mom",
    "relationship_type": "Family",
    "cadence_days": 7,
    "priority": "High",
    "tags": ["family", "core"]
  }'
```

### Log a connection interaction

```bash
curl -X POST http://localhost:5000/connections/1/ledger \
  -H "X-API-Key: YOUR5K" \
  -H "Content-Type: application/json" \
  -d '{
    "interaction_type": "Call",
    "medium": "Phone",
    "duration_minutes": 35,
    "quality_score": 4,
    "tags": ["family", "support"]
  }'
```

### Generate a report

Queue report generation through the event pipeline:

```bash
curl -X POST http://localhost:5000/reports/generate \
  -H "X-API-Key: YOUR5K" \
  -H "Content-Type: application/json" \
  -d '{
    "report_type": "daily",
    "anchor_date": "2026-03-28",
    "async_mode": true
  }'
```

Generate one immediately and inspect the JSON response:

```bash
curl -X POST http://localhost:5000/reports/generate \
  -H "X-API-Key: YOUR5K" \
  -H "Content-Type: application/json" \
  -d '{
    "report_type": "weekly",
    "anchor_date": "2026-03-28",
    "async_mode": false
  }'
```

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
