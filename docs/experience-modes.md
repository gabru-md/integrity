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

Rasbhari currently formalizes four user-facing experience tiers.

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

### 3. Work

This tier is for users running Rasbhari in a workplace or other screen-visible environment.

Primary goals:

- capture work thoughts quickly
- manage work projects and timelines
- draft blog posts without exposing leisure, private-life, or operator-heavy surfaces
- keep the shell safe when someone glances at the screen

This tier is a UI privacy mode, not a data security boundary. Direct URLs and permissions still depend on normal Rasbhari auth and app permissions.
The shell exposes a Work Mode toggle in the profile menu and mobile header so the user can quickly enter or leave this mode without visiting Profile Settings.

### 4. System

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

### Work

- `Dashboard`
- `Capture`
- `Thoughts`
- `Projects`
- `Blogs`
- lightweight `Profile`
- `Help`

These are the surfaces that support workplace capture and writing while keeping personal/leisure apps out of the sidebar. In Work mode, `/` redirects to `/dashboard`, and the Work dashboard filters widgets down to work-safe app widgets rather than exposing the full system dashboard.

### System

- `Admin`
- `Processes`
- `Apps`
- operator surfaces
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
- `Work` users should see only work-safe capture, writing, and project surfaces in shared-screen contexts
- `System` users can access the operator surfaces without hiding the rest of the product
- operator surfaces should be both visually tucked away and route-gated so a plain admin in a lighter mode does not fall into the control plane accidentally

### Density

- `Everyday` should prefer the quietest defaults
- `Structured` can expose more connected structure
- `Work` should stay compact and screen-safe
- `System` can tolerate more operational detail

### Onboarding

Onboarding should recommend a starting tier based on user goals, not app architecture.

### Recommendations

- `Everyday`: few, subtle, high-signal
- `Structured`: richer contextual linkage
- `Work`: limited to work-safe next steps
- `System`: deeper ecosystem and operator suggestions

## Product Rule

Rasbhari should not present itself as the whole machine on day one.

It should present:

- a minimum helpful loop first
- a structured system second
- a full personal operating environment only when the user wants that depth
