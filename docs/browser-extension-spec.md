# Rasbhari Browser Extension Spec

This document defines the formal product spec for the Rasbhari browser extension as the first shipped `Capture Automation` surface.

It is intentionally product-first rather than implementation-first. The goal is to clarify what the extension is for, what it should do, what it should not do, and how it should fit the rest of the Rasbhari ecosystem.

## Positioning

The Rasbhari browser extension is not a separate productivity tool and not a generic browser logger.

It is:

- a browser-side Rasbhari capture client
- a trigger surface for Activities and event-backed flows
- the first concrete product under the broader `Automation` vertical

It should help Rasbhari receive meaningful browser-context signals without forcing the user to stop and manually log every browser-based action.

## Goals

The browser extension should:

- work with any Rasbhari instance using `base_url` and `api_key`
- let browser activity feed cleanly into the existing Rasbhari event bus
- prefer triggering existing Rasbhari Activities where possible
- support manual, confirmation-based, and automatic browser-triggered capture
- support user-configured browser actions and rules that originate in Rasbhari
- capture bounded browser context such as URL, page title, domain, and optional selected text
- keep local history so the user can review what the extension matched or sent
- feel visually and behaviorally like part of Rasbhari
- be downloadable from Rasbhari itself during the early product phase

## Non-Goals

The first browser extension should not:

- become a full browser surveillance tool
- silently scrape everything a user does in the browser
- replace Rasbhari Activities with an unrelated browser-only action taxonomy
- depend on machine-learning inference as a foundation
- require browser store publication as the first distribution path
- try to solve every possible automation workflow in v1

## Core Product Model

The browser extension should follow this model:

- Rasbhari defines the meaning
- the extension observes browser context
- extension rules determine whether a browser condition matches
- the extension either asks for confirmation or triggers the mapped Rasbhari action
- Rasbhari receives a normal event-backed action, usually through an Activity or a small app-specific execution path

This keeps the extension thin and keeps Rasbhari as the source of truth.

## Product Principles

### 1. Activity-first mapping

When a user already has an Activity that models the behavior, the extension should prefer triggering that Activity.

Why:

- Activities already carry Rasbhari meaning
- they already emit events
- promises, skills, reports, and recommendations can already respond to those events

Raw event creation should still exist as a fallback, but it should not be the preferred default.

### 2. Event-first integration

The extension should still feed Rasbhari's event system rather than inventing a parallel browser-only data model.

That keeps:

- reports coherent
- promises reactive
- notifications usable
- ecosystem linkage intact

### 3. Explainable automation

The extension should be understandable as:

- "when this browser condition happened"
- "this Rasbhari action became available or fired"

It should never feel magical in a way that makes the user distrust it.

### 4. Privacy-safe browser capture

The extension should only capture the context necessary for the configured action.

It should default to bounded fields such as:

- `url`
- `title`
- `domain`
- optional `selection_text`

It should not act like a silent general-purpose tracker.

## Distribution Model

The early extension should be downloadable from Rasbhari itself.

This means:

- Rasbhari provides the current extension bundle or unpacked download
- Rasbhari provides install instructions
- the user can install the extension without requiring a browser store listing

Why this approach:

- faster iteration
- less operational overhead
- keeps early automation setup inside the Rasbhari ecosystem
- fits Pi-hosted and self-hosted usage better than store-first distribution

Browser-store publication can come later if the product needs it.

## Initial Platform

The first implementation should target:

- Chrome

This is the cleanest path for validating the model before expanding to other Chromium browsers or Firefox.

## Setup Flow

The first setup flow should be:

1. user downloads the extension from Rasbhari
2. user loads the extension in Chrome
3. user opens extension settings
4. user enters:
   - `Rasbhari Base URL`
   - `API Key`
5. extension tests the connection
6. extension syncs browser actions and rules from Rasbhari
7. extension becomes ready for manual, confirm, or automatic browser triggers

## Browser Actions

Browser actions are the generic actions the extension understands.

Rasbhari should map these browser-side actions into Activities, events, project updates, or quick-log flows.

### `trigger_activity`

Meaning:

- trigger a chosen Rasbhari Activity using current page context

Typical payload:

- `activity_id`
- `url`
- `title`
- `domain`
- optional `selection_text`

This is the most important browser action in v1.

### `save_current_page`

Meaning:

- capture the current page as something meaningful or worth keeping

Typical payload:

- `url`
- `title`
- `domain`
- `captured_at`

Likely uses:

- research capture
- wishlist capture
- reading save
- reference save

### `capture_selection`

Meaning:

- capture selected text from the page plus page context

Typical payload:

- `selection_text`
- `url`
- `title`
- `domain`

Likely uses:

- quote capture
- note capture
- research highlight

### `open_quick_log`

Meaning:

- open a Rasbhari quick logging flow prefilled with browser context

Typical payload:

- `url`
- `title`
- `domain`
- optional `selection_text`

Best for:

- ambiguous cases where the user should decide meaning explicitly

### `start_focus_session`

Meaning:

- begin a browser-linked work or research session

Typical payload:

- `url`
- `title`
- `domain`
- `started_at`

### `end_focus_session`

Meaning:

- close a previously started browser-linked focus session

Typical payload:

- `url`
- `title`
- `domain`
- `ended_at`
- optional `duration_seconds`

### `save_to_project`

Meaning:

- attach the current page to a project context in Rasbhari

Typical payload:

- `project_id`
- `url`
- `title`
- `domain`
- optional `selection_text`

In v1 this should usually mean:

- create a project timeline update
- or create a lightweight project-linked context note

It should not default to creating a ticket unless the user explicitly wants that behavior.

## Rule Model

The core Rasbhari browser automation rule should follow this pattern:

- if user does `A`
- on website `B`
- then trigger `C`

Where:

- `A` is a browser condition or browser action
- `B` is a domain or URL scope
- `C` is a Rasbhari-side target

### Rule Fields

A browser rule should conceptually define:

- `id`
- `name`
- `enabled`
- `browser_action`
- `trigger_mode`
- `conditions`
- `target_type`
- `target_config`
- `payload_mapping`
- `priority`

### Conditions

The first rule system should support conditions such as:

- domain equals or matches
- URL contains or matches
- manual popup action selected
- context menu action selected
- selection exists
- current tab active for at least `N` seconds

This is enough for a useful v1 without overbuilding.

### Target Types

The rule target should usually be one of:

- `activity`
- `event`
- `project_update`
- `quick_log`

Again, `activity` should be preferred when an existing Activity already models the action.

## Trigger Modes

Each rule should support one of three modes:

### `manual`

The user explicitly chooses the action from the extension UI or browser context menu.

Nothing runs automatically.

### `confirm`

The extension detects a rule match and proposes the action.

The user confirms before the extension sends anything to Rasbhari.

This is important for actions where:

- certainty is lower
- the action has more personal weight
- the user wants more control

### `automatic`

The extension sends the mapped Rasbhari action immediately when the rule matches.

This should be used only when:

- the signal is strong enough
- the user has chosen it explicitly
- the action is safe enough to run without interruption

## Event Payload Usage

The browser extension should make strong use of Rasbhari's real event `payload` support.

For browser-triggered capture:

- `event_type` describes what happened
- `tags` describe what it relates to
- `payload` stores structured browser context

Examples of payload fields:

- `url`
- `title`
- `domain`
- `selection_text`
- `started_at`
- `ended_at`
- `duration_seconds`
- `project_id`

The extension should not rely on hiding machine-readable context in the event description.

## Sync Model

The extension should treat Rasbhari as the configuration authority.

### Rasbhari should own:

- browser action definitions
- user rules
- activity mappings
- target metadata
- trigger behavior defaults

### The extension should own:

- browser-side context gathering
- local cache of the synced configuration
- confirmation UX
- local execution history

### Sync flow

1. user connects extension to Rasbhari
2. extension validates the instance using `base_url` and `api_key`
3. extension fetches browser actions and rule definitions
4. extension stores them locally
5. extension runs using the local synced configuration
6. user can resync manually or the extension can refresh periodically

This keeps the extension generic while keeping meaning in Rasbhari.

## Local History

The extension should maintain a local history of what it did.

Each history entry should include:

- timestamp
- matched rule name
- browser action
- target domain or page
- short payload summary
- result:
  - `sent`
  - `confirmed`
  - `cancelled`
  - `failed`

Optional later fields:

- Rasbhari response summary
- returned record id
- error details

Local history matters because it improves:

- trust
- debuggability
- user understanding of automation behavior

## UX Model

The extension should feel like Rasbhari:

- calm
- structured
- summary-first
- subtle
- not loud or gamified

The first extension UI should probably include:

- a popup for current page context and available actions
- a settings screen for Rasbhari connection and sync
- a local history view
- a lightweight confirmation surface for `confirm` rules

## v1 Scope

The first version should support:

- Chrome only
- download from Rasbhari
- connection via `base_url` and `api_key`
- sync of browser actions and rules
- `trigger_activity`
- `save_current_page`
- `capture_selection`
- `open_quick_log`
- `start_focus_session`
- `end_focus_session`
- `save_to_project`
- manual and confirm modes
- a narrow automatic mode for explicitly configured safe rules
- local history
- bounded browser-context payloads

## Deferred Scope

The first version should explicitly defer:

- browser-store publication
- complex media-completion detection
- aggressive background browsing heuristics
- ML-based behavior classification
- broad order-parsing or checkout intelligence
- multi-browser packaging

## Success Criteria

This spec is successful if the shipped browser extension lets a user:

- download the extension from Rasbhari
- connect it to their Rasbhari instance
- sync browser actions and rules
- trigger Rasbhari capture from normal browser activity
- see what the extension did
- trust that those actions still flow into the normal Rasbhari ecosystem

That is the first real proof that `Capture Automation` works as a product direction, not just as a technical idea.
