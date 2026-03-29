# Rasbhari AI

This document explains how AI fits into the Rasbhari ecosystem today.

## Purpose

Rasbhari AI is not a separate chatbot product and it is not a replacement for the existing apps.

Its job is to:

- accept natural-language input from the user
- interpret the user's intent with a local LLM through Ollama
- route that intent through Rasbhari's app-aware command layer
- stage a safe action for confirmation
- execute through the normal Rasbhari services and event system

The important design rule is:

- the LLM interprets intent
- Rasbhari validates, stages, and executes

That separation is what keeps the system safe.

## Why It Exists

Rasbhari already has strong domain structure:

- `activities`
- `events`
- `promises`
- `thoughts`
- `skills`
- `reports`
- `connections`
- downstream processors and notifications

The AI layer is meant to make those capabilities easier to reach.

Instead of forcing the user to open many apps and shape data manually, the assistant should help convert a natural-language command into the smallest correct Rasbhari action.

Example:

- user says: `litterbox cleaned`
- assistant should prefer an existing activity if one matches
- if no activity exists, it may propose creating an event
- once that action is executed, the rest of Rasbhari reacts normally through the event bus

This means the assistant is a front door into Rasbhari, not a parallel system.

## Current User Interface

The AI surface currently appears as a floating `Rasbhari AI` chat panel in the shared shell.

Files:

- [templates/index.html](/Users/manish/PycharmProjects/integrity/templates/index.html)
- [static/css/style.css](/Users/manish/PycharmProjects/integrity/static/css/style.css)

Current UI behavior:

- the assistant thread persists for the lifetime of the browser tab through `sessionStorage`
- the thread is cleared on a real browser refresh
- staged actions lock the input so the user must resolve the pending action first
- staged actions support:
  - `Confirm Action`
  - `Ignore`
  - `Change`
- `Change` restages the action type and asks for confirmation again
- if a staged action is replaced, the older staged card is marked as changed and no longer remains active

## Public API Surface

Current route:

- `POST /assistant/command`

This route accepts the current authenticated user through either:

- session auth
- `X-API-Key`
- `Authorization: ApiKey <key>`

The assistant route is not meant to be a raw execution endpoint. It is a staged command endpoint.

## Request Shape

Typical request:

```json
{
  "message": "litterbox cleaned"
}
```

Confirmation request:

```json
{
  "message": "yes",
  "confirm": true
}
```

Ignore current staged action:

```json
{
  "cancel": true
}
```

Restage the current action to another supported action type:

```json
{
  "change_action": "create_thought"
}
```

Supported change targets today:

- `trigger_activity`
- `create_event`
- `create_thought`
- `create_promise`

## Response Model

The assistant returns a structured response model rather than arbitrary chat text.

Core fields:

- `ok`
- `executed`
- `requires_confirmation`
- `action`
- `confidence`
- `summary`
- `reasoning`
- `response`
- `payload`

The UI turns that result into cards rather than dumping the raw payload as plain text.

## Architecture

High-level flow:

```text
User message
    -> /assistant/command
    -> AssistantCommandProvider contract
    -> AssistantCommandService
    -> Ollama chat call
    -> plan normalization
    -> app-specific resolver routing
    -> staged result
    -> user confirmation / ignore / change
    -> normal Rasbhari service execution
    -> optional event emission and downstream processing
```

Important files:

- [gabru/contracts.py](/Users/manish/PycharmProjects/integrity/gabru/contracts.py)
- [gabru/flask/server.py](/Users/manish/PycharmProjects/integrity/gabru/flask/server.py)
- [runtime/providers.py](/Users/manish/PycharmProjects/integrity/runtime/providers.py)
- [services/assistant_command.py](/Users/manish/PycharmProjects/integrity/services/assistant_command.py)
- [services/assistant_resolvers.py](/Users/manish/PycharmProjects/integrity/services/assistant_resolvers.py)
- [model/assistant_command.py](/Users/manish/PycharmProjects/integrity/model/assistant_command.py)

### Layer responsibilities

`gabru/`

- defines the contract boundary
- exposes the HTTP route
- does not contain Rasbhari-specific assistant logic

`runtime/`

- binds the framework contract to the concrete Rasbhari assistant service

`services/assistant_command.py`

- calls Ollama
- normalizes model output
- manages staged pending actions
- executes confirmed actions

`services/assistant_resolvers.py`

- contains app-specific routing logic
- gives each domain a chance to claim the command

`templates/index.html`

- renders the current chat interface and pending-action controls

## Ollama Integration

The assistant uses Ollama chat mode rather than a raw generate prompt.

Relevant environment variables:

- `OLLAMA_BASE_URL`
- `OLLAMA_COMMAND_MODEL`
- `OLLAMA_TIMEOUT_SECONDS`

Why chat mode is used:

- better role separation
- more reliable structured responses
- behavior closer to interactive chat clients like Open WebUI

The assistant asks the model for a JSON plan and then validates that plan before it can affect Rasbhari.

## Plan Normalization

Model output is not trusted as-is.

The assistant currently normalizes common drift cases such as:

- action aliases
- action text placed in the wrong field
- nested `response` objects
- tags returned as a string
- promise-like payloads mislabeled as an activity action
- thought-like payloads mislabeled as another action

This matters because local models can be useful while still being inconsistent at strict schema output.

## App-Specific Resolver Layer

After the model returns a plan, Rasbhari routes that plan through domain-aware resolvers.

Current resolvers:

- `PromiseCommandResolver`
- `ThoughtCommandResolver`
- `ActivityCommandResolver`
- `EventCommandResolver`
- `AnswerCommandResolver`

Why this layer exists:

- a single model plan is often too coarse
- different apps have different semantics
- promises, activities, thoughts, and events should not all be interpreted the same way

The resolver layer is where Rasbhari becomes app-aware.

### Activity preference

One of the most important rules is:

- if a meaningful existing activity already models the command, prefer that activity over inventing a new raw event

This protects existing promise chains, skill XP flows, and downstream processing patterns that are already tied to activities and their event types.

## Staging and Safety Model

The assistant currently stages all write actions.

This includes:

- `create_event`
- `trigger_activity`
- `create_thought`
- `create_promise`

The system does not immediately commit those actions just because the model was confident.

Instead:

1. the assistant proposes a structured action
2. the user sees the planned action
3. the user explicitly:
   - confirms it
   - ignores it
   - or changes the action type and restages it
4. only then does Rasbhari execute it

This is intentional.

Rasbhari is event-driven, so a wrong event can trigger many downstream effects:

- promise updates
- skill XP
- reports
- notifications
- processors reacting to the event bus

Staging protects the ecosystem from accidental LLM writes.

## Pending Action Rules

Rasbhari currently keeps one pending action per user.

That means:

- while a staged action exists, new commands are blocked
- the user must resolve the staged action first
- resolving means:
  - confirm
  - ignore
  - or change and restage

This is simpler and safer than allowing an uncontrolled queue of pending AI actions.

## What "Change" Means

`Change` does not ask the model to reinterpret the command from scratch.

It does this:

- takes the original user message
- takes the current staged plan
- coerces the staged plan into another supported action type
- stages the revised action
- asks for confirmation again

Example:

- original command was staged as `create_event`
- user chooses `create_thought`
- Rasbhari restages it as a thought and asks for confirmation again

This is a controlled override path, not a second LLM round-trip.

## Supported Actions Today

The assistant currently supports these action types:

- `create_event`
- `trigger_activity`
- `create_thought`
- `create_promise`
- `answer`

These are intentionally limited. Rasbhari should grow this list slowly and only when each action has a clear validation and safety model.

## What the Assistant Should Prefer

The preferred decision order today is:

1. if a matching activity exists, prefer `trigger_activity`
2. if the user is clearly creating a commitment, use `create_promise`
3. if the user is clearly recording a note or reflection, use `create_thought`
4. if no activity exists and an event is the right system primitive, use `create_event`
5. use `answer` for informational or conversational replies

This keeps the assistant aligned with the Rasbhari event model rather than letting it invent arbitrary system writes.

## Interaction Examples

### Existing activity

Input:

- `I played counter strike with friends for 1 hour`

Preferred result:

- match an existing gaming activity if one exists
- stage `trigger_activity`

### Promise creation

Input:

- `create a weekly promise called Call Mom with target event type call:mom`

Preferred result:

- stage `create_promise`

### Thought capture

Input:

- `note that I need to order more cat litter`

Preferred result:

- stage `create_thought`

### Raw event

Input:

- `log an event that I read an article about postgres connection pooling`

Preferred result:

- stage `create_event`

## Current Constraints

Important current limitations:

- only one pending action is tracked per user
- `Change` only changes the action type, not the natural-language content
- the assistant does not yet support broad multi-tool execution across all apps
- the assistant does not yet expose a full audit/history model separate from the UI thread
- the assistant still depends on the quality of the configured Ollama model

## Future Direction

Likely next steps:

- richer app-specific resolvers for more domains
- better read/query capabilities
- explicit assistant history persistence
- command templates and aliases
- voice input on top of the same staged command system
- a dedicated custom Ollama model or Modelfile for Rasbhari

## Testing the Assistant

Stage a command:

```bash
curl -X POST http://localhost:5000/assistant/command \
  -H "X-API-Key: YOUR5K" \
  -H "Content-Type: application/json" \
  -d '{"message":"litterbox cleaned"}'
```

Confirm the staged action:

```bash
curl -X POST http://localhost:5000/assistant/command \
  -H "X-API-Key: YOUR5K" \
  -H "Content-Type: application/json" \
  -d '{"message":"yes","confirm":true}'
```

Ignore the staged action:

```bash
curl -X POST http://localhost:5000/assistant/command \
  -H "X-API-Key: YOUR5K" \
  -H "Content-Type: application/json" \
  -d '{"cancel":true}'
```

Restage the staged action:

```bash
curl -X POST http://localhost:5000/assistant/command \
  -H "X-API-Key: YOUR5K" \
  -H "Content-Type: application/json" \
  -d '{"change_action":"create_thought"}'
```
