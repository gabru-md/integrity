def build_rasbhari_mental_model() -> dict:
    return {
        "headline": "Rasbhari is a personal operating system for daily life.",
        "summary": "Rasbhari is one connected loop, not a folder of disconnected tools. Each app helps you capture life, add structure, keep commitments, grow, reflect, or decide what to do next.",
        "identity": {
            "title": "What Rasbhari Is",
            "body": "Rasbhari is a personal operating system for daily life. It helps you record what matters, organize it into projects and relationships, compare it against commitments, and turn it back into useful guidance.",
        },
        "stages": [
            {
                "name": "Capture",
                "description": "Events, activities, local signals, thoughts, media, and future imports turn real life into a shared record.",
                "apps": ["Events", "Activities", "Thoughts", "Devices", "rTV"],
            },
            {
                "name": "Structure",
                "description": "Projects, kanban tickets, blogs, and connections organize raw activity into work, relationships, and narrative context.",
                "apps": ["Projects", "KanbanTickets", "Blogs", "Connections"],
            },
            {
                "name": "Commit",
                "description": "Promises make expectations explicit by watching for the event types and tags that should exist.",
                "apps": ["Promises"],
            },
            {
                "name": "Grow",
                "description": "Skills turn repeated tagged work into visible progression and levels.",
                "apps": ["Skills"],
            },
            {
                "name": "Reflect",
                "description": "Reports and timeline signals show where behavior matched or drifted from visible intent.",
                "apps": ["Reports", "Projects", "Events"],
            },
            {
                "name": "Act",
                "description": "Today, notifications, and staged recommendations focus attention on the next small moves that matter.",
                "apps": ["Today", "Reports", "Projects", "Promises"],
            },
        ],
        "setup_path": [
            "Create one activity so repeated actions become easy to log.",
            "Create one project and one ticket so active work has structure.",
            "Add one promise tied to a real event type or tag.",
            "Add one skill tied to the tags you want to grow.",
            "Open Today and check whether work, promises, and growth now connect visibly.",
        ],
    }


def build_rasbhari_tutorial() -> dict:
    goals = [
        {
            "id": "daily_clarity",
            "title": "Stay on top of daily life",
            "summary": "Start with quick capture, Today, commitments, and reflection before adding deeper structure.",
            "why_it_matters": "This is the best starting point if you mainly want clarity, continuity, and less life drift.",
            "recommended_mode": "everyday",
        },
        {
            "id": "work_and_routines",
            "title": "Organize projects and routines",
            "summary": "Add projects, activities, skills, and richer structure once the daily loop already makes sense.",
            "why_it_matters": "This fits people who want stronger execution and visible growth without dropping into operator depth.",
            "recommended_mode": "structured",
        },
        {
            "id": "full_system",
            "title": "Operate the full Rasbhari system",
            "summary": "Expose the full ecosystem, including operator surfaces, deeper recommendations, and system-level controls.",
            "why_it_matters": "This mode is for people who want Rasbhari as an instrumented personal operating environment, not just a daily companion.",
            "recommended_mode": "system",
        },
    ]

    steps = [
        {
            "id": "today",
            "title": "Today is the front door",
            "target_label": "Today",
            "target_path": "/",
            "modes": ["everyday", "structured", "system"],
            "summary": "Start here each day. Today brings active work, due promises, neglected relationships, suggested activities, and useful guidance into one calm home.",
            "why_it_matters": "If Rasbhari feels fragmented, Today is where the system recomposes itself.",
            "checklist": [
                "Scan the guidance cards before opening other apps.",
                "Look for active tickets, due promises, or neglected connections.",
            ],
        },
        {
            "id": "capture",
            "title": "Capture keeps the system honest",
            "target_label": "Capture",
            "target_path": "/capture",
            "modes": ["everyday", "structured", "system"],
            "summary": "Use Capture when something meaningful happens and you want it recorded quickly before the moment is gone.",
            "why_it_matters": "Rasbhari becomes useful only when real life is turned into a visible record with very little friction.",
            "checklist": [
                "Use Quick Log for one-off moments that matter now.",
                "Use reusable shortcuts when you repeat the same action often.",
            ],
        },
        {
            "id": "events",
            "title": "Events are the shared record",
            "target_label": "Events",
            "target_path": "/events/home",
            "modes": ["system"],
            "summary": "Most of Rasbhari works because meaningful things become events. Other apps use them as the shared record of what actually happened.",
            "why_it_matters": "Promises, skills, reports, notifications, and imports all depend on stable event evidence.",
            "checklist": [
                "Notice the event type and tag vocabulary.",
                "Keep names stable when you log new signals.",
            ],
        },
        {
            "id": "activities",
            "title": "Activities make capture fast",
            "target_label": "Activities",
            "target_path": "/activities/home",
            "modes": ["structured", "system"],
            "summary": "Activities are reusable buttons for actions you repeat. Triggering one creates an event without making you fill the same form every time.",
            "why_it_matters": "Good activities reduce friction and improve event consistency.",
            "checklist": [
                "Create activities for repeated actions, not rare one-offs.",
                "Use tags if the action should count toward skills or promises.",
            ],
        },
        {
            "id": "projects",
            "title": "Projects give work a home",
            "target_label": "Projects",
            "target_path": "/projects/home",
            "modes": ["structured", "system"],
            "summary": "Projects organize larger bodies of work. Their timelines tell the story, and their focus tags link work back to promises and skills.",
            "why_it_matters": "Projects turn isolated events into ongoing intent and visible progress.",
            "checklist": [
                "Use focus tags when project work should count elsewhere.",
                "Open a project when work needs context, not just logging.",
            ],
        },
        {
            "id": "kanban",
            "title": "Kanban turns projects into execution",
            "target_label": "Kanban",
            "target_path": "/kanbantickets/home",
            "modes": ["structured", "system"],
            "summary": "Kanban tickets are the concrete units of project work. They move from backlog to shipped and emit project-work signals as they change.",
            "why_it_matters": "Tickets make Today, reports, and project history reflect actual execution instead of abstract plans.",
            "checklist": [
                "Keep tickets short and concrete.",
                "Move tickets when the state changes so the event bus stays honest.",
            ],
        },
        {
            "id": "promises",
            "title": "Promises make commitments visible",
            "target_label": "Promises",
            "target_path": "/promises/home",
            "modes": ["everyday", "structured", "system"],
            "summary": "Promises watch for the event types and tags that should exist over time. They are how Rasbhari compares intent to evidence.",
            "why_it_matters": "A promise only works if your events and tags actually describe the behavior you care about.",
            "checklist": [
                "Use a real event type or tag as the promise target.",
                "Check due or drifting promises from Today and reports.",
            ],
        },
        {
            "id": "skills",
            "title": "Skills reward repeated effort",
            "target_label": "Skills",
            "target_path": "/skills/home",
            "modes": ["structured", "system"],
            "summary": "Skills turn tagged work into XP and levels. They show whether repeated effort is accumulating into growth.",
            "why_it_matters": "Stable tags make growth visible across activities, tickets, and imports.",
            "checklist": [
                "Use one stable tag key per skill.",
                "Prefer skill names that reflect capabilities you actually want to grow.",
            ],
        },
        {
            "id": "reports",
            "title": "Reports reflect the whole system",
            "target_label": "Reports",
            "target_path": "/reports/home",
            "modes": ["everyday", "structured", "system"],
            "summary": "Reports are the behavioral mirror. They compare projects, promises, skills, thoughts, and events to reveal both progress and drift.",
            "why_it_matters": "This is where Rasbhari stops being a tracker and starts helping you see where life is lining up well and where it is drifting.",
            "checklist": [
                "Generate a report once real activity exists.",
                "Use it to adjust capture, structure, or commitments.",
            ],
        },
    ]

    return {
        "headline": "Choose the kind of help you want first.",
        "summary": "Rasbhari should not introduce the whole machine at once. Start with the use-case that matches you, let Rasbhari recommend a starting experience mode, and then learn the loop from there.",
        "goals": goals,
        "goal_summary": "Pick the closest fit. Rasbhari will recommend a starting experience mode and then continue with the walkthrough.",
        "steps": steps,
        "completion_copy": "You have seen the core loop. The next useful move is to create a little real structure and then return to Today.",
    }


def build_rasbhari_admin_guide() -> dict:
    sections = [
        {
            "title": "Process Health",
            "summary": "Use the Processes page as the operational heartbeat of Rasbhari. Dependency health, process state, and queue movement tell you whether the system is merely up or actually functioning.",
            "actions": [
                {"label": "Open Processes", "href": "/processes"},
                {"label": "Check Dependency Health", "href": "/processes"},
            ],
            "checklist": [
                "Confirm critical processes are enabled before expecting features to work.",
                "Use dependency health cards to catch ntfy, SendGrid, or OpenWebUI issues early.",
                "Treat stalled queue processors as product problems, not only infrastructure noise.",
            ],
        },
        {
            "title": "Notifications",
            "summary": "Notifications are now intentional and classed. As an admin, your job is to make sure delivery works and that the system stays high-signal instead of noisy.",
            "actions": [
                {"label": "Review Environment", "href": "/docs/environment.md"},
                {"label": "Open Processes", "href": "/processes"},
            ],
            "checklist": [
                "Make sure ntfy and email credentials are configured before relying on outbound alerts.",
                "Understand the difference between urgent, today, review, suggestion, digest, and system notifications.",
                "Investigate Courier failures before users assume Rasbhari is quiet by design.",
            ],
        },
        {
            "title": "User Onboarding",
            "summary": "Admins own the first impression. New users need approval, a clean mental model, the guided tutorial, and a minimum useful setup path to feel the ecosystem instead of just seeing many apps.",
            "actions": [
                {"label": "Open Users", "href": "/users/home"},
                {"label": "Open Today", "href": "/"},
            ],
            "checklist": [
                "Approve legitimate signups promptly so onboarding momentum is not lost.",
                "Point new users to the Today page, tutorial, and setup checklist rather than every app at once.",
                "Encourage one real activity, project, promise, skill, and ticket before expecting reports or recommendations to feel useful.",
            ],
        },
        {
            "title": "App Relationships",
            "summary": "Rasbhari works when apps reinforce one another. Admins should understand and explain the chain from capture to action so operators and users configure things coherently.",
            "actions": [
                {"label": "Open Mental Model", "href": "/docs/mental-model.md"},
                {"label": "Open System Apps", "href": "/apps"},
            ],
            "checklist": [
                "Events are the shared language. Activities, imports, and processes should feed that stream cleanly.",
                "Projects and kanban structure work. Promises and skills should latch onto stable tags or event types.",
                "Today and Reports become useful only after the earlier layers produce honest evidence.",
            ],
        },
        {
            "title": "Operational Setup",
            "summary": "Operator work is not only running the server. It includes environment hygiene, app activation, process activation, and keeping the system understandable as it grows.",
            "actions": [
                {"label": "Open System Apps", "href": "/apps"},
                {"label": "Open Setup Docs", "href": "/docs/setup.md"},
                {"label": "Remote Pi Ops", "href": "/docs/remote-pi-ops.md"},
            ],
            "checklist": [
                "Only enable apps and widgets that are actually supported by the current environment.",
                "Verify core databases, logs, and secrets before debugging higher-level product behavior.",
                "Use the admin guide as the operator narrative and the user tutorial as the end-user narrative.",
            ],
        },
        {
            "title": "Operational Boundaries",
            "summary": "Admins should be able to operate the Rasbhari ecosystem from inside Rasbhari, but host-level infrastructure still belongs outside the product.",
            "actions": [
                {"label": "Open Admin Overview", "href": "/admin"},
                {"label": "Open Processes", "href": "/processes"},
                {"label": "Remote Pi Ops", "href": "/docs/remote-pi-ops.md"},
            ],
            "checklist": [
                "Manage app activation, widgets, process state, queue recovery, user approvals, and dependency health from inside Rasbhari.",
                "Keep PostgreSQL schema surgery, Docker/service restarts, restore workflows, and filesystem repair as infrastructure work outside Rasbhari.",
                "Scheduled backup execution can run through Rasbhari's process manager, but the actual backup script still operates at the host level.",
                "Add future admin features only when they operate the product itself rather than the host machine underneath it.",
            ],
        },
    ]

    return {
        "headline": "Admin Guide",
        "summary": "This path is for operators, not end users. It explains how to keep Rasbhari healthy, understandable, and coherent as one event-driven product.",
        "sections": sections,
    }


def build_app_user_guidance(app_name: str) -> dict:
    docs = {
        "BrowserActions": {
            "overview": "Browser Actions define the extension-visible actions Rasbhari can sync and trigger.",
            "app_purpose": "Use Browser Actions to map browser verbs back into Activities, events, project updates, or quick-log flows.",
            "how_to_use": [
                "Create one action per meaningful browser capture you want the extension to offer later.",
                "Pick the generic browser action first, then choose what Rasbhari target it should map to.",
                "Prefer target type activity when an existing Activity already models the behavior.",
                "Use default payload only for stable extra context that should always be merged with browser context.",
            ],
            "setup_leverage": [
                "Start with only a few browser actions.",
                "Prefer stable names and targets.",
            ],
            "pairs_with": ["Activities", "Projects", "Events", "Automation"],
            "glossary": [
                {"term": "Browser Action", "meaning": "A concrete action Rasbhari can sync to the browser extension."},
                {"term": "Target Type", "meaning": "What Rasbhari should trigger when the action runs."},
                {"term": "Default Payload", "meaning": "Extra structured data merged with browser context."},
            ],
            "examples": [
                "Example: name Save Docs Research, browser action save_current_page, target type activity, target activity id 12.",
            ],
        },
        "BrowserRules": {
            "overview": "Browser Rules decide when browser context should trigger a configured Browser Action.",
            "app_purpose": "Use Browser Rules to describe if user does A on website B then trigger C.",
            "how_to_use": [
                "Choose the Browser Action the rule should trigger first, then define when and where it should apply.",
                "Use trigger mode confirm for most rules until the capture pattern proves trustworthy.",
                "Keep scope narrow with domains or URL matching so browser automation stays explainable.",
                "Only use automatic mode for low-risk, high-confidence captures.",
            ],
            "setup_leverage": [
                "Start with one or two calm rules.",
                "Use lower priority only when a rule should win.",
            ],
            "pairs_with": ["BrowserActions", "Automation", "Activities", "Projects"],
            "glossary": [
                {"term": "Browser Rule", "meaning": "A rule that decides when to trigger a Browser Action."},
                {"term": "Trigger Mode", "meaning": "Manual, confirm, or automatic."},
                {"term": "Match Scope", "meaning": "The site and URL boundaries where the rule may match."},
                {"term": "Payload Behavior", "meaning": "How browser context is forwarded into Rasbhari."},
            ],
            "examples": [
                "Example: on docs.python.org, when selection exists, ask for confirmation before triggering Save Docs Research.",
            ],
        },
        "rTV": {
            "overview": "rTV is a small owned-movie shelf for Rasbhari and your TV.",
            "app_purpose": "Use rTV to scan ready local movie files, open a TV-first movie surface, and turn watching into Rasbhari media events.",
            "how_to_use": [
                "Put supported movie files in the configured rTV media folder.",
                "Use Scan Folder from the rTV admin page to add ready local movies.",
                "Open the TV surface from a browser on your TV, use search or the rails, then play, resume, or restart ready movies.",
                "For magnet candidates, resolve metadata first so rTV can choose the largest movie file, then queue the download for the later processor.",
                "Use the inline title field for cleanup, Retry for failed candidates or downloads, Delete File to free local cache, and Delete to remove the rTV record.",
            ],
            "setup_leverage": [
                "Start with MP4 H264 AAC files for the best TV-browser playback chance.",
                "Keep the library small and curated so the Raspberry Pi stays responsive.",
            ],
            "pairs_with": ["Events", "Reports", "Today"],
            "glossary": [
                {"term": "Ready Movie", "meaning": "A local movie file that rTV can serve to the TV player."},
                {"term": "Candidate", "meaning": "A movie record saved for later download or preparation."},
            ],
        },
        "Activities": {
            "overview": "Activities are reusable actions you want to trigger from the dashboard. When you trigger one, Rasbhari turns it into an event so promises, skills, Today, and reports can react.",
            "app_purpose": "Use Activities when you want repeated real-world actions to become consistent event-producing shortcuts instead of manual form work, and when you want those triggers to stay visibly connected to the rest of the ecosystem.",
            "how_to_use": [
                "Create an activity once, then trigger it whenever that action happens in real life.",
                "Use a stable event type so processors and dashboards can recognize the action consistently.",
                "Add tags when you want skills, promises, or filters to pick up the event later.",
                "Use the activity catalog to verify which promises or skills the emitted event will actually satisfy.",
            ],
            "setup_leverage": [
                "Create activities for the 3 to 5 actions you repeat most often.",
                "Choose stable event types and tags so the rest of Rasbhari can react consistently.",
                "Prefer tags that already exist in promises or skills so each trigger visibly contributes elsewhere.",
            ],
            "pairs_with": ["Events", "Skills", "Promises", "Today"],
            "glossary": [
                {"term": "Activity",
                 "meaning": "A reusable action template such as Clean Kitchen, Study Session, or Water Plants."},
                {"term": "Event Type",
                 "meaning": "The machine-readable name emitted when the activity is triggered, such as kitchen:cleaned."},
                {"term": "Tags",
                 "meaning": "Short labels attached to the emitted event. Tags make it easier to match skills, promises, and searches."},
                {"term": "Default Payload",
                 "meaning": "Extra JSON data sent with the event every time this activity is triggered unless you override it."},
            ],
            "examples": [
                "Example: an activity named Study Session can emit event type learning:session with tags study, python.",
            ],
        },
        "Blogs": {
            "overview": "Blogs let you publish longer notes or articles inside Rasbhari. Posts support markdown and can also create timeline-friendly history for your work.",
            "app_purpose": "Use Blogs when a project update or reflection deserves longer narrative form than an event, thought, or short project update.",
            "how_to_use": [
                "Use draft status while writing, then switch to published when the post is ready to share on the site.",
                "Keep slugs short and stable because they become part of the post URL.",
                "Use tags to group related posts and make them easier to scan later.",
            ],
            "setup_leverage": [
                "Write blogs only for material that benefits from longer narrative context.",
                "Use tags that align with projects or recurring themes so reports and browsing stay coherent.",
            ],
            "pairs_with": ["Projects", "Reports"],
            "glossary": [
                {"term": "Slug", "meaning": "The URL-safe identifier for a post, such as weekly-review-12."},
                {"term": "Markdown",
                 "meaning": "A lightweight writing format for headings, links, lists, and code blocks."},
                {"term": "Status",
                 "meaning": "Draft keeps the post in progress. Published marks it as ready for reading."},
            ],
            "examples": [
                "Example: title Weekly Review, slug weekly-review, tags review, reflection.",
            ],
        },
        "Devices": {
            "overview": "Devices describe physical or network-connected things Rasbhari can reason about, monitor, or control.",
            "app_purpose": "Use Devices to describe the physical endpoints future automation, imports, and system processes may need to reference consistently.",
            "how_to_use": [
                "Create one record per real device so automation and monitoring can reference it consistently.",
                "Use location and type values that make sense to you when scanning the dashboard.",
                "Only enable devices for apps that should be allowed to use them.",
            ],
            "setup_leverage": [
                "Add devices only when a process or automation actually needs a named endpoint.",
                "Keep names and locations human-readable so system panels stay legible.",
            ],
            "pairs_with": ["Processes", "Imports"],
            "glossary": [
                {"term": "Location", "meaning": "The room or place where the device belongs, such as Kitchen or Desk."},
                {"term": "Type", "meaning": "The category of device, such as Camera, Beacon, Light, or Sensor."},
                {"term": "Authorized Apps",
                 "meaning": "The Rasbhari apps or processes that are allowed to use this device."},
            ],
        },
        "Connections": {
            "overview": "Connections represent people or relationships you want Rasbhari to help you maintain with intention.",
            "app_purpose": "Use Connections when you want relationships to be visible enough for Today and Reports to surface neglect, cadence drift, and social balance.",
            "how_to_use": [
                "Create one record per person or relationship that matters enough to track.",
                "Set cadence days to the maximum gap you want between meaningful touchpoints.",
                "Use priority to distinguish relationships that should affect integrity scoring more strongly in your own review process.",
                "Log interactions directly inside the Connections page so the relationship record and its timeline stay together.",
                "Use the card expanders when you want tags or last-contact detail without keeping every relationship fully open at once.",
            ],
            "setup_leverage": [
                "Start with only the people you actually want Rasbhari to remind you about.",
                "Set cadence days honestly so overdue signals are meaningful instead of noisy.",
            ],
            "pairs_with": ["Today", "Reports", "Events"],
            "glossary": [
                {"term": "Cadence",
                 "meaning": "How many days can pass before the relationship is considered overdue for contact."},
                {"term": "Priority",
                 "meaning": "A simple importance flag to help you visually separate core relationships from lighter ties."},
                {"term": "Ledger",
                 "meaning": "The timeline of calls, texts, meetups, and other interactions logged under a connection."},
                {"term": "Last Contact",
                 "meaning": "The latest timestamp automatically updated when a connection interaction is created."},
            ],
            "examples": [
                "Example: create Mom with cadence 7 days and priority High to make overdue contact obvious in reports.",
            ],
        },
        "Events": {
            "overview": "Events are the shared language of Rasbhari. Most automation, tracking, and history features work by creating or consuming events.",
            "app_purpose": "Use Events to record meaningful facts and inspect the shared evidence stream that powers promises, skills, reports, notifications, and imports.",
            "how_to_use": [
                "Log an event whenever something meaningful happens.",
                "Keep event types consistent so background processors can match them reliably.",
                "Use tags for cross-cutting labels like python, workout, notification, or project names.",
            ],
            "setup_leverage": [
                "Standardize event types early so downstream processors stay reliable.",
                "Use tags for cross-app linkage rather than inventing too many similar event types.",
            ],
            "pairs_with": ["Activities", "Promises", "Skills", "Reports", "Today"],
            "glossary": [
                {"term": "Event", "meaning": "A record of something that happened at a point in time."},
                {"term": "Event Type", "meaning": "The main event identifier, usually written like domain:action."},
                {"term": "Tags",
                 "meaning": "Secondary labels that help other apps group, reward, notify, or count events."},
            ],
            "examples": [
                "Example: event type learning:session, description Read chapter 3, tags python, study.",
            ],
        },
        "Projects": {
            "overview": "Projects track larger bodies of work. Use the project page to manage the project record, then open a project to maintain its narrative timeline, real linked blog posts, and execution board.",
            "app_purpose": "Use Projects to give larger work a durable home so execution, narrative updates, blog writing, promises, skills, and reports all point back to the same body of work.",
            "how_to_use": [
                "Create a project first, then use View Progress to maintain its narrative timeline.",
                "Use Open Board when you want to track concrete tickets from backlog to shipped.",
                "Use project type for broad grouping only. The timeline carries the detailed story.",
                "Add focus tags when project work should count toward promises or skills, for example python, writing, or deep-work.",
                "Set a ticket prefix like RSB or QDS when you want tickets to get stable references such as RSB-14.",
                "Post short updates for milestones and choose Blog when an update deserves a fuller markdown write-up that should also exist in Blogs.",
            ],
            "setup_leverage": [
                "Add focus tags for any project whose work should count toward promises or skills.",
                "Choose a ticket prefix before the board gets busy so references stay clean from the start.",
                "Use the board for execution and the timeline for narrative progress.",
            ],
            "pairs_with": ["KanbanTickets", "Reports", "Skills", "Promises", "Today"],
            "glossary": [
                {"term": "Project Type", "meaning": "A simple category such as Code, DIY, or Other."},
                {"term": "Focus Tags", "meaning": "Shared tags Rasbhari adds to project work events so tickets, promises, skills, and Today can line up around the same work."},
                {"term": "Ticket Prefix", "meaning": "The short code Rasbhari uses to issue stable ticket references like RSB-14 for this project."},
                {"term": "State",
                 "meaning": "The current lifecycle status of the project, such as Active or Completed."},
                {"term": "Progress Count", "meaning": "How many timeline updates have been logged for the project."},
                {"term": "Board", "meaning": "A simple project kanban view for tickets moving from backlog to shipped."},
            ],
        },
        "KanbanTickets": {
            "overview": "Kanban tickets are minimal project work items. Each ticket belongs to one project and moves through a fixed board from backlog to shipped.",
            "app_purpose": "Use KanbanTickets to turn project intent into concrete execution that Rasbhari can reflect through events, Today, skills, and reports.",
            "how_to_use": [
                "Keep tickets short and concrete so the board stays fast to scan.",
                "Use the board for day-to-day execution and the project timeline for narrative updates.",
                "Move tickets forward as work advances. Rasbhari emits events when tickets are created or moved.",
                "Use ticket codes like RSB-14 when you want a stable project-specific reference for conversation, notes, or follow-up.",
                "Project focus tags are automatically added to ticket workflow events so project work can contribute to promises and skills.",
                "Archive shipped or stale tickets when you want them out of the active board without deleting their history.",
            ],
            "setup_leverage": [
                "Only keep the next layer of concrete work on the board so it stays fast to scan.",
                "Make sure the parent project has useful focus tags so ticket work contributes elsewhere.",
            ],
            "pairs_with": ["Projects", "Today", "Reports", "Skills", "Promises"],
            "glossary": [
                {"term": "Backlog", "meaning": "Work that exists but is not yet selected."},
                {"term": "Prioritized", "meaning": "Work chosen as likely next."},
                {"term": "In Progress", "meaning": "Work currently being executed."},
                {"term": "Completed", "meaning": "Work finished but not yet shipped or deployed."},
                {"term": "Shipped", "meaning": "Work delivered, released, or deployed."},
                {"term": "Ticket Code", "meaning": "The stable project-specific identifier like RSB-14 that stays with the ticket even if the project prefix changes later."},
                {"term": "Archived", "meaning": "A ticket hidden from the project board but still kept in the system and global ticket list."},
            ],
        },
        "Promises": {
            "overview": "Promises track commitments over time.",
            "app_purpose": "Use Promises to turn intentions into commitments Rasbhari can verify against event evidence.",
            "how_to_use": [
                "Use a target event type, a target tag, or both.",
                "Set required count for each period.",
                "Use refresh when you want the UI to recount recent matching events immediately.",
            ],
            "setup_leverage": [
                "Attach promises to event types or tags you already use.",
                "Prefer a few meaningful promises over many weak ones.",
            ],
            "pairs_with": ["Events", "Today", "Reports", "Projects"],
            "glossary": [
                {"term": "Frequency",
                 "meaning": "How often the promise resets, such as daily, weekly, monthly, or once."},
                {"term": "Target Event Tag",
                 "meaning": "A tag that matching events must contain, such as workout or reading."},
                {"term": "Target Event Type",
                 "meaning": "A specific event type the promise should watch, such as fitness:session."},
                {"term": "Required Count",
                 "meaning": "How many matching events are needed in a period for the promise to be fulfilled."},
                {"term": "Streak", "meaning": "How many periods in a row the promise has been kept."},
            ],
        },
        "Skills": {
            "overview": "Skills convert repeated tagged activity into progression. Rasbhari reads matching events, adds XP, and levels a skill up over time.",
            "app_purpose": "Use Skills to make growth visible by rewarding repeated tagged work across activities, project work, and imported signals.",
            "how_to_use": [
                "Create one skill per thing you want to intentionally improve.",
                "Pick a stable tag key because that is what incoming event tags are matched against first.",
                "Add aliases when people or systems might log the same skill under different names.",
            ],
            "setup_leverage": [
                "Choose stable tag keys that already appear in activities, projects, or events.",
                "Keep aliases limited to real naming variations so XP does not become noisy.",
            ],
            "pairs_with": ["Events", "Projects", "KanbanTickets", "Today", "Reports"],
            "glossary": [
                {"term": "Skill",
                 "meaning": "A capability you want to grow over time, such as Python, Cooking, or Counter Strike."},
                {"term": "Tag Key",
                 "meaning": "The primary tag used to match events to this skill. It should stay stable over time."},
                {"term": "Aliases", "meaning": "Alternative tag names that should also count toward the same skill."},
                {"term": "Total XP",
                 "meaning": "The accumulated experience points earned for the skill from matching events."},
                {"term": "Requirement",
                 "meaning": "The current description of what is needed to reach the next level."},
            ],
            "examples": [
                "Example: skill Python with tag key python and alias py will gain XP from events tagged python or py.",
            ],
        },
        "Reports": {
            "overview": "Reports turn raw activity into a behavioral mirror.",
            "app_purpose": "Use Reports to surface drift, missing action, and integrity gaps.",
            "how_to_use": [
                "Generate daily, weekly, or monthly mirrors.",
                "Use async generation when you want the event pipeline to handle it.",
                "Open observations only when the summary looks interesting.",
                "Use print view for a local PDF-friendly page.",
                "Add Connections and log interactions inside their ledger if you want the report to score social balance and neglected relationships.",
            ],
            "setup_leverage": [
                "Reports become useful after the system has real data.",
                "Use reports to adjust structure, not just admire outputs.",
            ],
            "pairs_with": ["Today", "Projects", "Promises", "Skills", "Connections", "Events"],
            "glossary": [
                {"term": "Integrity Score",
                 "meaning": "A 0 to 100 score estimating how closely your behavior matched your visible commitments and growth signals."},
                {"term": "Stalled Intent",
                 "meaning": "An active project with no matching progress evidence in the selected time window."},
                {"term": "Behavioral Mirror",
                 "meaning": "A report that reflects both logged action and missing action, not just completed items."},
                {"term": "Neglected Connection",
                 "meaning": "A tracked relationship whose last contact is older than the cadence you set in Connections."},
            ],
            "examples": [
                "Example: a daily report can flag that a project stayed active while no project-linked events or updates were logged.",
            ],
        },
        "Thoughts": {
            "overview": "Thoughts are a private posting stream for ideas, reflections, reminders, and fragments you want to capture before they disappear. They are lighter than blog posts and faster than creating a full project or event entry.",
            "app_purpose": "Use Thoughts as a personal micro-posting engine for fast human context that matters but is not yet structured enough to become an event, project update, or blog post.",
            "how_to_use": [
                "Use thoughts for short captures you do not want to lose.",
                "Treat the stream like a private feed: post quickly, scan later, and edit only when the wording matters.",
                "Prefer blogs when you need formatting and longer writing.",
                "Prefer events when the main goal is to record that something happened rather than what you are thinking about it.",
            ],
            "setup_leverage": [
                "Capture thoughts quickly, then later convert the important ones into projects, events, or reports.",
                "Use thoughts for context and reflection, not as a substitute for all structured data.",
            ],
            "pairs_with": ["Reports", "Projects", "Today"],
            "glossary": [
                {"term": "Thought", "meaning": "A short private post captured with minimal structure."},
            ],
        },
        "Users": {
            "overview": "Users manage who can sign into this Rasbhari instance. Each person gets their own private workspace, while admin access only unlocks system panels.",
            "app_purpose": "Use Users to manage ownership and operator access without collapsing everyone into one shared data space.",
            "how_to_use": [
                "Create one account per family member or operator who should use this Rasbhari installation.",
                "Only mark trusted operator accounts as admin. Admins can manage the system but do not automatically see other users' personal records.",
                "Set a password when creating a user. Enter a new password later only when you want to rotate or reset it.",
            ],
            "setup_leverage": [
                "Keep admin accounts limited to trusted operators.",
                "Treat onboarding and profile settings as part of user adoption, not just account management.",
            ],
            "pairs_with": ["Today", "Processes", "Profile"],
            "glossary": [
                {"term": "Admin",
                 "meaning": "An operator who can access system panels like Processes, Devices, and dependency health."},
                {"term": "Personal Workspace",
                 "meaning": "The private set of app records owned by a specific user account."},
                {"term": "Active", "meaning": "Whether the account is allowed to sign in."},
            ],
        },
    }
    guidance = dict(docs.get(app_name, {}))
    mental_model = build_rasbhari_mental_model()
    stage_lookup = {}
    for stage in mental_model["stages"]:
        for app in stage["apps"]:
            stage_lookup.setdefault(app, []).append(stage["name"])

    guidance["ecosystem_fit"] = {
        "headline": "How this app fits Rasbhari",
        "summary": {
            "BrowserActions": "BrowserActions are the Rasbhari-side configuration layer the browser extension will later sync and expose as Capture Automation choices.",
            "BrowserRules": "BrowserRules decide when those BrowserActions should appear, ask first, or trigger automatically on matching browser context.",
            "rTV": "rTV turns ready owned movies into a TV-first watch surface and records watching as media events.",
            "Activities": "Activities are the easiest way to capture repeated real-world actions so the rest of Rasbhari can react to them.",
            "Blogs": "Blogs add longer narrative context to project work and reflection.",
            "Connections": "Connections turn relationship maintenance into something visible enough for Today and Reports to reason about.",
            "Devices": "Devices define the physical endpoints future automation and imports can use.",
            "Events": "Events are the shared language everything else listens to or emits.",
            "Projects": "Projects structure larger bodies of work so execution, progress, promises, and skills can line up.",
            "KanbanTickets": "Kanban tickets make project execution concrete and emit project-work signals back into the event bus.",
            "Promises": "Promises convert your intentions into checkable commitments against real evidence.",
            "Skills": "Skills reward repeated tagged work so growth becomes visible instead of assumed.",
            "Reports": "Reports reflect the whole system back to you and expose drift between visible intent and recorded behavior.",
            "Thoughts": "Thoughts capture fast human context before it turns into an event, project, or report input.",
            "Users": "Users define who owns a private workspace and who operates the system.",
        }.get(app_name, "This app is one part of the shared Rasbhari loop."),
        "stages": stage_lookup.get(app_name, []),
    }
    return guidance
