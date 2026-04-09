# Automation

Rasbhari's `Automation` vertical is the product area responsible for reducing capture friction and turning real-world or device-side signals into meaningful Rasbhari events.

The point of Automation is not surveillance and not black-box inference. Its role is to help a user keep living normally while Rasbhari receives enough trustworthy signal to stay useful.

## Product Role

Automation exists to make Rasbhari easier to live with.

It should:

- lower the amount of manual event entry required to keep the system useful
- keep capture aligned with the existing event bus, activities, reports, promises, and notifications
- preserve user trust through explainable rules and visible history
- prefer privacy-safe signals over invasive monitoring
- support both direct automation and lightweight confirmation flows

Automation is a broader vertical than capture alone. Over time it can include scheduler-style helpers, import adapters, and device-driven orchestration. The first concrete track inside it is `Capture Automation`.

## Capture Automation

`Capture Automation` is the first sub-track under Automation.

Its goal is simple:

- let the user keep doing things
- observe or assist those actions with minimal friction
- emit the smallest correct Rasbhari event or activity trigger

The first implementation path is not "automate everything." It is to add a few trustworthy capture channels that fit the existing Rasbhari ecosystem cleanly.

## Automation Principles

Rasbhari should follow these rules when adding Automation capabilities:

1. Event-first integration

- meaningful automated actions should still flow into the event bus
- existing promises, skills, reports, notifications, and recommendations should continue to react without special-case side paths

2. Activity-first orchestration where possible

- if a user already has an Activity that models the action, Automation should prefer triggering that Activity
- the automation surface should not invent a parallel meaning system when Rasbhari already has one

3. Explainability over magic

- automation rules should be understandable as "when this happened, Rasbhari did that"
- the user should be able to inspect what matched, what was sent, and why

4. Privacy-safe capture

- capture only what is needed for the configured workflow
- avoid camera-first or surveillance-style approaches
- prefer explicit context, device signals, and bounded environmental sensing

5. Structured context, not description stuffing

- event `event_type` and `tags` remain the primary semantic layer
- structured extra context belongs in event `payload`
- automation should not rely on hiding machine-readable detail inside free-text descriptions

6. Support both automation and confirmation

- some actions should run automatically
- others should ask first
- Rasbhari should support both without forcing one style on all users

## Capture Channels

Rasbhari should treat capture as a multi-channel problem, not a single perfect mechanism.

The current planned channels are:

### 1. Browser Extension

The browser extension is the first Capture Automation surface.

It should:

- connect to any Rasbhari instance with `base_url` and `api_key`
- sync browser actions and rules from Rasbhari
- support manual, confirm, and automatic trigger modes
- capture bounded browser context such as URL, title, domain, and optional selected text
- trigger Rasbhari Activities or event-backed flows instead of becoming a separate productivity system
- keep local execution history so users can inspect what it did

The browser extension should be configurable by Rasbhari itself. Rasbhari should remain the source of truth for action definitions, mappings, and rule behavior.

The detailed product contract for this surface lives in [browser-extension-spec](wip/browser-extension-spec.md).
The detailed shared browser action vocabulary lives in [browser-actions](wip/browser-actions.md).
The detailed shared rule contract lives in [browser-rules](wip/browser-rules.md).
The detailed sync and extension-history contract lives in [browser-sync-history](wip/browser-sync-history.md).
The Chrome-first build order lives in [browser-extension-implementation-plan](wip/browser-extension-implementation-plan.md).

### 2. Desktop Agents

Desktop agents are the next strong capture channel after the browser.

They can observe privacy-safe workstation signals such as:

- active app category
- lock or unlock state
- idle or active boundaries
- bounded work-session markers
- optional local machine signals already normalized into raw events

Desktop agents are especially useful because they can generate trustworthy low-friction signals without requiring the user to stop and log what happened.

### 3. Mobile Shortcuts

Mobile shortcuts are the lightweight mobile capture channel.

They are useful for:

- one-tap quick capture
- arrival or departure automations
- focus mode or routine transitions
- assisted confirmation flows

They are not the whole automation strategy, but they are a practical bridge between passive capture and full manual event entry.

### 4. Environmental Sensors

Sensors are a later-stage capture channel.

They should be used carefully and preferably only when privacy-safe and explainable. Promising examples include:

- presence or motion sensing
- contact switches
- humidity or water-adjacent signals
- smart buttons
- dedicated NFC readers

Sensor capture should usually rely on deterministic heuristics or rule fusion, not black-box ML.

## Trust Model

Automation should not treat every signal equally.

Rasbhari should increasingly distinguish between:

- direct capture
- assisted capture
- imported capture
- inferred capture

This distinction does not need to dominate the everyday UI, but it matters for future reasoning, reporting, and user trust.

## Early Scope

The first concrete Automation work should establish:

- real structured event payload support
- browser-action and rule design
- a Chrome extension as the first capture client
- Rasbhari-side configuration and sync for that extension
- local history and confirmation support in the extension

That makes Automation a real vertical instead of an idea, while still keeping the first shipped surface narrow and testable.

## Relationship To The Rest Of Rasbhari

Automation is not separate from Rasbhari's mental model. It exists to feed it.

The intended flow is still:

- something happened
- Rasbhari captured or inferred it with low friction
- the event bus recorded it
- projects, promises, skills, reports, notifications, and recommendations reacted normally

That keeps Automation as a multiplier for the existing ecosystem rather than a detached subsystem.
