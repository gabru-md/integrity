# Browser Action Model

This document defines the shared browser action model for Rasbhari `Capture Automation`.

It is narrower than the full [browser extension spec](browser-extension-spec.md). The purpose of this document is to define what each generic browser-side action means and how it maps back into the Rasbhari ecosystem.

The extension should understand these actions as stable verbs. Rasbhari should remain the source of truth for how a particular user's action maps into Activities, events, project updates, or quick-log flows.

## Why A Browser Action Model Exists

The browser extension needs a small, generic, reusable vocabulary.

Without that model:

- the extension becomes a one-off bundle of ad hoc behaviors
- browser rules become harder to reason about
- Rasbhari-side configuration becomes inconsistent
- the browser extension risks inventing a parallel meaning system

The browser action model prevents that.

It lets Rasbhari say:

- this is the browser-side action
- this is the browser context attached to it
- this is how it should map into the Rasbhari ecosystem

## Action Model Principles

Browser actions should follow these rules:

1. Generic browser-side verbs

- actions should describe what happened in browser terms
- they should not be tied to one user's exact life semantics

2. Rasbhari owns the meaning

- the extension knows the action type
- Rasbhari decides whether that action triggers an Activity, event, project update, or quick-log flow

3. Activity-first mapping

- if an existing Activity already models the behavior, prefer it
- Activities remain the strongest bridge back into the broader Rasbhari system

4. Payload carries context

- browser actions should send structured context in event payloads or Activity trigger payloads
- descriptions should stay human-readable

5. Summary-first behavior

- actions should do the smallest correct thing
- they should not over-create records or over-assume meaning

## Shared Browser Context

Most browser actions should support some subset of this context:

- `url`
- `title`
- `domain`
- `selection_text`
- `captured_at`
- `started_at`
- `ended_at`
- `duration_seconds`
- `project_id`
- `activity_id`

Not every action needs every field. The point is to define a stable pool of browser-side context that can be passed through Rasbhari cleanly.

## Action Definitions

### `trigger_activity`

#### Meaning

Directly trigger a chosen Rasbhari Activity using browser context.

This is the most important browser action in the model, because it gives the extension a direct path back into Rasbhari's existing meaning system.

#### Typical payload

- `activity_id`
- `url`
- `title`
- `domain`
- optional `selection_text`
- `captured_at`

#### Rasbhari mapping

Preferred target:

- a specific `Activity`

Result:

- the Activity emits its normal event
- the browser context becomes the event payload
- promises, skills, reports, and recommendations can react normally

#### When to use it

Use this when the user already has a named Activity that matches the browser behavior, such as:

- `Research Capture`
- `Article Saved`
- `Learning Session`
- `Reference Logged`

#### Why it matters

This action keeps the extension aligned with Rasbhari instead of bypassing it.

### `save_current_page`

#### Meaning

Capture the current page as something worth keeping or revisiting.

This is a browser-native action, not yet a claim about why the page matters. Rasbhari should decide whether it becomes research, a reading save, a wishlist item, a reference, or another reusable record.

#### Typical payload

- `url`
- `title`
- `domain`
- `captured_at`

#### Rasbhari mapping

Preferred targets:

- an `Activity` such as `Research Save`, `Reference Save`, or `Wishlist Save`
- fallback `event` creation if no matching Activity exists

Result:

- a stable event-backed save with structured browser context in payload

#### Good use cases

- save article
- save documentation page
- save reference page
- save product page

#### Constraint

This should not automatically become a task or ticket unless the user explicitly configures that later.

### `capture_selection`

#### Meaning

Capture selected text from a page together with the page context.

This is for smaller, more specific captures than saving the whole page.

#### Typical payload

- `selection_text`
- `url`
- `title`
- `domain`
- `captured_at`

#### Rasbhari mapping

Preferred targets:

- an `Activity` such as `Quote Saved`, `Research Snippet`, or `Idea Capture`
- fallback `quick_log` or `event` path

Result:

- a focused event or Activity trigger with the selected text kept in payload

#### Good use cases

- saving a quote
- grabbing a research snippet
- storing a key paragraph
- capturing a title or headline from a page

#### Constraint

This should remain explicit and bounded. It is not a general page-scrape action.

### `open_quick_log`

#### Meaning

Open a Rasbhari quick logging flow prefilled with browser context rather than deciding the meaning automatically.

This is useful when the browser can provide context but should not make the semantic decision on behalf of the user.

#### Typical payload

- `url`
- `title`
- `domain`
- optional `selection_text`

#### Rasbhari mapping

Preferred target:

- a `quick_log` flow in Rasbhari

Result:

- Rasbhari opens or stages a lightweight logging UI with browser context already attached

#### Good use cases

- ambiguous pages
- ad hoc capture
- situations where user intent matters more than automation certainty

#### Why it matters

This action keeps the system low-friction without forcing full automation everywhere.

### `start_focus_session`

#### Meaning

Mark the beginning of a browser-linked focus or work session.

This action is about boundaries rather than page saving.

#### Typical payload

- `url`
- `title`
- `domain`
- `started_at`

#### Rasbhari mapping

Preferred targets:

- an `Activity` such as `Focus Start`, `Research Start`, or `Study Start`
- fallback `event`

Result:

- a stable start-of-session event with browser context payload

#### Good use cases

- beginning deep work on a docs site
- starting focused research
- opening a browser-based study block

#### Constraint

This action should work together with `end_focus_session`. The two should not drift into unrelated meanings.

### `end_focus_session`

#### Meaning

Mark the end of a browser-linked focus or work session.

This action should close a previously started session rather than create an unrelated end event with no context.

#### Typical payload

- `url`
- `title`
- `domain`
- `ended_at`
- optional `duration_seconds`

#### Rasbhari mapping

Preferred targets:

- an `Activity` such as `Focus End`, `Research End`, or `Study End`
- fallback `event`

Result:

- a stable end-of-session event with structured payload

#### Good use cases

- ending a research session
- stopping a study block
- closing a browser-based work interval

#### Constraint

If session boundaries later become more intelligent, this action should still remain the explicit browser-side verb for finishing a session.

### `save_to_project`

#### Meaning

Attach the current page or selection to a specific Rasbhari project context.

This is not just "save page" with a project tag. It is specifically about project context.

#### Typical payload

- `project_id`
- `url`
- `title`
- `domain`
- optional `selection_text`
- `captured_at`

#### Rasbhari mapping

Preferred targets:

- `project_update`
- lightweight project-linked context note
- project-specific Activity if one exists

Result:

- the page becomes part of the project's visible working context

#### Good use cases

- save a reference for a project
- attach research to a project timeline
- keep a useful page in project context without turning it into a ticket

#### Constraint

In v1 this should usually create a project timeline update or project-linked note, not a Kanban ticket.

## Mapping Priority

When Rasbhari receives a browser action, it should prefer these mapping paths in order:

1. matching configured `Activity`
2. explicit app-specific target such as `project_update`
3. fallback `event`
4. `quick_log` when the action is intentionally ambiguous

This keeps browser automation aligned with the rest of the system.

## Relationship To Rules

Browser actions are not rules.

They are the verbs the extension understands.

Rules combine:

- browser conditions
- website scope
- one of these browser actions
- a Rasbhari-side target and trigger mode

So a rule might say:

- if user selects text
- on `docs.python.org`
- use `capture_selection`
- in `confirm` mode
- map to Activity `Research Snippet`

That is why the browser action model should stay generic and stable.

## Relationship To Payload

The browser action model assumes Rasbhari events support real structured payloads.

That means:

- browser actions carry context as payload
- Activities can pass browser context into the emitted event payload
- future reports, recommendations, and imports can still reason on event type and tags first while retaining structured browser detail

## v1 Recommendation

For the first shipped extension, these browser actions should all exist in the model, but the highest-priority ones are:

- `trigger_activity`
- `save_current_page`
- `capture_selection`
- `open_quick_log`
- `save_to_project`

The focus-session actions should still be part of the model in v1, but they can start with a narrower UX if needed.

## Summary

The browser action model gives Rasbhari a stable browser-side vocabulary.

That vocabulary should remain:

- generic on the extension side
- meaningful on the Rasbhari side
- event-first
- activity-first where possible
- payload-aware

That is what makes the browser extension a Rasbhari surface instead of a detached browser plugin.
