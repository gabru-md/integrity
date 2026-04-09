# Chrome Extension Implementation Plan

This document defines the implementation plan for starting Rasbhari `Capture Automation` with a Chrome extension first.

It translates the broader product spec into a build order, a v1 feature set, and a clear defer list so the first shipped extension remains small, testable, and coherent.

## Why Chrome First

The first Capture Automation surface should be a Chrome extension because it gives Rasbhari:

- a high-signal capture channel
- a bounded product surface
- clear install and test loops
- a practical path to browser context capture without building a native desktop client first

Chrome-first is not a statement that Chrome is the only long-term surface. It is the cleanest way to prove the automation model early.

## Implementation Goal

The first release should let a user:

- download the extension from Rasbhari
- connect it with `base_url` and `api_key`
- sync browser actions and rules
- trigger a small set of Rasbhari browser captures
- inspect what the extension did through local history

That is enough to make Capture Automation real without dragging in every future automation idea.

## v1 Product Slice

The first shipped slice should include four things:

1. Rasbhari-side configuration and API foundation
2. downloadable Chrome extension delivery
3. Chrome extension v1 client
4. an end-to-end setup and test loop

## What v1 Must Support

### 1. Connection

The extension must support:

- `base_url`
- `api_key`
- test connection

Without this, the extension is not meaningfully generic.

### 2. Sync

The extension must support:

- startup sync
- manual resync
- local cached config

Periodic background refresh can wait.

### 3. Local History

The extension must support:

- local execution history
- confirmation outcome visibility
- a compact summary of what Rasbhari returned

Without history, the extension will not feel trustworthy.

### 4. Manual And Confirm Flows

The extension must support:

- manual execution
- confirm-before-send execution

Automatic execution should exist only in a narrow, explicitly safe form in v1.

### 5. Bounded Browser Context

The extension must support sending only minimal structured browser context such as:

- `url`
- `title`
- `domain`
- optional `selection_text`

This should go through event payloads or Activity payloads, not free-text descriptions.

## Browser Actions To Ship First

Not every action in the model should receive equal build attention in v1.

### Highest-priority actions

These should ship in the first usable version:

- `trigger_activity`
- `save_current_page`
- `capture_selection`
- `open_quick_log`
- `save_to_project`

Why these first:

- they cover the most common browser capture needs
- they keep Rasbhari strongly activity-first
- they give the user both explicit capture and assisted capture paths
- they are easy to reason about in a popup-first UI

### Second-tier actions for v1

These can still exist in the model and, if implementation goes smoothly, can ship in the initial version with narrower UX:

- `start_focus_session`
- `end_focus_session`

Why second-tier:

- they are useful
- but they require more lifecycle thinking than simple page or selection capture
- they are easier to get wrong if rushed

So they should be included only if they do not destabilize the smaller capture flows.

## Trigger Modes To Ship First

### Must ship

- `manual`
- `confirm`

These are the most important trigger modes for the first release because they:

- minimize trust risk
- make the extension easier to debug
- keep the user in the loop while the product is still being proven

### Narrow v1 support

- `automatic`

Automatic mode should be present only for a small subset of deterministic rules in v1.

Examples of acceptable early automatic use:

- explicit page-save rule on a tightly scoped domain
- explicit focus boundary rule where the user intentionally enabled it

What should not happen in v1:

- broad passive automation everywhere
- silent rules with unclear value

## Recommended v1 Rule Scope

The first version should support only a small rule feature set:

- manual popup action selection
- context menu selection for text capture
- simple domain matching
- simple URL matching
- explicit target type
- explicit payload mapping
- numeric priority

This is enough to prove the architecture without creating a full automation language.

## Recommended v1 UI Surfaces

The extension should stay small.

### 1. Popup

The popup should show:

- current page context
- relevant actions for the page
- quick status
- sync state

This is the primary interaction surface in v1.

### 2. Settings

The settings screen should show:

- `base_url`
- `api_key`
- connection test
- last sync time
- manual sync action

### 3. History

The history screen should show:

- recent extension actions
- confirmation results
- send results
- compact Rasbhari response summaries

### 4. Confirmation surface

For `confirm` rules, the extension should show a small confirmation UI rather than forcing everything through the popup.

This can be lightweight as long as it is clear.

## Rasbhari-Side Implementation Order

The first implementation should proceed in this order:

### Phase 1: Rasbhari-side data and docs foundation

- event payload support
- browser action model
- browser rule model
- sync and local-history contract

This foundation is already the right first move because the extension should not be built against vague assumptions.

### Phase 2: Rasbhari automation surface

- add a first-class Automation page in Rasbhari
- explain the browser-extension setup flow
- make extension distribution discoverable

This gives the feature a real home inside the product.

### Phase 3: Rasbhari extension APIs

Build the minimal API surface for:

- connection validation
- syncing browser actions and rules
- executing browser-triggered actions

These APIs should stay thin and route back into normal Rasbhari app and event flows.

### Phase 4: Downloadable extension delivery

- make the Chrome extension bundle downloadable from Rasbhari
- include install instructions

This keeps early distribution inside Rasbhari instead of depending on a browser store.

### Phase 5: Chrome extension client

Build:

- settings
- popup
- sync client
- local cache
- manual actions
- confirm flow
- local history

### Phase 6: End-to-end test loop

Verify:

- download works
- connection works
- sync works
- actions trigger correctly
- history reflects what happened

## Extension-Side Implementation Order

The Chrome extension itself should be built in this order:

### Step 1

Basic scaffold:

- manifest
- popup shell
- settings storage

### Step 2

Connection and sync:

- save `base_url`
- save `api_key`
- test connection
- fetch synced config
- persist local cache

### Step 3

Manual actions:

- `trigger_activity`
- `save_current_page`
- `open_quick_log`

These are the cleanest first browser interactions.

### Step 4

Selection capture:

- context menu support
- `capture_selection`

### Step 5

Project capture:

- `save_to_project`

### Step 6

Confirm mode:

- local pending state
- confirm or cancel flow
- history entries for both outcomes

### Step 7

Narrow automatic mode:

- limited support for explicitly safe deterministic rules

### Step 8

Optional session actions:

- `start_focus_session`
- `end_focus_session`

Only if the earlier steps are already stable.

## What To Defer

The first release should explicitly defer:

- browser-store publication
- Firefox and multi-browser packaging
- complex passive browsing heuristics
- aggressive auto-triggering
- ML-based automation
- advanced media or checkout parsing
- rich background scheduling inside the extension
- remote history sync back into Rasbhari
- deeply dynamic site-specific custom UIs
- sensor and desktop-agent work

These are all valid later directions, but they are not necessary to prove the product.

## Success Criteria For v1

The first Chrome extension release is successful if:

- a user can download it from Rasbhari
- a user can connect it to their Rasbhari instance
- a user can sync browser actions and rules
- at least the highest-priority actions work end to end
- manual and confirm modes are usable and trustworthy
- the extension keeps local history that makes its behavior inspectable

That is the correct first proof of Capture Automation.

## Build Recommendation

The most important discipline is to keep the first release small.

If the team has to choose between:

- more automation breadth
- or a tighter trustworthy loop

the correct choice is the tighter trustworthy loop.

That means the first build should prioritize:

- explicit setup
- explicit action mapping
- local visibility
- small high-value browser actions
- low-risk trigger modes

That is how Rasbhari Capture Automation becomes a real product instead of a vague automation experiment.
