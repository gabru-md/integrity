# Rasbhari Experience Modes

Rasbhari should feel deep by capability but shallow by default.

The product goal is not to expose the whole machine immediately. It is to let a user start with the smallest helpful loop, then reveal richer structure only when they are ready for it.

## Pacing Model

Rasbhari should introduce itself in this order:

1. help the user capture something meaningful
2. show what matters now
3. make commitments and patterns legible
4. reveal deeper structure and operating surfaces only when useful

That means:

- daily-use surfaces should feel calm first
- advanced structure should expand gradually
- operator and system-management surfaces should stay out of the default path
- complexity should be staged, not removed

## Experience Tiers

Rasbhari currently formalizes three user-facing experience tiers.

### 1. Everyday

This is the default experience for a regular person who wants a calm daily system, not a full operating console.

Primary goals:

- capture what happened quickly
- see what matters today
- keep a few commitments visible
- notice drift without needing to understand the whole ecosystem

This tier should feel complete on its own.

### 2. Structured

This tier is for users who want more deliberate organization across work, routines, and growth.

Primary goals:

- manage projects and active work
- connect activities to promises and skills
- keep richer structure without dropping into operator concerns

This tier adds planning and ecosystem linkage, not system administration.

### 3. System

This tier is for users who want to operate Rasbhari as an instrumented personal system.

Primary goals:

- manage background processes and app activation
- inspect system health and dependencies
- work with recommendations, automations, and deeper operational control

This tier includes the control-plane weight that should not be pushed into the default daily experience.

## App And Surface Mapping

### Everyday

- `Today`
- `Capture`
- `Thoughts`
- `Promises`
- `Reports`
- lightweight `Profile`
- first-run tutorial and setup checklist

These are the surfaces that should define Rasbhari for a new or regular user.

### Structured

- `Projects`
- `KanbanTickets`
- `Activities`
- `Skills`
- `Connections`
- richer project timeline and project board surfaces

These are the surfaces that turn Rasbhari from a daily companion into a more intentional life-and-work system.

### System

- `Admin`
- `Processes`
- `Apps`
- operator guide surfaces
- advanced recommendation behavior
- deployment, backup, and update visibility

These are valid Rasbhari surfaces, but they belong to the deepest tier because they are operating-system concerns rather than normal daily-use concerns.

## UX Implications

The tier model should drive future product work in four places:

1. navigation visibility
2. page density and disclosure defaults
3. onboarding and tutorial framing
4. recommendation intensity

### Navigation

- `Everyday` users should see the calm daily loop first
- `Structured` users can see planning and ecosystem apps more prominently
- `System` users can access the operator surfaces without hiding the rest of the product

### Density

- `Everyday` should prefer the quietest defaults
- `Structured` can expose more connected structure
- `System` can tolerate more operational detail

### Onboarding

Onboarding should recommend a starting tier based on user goals, not app architecture.

### Recommendations

- `Everyday`: few, subtle, high-signal
- `Structured`: richer contextual linkage
- `System`: deeper ecosystem and operator suggestions

## Product Rule

Rasbhari should not present itself as the whole machine on day one.

It should present:

- a minimum helpful loop first
- a structured system second
- a full personal operating environment only when the user wants that depth
