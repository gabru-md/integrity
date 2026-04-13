# Browser Action Model

Browser Actions are the generic verbs the Rasbhari browser extension understands.

Use them to map browser-side intent back into Rasbhari as Activities, events, project updates, or quick-log flows.

## V1 Actions

- `trigger_activity`
- `save_current_page`
- `capture_selection`
- `open_quick_log`
- `start_focus_session`
- `end_focus_session`
- `save_to_project`

## Rules

- keep actions generic and browser-side
- let Rasbhari own the semantic target
- prefer Activity-first mapping
- carry browser context in structured payloads
- keep the smallest correct behavior

## Shared Context

- `url`
- `title`
- `domain`
- `selection_text`
- `captured_at`
- `started_at`
- `ended_at`
- `duration_seconds`
- `project_id`
- `activity_id`

## Reference

- [Browser Extension Spec](browser-extension-spec.md)
- [Browser Rule Model](browser-rules.md)
- [Browser Sync And Local History](browser-sync-history.md)
