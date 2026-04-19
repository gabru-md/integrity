# Rasbhari Mental Model

Rasbhari is a personal operating system built around an event bus.

The apps are not meant to stand alone. They work together by sharing one language: events.

In product terms, Rasbhari is meant to feel like one daily operating loop:

- capture what happened
- structure it into meaningful context
- compare it against commitments
- let repeated effort accumulate into growth
- reflect on what changed
- turn that back into the next useful action

That means:

- something happens
- Rasbhari captures it
- other apps interpret or structure it
- commitments and growth react to it
- reflection surfaces what changed
- the dashboard and reports keep the current state visible

## The Core Loop

### 1. Capture

Capture is how real life enters Rasbhari.

Primary capture surfaces:

- `Events`
- `Activities`
- `Thoughts`
- local machine signals
- future imports like calendar or device feeds

Rule:

- if something meaningful happened, it should usually become an event or something that creates an event

### 2. Structure

Structure turns raw events into organized context.

Primary structure surfaces:

- `Projects`
- `KanbanTickets`
- `Blogs`
- `Connections`

Rule:

- events say what happened
- structure says where that work belongs

### 3. Commit

Commit makes intent explicit.

Primary commit surface:

- `Promises`

Promises watch event signals: the event type, event tags, and whether a promise needs any or all target tags. They are how Rasbhari checks whether reality matched what you said mattered.

Rule:

- a promise without matching event evidence will feel broken

### 4. Grow

Grow turns repeated effort into visible progression.

Primary growth surface:

- `Skills`

Skills look at event tags and reward repeated work with XP and levels.

Rule:

- if you want work to count as growth, use stable tags

### 5. Reflect

Reflect is where Rasbhari stops being a logbook and becomes a mirror.

Primary reflection surfaces:

- `Reports`
- project timelines
- cross-system history

Reports compare projects, events, skills, thoughts, and relationships to show not only what happened, but what is missing.

Rule:

- reflection depends on capture quality and stable structure

### 6. Act

Act is how Rasbhari helps you move, not just archive the past.

Primary action surfaces:

- `Dashboard`
- notifications
- staged recommendation follow-ups

The dashboard keeps active surfaces visible while reports and notifications help narrow attention.

Rule:

- the system should narrow attention, not add noise

## How The Apps Fit Together

- `Activities` create reusable event-producing actions
- `Events` are the shared language
- `Projects` and `KanbanTickets` create project-work structure and emit project-work events
- `Promises` check whether important signals appeared often enough
- `Skills` reward repeated tagged work
- `Connections` let relationship maintenance become visible
- `Reports` reflect the system back to you
- `Dashboard` keeps the current workspace visible

## What Makes Rasbhari Cohesive

Rasbhari becomes useful when the same work can be seen from multiple angles:

- a ticket move advances a project
- that project emits focus tags
- those tags can satisfy a promise
- those same tags can grow a skill
- Reports can reflect whether that work is actually happening
- reports and notifications can tell you what deserves attention next

That is the point of the ecosystem.

If the product starts to feel like a pile of apps, the right recovery question is:

- where in the loop did the signal break?

Usually the answer is one of these:

- nothing meaningful is being captured yet
- captured signals are not being structured into projects or relationships
- commitments are not watching the same event vocabulary
- growth is not tied to stable tags
- reflection does not yet have enough honest evidence to become useful

## Minimal Useful Setup

If you are setting up Rasbhari from scratch, start here:

1. Create one `Activity`
2. Create one `Project`
3. Create one `KanbanTicket`
4. Create one `Promise`
5. Create one `Skill`
6. Trigger or log one real event
7. Open `Dashboard` and see whether the connections are visible

## A Simple Test

If Rasbhari feels confusing, ask:

- did I capture anything real?
- did I structure it into a project or relationship?
- did I tie any commitment to that signal?
- did I give growth a stable tag to reward?
- did I generate enough evidence for reflection?

If the answer is no to most of those, the system will feel fragmented. If the answer is yes, Rasbhari starts to feel like one system instead of many apps.

## Guided Tutorial

Rasbhari includes a first-run interactive tutorial for signed-in users.

It walks through the ecosystem in product order:

1. `Dashboard`
2. `Events`
3. `Activities`
4. `Projects`
5. `KanbanTickets`
6. `Promises`
7. `Skills`
8. `Reports`

The tutorial is intentionally non-AI. It explains the product loop, why each surface exists, and what to look at on each page before the user starts trying to optimize the system.

It is also designed to guide alongside the product instead of covering it up. The current page should remain visible enough that the tutorial feels like a live walkthrough, not a blocking modal.

Users can restart it later from `Profile Settings`.

## App-Level Helpers

Every app also includes a shared helper layer in its `Instructions` drawer. The goal is not only to explain local fields, but to explain:

- what the app is for
- how it connects to the rest of Rasbhari
- what setup makes it more useful
- which other apps it works especially well with

This keeps the ecosystem legible even after the first-run tutorial is finished.
