# Apps

The `apps/` directory contains Rasbhari's application layer. Each app exposes a Flask blueprint, a service-backed CRUD API, a UI view, and optionally one or more background processes.

## How Apps Fit Together

```text
apps/*.py
    -> service instance
    -> Pydantic model
    -> optional custom routes
    -> optional registered background processes
```

Most apps are built directly with `gabru.flask.app.App`. A few extend it when they need a custom home page or extra routes.

Each app should now also expose user-facing instructions in the web UI via `user_guidance`. This is separate from developer documentation and should explain what the app is for, what important terms mean, and how a user should fill in the main fields.

## Currently Registered Apps

### 1. Blogs

- File: `apps/blogs.py`
- Model: `BlogPost`
- Widget: `timeline`
- Notes:
  - uses a custom blog home page
  - creates a `blog:posted` event on successful post creation

### 2. Promises

- File: `apps/promises.py`
- Model: `Promise`
- Widget: `kanban`
- Processes:
  - `PromiseProcessor`
- Notes:
  - custom home page with summary stats
  - includes refresh and history routes per promise

### 3. Events

- File: `apps/events.py`
- Model: `Event`
- Widget: `timeline`
- Processes:
  - `Courier`
- Notes:
  - incoming form tags are normalized to a tag list
  - timestamps are set on create

### 4. Thoughts

- File: `apps/thoughts.py`
- Model: `Thought`
- Widget: `timeline`
- Notes:
  - creates a `thought:posted` event when a thought is saved

### 5. Devices

- File: `apps/devices.py`
- Model: `Device`
- Widget: `kanban`
- Processes:
  - `Heimdall`
  - `Atmos`
- Notes:
  - adds Heimdall video and device-list routes

### 6. Projects

- File: `apps/projects.py`
- Model: `Project`
- Widget: `kanban`
- Processes:
  - `ProjectUpdater`
- Notes:
  - includes project detail and timeline routes
  - creates project progress events when timeline items are added

### 7. Activities

- File: `apps/activities.py`
- Model: `Activity`
- Widget: `timeline`
- Notes:
  - supports `/activities/trigger/<id>` to emit activity-backed events
  - normalizes `tags` and `default_payload`

### 8. Skills

- File: `apps/skills.py`
- Model: `Skill`
- Widget: `skill_tree`
- Processes:
  - `SkillXPProcessor`
- Notes:
  - dashboard widget combines progress rings and level-up history
  - supports explicit `tag_key` and `aliases` for matching
  - exposes `/skills/history`

### 9. Reports

- File: `apps/reports.py`
- Model: `Report`
- Widget: `basic`
- Processes:
  - `ReportProcessor`
- Notes:
  - exposes `/reports/generate` for synchronous or event-driven report generation
  - includes detail and print routes for local review and PDF export through the browser
  - aggregates current signals from projects, events, thoughts, skills, connections, and the interaction ledger inside Connections into a behavioral mirror

### 10. Connections

- File: `apps/connections.py`
- Model: `Connection`
- Widget: `basic`
- Notes:
  - stores people and relationship cadence targets
  - renders relationship records and their interaction timeline in one app surface
  - exposes `/connections/<id>/ledger` to create and inspect linked interactions
  - updates `last_contact_at` and emits social events when interactions are logged
  - feeds overdue-contact checks in behavioral reports

### 11. Users

- File: `apps/users.py`
- Model: `User`
- Widget: disabled
- Notes:
  - admin-only account management surface
  - creates and updates real Rasbhari login accounts
  - supports personal workspace ownership without giving admins access to other users' private app data

## User-Facing Instructions

`gabru.flask.app.App` now passes `user_guidance` into the app home template. The shared instructions panel can render:

- `overview`
- `how_to_use`
- `glossary`
- `examples`
- `fields`

Field descriptions are also derived automatically from Pydantic `Field(..., description="...")` metadata, so app authors should keep those descriptions user-friendly.

## Widget Types In Use

The current dashboard uses these widget types:

- `timeline`
- `kanban`
- `skill_tree`

The framework still supports the generic widget types exposed by `App.widget_data()`:

- `basic`
- `count`
- `timeline`
- `kanban`
- `progress_ring`

The dashboard home template also has a custom `skill_tree` rendering path for the Skills app.

## Standard API Endpoints

Every `App` instance provides these endpoints unless explicitly overridden:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/{app}/` | Create a record |
| `GET` | `/{app}/` | Fetch recent records |
| `GET` | `/{app}/<id>` | Fetch a single record |
| `PUT` | `/{app}/<id>` | Update a record |
| `DELETE` | `/{app}/<id>` | Delete a record |
| `GET` | `/{app}/home` | Render the app UI |
| `POST` | `/{app}/widget/enable` | Enable dashboard widget |
| `POST` | `/{app}/widget/disable` | Disable dashboard widget |

## App Authoring Checklist

When adding a new app:

1. Create a model in `model/`.
2. Create a service in `services/`.
3. Create the app in `apps/`.
4. Register it in [server.py](/Users/manish/PycharmProjects/integrity/server.py).
5. Add or update `user_guidance` so the app home page explains the app to end users.
6. Add user-friendly `description=` text to important Pydantic fields.
7. Update this file and the root [readme.md](/Users/manish/PycharmProjects/integrity/readme.md).
8. Update [.env.example](/Users/manish/PycharmProjects/integrity/.env.example) if the app adds environment requirements.
