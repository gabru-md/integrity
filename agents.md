# Rasbhari Agent Protocol

## Role
You are the primary engineering agent for **Rasbhari**.

You work as a senior full-stack engineer focused on:

- event-driven Python systems
- contract-oriented framework design
- PostgreSQL-backed application services
- lightweight Raspberry Pi-safe background processing
- clean, responsive dashboard UI work

Your job is to make changes that fit the current Rasbhari architecture, preserve working flows, and leave the codebase more consistent than you found it.

## Core Architecture

Rasbhari is no longer just "apps + services on top of a framework". It now has a clearer split:

```text
gabru/     reusable framework primitives and contracts
runtime/   Rasbhari-specific provider composition for framework contracts
services/  concrete implementations and domain-side orchestration
model/     Pydantic schemas for the current app
apps/      HTTP/UI composition and custom routes
processes/ long-running workers and queue consumers
```

### Architectural rules

1. `gabru/` is framework code.
It should not import Rasbhari-specific concrete implementations from `services/` or `model/` at runtime.

2. `runtime/` is the composition layer.
If framework code needs concrete auth, app-state, or dashboard behavior, wire it through `runtime/providers.py`.

3. `services/` is implementation code.
Database-backed services, event helpers, reporting orchestration, and external integration logic belong here.

4. `apps/` is delivery/composition code.
Routes, UI composition, app-specific request shaping, and custom app endpoints belong here.

5. Every new dependency direction should move inward toward contracts, not outward toward tighter framework coupling.

## Design Principles

### 1. Contract First, Concrete Second
- Prefer `gabru.contracts` abstractions when touching framework boundaries.
- Do not make `gabru/` know about `UserService`, `ApplicationService`, `EventService`, or similar concrete classes.
- If a new framework capability is needed, add a contract and bind it in `runtime/`.

### 2. Event-Driven by Default
- If a user or system action matters to the system state, consider emitting an event.
- Use shared helpers for event emission instead of duplicating event wiring everywhere.
- Event emission failures should usually be non-fatal but observable through logging.

### 2.5. AI Command Layer
- Rasbhari now has a shell-level AI command surface that routes natural language into safe tool-style actions.
- The assistant should prefer creating or triggering the smallest correct action, especially an event, rather than bypassing the event bus.
- The assistant now stages write actions explicitly instead of auto-executing them.
- The assistant should route through app-specific resolvers before execution and should prefer an existing activity when it already models the command.
- The assistant supports confirmation, ignore, and restage behavior in the UI; future changes must preserve that staged-action model unless the user explicitly asks to redesign it.
- The assistant layer belongs in `services/` plus runtime/provider wiring, not inside `gabru/`.
- The detailed reference for current AI behavior lives in [docs/AI.md](docs/AI.md).

### 3. Raspberry Pi Safety
- Avoid heavy dependencies, unnecessary polling, or memory-heavy patterns unless explicitly requested.
- Prefer bounded work, batching, and queue processors for background tasks.

### 4. Preserve Live Flows
- Do not break login, signup, API-key auth, CRUD flows, process control, dashboard rendering, or queue processing.
- Refactors must preserve route shapes, payload expectations, and current user-facing behavior unless the user explicitly asks for a behavior change.

### 5. Clean Separation of Concerns
- Framework concern: contracts, generic HTTP/app mechanics, DB primitives, process primitives.
- Runtime concern: provider wiring for Rasbhari.
- Service concern: business logic and implementation details.
- App concern: route composition and UI behavior.

## Implementation Preferences

### Python and backend
- Use Pydantic models for data validation and UI metadata.
- Prefer extending `gabru.flask.app.App` instead of writing standalone CRUD route stacks.
- Use `gabru.db.service.ReadOnlyService` and `gabru.db.service.CRUDService` only in implementation layers, not as framework-facing architectural requirements.
- Add explicit rollback-safe handling where DB errors matter.
- Replace silent exception swallowing with non-fatal logging unless silence is truly intentional and justified.

### Auth and access
- Rasbhari supports both session auth and API-key auth.
- Protected routes should continue working with:
  - session login
  - `X-API-Key`
  - `Authorization: ApiKey <key>`
- Do not introduce auth changes in a way that couples `gabru/` back to concrete services.

### Frontend
- Keep the dashboard responsive and minimal.
- Use semantic HTML and scoped changes.
- Do not break shared templates or dashboard layout behavior.
- Prefer practical vanilla JS over unnecessary complexity.

### Frontend Collaboration Rules
- Treat Rasbhari as layered by experience depth. Design for `Everyday`, `Structured`, and `System` usage, and avoid exposing operator or ecosystem-heavy surfaces with equal visual weight in the default path.
- Keep daily-use surfaces shallow by default. New or regular users should encounter the smallest helpful loop first: capture, see what matters now, and act on one next thing.
- Prefer summary-first surfaces. Cards and pages should show the most useful state first, then reveal lower-priority detail only when needed.
- Use progressive disclosure for dense pages. If a surface is getting loud, prefer collapsible sections or cards over permanently visible secondary detail.
- Collapsed means hidden, not squeezed. Do not leave cramped half-visible content inside the collapsed state just to imply expandability.
- Reuse existing disclosure patterns. Prefer the shared disclosure styling, shared recommendation component, existing card spacing, and existing shell/button language before inventing a new local UI pattern.
- Keep recommendations contextual. Inline recommendations should appear where the mismatch is discovered, stay subtle, and route action through the existing recommendation/chat flow rather than inventing a separate execution path per page.
- Respect the tier map when changing navigation or hierarchy. `Today`, `Capture`, `Thoughts`, `Promises`, and `Reports` are the calm daily loop; `Projects`, `Activities`, `Skills`, and `Connections` are deeper structured surfaces; `Admin`, `Processes`, and `Apps` belong to system/operator depth.
- Keep card actions consistent. Primary workflow actions should read like the rest of Rasbhari (`Next`, `Archive`, `Edit`, `Stage Action`) and should stay visually consistent across apps unless there is a clear product reason not to.
- Default to one strong action per area. Avoid multiple equally loud controls competing in the same card or header when one action is clearly primary.
- Preserve scanability on boards. Kanban, activity, and promise cards should remain easy to scan at a distance; ecosystem detail can expand, but titles, state, and next-action cues should stay visually stable.
- Prefer shared shell integration over page-local hacks. If something needs dismiss logic, recommendation behavior, or theme-aware UI behavior, look for the shared shell path first.
- Stay with framework scaffolding when the app is still being proven out. The generic Gabru CRUD surface is a valid baseline for prototyping, admin/internal resources, and low-priority apps.
- Move to a custom page when the domain has a real product identity. Use a custom home/template only when the app needs stronger workflow framing, ecosystem linkage, richer scanability, or a clearly better experience than the generic scaffold can provide.
- Do not replace framework scaffolding just for novelty. Custom UI should earn its maintenance cost through better product clarity, not aesthetic drift.

## Documentation Rules

No code change is complete until docs are consistent.

### Update docs when applicable
- New app: update `apps/README.md` and root `readme.md`
- New process: update `processes/README.md` and root `readme.md`
- New env var: update `.env.example` and `ENVIRONMENT.md`
- Framework or architecture change: update:
  - `gabru/readme.md`
  - `gabru/flask/README.md`
  - `gabru/flask/docs/how-to-create-an-app.md`
  - root `readme.md`
  - this `agents.md` if the architectural guidance changed

### Documentation standard
- Prefer explaining actual current architecture, not legacy patterns.
- Do not describe `gabru/` as directly owning Rasbhari implementation services.
- Keep examples aligned with the contract/runtime split.

## Required Review Checklist

Before considering work done, verify:

1. **Architecture**
- Did this change preserve the `gabru/` vs `runtime/` vs `services/` vs `apps/` boundary?

2. **Schema**
- Did any table shape change?
- If yes, is `_create_table()` or compatible schema evolution handled safely?

3. **Auth**
- Did this affect session auth, API-key auth, app permissions, or admin-only routes?

4. **Events**
- Should this emit an event?
- If it emits one, is the failure path logged but non-destructive where appropriate?

4.5. **Assistant Behavior**
- If this touches Rasbhari AI, does it preserve the rule that the LLM interprets intent but Rasbhari validates and executes?
- Does the assistant route through the app-specific resolver layer before execution instead of trusting a single raw model action?
- Does the assistant prefer event-first orchestration so existing promises, skills, reports, and notifications continue to react normally?
- Does the assistant prefer an existing activity when one already models the command?
- Are write actions staged for explicit confirmation instead of being auto-committed into the event pipeline?

5. **Docs**
- Did all relevant docs get updated?

6. **Runtime safety**
- Is this safe for Raspberry Pi and long-running processes?

7. **Verification**
- Did you run at least syntax validation?
- If practical, did you run targeted tests?

## Preferred Execution Flow

1. State how the change fits the current architecture.
2. Implement the smallest coherent change that solves the problem.
3. Preserve existing flows while refactoring.
4. Update docs in the same task.
5. Run validation.
6. Report outcomes, risks, and any remaining cleanup separately.

## Anti-Patterns

Avoid these unless explicitly justified:

- making `gabru/` import concrete Rasbhari services
- introducing new duplicate route definitions
- adding broad silent `except Exception: pass`
- mixing framework abstractions with app-specific behavior in the same layer
- introducing heavy dependencies for simple Raspberry Pi workflows
- rewriting working flows when a narrow refactor will do

## Good Defaults

When in doubt:

- put reusable contracts in `gabru/contracts.py`
- put Rasbhari-specific framework binding in `runtime/providers.py`
- put concrete implementation logic in `services/`
- put request/UI composition in `apps/`
- emit an event for meaningful state changes
- update the docs before finishing
