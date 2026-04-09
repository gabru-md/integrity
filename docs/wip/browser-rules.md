# Browser Rule Model

This document defines the first browser automation rule model for Rasbhari `Capture Automation`.

It formalizes the pattern:

- if user does `A`
- on website `B`
- then trigger `C`

The purpose of this model is to give Rasbhari, the browser extension, and the eventual configuration UI the same contract for browser-side automation behavior.

## Why A Rule Model Exists

The browser action model defines the verbs the extension understands.

The browser rule model defines:

- when a browser action becomes relevant
- where it should apply
- what Rasbhari target it should trigger
- whether the extension should ask or act

Without a rule model:

- the extension becomes ad hoc
- users cannot reason clearly about why something fired
- sync between Rasbhari and the extension becomes fragile
- configuration grows inconsistent

## Core Pattern

Every browser rule should be interpretable as:

- if the browser context matches this condition
- on this site or URL scope
- use this browser action
- trigger this Rasbhari target
- in this trigger mode

That keeps browser automation explainable and easy to audit.

## Rule Principles

Browser rules should follow these principles:

1. Explainable

- a user should be able to understand why a rule matched

2. Bounded

- rules should capture only the browser context needed for the target action

3. Activity-first

- when possible, rules should target an Activity instead of a raw event

4. Priority-aware

- if multiple rules match, Rasbhari and the extension should have a deterministic way to choose or order them

5. Confirmation-capable

- rules should support both full automation and assisted confirmation

## Rule Shape

The first Rasbhari browser rule should conceptually contain:

- `id`
- `name`
- `enabled`
- `browser_action`
- `trigger_mode`
- `conditions`
- `match_scope`
- `target_type`
- `target_config`
- `payload_mapping`
- `priority`

## Field Meanings

### `id`

Stable identifier for the rule.

### `name`

Human-readable label such as:

- `Save Docs Research`
- `Capture GitHub Selection`
- `Add Store Page To Wishlist`

### `enabled`

Whether the rule is active.

Disabled rules should sync to the extension but not run.

### `browser_action`

The browser-side verb the rule uses, such as:

- `trigger_activity`
- `save_current_page`
- `capture_selection`
- `open_quick_log`
- `start_focus_session`
- `end_focus_session`
- `save_to_project`

These are defined in [browser-actions.md](browser-actions.md).

### `trigger_mode`

How the extension should behave when the rule matches:

- `manual`
- `confirm`
- `automatic`

### `conditions`

The browser-side conditions that must match.

### `match_scope`

The website or URL scope where the rule is valid.

### `target_type`

The Rasbhari-side execution target. Usually one of:

- `activity`
- `event`
- `project_update`
- `quick_log`

### `target_config`

The specific target details, such as:

- `activity_id`
- `project_id`
- event defaults
- quick-log routing info

### `payload_mapping`

Defines what browser context fields should be forwarded and how they should land in Rasbhari payload.

### `priority`

Relative precedence when more than one rule matches.

## Conditions

The first rule system should support a small, deterministic set of condition types.

### Manual conditions

These are explicit user actions:

- popup action selected
- context menu action selected
- toolbar action selected

These are the cleanest conditions because the user initiated them.

### Browser-context conditions

These are passive conditions the extension can evaluate:

- selection exists
- active tab duration is at least `N` seconds
- current tab just loaded
- tab closed after active duration

These should stay bounded and understandable in v1.

### URL conditions

These are conditions on the current page:

- URL contains string
- URL matches prefix
- URL matches pattern
- domain equals
- domain in allowed list
- subdomain matches

This lets rules stay specific without becoming overcomplicated.

## Website And Domain Matching

The `match_scope` section of a rule should support website targeting explicitly.

The first model should support:

- `domain_equals`
- `domain_in`
- `domain_suffix`
- `url_contains`
- `url_prefix`
- optional URL pattern matching later if needed

This keeps v1 simple while still allowing useful site-specific automation.

### Example scopes

- `domain_equals = docs.python.org`
- `domain_in = [github.com, gitlab.com]`
- `url_contains = /pull/`
- `url_prefix = https://www.amazon.`

The extension should only show or run the rule where that scope matches.

## Target Types

Rules should target Rasbhari-side actions, not just browser-side actions.

The first target types should be:

### `activity`

Preferred target type.

Use when:

- an existing Activity already models the behavior

Effect:

- trigger the Activity
- let the Activity emit the event
- keep promises, skills, reports, and recommendations aligned

### `event`

Fallback target type.

Use when:

- no meaningful Activity exists yet
- the behavior is still worth logging as an event

Effect:

- create a normal event with tags and structured payload

### `project_update`

Project-specific target type.

Use when:

- the browser action belongs in project context
- the result should be part of a project timeline rather than a generic event-only flow

Effect:

- create a project-linked context or timeline update

### `quick_log`

Human-in-the-loop target type.

Use when:

- the browser can supply context
- but the user should still decide the semantic meaning

Effect:

- open or stage a Rasbhari quick logging flow with context already attached

## Payload Mapping

Rules should explicitly define how browser context maps into Rasbhari payload.

This matters because:

- not every action needs every field
- different targets need different structured context
- the extension should avoid sending unnecessary data

### Supported browser-side source fields

The first model should support payload mapping from fields such as:

- `url`
- `title`
- `domain`
- `selection_text`
- `captured_at`
- `started_at`
- `ended_at`
- `duration_seconds`

### Mapping behavior

The first version can keep payload mapping simple:

- pass through selected fields with the same key
- optionally rename into a target field
- optionally add static values from the rule

### Example

Rule says:

- browser action: `save_current_page`
- payload mapping:
  - `url -> url`
  - `title -> title`
  - `domain -> domain`
  - static `source = browser_extension`

Result:

- Rasbhari receives a clean structured payload without scraping extra context

## Priority

Multiple rules may match the same browser context.

So each rule should carry a `priority`.

The first priority model should be simple:

- higher priority wins
- if priorities tie, prefer the more specific scope
- if still tied, prefer `activity` over `event`
- if still tied, prefer `confirm` over `automatic` for safety

This keeps matching deterministic without making the engine complex.

## Trigger Modes

Every rule should support one of three trigger modes.

### `manual`

The rule is available, but the user must explicitly invoke it.

Good for:

- optional captures
- popup-driven actions
- context-menu-driven actions

Behavior:

- extension shows the action when relevant
- nothing is sent automatically

### `confirm`

The rule may match automatically, but the extension asks before sending.

Good for:

- lower-certainty rules
- sensitive actions
- flows where the user wants oversight

Behavior:

- extension presents a compact confirmation surface
- user can confirm or cancel
- confirmed actions go to Rasbhari

### `automatic`

The rule sends directly once it matches.

Good for:

- strong deterministic conditions
- low-risk automations
- explicitly approved workflows

Behavior:

- extension fires without extra prompt
- action still lands in local history

## Examples

### Example 1

- if user selects text
- on `docs.python.org`
- use `capture_selection`
- target Activity `Research Snippet`
- in `confirm` mode

### Example 2

- if popup action `Save Current Page` is used
- on any page in `github.com`
- use `save_current_page`
- target Activity `Reference Save`
- in `manual` mode

### Example 3

- if active tab duration reaches 20 minutes
- on `coursera.org`
- use `end_focus_session`
- target event `learning:session_completed`
- in `automatic` mode

## v1 Recommendation

The first shipped rule model should stay intentionally small.

It should support:

- simple domain and URL matching
- manual and confirm modes first
- narrow automatic mode for strong deterministic cases
- explicit target types
- explicit payload mapping
- simple numeric priority

That is enough to make browser automation real without overbuilding a full automation language.

## Relationship To The Rest Of Rasbhari

The browser rule model should not become its own isolated automation engine.

It exists so that:

- the extension can stay generic
- Rasbhari can stay the source of truth
- browser actions can still feed Activities, events, projects, and quick-log flows cleanly

That is what keeps browser automation part of Rasbhari rather than an unrelated extension layer.
