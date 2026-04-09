# Rasbhari

Rasbhari is an event-driven personal operating system for Raspberry Pi and lightweight Linux hosts. It is designed to feel like one daily operating loop, not a set of disconnected apps: capture what happened, structure it, compare it against commitments, accumulate growth, reflect on the result, and act on what matters next. The product combines a Flask Today surface, an operational dashboard, contract-based framework primitives, PostgreSQL-backed runtime services, and background workers to track activities, projects, promises, notifications, devices, and skill progression.

For temporary hosted demos, Rasbhari can also fall back to a single shared PostgreSQL database through `DATABASE_URL`, which is useful on platforms like Render. The long-term intended home is still a user-owned Raspberry Pi or similar host.

Rasbhari now also has a formal pacing model documented in [experience-modes.md](experience-modes.md): the system should be deep by capability but shallow by default, with `Everyday`, `Structured`, and `System` tiers guiding which surfaces feel primary for different users.

Rasbhari now also defines `Automation` as a formal product vertical, documented in [automation.md](automation.md). Automation is the broader area responsible for reducing capture friction and turning trustworthy signals into real Rasbhari events, while `Capture Automation` is the first sub-track covering browser extensions, desktop agents, mobile shortcuts, and later sensor-based capture.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1%2B-green)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-12%2B-blue)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](license.md)

## What It Does

- Explains itself in-product as one event-driven ecosystem instead of a menu of unrelated tools.
- Gives the system one clear mental model: capture, structure, commit, grow, reflect, and act.
- Stores everything important as events.
- Uses queue processors to react to those events in the background.
- Exposes CRUD-style apps for core domains such as projects, promises, activities, and skills.
- Adds project-scoped kanban boards with minimal tickets that emit workflow events into the shared event bus.
- Lets projects declare shared focus tags so ticket moves and timeline updates can contribute directly to promises and skills through the same event bus.
- Generates daily, weekly, and monthly behavioral mirror reports from current activity, thought, project, and skill signals.
- Includes a consistent helper layer inside each app UI that explains what the app is for, how it connects to the rest of Rasbhari, and what setup makes it more useful.
- Provides a `Today` front door that unifies active work, due promises, neglected connections, suggested activities, and daily guidance.
- Keeps the shared shell intentionally lighter by prioritizing navigation over persistent explanatory chrome.
- Includes a first-run interactive tutorial that walks users through Today, Events, Activities, Projects, Kanban, Promises, Skills, and Reports in product order.
- Lets Today stage deterministic recommendation follow-ups such as creating a skill, promise, ticket, or project update, and now also suggests explicit ecosystem-linking edits like connecting promises to tags or adding matching tags to activities through the same assistant confirmation flow.
- Uses a central deterministic recommendation engine that ranks structured ecosystem-linking opportunities with app scope, item scope, priority, confidence, reasoning, and action metadata so future apps can plug into the same recommendation layer.
- Lets each user opt contextual recommendations in or out globally and set one global visible recommendation limit across Rasbhari, while keeping dismissals lightweight and temporary on the client side.
- Lets each user choose an `experience_mode` of `everyday`, `structured`, or `system`, which becomes the main pacing control for future navigation, density, onboarding, and recommendation behavior.
- Uses a shared inline recommendation component so app-level or item-level suggestions can be rendered consistently, dismissed temporarily, and either staged or directly applied depending on recommendation type.
- Preserves a separate operational dashboard with reliability cards, pinned widgets, drag reordering, action-first controls, and a universal timeline.
- Includes a low-friction macOS local signal collector that can autonomously emit normalized raw machine events into the event bus.
- Includes a rule-based session inference layer that turns raw local signals into grounded session boundary events such as coding, writing, planning, and research.
- Defines an `Automation` vertical so capture can become more ambient over time without breaking the event-first Rasbhari model.
- Uses a typed notification model so outbound alerts are classed as `urgent`, `today`, `review`, `suggestion`, `digest`, or `system` instead of a single generic stream.
- Includes a shared import foundation so future calendar, device, and external adapters normalize records once, dedupe them, and emit compatible events into the same event bus.
- Includes a native `Rasbhari AI` command layer that can interpret natural-language commands, route them through app-specific resolvers, and execute safe actions through the existing apps and event bus.
- Includes a safe admin-triggered update flow that compares the deployed repo commit with the latest remote commit and runs a script-backed upgrade with rollback on failed health checks.
- Runs comfortably on a Raspberry Pi while staying inspectable and hackable.

## Experience Modes

Rasbhari should not expose the whole machine equally to every user on day one.

The product now defines three formal experience modes:

- `Everyday`: calm daily-use surfaces such as `Today`, `Capture`, `Thoughts`, `Promises`, and `Reports`
- `Structured`: richer planning and ecosystem-linking surfaces such as `Projects`, `KanbanTickets`, `Activities`, `Skills`, and `Connections`
- `System`: operator and control-plane surfaces such as `Admin`, `Processes`, `Apps`, update flow, and backup/process visibility

This is a pacing model, not a capability split. Lower tiers should still feel complete, while deeper tiers reveal more of the Rasbhari system when the user actually wants it.

The full tier map and product rationale live in [experience-modes.md](experience-modes.md).

## Automation

Rasbhari should not depend forever on manual event entry for everything important.

The product now formally treats `Automation` as its own vertical. The goal is to reduce capture friction while keeping the system explainable, privacy-safe, and aligned with the existing event bus.

The first sub-track is `Capture Automation`, which covers:

- browser extensions as the first direct capture client
- desktop agents that can emit low-friction machine-side signals
- mobile shortcuts for quick assisted capture
- later environmental sensors and dedicated ambient devices

Automation is not meant to become a separate meaning system. It should prefer existing Activities where possible, emit real events, and let the rest of Rasbhari react normally. The full direction lives in [automation.md](automation.md).

Rasbhari now also exposes `/automation` as the in-product home for this vertical. That page introduces the Automation mental model, explains the browser-extension workflow, and will later surface connection and setup status as the Capture Automation client and APIs land.

## Current Apps

Rasbhari currently registers these apps in [server.py](server.py):

- `Blogs`
- `BrowserActions`
- `Promises`
- `Events`
- `Thoughts`
- `Devices`
- `Projects`
- `KanbanTickets`
- `Activities`
- `Skills`
- `Connections`
- `Reports`
- `Users`

The `Projects` app now includes a per-project board view backed by the `KanbanTickets` app.
The `BrowserActions` app is the first Rasbhari-side configuration layer for the future browser extension, letting each user define extension-visible actions that map generic browser verbs back into Activities, events, project updates, or quick-log flows.
Projects can also issue stable per-project ticket references through a configurable `ticket_prefix`, so tickets become identifiers like `RSB-14` or `QDS-123`.
Kanban tickets can also link explicit same-project dependencies, so a board card can show which other ticket must move first without turning the board into a separate planning tool.
The project timeline is now a narrative surface: lightweight updates stay inline, while blog-style writing creates real markdown `BlogPost` records that remain linked back into the project history.
The `Activities` app now exposes each activity as a visible orchestrator, showing the event type it emits plus the promises and skills that can react to that trigger.
Events now support a real structured `payload` field in addition to `event_type`, `description`, and `tags`, so activities, automations, imports, and future extensions can attach machine-readable context without stuffing JSON into the description text.
The `Reports` page now uses progressive disclosure so explanatory context and observation blocks stay available without overwhelming the summary view.
The `Thoughts` app now behaves more like a private personal posting stream than a generic notes CRUD page, with a lightweight composer and timestamped feed.
The `Skills` app now has a dedicated progress-focused page that mirrors the stronger dashboard widget language with XP rings, level momentum, and a level-up timeline while preserving the existing skill data model and CRUD flow.

## Current Background Processes

Rasbhari currently uses these background processes:

- `Courier`
- `SessionInferenceProcessor`
- `PromiseProcessor`
- `ProjectUpdater`
- `SkillXPProcessor`
- `ReportProcessor`
- `Atmos`
- `Heimdall`

See [processes/README.md](processes/README.md) for details.

## Today

The default home page is now `Today`, a focused daily control surface rather than a general dashboard. It currently brings together:

- active in-progress work from project boards
- prioritized tickets that are ready to start
- due promises
- neglected connections
- suggested activities
- high-signal guidance derived from the current state of work and commitments
- the latest report mirror when available

The goal of `Today` is to answer: what matters now, what is drifting, and what should move next.

It is also the clearest product framing surface. If a user forgets what Rasbhari is, `Today` should remind them that the rest of the apps exist to feed the same loop rather than compete for attention separately.

## First-Run Tutorial

Rasbhari now includes a first-run walkthrough for signed-in users. It is:

- product-focused
- non-AI
- lightweight and cross-app

The tutorial explains how the ecosystem works instead of just explaining individual forms. It now uses a lighter, less modal presentation so users can still see the current page while stepping through the guide. Completion is stored per user and can be reset from `/users/profile`.

The onboarding flow now starts with user goals rather than app architecture. A new user first chooses the kind of help they want from Rasbhari, the tutorial recommends a starting `experience_mode`, and the visible shell then re-paces itself around that depth before the walkthrough continues.

`Today` also includes a guided setup checklist so a new user can reach a minimum useful Rasbhari environment quickly. The checklist is state-aware and marks progress automatically as the user creates the first activity, project, promise, skill, ticket, and first ticket move.

## Admin Guide

Rasbhari also includes a separate admin-only guide at `/admin/guide`.

This path is distinct from the end-user tutorial and focuses on:

- process health
- notification delivery and signal quality
- user onboarding and approval flow
- app relationships inside the Rasbhari ecosystem
- operational setup and configuration hygiene

The admin guide is meant to explain how to operate Rasbhari, not how to use it as an end user.

For Raspberry Pi-hosted remote use, the operator runbook lives in [remote-pi-ops.md](remote-pi-ops.md). It documents the actual remote triage path, what to check first, which failures can be recovered from inside Rasbhari, and where the boundary shifts back to SSH or host access.

## Admin Control Plane

Rasbhari now includes an admin overview at `/admin`.

This is the operator front door for the Rasbhari ecosystem. It is meant to unify:

- app activation and registry state
- process runtime and queue recovery
- user stewardship and pending approvals
- dependency health and degraded capabilities
- stuck processors and operator-facing issues
- deployment update visibility and safe upgrade orchestration

The goal is to let admins oversee most Rasbhari-level operational work from inside Rasbhari itself instead of treating the web UI as read-only and the shell as the real control plane.

The admin overview is intentionally high-signal. It should quickly surface:

- degraded capabilities that affect the product loop
- enabled processors that are stopped and need recovery
- pending approvals that block onboarding
- operator-facing issues before they disappear into lower-level pages
- whether the deployed Raspberry Pi repo is behind the latest remote commit

For Pi-hosted remote use, the admin overview now also acts as a quick remote health snapshot:

- server availability, as observed by the fact that the admin surface is reachable
- event-flow freshness, so you can tell whether the system is still receiving signals
- queue drift, so backlog and stalled processing are visible quickly
- dependency issues, so external delivery or AI-related failures are obvious

It also exposes the most important Rasbhari-level recovery actions directly from the admin surface:

- restart stopped processors
- replay queue processors from zero
- jump queue processors to latest
- trigger a deterministic script-backed code update with rollback on failed health checks
- re-enable disabled apps

That means common product-level recovery should no longer require SSH most of the time.

Operational boundary:

- Inside Rasbhari: app activation, widget participation, process controls, queue recovery, dependency checks, approvals, and product-level health
- Outside Rasbhari: database repair, container or service restarts, backups, filesystem repair, package installation, and host-level networking

For Raspberry Pi-hosted deployments, use the documented PostgreSQL backup workflow in [backup-restore.md](backup-restore.md). The bundled [backup_rasbhari_postgres.sh](../scripts/backup_rasbhari_postgres.sh) script backs up all five Rasbhari databases, writes checksums and a manifest. Rasbhari can now schedule that host-side script through its own `BackupScheduler` process, while restore remains an explicit infrastructure operation.

## Dashboard

The operational dashboard is still available at `/dashboard`. It includes:

- `Reliability` row for processes, queue backlog, notifications, devices, and event flow
- `Pinned` widgets section
- drag reorder for the remaining widgets
- action-first widget controls such as quick event logging, thought capture, skill practice logging, and activity triggering
- a `Universal Timeline` that merges skills, projects, notifications, and recent events
- a floating `Rasbhari AI` command panel that can log events, trigger activities, create thoughts, and create promises using local Ollama-backed intent routing with per-app command resolvers

Widget pinning, collapsing, and ordering are persisted locally in the browser.

For remote use over Tailscale, Rasbhari now also exposes a dedicated `/capture` surface. It is intentionally narrower than Today or the full Events app:

- one-tap triggering for recent activities
- a compact direct event form
- recent event-type and tag suggestions from your own data

That keeps urgent remote logging on the normal event pipeline without requiring the full dashboard or shell access.

Rasbhari now also applies more progressive disclosure on dense pages so the first screen stays calmer:

- `Admin Overview` keeps live health visible, but collapses lower-signal reference and maintenance sections until needed
- `Processes` keeps recovery actions prominent while collapsing dependency detail and the full low-level registry
- `Promises` collapses the overview metrics so the actual promise cards stay primary

Each app home page also includes an `Instructions` block for end users. These in-app explanations are intentionally separate from developer docs and now follow one helper pattern:

- what the app is for
- how it fits the shared Rasbhari loop
- how it fits the Rasbhari ecosystem
- what setup makes it more useful
- what important terms mean
- what key fields do

Appearance is now its own first-class destination at `/appearance` instead of a nested sidebar subgroup. That keeps `Profile`, `Help`, and `Appearance` visually consistent and gives theme, density, surface, and motion controls a clearer home.

The admin `Processes` page also includes dependency health cards for configured external services such as OpenWebUI, ntfy, and SendGrid so operator mistakes and external outages are easier to spot.

For queue-backed workers, the `Processes` page now provides clearer maintenance actions for operational recovery:
- `Replay From 0` to rebuild a processor from the start of the queue
- `Replay From Exact ID` for targeted reprocessing
- `Jump To Latest` to skip backlog and resume from the newest known item
- `Restart` to recycle the running processor without dropping into the shell

These controls update persisted queue progress and reload the live processor state so recovery actions take effect immediately.

The admin `App Registry` is also operator-oriented now. It shows:
- which apps are active or disabled
- what resource each app owns
- which background workers the app depends on
- how the app participates in the dashboard and the wider ecosystem
- which other apps it works especially well with

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
- **Assistant Commands**: The `/assistant/command` route accepts natural-language commands, runs them through a local Ollama model, and then routes the plan through app-specific resolvers for `activities`, `promises`, `thoughts`, `events`, and `answer` before execution.
- **Kanban Events**: Ticket creation and state movement emit `kanban:ticket_created`, `kanban:ticket_moved`, and `kanban:ticket_updated` events with project and state tags.
- **Safe Staging**: Write actions are staged first. Rasbhari explains the planned change, then waits for explicit confirmation through the UI `Confirm Action` button or a short acknowledgement like `yes` or `thanks` before committing anything to the system.
- **AI Design Reference**: See [docs/AI.md](docs/AI.md) for the detailed architecture, staging model, resolver flow, current limits, and testing patterns.
- **Data Ownership**: Every personal record is owned by a specific `user_id`.
- **Permissions**: Normal users can only read and write their own app data. Admin users can access system panels like `Processes`, `Devices`, and `Users`.
- **Private Data**: Admin access does not automatically bypass private data ownership checks.
- **Global Processes**: Global processes still run once for the whole system, but they process user-scoped work items by `user_id`.

## Architecture

```text
Dashboard / Web UI
    -> Rasbhari app modules in apps/
    -> Rasbhari AI command layer
    -> Gabru framework contracts and Flask primitives
    -> Runtime providers and service implementations
    -> Pydantic models and PostgreSQL databases
    -> Background processes and queue processors
    -> Events emitted back into the system
```

Key building blocks:

- `gabru/` for framework contracts, Flask primitives, DB primitives, process management, and queue processing
- `runtime/` for Rasbhari-specific provider wiring that binds framework contracts to concrete services
- `services/` for concrete PostgreSQL-backed implementations and domain-side orchestration
- `model/` for Pydantic schemas used by the current Rasbhari implementation
- `services/assistant_command.py` for the AI command router that translates natural language into safe Rasbhari actions
- `services/assistant_resolvers.py` for app-specific routing decisions that let each domain claim a command before execution
- `docs/AI.md` for the detailed AI architecture and behavior contract
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
  Optional. If omitted, Rasbhari logs to stdout instead of file-backed logs, which is useful on hosted platforms such as Render.
- `SERVER_FILES_FOLDER`

Optional but useful:

- `NTFY_TOPIC`
- `SENDGRID_API_KEY`
- `COURIER_SENDER_EMAIL`
- `COURIER_RECEIVER_EMAIL`
- `OPEN_WEBUI_URL`
- `OLLAMA_BASE_URL`
- `OLLAMA_COMMAND_MODEL`
- `OLLAMA_TIMEOUT_SECONDS`
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

### Send an assistant command

```bash
curl -X POST http://localhost:5000/assistant/command \
  -H "X-API-Key: YOUR5K" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "litterbox cleaned"
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
- Rasbhari also has a subtle in-product notification tray in the shared shell for high-signal notices such as report generation, important admin/operator interruptions, and other UX feedback that should stay visible without becoming noisy.
- Some older docs used names like `Contracts` or `Shortcuts`; those are not part of the current registered application set.
