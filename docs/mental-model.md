# Rasbhari Mental Model

Rasbhari is a personal operating system built around an event bus.

The apps are not meant to stand alone. They work together by sharing one language: events.

That means:

- something happens
- Rasbhari captures it
- other apps interpret or structure it
- commitments and growth react to it
- reflection surfaces what changed
- Today turns that into the next small actions

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

Promises watch for event types or tags. They are how Rasbhari checks whether reality matched what you said mattered.

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

Act is how Rasbhari helps you move today, not just archive the past.

Primary action surfaces:

- `Today`
- notifications
- staged recommendation follow-ups

Today pulls together active work, due promises, neglected relationships, suggested actions, and high-signal guidance.

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
- `Today` unifies the important current state

## What Makes Rasbhari Cohesive

Rasbhari becomes useful when the same work can be seen from multiple angles:

- a ticket move advances a project
- that project emits focus tags
- those tags can satisfy a promise
- those same tags can grow a skill
- Reports can reflect whether that work is actually happening
- Today can tell you what deserves attention next

That is the point of the ecosystem.

## Minimal Useful Setup

If you are setting up Rasbhari from scratch, start here:

1. Create one `Activity`
2. Create one `Project`
3. Create one `KanbanTicket`
4. Create one `Promise`
5. Create one `Skill`
6. Trigger or log one real event
7. Open `Today` and see whether the connections are visible

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

1. `Today`
2. `Events`
3. `Activities`
4. `Projects`
5. `KanbanTickets`
6. `Promises`
7. `Skills`
8. `Reports`

The tutorial is intentionally non-AI. It explains the product loop, why each surface exists, and what to look at on each page before the user starts trying to optimize the system.

Users can restart it later from `Profile Settings`.
