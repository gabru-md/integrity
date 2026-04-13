# Apps

The `apps/` directory contains Rasbhari's application layer. Each app exposes a Flask blueprint, a contract-backed CRUD API, a UI view, and optionally one or more background processes.

## How Apps Fit Together

```text
apps/*.py
    -> concrete service instance from services/
    -> Pydantic model
    -> optional custom routes
    -> optional registered background processes
```

Most apps are built directly with `gabru.flask.app.App`. A few extend it when they need a custom home page or extra routes. The app layer is where Rasbhari chooses concrete implementations; the framework itself only knows about contracts.

Each app should now also expose user-facing instructions in the web UI via `user_guidance`. This is separate from developer documentation and should explain what the app is for, what important terms mean, and how a user should fill in the main fields.

## Shared AI Command Layer

Rasbhari also exposes a shell-level assistant command surface through the floating `Rasbhari AI` panel and the `/assistant/command` route.

- This is not a separate app.
- It is a cross-app orchestration layer that can create events, trigger activities, save thoughts, and create promises.
- Internally it now routes commands through app-specific resolvers, so `activities`, `promises`, `thoughts`, and `events` can each score whether they should own the request.
- The assistant should prefer an existing activity over inventing a new event, and otherwise prefer event creation when downstream promises, skills, reports, or notifications can react through the normal event bus.
- Write actions are staged first and must be explicitly confirmed before they execute, which protects the event bus and downstream processors from accidental AI writes.
- The full behavior contract and current UX rules for the assistant live in [docs/AI.md](docs/AI.md).

## Currently Registered Apps

### 1. Blogs

- File: `apps/blogs.py`
- Model: `BlogPost`
- Widget: `timeline`
- Notes:
  - uses a custom blog home page
  - creates a `blog:posted` event on successful post creation

### 2. BrowserActions

- File: `apps/browser_actions.py`
- Model: `BrowserAction`
- Widget: disabled
- Notes:
  - user-scoped configuration surface for future browser extension action sync
  - stores mappings from generic browser verbs into Activities, events, project updates, or quick-log flows
  - normalizes `target_tags`, `default_payload`, and optional target ids for later extension use

### 3. BrowserRules

- File: `apps/browser_rules.py`
- Model: `BrowserRule`
- Widget: disabled
- Notes:
  - user-scoped configuration surface for future browser extension rule sync
  - stores `if A on B then trigger C` matching rules that point at configured `BrowserActions`
  - normalizes domain lists, optional duration thresholds, payload mapping, and priority for later extension use

### 4. Promises

- File: `apps/promises.py`
- Model: `Promise`
- Widget: `kanban`
- Processes:
  - `PromiseProcessor`
- Notes:
  - custom home page with summary stats
  - includes refresh and history routes per promise
  - matches events through a shared signal matcher that combines event type, event tags, and the promise tag match mode
  - **Negative Promises**: Supports "I will not..." commitments. Set `is_negative=True` and `max_allowed=0` (or a small threshold) to track avoiding certain behaviors.

### 5. Events

- File: `apps/events.py`
- Model: `Event`
- Widget: `timeline`
- Processes:
  - `Courier`
- Notes:
  - incoming form tags are normalized to a tag list
  - timestamps are set on create

### 6. Thoughts

- File: `apps/thoughts.py`
- Model: `Thought`
- Widget: `timeline`
- Notes:
  - creates a `thought:posted` event when a thought is saved

### 7. Devices

- File: `apps/devices.py`
- Model: `Device`
- Widget: `kanban`
- Processes:
  - `Heimdall`
  - `Atmos`
- Notes:
  - adds Heimdall video and device-list routes

### 8. Projects

- File: `apps/projects.py`
- Model: `Project`
- Widget: `kanban`
- Processes:
  - `ProjectUpdater`
- Notes:
  - includes project detail and timeline routes
  - creates project progress events when timeline items are added

### 9. Activities

- File: `apps/activities.py`
- Model: `Activity`
- Widget: `timeline`
- Notes:
  - supports `/activities/trigger/<id>` to emit activity-backed events
  - normalizes `tags` and `default_payload`

### 10. Skills

- File: `apps/skills.py`
- Model: `Skill`
- Widget: `skill_tree`
- Processes:
  - `SkillXPProcessor`
- Notes:
  - dashboard widget combines progress rings and level-up history
  - supports explicit `tag_key` and `aliases` for matching
  - exposes `/skills/history`

### 11. Reports

- File: `apps/reports.py`
- Model: `Report`
- Widget: `basic`
- Processes:
  - `ReportProcessor`
- Notes:
  - exposes `/reports/generate` for synchronous or event-driven report generation
  - includes detail and print routes for local review and PDF export through the browser
  - aggregates current signals from projects, events, thoughts, skills, connections, and the interaction ledger inside Connections into a behavioral mirror

### 12. Connections

- File: `apps/connections.py`
- Model: `Connection`
- Widget: `basic`
- Notes:
  - stores people and relationship cadence targets
  - renders relationship records and their interaction timeline in one app surface
  - exposes `/connections/<id>/ledger` to create and inspect linked interactions
  - updates `last_contact_at` and emits social events when interactions are logged
  - feeds overdue-contact checks in behavioral reports

### 13. rTV

- File: `apps/rtv.py`
- Model: `MediaItem`
- Widget: `kanban`
- Processes:
  - `MediaDownloadProcessor`
- Notes:
  - movie-only owned-media MVP for a small personal TV shelf
  - exposes `/rtv/home` for desktop/admin management and `/tv` for the TV-first surface
  - TV surface renders as an immersive standalone app without the normal Rasbhari sidebar
  - TV surface shows only ready cached movies with search, Continue Watching, Recently Added, resume, restart, and large focusable cards
  - player route uses remote-friendly focusable controls for play/pause, seek, fullscreen, and back instead of relying on native browser controls
  - admin page supports adding magnet candidates, resolving metadata, queueing downloads, inspecting progress, retrying failures, editing titles, and deleting local files while preserving records
  - scans the configured `RTV_MEDIA_DIR` folder for ready local video files
  - stores selected-file metadata and cache state so later download and eviction processors can promote or remove local files without losing the movie record
  - accepts magnet candidates, resolves torrent metadata, selects the largest video file, and queues downloads for the later processor
  - downloads one queued selected movie at a time and updates progress on the media item
  - enforces an rTV cache cap with `RTV_MEDIA_CACHE_LIMIT_BYTES`, defaulting to 3GB, and evicts least-recently-watched cached movies before new downloads
  - preserves evicted movie records while clearing local file paths and cache state
  - avoids evicting queued, downloading, or currently playing movies
  - serves ready files through `/rtv/stream/<id>` with browser range support via Flask and blocks paths outside `RTV_MEDIA_DIR`
  - records watch start through `/rtv/watch-started/<id>` and watch progress through `/rtv/progress/<id>`
  - emits `media:watch_started`, `media:watch_progressed`, and `media:watch_finished`, with finish detected when progress crosses 90%
  - documents the end-to-end V1 validation path in [docs/rtv-test-loop.md](rtv-test-loop.md)

### 14. Users

- File: `apps/users.py`
- Model: `User`
- Widget: disabled
- Notes:
  - admin-only account management surface
  - creates and updates real Rasbhari login accounts
  - supports personal workspace ownership without giving admins access to other users' private app data
  - generates a 5-character API key for each account and lets users rotate it from `/users/profile`
  - protected routes also accept `X-API-Key` or `Authorization: ApiKey <key>` for non-session access
  - **Signup & Approval**: Users can self-signup at `/signup`. New accounts are disabled (`is_approved=False`) until an admin approves them in the Users panel. Accounts created directly by admins are auto-approved.

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
| `POST` | `/enable_app/{app_name}` | Enable an application |
| `POST` | `/disable_app/{app_name}` | Disable an application |
| `POST` | `/{app}/widget/enable` | Enable dashboard widget |
| `POST` | `/{app}/widget/disable` | Disable dashboard widget |

## App Authoring Checklist

When adding a new app:

1. Create a model in `model/`.
2. Create a service in `services/`.
3. If the feature needs app-wide framework composition, wire it through `runtime/providers.py`.
4. Create the app in `apps/`.
5. Register it in [server.py](server.py).
6. Add or update `user_guidance` so the app home page explains the app to end users.
7. Add user-friendly `description=` text to important Pydantic fields.
8. Update this file and the root [readme.md](readme.md).
9. Update [.env.example](.env.example) if the app adds environment requirements.
