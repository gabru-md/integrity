<p align="center">
  <img src="static/favicon.png" alt="Rasbhari logo" width="120">
</p>

# Rasbhari

Rasbhari is an event-driven personal operating system for Raspberry Pi and lightweight Linux hosts.

It is designed to help one user own a daily loop, not a pile of disconnected apps:

- capture what happened
- structure it into projects and promises
- reflect on what is drifting
- grow skills from repeated work
- act on what matters next

The system is built from a contract-first framework, a runtime composition layer, and a set of product apps and background processes. That split keeps the codebase maintainable while the product keeps growing.

## What Rasbhari Is For

Rasbhari is useful when you want one place to:

- remember what happened without relying on memory alone
- turn repeated actions into Activities
- keep commitments visible
- see project work without losing personal context
- review progress through reports and history
- reduce friction through Capture Automation instead of manual entry everywhere

## How To Use Rasbhari

### As a daily user

Start with `Today`. That page is the calmest entry point and shows what matters now.

Then use the core flow:

1. Capture something in `Capture` or via an Activity.
2. Turn recurring work into `Projects` or `Promises`.
3. Review what changed in `Reports`.
4. Let `Skills` and recommendations grow from the events you already produce.

### As a structured user

If you want more control, add the ecosystem pieces gradually:

- `Activities` for reusable triggers
- `Projects` and `Kanban` for work structure
- `Connections` for people and relationship cadence
- `Thoughts` and `Blogs` for narrative context

### As an operator

Use the deeper surfaces only if you need them:

- `Admin` for health and approvals
- `Processes` for background workers
- `Apps` for enabling and disabling components
- `Automation` for browser capture and future automation surfaces

## Product Model

Rasbhari follows a pacing model with three experience modes:

- `Everyday`
- `Structured`
- `System`

That model keeps the product deep by capability but shallow by default. Regular users should see the calm daily loop first, while operator-heavy surfaces stay tucked away until they are actually needed.

Automation is now a first-class product vertical inside Rasbhari. The first sub-track is `Capture Automation`, starting with a Chrome extension that can sync browser actions and rules back into the system.

## Deployment Notes

Rasbhari is intended to live on a Raspberry Pi or similar machine you own.

For demos and hosted trials, it can also run with a single shared PostgreSQL database through `DATABASE_URL`, which is useful on platforms like Render. That mode is for testing and sharing, not the long-term home.

## Project Structure

- `gabru/` contains reusable framework primitives and contracts
- `runtime/` composes Rasbhari-specific provider wiring
- `services/` contains concrete implementation logic
- `apps/` contains request/UI composition and custom routes
- `processes/` contains long-running workers and queue consumers

## Important Surfaces

- `Today` for the daily home
- `Capture` for quick logging
- `Projects` and `Kanban` for work structure
- `Activities` for reusable triggers
- `Promises` for commitments
- `Reports` for reflection and summaries
- `Automation` for capture and extension workflows
- `Admin` and `Processes` for operator control

## WIP Notes

Some browser-extension and automation design notes are still moving and live in `docs/wip/`.

## Navigation

- [Docs Hub](docs/README.md)
- [Rasbhari Overview](docs/rasbhari.md)
- [Automation](docs/automation.md)
- [Experience Modes](docs/experience-modes.md)
- [AI Command Layer](docs/AI.md)
- [Setup Guide](docs/setup.md)
- [Environment Reference](docs/environment.md)
- [Backup And Restore](docs/backup-restore.md)
- [Remote Pi Operations](docs/remote-pi-ops.md)
- [Test Suite](docs/testing.md)
- [Testing Sandbox](docs/testing-sandbox.md)

### WIP Docs

- [Browser Action Model](docs/wip/browser-actions.md)
- [Browser Extension Spec](docs/wip/browser-extension-spec.md)
- [Browser Extension Implementation Plan](docs/wip/browser-extension-implementation-plan.md)
- [Browser Rule Model](docs/wip/browser-rules.md)
- [Browser Sync And Local History](docs/wip/browser-sync-history.md)
