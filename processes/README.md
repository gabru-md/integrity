# Processes

The `processes/` directory contains Rasbhari's background workers. Some are plain daemon threads and some are queue processors that consume rows from the events database.

## Process Types

### Standard `Process`

Used for long-running loops such as camera monitoring or BLE polling.

Examples:

- `Atmos`
- `Heimdall`

### `QueueProcessor`

Used for event-driven background work with persisted progress.

Examples:

- `Courier`
- `PromiseProcessor`
- `ProjectUpdater`
- `SkillXPProcessor`

Queue progress is persisted in `queue.queuestats`.

## Current Processes

### Courier

- File: `processes/courier/courier.py`
- Type: `QueueProcessor`
- Input: `events`
- Purpose:
  - listens for events tagged with `notification`
  - sends ntfy.sh notifications by default
  - routes to SendGrid when the event also has the `email` tag
  - records sent notifications in the notifications database

### PromiseProcessor

- File: `processes/promise_processor.py`
- Type: `QueueProcessor`
- Input: `events`
- Purpose:
  - updates promise counters from matching events
  - performs periodic due checks
  - tracks streaks, completions, and next-check windows

### ProjectUpdater

- File: `processes/project_updater.py`
- Type: `QueueProcessor`
- Input: `events`
- Purpose:
  - increments project progress from project/progress events
  - applies state changes from `project:state:*` tags

### SkillXPProcessor

- File: `processes/skill_xp_processor.py`
- Type: `QueueProcessor`
- Input: `events`
- Purpose:
  - matches event tags like `#python` to each skill's `tag_key` and aliases
  - awards XP
  - recalculates levels
  - writes skill level-up history
  - emits `skill:level_up` events

### Atmos

- File: `processes/atmos/atmos.py`
- Type: `Process`
- Purpose:
  - fetches BLE data from enabled device URLs
  - triangulates approximate beacon locations using RSSI
  - emits `atmos:*` events

### Heimdall

- File: `processes/heimdall/heimdall.py`
- Type: `Process`
- Purpose:
  - pulls frames from enabled devices
  - runs YOLO11n detection
  - emits `tracking:*` events
  - supports a streaming endpoint for the dashboard

## Queue Checkpointing

Queue processors now use batched checkpointing:

- fetched records are processed in memory
- `last_consumed_id` is updated in memory for every consumed row
- queue stats are flushed every `10` items by default
- queue stats are also flushed when the queue becomes idle

This keeps DB writes lower than per-item persistence while preventing large replays after restarts.

## Runtime Control

The process manager is exposed by the server:

- `POST /enable_process/<name>`
- `POST /disable_process/<name>`
- `POST /start_process/<name>`
- `POST /stop_process/<name>`
- `GET /process_logs/<name>`

The dashboard's reliability row also summarizes process, queue, notification, and device health.

## When Adding a Process

1. Pick `Process` or `QueueProcessor`.
2. Register it from the owning app.
3. Decide whether it should be enabled by default.
4. Update this file and the root [readme.md](/Users/manish/PycharmProjects/integrity/readme.md).
5. Document any env requirements in [ENVIRONMENT.md](/Users/manish/PycharmProjects/integrity/ENVIRONMENT.md) and [.env.example](/Users/manish/PycharmProjects/integrity/.env.example).
