# Rasbhari Testing Sandbox

Rasbhari now supports a disposable sandbox instance for manual testing and feature exploration.

The sandbox gives you:

- a separate Postgres stack
- a separate Rasbhari app instance
- deterministic seed data
- quick reset and reseed commands

It is designed for trying UI changes, project workflows, dashboards, reports, recommendations, and event-driven features without touching your real profile.

## Files

- [docker-compose.sandbox.yml](../docker-compose.sandbox.yml)
- [.env.test.example](../.env.test.example)
- [scripts/test_sandbox.sh](../scripts/test_sandbox.sh)
- [scripts/reset_test_data.py](../scripts/reset_test_data.py)
- [scripts/seed_test_data.py](../scripts/seed_test_data.py)

## First Run

1. Copy the sandbox env file:

```bash
cp .env.test.example .env.test
```

2. Start and seed the sandbox:

```bash
./scripts/test_sandbox.sh up realistic
```

3. Open the sandbox:

```text
http://localhost:5510
```

Seeded login:

- username: `sandbox`
- password: `sandbox`
- API key: `SBOX1`

## Commands

Start from scratch and run the app:

```bash
./scripts/test_sandbox.sh up realistic
```

Reset and reseed without restarting the app container:

```bash
./scripts/test_sandbox.sh reseed project_heavy
```

Stop the sandbox:

```bash
./scripts/test_sandbox.sh down
```

## Scenarios

`minimal`
- one user
- one project
- a few events, tickets, promises, and reports

`realistic`
- a believable mixed personal profile
- projects, timeline items, kanban tickets, skills, promises, thoughts, reports, notifications, and connections

`project_heavy`
- extends `realistic`
- adds more active projects and ticket movement for board-focused testing

`messy`
- extends `realistic`
- intentionally inconsistent tags and weak promise alignment for cleanup and recommendation testing

## What It Can Test

- login and API-key auth against sandbox users
- CRUD flows for the registered apps
- dashboard rendering against non-empty data
- project and kanban workflows
- reports against realistic seeded records
- recommendation scripts against structured but disposable data
- event emission from normal app actions

## What It Does Not Fully Test

- live assistant command history replay
- importing or cloning your real profile
- external device or agent integrations
- production-scale performance behavior
- third-party side effects such as real notification delivery unless you explicitly point the env at them

## Design Notes

- Data is seeded through Rasbhari service classes, not raw SQL dumps.
- Resetting drops and recreates the `public` schema in each sandbox database.
- The sandbox uses the same database names as the main compose stack, but in an isolated Postgres container and volume.
