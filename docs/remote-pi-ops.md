# Remote Pi Operations

This playbook is for the Raspberry Pi-hosted Rasbhari setup that you access remotely over Tailscale.

It answers four practical operator questions:

1. How do I reach Rasbhari remotely?
2. What should I check first if it feels broken?
3. What can I fix from inside Rasbhari?
4. What still requires SSH or host-level access?

Use this together with:

- [rasbhari.md](rasbhari.md) for the overall admin/control-plane model
- [backup-restore.md](backup-restore.md) for PostgreSQL backup and restore
- [setup.md](setup.md) for baseline environment and deployment setup

## 1. Canonical Remote Access Path

The intended remote access model is:

- Raspberry Pi runs Rasbhari as a `systemd` service
- the Pi joins your Tailscale tailnet
- you access Rasbhari through its Tailscale hostname
- Rasbhari still requires its own auth

Recommended remote URLs:

- `http://<pi-magicdns-name>:5000`
- or your chosen stable tailnet hostname

Primary remote product surfaces:

- `/` for `Today`
- `/capture` for urgent event logging
- `/admin` for operator health and recovery
- `/processes` for queue and worker intervention

## 2. First Checks When It Feels Broken

If Rasbhari feels wrong while you are away, check in this order.

### 2.1 Can You Reach The App At All?

Try the canonical Tailscale URL first.

If the page loads, the server process is at least reachable.

If the page does not load:

- confirm your client device is still on Tailscale
- confirm the Raspberry Pi is still on the tailnet
- if you cannot reach the Pi at all, this is now outside Rasbhari and likely needs host-level access

### 2.2 Open `/admin`

If Rasbhari loads, go to `/admin` first.

That is the fastest high-signal view for remote health.

Look at:

- `Server Availability`
- `Event Flow`
- `Queue Drift`
- `Dependency Issues`
- `Degraded Capabilities`
- `Stuck Processors`

Typical interpretations:

- `Server healthy, Event Flow stale`:
  raw capture may be paused or no new events are arriving
- `Queue Drift growing`:
  one or more queue processors are behind
- `Dependency Issues present`:
  ntfy, Ollama/OpenWebUI, or another external dependency may be degraded
- `Stuck Processors present`:
  use the in-product restart/replay tools first

### 2.3 Open `/processes`

If `/admin` shows queue or worker problems, use `/processes`.

That is the main runtime maintenance surface.

Check:

- which processors are running
- which queue processors are behind
- which workers are stopped
- whether queue progress looks stale or wrong

### 2.4 Check `/capture` Or `/`

If the app is reachable but the system feels stale:

- open `/capture` and log one test event
- or trigger one activity

Then go back to `/admin` or `/events/home` and see whether the event appears.

This distinguishes:

- UI feels stale but the event pipeline works
- event creation itself is broken
- processors are not reacting to new events

## 3. What You Can Fix Inside Rasbhari

These are the intended product-level recovery actions.

### Process Runtime

From `/admin` or `/processes`, you can:

- restart stopped processors
- inspect queue drift
- replay queue processors from `0`
- replay from an exact id
- jump queue processors to latest

Use these first when:

- promises are not catching up
- reports seem stale
- notifications stopped after backlog built up
- a worker looks behind after a restore or config fix

### App State

From `/admin` or `/apps`, you can:

- see which apps are disabled
- re-enable apps
- check which workers an app depends on
- understand which capabilities are degraded because an app or worker is inactive

Use this when:

- an app disappeared from navigation
- a product area feels missing
- a user expects a feature that is currently disabled

### User And Onboarding State

From `/admin`, `/users/home`, and the admin guide, you can:

- approve users
- review onboarding readiness
- verify that people are being sent to the right surfaces (`Today`, tutorial, checklist)

### Dependency Visibility

From `/admin` and `/processes`, you can:

- see dependency issues
- tell whether external delivery or AI-adjacent services are degraded

This is visibility first, not full infrastructure repair.

### Remote Logging

From `/capture`, you can:

- trigger one-tap recent activities
- log a direct event quickly

This is the intended remote-safe path when something important happens away from home and cannot wait.

## 4. What Still Requires System Access

Some problems are intentionally outside Rasbhari.

These still require SSH, local shell access, or other host-level intervention:

- Raspberry Pi is offline or unreachable on Tailscale
- Rasbhari `systemd` service itself is stopped and the web UI is unreachable
- PostgreSQL service is down or damaged
- database repair or schema surgery
- restore of PostgreSQL dumps
- filesystem repair
- package installation or OS upgrades
- Tailscale installation or tailnet/node repair
- host-level networking changes
- backup job setup and backup verification

This boundary is intentional. Rasbhari should operate the product, not replace the operating system.

## 5. Practical Remote Triage Flow

Use this exact sequence when you are away and Rasbhari feels wrong.

1. Open the Tailscale Rasbhari URL.
2. If it loads, open `/admin`.
3. Check `Server Availability`, `Event Flow`, `Queue Drift`, and `Dependency Issues`.
4. If a processor is stuck or stopped, go to `/processes`.
5. Use `Restart`, `Replay From 0`, `Replay From Exact ID`, or `Jump To Latest` as appropriate.
6. If the product is reachable but stale, log one event through `/capture`.
7. Verify that the event appears and downstream systems react.
8. If the app is unreachable or PostgreSQL itself is broken, switch to system-level recovery.

## 6. Practical Recovery Guidance

### When To Restart A Processor

Use `Restart` when:

- the processor is stopped
- you changed queue progress and want a clean runtime state
- the worker looks wedged but the queue state itself is still valid

### When To Replay From 0

Use `Replay From 0` when:

- matching logic changed
- evidence should be rebuilt from the full queue
- you restored data and want processors to rebuild state from the beginning

Be aware that this may take time and reprocess all historical queue items.

### When To Replay From An Exact ID

Use exact replay when:

- only one region of the queue matters
- a bug fix should only affect newer items
- full replay would be excessive

### When To Jump To Latest

Use `Jump To Latest` when:

- backlog is irrelevant
- you want the processor to stop chewing old items and resume normal live operation

Do not use this if the backlog still matters for correctness.

## 7. Minimum Trusted Remote Setup

For a Pi-hosted Rasbhari you want to trust remotely, the minimum standard is:

- Tailscale access works reliably
- `/admin` gives a useful health snapshot
- `/processes` gives queue and worker recovery controls
- `/capture` gives urgent remote logging
- nightly PostgreSQL backups are running
- backup restore steps are documented and understood

That combination is what turns the setup from "reachable from away" into "safe to rely on from away."
