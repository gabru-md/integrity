def build_app_user_guidance(app_name: str) -> dict:
    docs = {
        "Activities": {
            "overview": "Activities are reusable actions you want to trigger from the dashboard. When you trigger one, Rasbhari turns it into an event so the rest of the system can react.",
            "how_to_use": [
                "Create an activity once, then trigger it whenever that action happens in real life.",
                "Use a stable event type so processors and dashboards can recognize the action consistently.",
                "Add tags when you want skills, promises, or filters to pick up the event later.",
            ],
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
            "how_to_use": [
                "Use draft status while writing, then switch to published when the post is ready to share on the site.",
                "Keep slugs short and stable because they become part of the post URL.",
                "Use tags to group related posts and make them easier to scan later.",
            ],
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
            "how_to_use": [
                "Create one record per real device so automation and monitoring can reference it consistently.",
                "Use location and type values that make sense to you when scanning the dashboard.",
                "Only enable devices for apps that should be allowed to use them.",
            ],
            "glossary": [
                {"term": "Location", "meaning": "The room or place where the device belongs, such as Kitchen or Desk."},
                {"term": "Type", "meaning": "The category of device, such as Camera, Beacon, Light, or Sensor."},
                {"term": "Authorized Apps",
                 "meaning": "The Rasbhari apps or processes that are allowed to use this device."},
            ],
        },
        "Connections": {
            "overview": "Connections represent people or relationships you want Rasbhari to help you maintain with intention.",
            "how_to_use": [
                "Create one record per person or relationship that matters enough to track.",
                "Set cadence days to the maximum gap you want between meaningful touchpoints.",
                "Use priority to distinguish relationships that should affect integrity scoring more strongly in your own review process.",
                "Log interactions directly inside the Connections page so the relationship record and its timeline stay together.",
            ],
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
            "how_to_use": [
                "Log an event whenever something meaningful happens.",
                "Keep event types consistent so background processors can match them reliably.",
                "Use tags for cross-cutting labels like python, workout, notification, or project names.",
            ],
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
            "overview": "Projects track larger bodies of work. Use the project page to manage the project record, then open a project to post updates, maintain a lightweight kanban board, or add blog-style progress notes.",
            "how_to_use": [
                "Create a project first, then use View Progress to maintain its timeline.",
                "Use Open Board when you want to track concrete tickets from backlog to shipped.",
                "Use project type for broad grouping only. The timeline carries the detailed story.",
                "Add focus tags when project work should count toward promises or skills, for example python, writing, or deep-work.",
                "Post short updates for milestones and choose Blog when an update deserves a fuller write-up.",
            ],
            "glossary": [
                {"term": "Project Type", "meaning": "A simple category such as Code, DIY, or Other."},
                {"term": "Focus Tags", "meaning": "Shared tags Rasbhari adds to project work events so tickets, promises, skills, and Today can line up around the same work."},
                {"term": "State",
                 "meaning": "The current lifecycle status of the project, such as Active or Completed."},
                {"term": "Progress Count", "meaning": "How many timeline updates have been logged for the project."},
                {"term": "Board", "meaning": "A simple project kanban view for tickets moving from backlog to shipped."},
            ],
        },
        "KanbanTickets": {
            "overview": "Kanban tickets are minimal project work items. Each ticket belongs to one project and moves through a fixed board from backlog to shipped.",
            "how_to_use": [
                "Keep tickets short and concrete so the board stays fast to scan.",
                "Use the board for day-to-day execution and the project timeline for narrative updates.",
                "Move tickets forward as work advances. Rasbhari emits events when tickets are created or moved.",
                "Project focus tags are automatically added to ticket workflow events so project work can contribute to promises and skills.",
                "Archive shipped or stale tickets when you want them out of the active board without deleting their history.",
            ],
            "glossary": [
                {"term": "Backlog", "meaning": "Work that exists but is not yet selected."},
                {"term": "Prioritized", "meaning": "Work chosen as likely next."},
                {"term": "In Progress", "meaning": "Work currently being executed."},
                {"term": "Completed", "meaning": "Work finished but not yet shipped or deployed."},
                {"term": "Shipped", "meaning": "Work delivered, released, or deployed."},
                {"term": "Archived", "meaning": "A ticket hidden from the project board but still kept in the system and global ticket list."},
            ],
        },
        "Promises": {
            "overview": "Promises track commitments over time. They watch events and decide whether a recurring promise is currently on track, fulfilled, or broken.",
            "how_to_use": [
                "Use either a target event type, a target tag, or both to describe what counts toward the promise.",
                "Set required count to the number of matching events needed in each period.",
                "Use refresh when you want the UI to recount recent matching events immediately.",
            ],
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
            "how_to_use": [
                "Create one skill per thing you want to intentionally improve.",
                "Pick a stable tag key because that is what incoming event tags are matched against first.",
                "Add aliases when people or systems might log the same skill under different names.",
            ],
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
            "overview": "Reports turn raw activity into a behavioral mirror. They compare projects, events, skills, and thoughts to surface integrity gaps instead of only listing what happened.",
            "how_to_use": [
                "Generate daily, weekly, or monthly mirrors from the Reports page.",
                "Use the asynchronous option when you want generation to happen through the event pipeline and background processor.",
                "Use the print view when you want a clean local page that can be saved as PDF without uploading data anywhere.",
                "Add Connections and log interactions inside their ledger if you want the report to score social balance and neglected relationships.",
            ],
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
            "overview": "Thoughts are quick captures for ideas, reflections, or reminders. They are lighter than blog posts and faster than creating a full project or event entry.",
            "how_to_use": [
                "Use thoughts for short captures you do not want to lose.",
                "Prefer blogs when you need formatting and longer writing.",
                "Prefer events when the main goal is to record that something happened rather than what you are thinking about it.",
            ],
            "glossary": [
                {"term": "Thought", "meaning": "A quick note captured with minimal structure."},
            ],
        },
        "Users": {
            "overview": "Users manage who can sign into this Rasbhari instance. Each person gets their own private workspace, while admin access only unlocks system panels.",
            "how_to_use": [
                "Create one account per family member or operator who should use this Rasbhari installation.",
                "Only mark trusted operator accounts as admin. Admins can manage the system but do not automatically see other users' personal records.",
                "Set a password when creating a user. Enter a new password later only when you want to rotate or reset it.",
            ],
            "glossary": [
                {"term": "Admin",
                 "meaning": "An operator who can access system panels like Processes, Devices, and dependency health."},
                {"term": "Personal Workspace",
                 "meaning": "The private set of app records owned by a specific user account."},
                {"term": "Active", "meaning": "Whether the account is allowed to sign in."},
            ],
        },
        "NetworkSignatures": {
            "overview": "The Network Signatures app allows Rasbhari to monitor your local network for specific devices. When a device (like your phone) is detected, Rasbhari can automatically log an event in your timeline.",
            "how_to_use": [
                "To start tracking, add a new signature with your device's MAC address.",
                "You can find this in your phone's Wi-Fi settings.",
                "Once saved, the Network Sniffer process will scan for your device every 30 seconds.",
            ],
            "glossary": [
                {"term": "Name",
                 "meaning": "A friendly name for this signature (e.g., 'My iPhone')."},
                {"term": "MAC Address",
                 "meaning": "The unique hardware address of your device (e.g., 00:11:22:33:44:55)."},
                {"term": "Event Type",
                 "meaning": "The type of event to log when the device is detected (e.g., 'presence' or 'habit')."},
                {"term": "Tags",
                 "meaning": "Comma-separated tags to add to the generated event."},
                {"term": "Is Active",
                 "meaning": "Whether this signature should currently be monitored."}
            ]
        }
    }
    return docs.get(app_name, {})
