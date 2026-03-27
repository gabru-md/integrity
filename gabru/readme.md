# Gabru Framework

Gabru is the small framework that powers Rasbhari. It provides the database layer, Flask abstractions, process management, and queue processing that the app code builds on top of.

## Main Pieces

```text
gabru/
  db/          PostgreSQL connection + CRUD helpers
  flask/       server, app, model, and template helpers
  qprocessor/  database-backed queue processing
  process.py   daemon and process manager primitives
  log.py       multi-file logger
  apple/       Apple Shortcuts signing helpers
```

## Database Layer

### `DB`

`gabru.db.db.DB` creates a connection using environment variables derived from the logical DB name.

Example:

```python
from gabru.db.db import DB

events_db = DB("events")
main_db = DB("rasbhari")
```

That resolves to variables such as:

- `EVENTS_POSTGRES_DB`
- `EVENTS_POSTGRES_USER`
- `RASBHARI_POSTGRES_DB`
- `RASBHARI_POSTGRES_USER`

### `ReadOnlyService` and `CRUDService`

These generic services provide:

- `get_by_id`
- `get_all`
- `get_recent_items`
- `get_all_items_after`
- `find_all`
- `create`
- `update`
- `delete`

Current codebase examples:

- `EventService` uses `DB("events")`
- `SkillService`, `ProjectService`, `PromiseService`, `ActivityService` use `DB("rasbhari")`
- `NotificationService` uses `DB("notifications")`
- `ThoughtService` uses `DB("thoughts")`

## Flask Layer

### `Server`

`gabru.flask.server.Server` wraps Flask and provides:

- app registration
- process manager startup
- process control routes
- dashboard aggregation

Rasbhari extends this in [server.py](/Users/manish/PycharmProjects/integrity/server.py) to register all current apps and add the `/chat` and `/heimdall` routes.

### `App`

`gabru.flask.app.App` is the default way to define a CRUD-backed app.

It generates:

- CRUD API endpoints
- a `/home` UI route
- widget support for the dashboard
- widget enable/disable endpoints

Apps can also subclass `App` to add custom routes or override widget generation. `SkillsApp`, `PromiseApp`, `ProjectApp`, and `BlogApp` all do that in the current project.

### `UIModel` and `WidgetUIModel`

These base models extend Pydantic with field-level UI metadata:

- `edit_enabled`
- `widget_enabled`
- `download_enabled`
- `ui_enabled`

## Process Layer

### `Process`

`gabru.process.Process` is a daemon-thread base class with:

- `running` lifecycle flag
- `stop()`
- abstract `process()` loop

### `ProcessManager`

`ProcessManager`:

- stores blueprints from registered apps
- initializes process instances
- starts enabled processes
- supports enable/disable/pause/run at runtime

The dashboard uses this state to build process and reliability views.

## Queue Processing

`gabru.qprocessor.QueueProcessor` is the event-processing workhorse.

How it works:

1. Read rows with `id > last_consumed_id`
2. Load a batch into memory
3. Optionally filter each item
4. Process it
5. Update in-memory queue progress
6. Flush queue progress to `queue.queuestats` in batches

Current behavior:

- default batch fetch size: `10`
- queue checkpoints flush every `10` consumed items
- queue checkpoints also flush when the queue goes idle

This matches the current replay/performance tradeoff in the code.

## Logging

`gabru.log.Logger` writes:

- `main.log`
- `warnings.log`
- `exceptions.log`
- one log per logger name, for example `Courier.log`

`LOG_DIR` must be configured.

## Current Rasbhari-Specific Extensions

Gabru is generic, but the current project extends it with:

- a dashboard reliability row
- a universal timeline
- pinned and locally reordered widgets
- action-first dashboard controls
- queue-backed event processing for promises, projects, notifications, and skills

For implementation details see:

- [gabru/flask/README.md](flask/README.md)
- [gabru/qprocessor/README.md](qprocessor/README.md)
