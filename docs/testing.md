# Rasbhari Test Suite

Rasbhari currently uses Python `unittest` for both unit and integration coverage.

The suite is grouped intentionally:

- `unit`
  - pure service logic
  - framework helpers
  - retry and event helper behavior
  - no real HTTP app composition required

- `integration`
  - Flask route behavior
  - auth/session request handling
  - app composition regressions

## Running Tests

Run everything:

```bash
PYTHONPATH=. python3 -m tests.run_suite all
```

Run only unit tests:

```bash
PYTHONPATH=. python3 -m tests.run_suite unit
```

Run only integration tests:

```bash
PYTHONPATH=. python3 -m tests.run_suite integration
```

List the exact modules in each group:

```bash
PYTHONPATH=. python3 -m tests.run_suite list
```

## Current Coverage Shape

Unit coverage currently focuses on:

- assistant command staging behavior
- DB reconnect and retry behavior
- event emission helper behavior
- skill matching and progress math

Integration coverage currently focuses on:

- signup and auth regressions
- generic app request parsing
- events app request parsing
- kanban ticket routes

## Scope Boundaries

The suite does not currently provide full end-to-end coverage for:

- live PostgreSQL-backed flows
- background process orchestration
- external integrations such as Ollama, ntfy, or SendGrid
- browser-level UI automation

Those should be added separately as dedicated environment tests rather than mixed into the fast local suite.
