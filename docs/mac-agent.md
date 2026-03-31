# macOS Agent

This is the first Rasbhari desktop integration for low-effort event generation on macOS.

It is intentionally simple:

- watches running GUI apps on macOS
- detects app `opened` and `closed`
- matches those transitions against local rules
- posts events directly into Rasbhari through the normal `/events/` API

This gives you a practical way to validate the ecosystem idea before building a full signals pipeline.

## File

- [scripts/rasbhari_mac_agent.py](scripts/rasbhari_mac_agent.py)

## What It Supports Today

- generic app-open rules
- generic app-close rules
- cooldowns per rule
- direct event posting with API key auth
- local config stored in `~/.config/rasbhari-mac-agent/config.json`
- optional background daemon mode with PID and log files
- tag serialization aligned with Rasbhari's current `/events/` handler

This is app-agnostic. You can use any visible macOS app name, for example:

- `PyCharm`
- `WebStorm`
- `Netflix`
- `Counter-Strike 2`
- `Spotify`

## Why It Is Useful

This is especially useful for:

- negative promises such as "do not watch Netflix"
- coding session tracking across JetBrains IDEs
- gaming or reading session starts and finishes
- simple desktop automation without invasive monitoring

Example:

- watch `Netflix` opening
- emit event type `entertainment:netflix`
- let negative promises react downstream inside Rasbhari

## Configuration Flow

### 1. Initialize the agent

Interactive:

```bash
python3 scripts/rasbhari_mac_agent.py init
```

Flag-driven:

```bash
python3 scripts/rasbhari_mac_agent.py init \
  --url http://localhost:5000 \
  --api-key YOUR5K \
  --machine-name macbook-pro
```

### 2. Add a rule

Interactive:

```bash
python3 scripts/rasbhari_mac_agent.py rule add
```

or:

```bash
python3 scripts/rasbhari_mac_agent.py rule wizard
```

Flag-driven examples:

Netflix example:

```bash
python3 scripts/rasbhari_mac_agent.py rule add \
  --app-name "Netflix" \
  --trigger opened \
  --event-type entertainment:netflix \
  --description "Opened Netflix on Mac" \
  --tags netflix,entertainment,negative
```

PyCharm example:

```bash
python3 scripts/rasbhari_mac_agent.py rule add \
  --app-name "PyCharm" \
  --trigger opened \
  --event-type coding:pycharm \
  --description "Opened PyCharm" \
  --tags coding,ide,pycharm
```

App-close example:

```bash
python3 scripts/rasbhari_mac_agent.py rule add \
  --app-name "Counter-Strike 2" \
  --trigger closed \
  --event-type gaming:cs2:finished \
  --description "Closed Counter-Strike 2" \
  --tags gaming,cs2
```

### 3. Inspect rules

```bash
python3 scripts/rasbhari_mac_agent.py rule list
```

### 4. Run diagnostics

```bash
python3 scripts/rasbhari_mac_agent.py doctor
```

### 5. Start the watcher

```bash
python3 scripts/rasbhari_mac_agent.py run
```

### 6. Run it as a background daemon

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

You can override them with `--pid-file` and `--log-file`.

## Rule Model

Each rule currently contains:

- `app_name`
- `trigger`
- `event_type`
- `description`
- `tags`
- `cooldown_seconds`
- `enabled`

Supported triggers today:

- `opened`
- `closed`

## Rule Ideas To Try

You can already build several useful rule styles with the current agent.

### 1. Distraction detection

- App: `Netflix`
- Trigger: `opened`
- Event type: `entertainment:netflix`
- Tags: `negative,entertainment,netflix`

### 2. Focus session start

- App: `pycharm`
- Trigger: `opened`
- Event type: `coding:session:start`
- Tags: `coding,python,focus`

### 3. Focus session finish

- App: `pycharm`
- Trigger: `closed`
- Event type: `coding:session:end`
- Tags: `coding,python,wrapup`

### 4. Communication tracking

- App: `WhatsApp`
- Trigger: `opened`
- Event type: `communication:whatsapp`
- Tags: `communication,relationships,messaging`

### 5. Reading or note-taking

- App: `Logseq`
- Trigger: `opened`
- Event type: `thinking:logseq`
- Tags: `notes,reflection,learning`

### 6. Browser intent markers

- App: `Google Chrome`
- Trigger: `opened`
- Event type: `browser:chrome`
- Tags: `browser,web,context-switch`

### 7. Gaming session start and end

- App: `steam_osx`
- Trigger: `opened`
- Event type: `gaming:session:start`
- Tags: `gaming,steam`

- App: `steam_osx`
- Trigger: `closed`
- Event type: `gaming:session:end`
- Tags: `gaming,steam,finished`

### 8. Security / network context

- App: `NordVPN`
- Trigger: `opened`
- Event type: `device:vpn:opened`
- Tags: `security,vpn,network`

### 9. Machine-specific automation

Because the agent always appends a `machine:<name>` tag, the same rule on multiple Macs can still be filtered separately inside Rasbhari.

### 10. Negative promise guardrails

Good candidates:

- `Discord` opened
- `Netflix` opened
- `steam_osx` opened
- `Google Chrome` opened

These pair well with promises that watch for distraction tags or entertainment event types.

## Notes on Reliability

This V1 intentionally avoids trying to detect everything on macOS.

It focuses on app lifecycle transitions because those are practical and reliable enough to validate the ecosystem.

It does not yet handle:

- browser URL/domain tracking
- detailed IDE project detection
- window titles
- media playback state
- focus mode state

Those can come later as optional integrations.

## How It Works

The agent polls the list of visible GUI processes using `osascript` and compares:

- current apps
- previously seen apps

From that diff it derives:

- newly opened apps
- recently closed apps

Matching rules emit normal Rasbhari events through:

- `POST /events/`

The current Rasbhari event route expects `tags` in the request body as a comma-separated string, and the mac agent formats them that way before sending.

This means no special server endpoint is required for the first validation phase.

## Intended Next Step

If this feels useful, the next version should move from direct event posting to:

- desktop agent emits `signals`
- Rasbhari maps signals into events or activities

That would keep clients thinner and make automation behavior easier to configure centrally.
