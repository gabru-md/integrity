# macOS Local Signals

This is the first autonomous local capture layer for Rasbhari on macOS.

It is designed to emit only high-confidence raw signals with very low setup friction.

By default it can emit:

- app `opened`
- app `closed`
- user `idle`
- user `active`
- machine `started`
- machine `woke`

Rasbhari also includes a separate local code-agent worker for Kanban-driven development tasks. That worker is intentionally pull-based: the laptop polls Rasbhari for queued agent runs, executes work locally, then posts a concise result back into the project timeline.

These are normalized into clean event bus entries instead of custom app-specific event names.

## File

- [scripts/rasbhari_mac_agent.py](../scripts/rasbhari_mac_agent.py)
- [scripts/rasbhari_agent_worker.py](../scripts/rasbhari_agent_worker.py)

## Kanban Agent Worker

Use this when Rasbhari runs on the Raspberry Pi but the code workspace and local agent live on a laptop.

Start with dry-run mode to verify the queue loop without editing files:

```bash
python3 scripts/rasbhari_agent_worker.py \
  --server http://rasbhari.local \
  --api-key YOUR_API_KEY \
  --worker macbook-work \
  --workspace integrity=/Users/manish/PycharmProjects/integrity \
  --workspace-key integrity \
  --agent-kind dry-run \
  --executor dry-run
```

Flow:

1. Open a project board in Rasbhari.
2. Click `Agent` on a Kanban ticket.
3. The worker polls `/agent-runs/next`, claims the run, and reports the result.
4. Rasbhari writes the result back into the project timeline.

After the dry-run loop is verified, switch the worker executor to `codex` or `gemini`. The worker still pulls jobs from Rasbhari, so the laptop does not need an inbound network port.

## Why This Exists

Rasbhari needs a foundation for autonomous capture before it can infer richer sessions or recommendations.

This agent is that foundation:

- it captures local machine signals automatically
- it emits normalized raw events
- it keeps the setup small enough to actually use
- it still supports legacy custom rules when you want app-specific downstream automation

## Normalized Event Types

The autonomous layer currently emits these event types:

- `local:app:opened`
- `local:app:closed`
- `local:user:idle`
- `local:user:active`
- `local:machine:started`
- `local:machine:woke`

These events carry tags such as:

- `source:mac_agent`
- `signal:raw`
- `signal:app_lifecycle`
- `signal:user_activity`
- `signal:machine_state`
- `state:opened`
- `state:closed`
- `state:idle`
- `state:active`
- `state:started`
- `state:woke`
- `app:<slug>`
- `machine:<name>`

This keeps the event bus consistent and makes later session inference easier.

## Low-Friction Setup

### 1. Initialize

```bash
python3 scripts/rasbhari_mac_agent.py init \
  --url http://localhost:5000 \
  --api-key YOUR5K \
  --machine-name macbook-pro
```

### 2. Check local setup

```bash
python3 scripts/rasbhari_mac_agent.py doctor
```

### 3. Start watching

```bash
python3 scripts/rasbhari_mac_agent.py run
```

That is enough to start emitting autonomous raw signals.

## Daemon Mode

Start:

```bash
python3 scripts/rasbhari_mac_agent.py daemon start
```

Status:

```bash
python3 scripts/rasbhari_mac_agent.py daemon status
```

Stop:

```bash
python3 scripts/rasbhari_mac_agent.py daemon stop
```

Default files:

- PID: `~/.config/rasbhari-mac-agent/agent.pid`
- Log: `~/.config/rasbhari-mac-agent/agent.log`

## Default Signal Behavior

### App lifecycle

Enabled by default.

The agent watches visible GUI apps and emits:

- `local:app:opened`
- `local:app:closed`

It excludes a few noisy system apps by default:

- `Finder`
- `Dock`
- `Control Center`
- `Notification Center`
- `System Settings`

### User activity

Enabled by default.

The agent checks macOS idle time and emits:

- `local:user:idle`
- `local:user:active`

Default idle threshold:

- `300` seconds

### Machine state

Enabled by default.

The agent emits:

- `local:machine:started` when the watcher begins
- `local:machine:woke` when it detects a long pause consistent with sleep/resume

Default wake detection gap:

- `60` seconds

## Legacy Rule Layer

The old custom rule system still exists on top of the autonomous signal layer.

Use it when you want app-specific derived events such as:

- `entertainment:netflix`
- `coding:session:start`
- `gaming:session:end`

Examples:

```bash
python3 scripts/rasbhari_mac_agent.py rule add \
  --app-name "Netflix" \
  --trigger opened \
  --event-type entertainment:netflix \
  --description "Opened Netflix on Mac" \
  --tags netflix,entertainment,negative
```

```bash
python3 scripts/rasbhari_mac_agent.py rule add \
  --app-name "PyCharm" \
  --trigger opened \
  --event-type coding:session:start \
  --description "Opened PyCharm" \
  --tags coding,python,focus
```

List configured rules:

```bash
python3 scripts/rasbhari_mac_agent.py rule list
```

## Model Going Forward

This macOS agent should be treated as the first local signal collector, not the final behavior engine.

The intended stack is:

1. raw local signals
2. normalized event bus entries
3. later session inference and recommendations inside Rasbhari

That means the agent should stay conservative:

- emit facts
- avoid heavy interpretation
- stay easy to set up
