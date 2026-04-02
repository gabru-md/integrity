from flask import request, jsonify
from apps.user_docs import build_app_user_guidance
from gabru.auth import write_access_required
from gabru.flask.app import App
from model.kanban_ticket import KanbanTicketState
from model.project import Project
from model.timeline import TimelineItem
from services.projects import ProjectService
from services.kanban_tickets import KanbanTicketService
from services.timeline import TimelineService
from services.events import EventService
from services.promises import PromiseService
from services.skills import SkillService
from model.event import Event
from processes.project_updater import ProjectUpdater
from datetime import datetime
from gabru.flask.util import render_flask_template

event_service = EventService()
kanban_ticket_service = KanbanTicketService()
promise_service = PromiseService()
skill_service = SkillService()

project_app = App(
    'Projects',
    service=ProjectService(),
    model_class=Project,
    widget_enabled=True,
    get_recent_limit=10,
    home_template="project_crud.html",
    widget_type="kanban",
    widget_recent_limit=4,
    user_guidance=build_app_user_guidance("Projects")
)

project_app.register_process(ProjectUpdater, enabled=True)

timeline_service = TimelineService()


def _build_project_shared_tags(project) -> list[str]:
    tags = []
    if getattr(project, "name", None):
        tags.append(project.name.strip().lower().replace(" ", "-"))
    tags.extend(str(tag).strip().lower() for tag in (getattr(project, "focus_tags", None) or []) if str(tag).strip())
    deduped = []
    for tag in tags:
        if tag not in deduped:
            deduped.append(tag)
    return deduped


def _build_promise_index() -> list[dict]:
    promises = promise_service.find_all(sort_by={"name": "ASC"})
    indexed = []
    for promise in promises:
        match_values = []
        if promise.target_event_tag:
            match_values.append(str(promise.target_event_tag).strip().lower())
        if promise.target_event_type and promise.target_event_type.startswith("project:"):
            match_values.append(promise.target_event_type.split(":", 1)[1].strip().lower())
        if match_values:
            indexed.append({
                "id": promise.id,
                "name": promise.name,
                "href": "/promises/home",
                "match_values": set(match_values),
            })
    return indexed


def _build_skill_index() -> list[dict]:
    skills = skill_service.find_all(sort_by={"name": "ASC"})
    return [
        {
            "id": skill.id,
            "name": skill.name,
            "href": "/skills/home",
            "match_values": skill_service.get_match_keys(skill),
        }
        for skill in skills
    ]


def _match_promises_for_tags(tags: list[str], promise_index: list[dict]) -> list[dict]:
    tag_set = set(tags)
    return [
        {"id": item["id"], "name": item["name"], "href": item["href"]}
        for item in promise_index
        if item["match_values"].intersection(tag_set)
    ][:3]


def _match_skills_for_tags(tags: list[str], skill_index: list[dict]) -> list[dict]:
    normalized_tags = {"".join(char for char in tag if char.isalnum()) for tag in tags if tag}
    return [
        {"id": item["id"], "name": item["name"], "href": item["href"]}
        for item in skill_index
        if item["match_values"].intersection(normalized_tags)
    ][:3]


def _build_contribution_summary(linked_promises: list[dict], linked_skills: list[dict]) -> str:
    parts = []
    if linked_promises:
        parts.append(f"{len(linked_promises)} promise{'s' if len(linked_promises) != 1 else ''}")
    if linked_skills:
        parts.append(f"{len(linked_skills)} skill{'s' if len(linked_skills) != 1 else ''}")
    if not parts:
        return ""
    return "Supports " + " and ".join(parts)


def _serialize_board_tickets(project, tickets) -> list[dict]:
    shared_tags = _build_project_shared_tags(project)
    promise_index = _build_promise_index()
    skill_index = _build_skill_index()
    serialized = []
    for ticket in tickets:
        linked_promises = _match_promises_for_tags(shared_tags, promise_index)
        linked_skills = _match_skills_for_tags(shared_tags, skill_index)
        ticket_data = ticket.dict()
        ticket_data["focus_tags"] = shared_tags
        ticket_data["linked_promises"] = linked_promises
        ticket_data["linked_skills"] = linked_skills
        ticket_data["contribution_summary"] = _build_contribution_summary(linked_promises, linked_skills)
        serialized.append(ticket_data)
    return serialized

@project_app.blueprint.route('/<int:project_id>/view', methods=['GET'])
def view_project(project_id):
    project = project_app.service.get_by_id(project_id)
    if not project:
        return "Project not found", 404
    return render_flask_template('project_details.html', project=project)


@project_app.blueprint.route('/<int:project_id>/board', methods=['GET'])
def view_project_board(project_id):
    project = project_app.service.get_by_id(project_id)
    if not project:
        return "Project not found", 404
    tickets = kanban_ticket_service.get_by_project_id(project_id, include_archived=False)
    archived_tickets = kanban_ticket_service.get_by_project_id(project_id, include_archived=True)
    archived_count = sum(1 for ticket in archived_tickets if ticket.is_archived)
    all_tickets = _serialize_board_tickets(project, archived_tickets)
    last_updated = None
    if all_tickets:
        latest_ticket = max(
            all_tickets,
            key=lambda ticket: ticket.get("updated_at") or ticket.get("state_changed_at") or ticket.get("created_at") or "",
        )
        last_updated = latest_ticket.get("updated_at") or latest_ticket.get("state_changed_at") or latest_ticket.get("created_at")
    project_tag = f"project:{project.name.lower().replace(' ', '-')}"
    recent_activity = []
    try:
        events = event_service.find_all(
            filters={"event_type": {"$in": [
                "kanban:ticket_created",
                "kanban:ticket_moved",
                "kanban:ticket_updated",
                "kanban:ticket_archived",
            ]}},
            sort_by={"timestamp": "DESC"},
        )
        for event in events:
            tags = event.tags or []
            if project_tag in tags:
                recent_activity.append(event.dict())
            if len(recent_activity) >= 5:
                break
    except Exception:
        recent_activity = []
    return render_flask_template(
        'project_board.html',
        project=project,
        initial_tickets=[ticket for ticket in all_tickets if not ticket.get("is_archived")],
        board_states=KanbanTicketService.STATE_ORDER,
        ticket_state_labels={state.value: state.value.replace("_", " ").title() for state in KanbanTicketState},
        app_name="KanbanTickets",
        user_guidance=build_app_user_guidance("KanbanTickets"),
        board_last_updated=last_updated,
        archived_count=archived_count,
        recent_activity=recent_activity,
    )


@project_app.blueprint.route('/<int:project_id>/board-data', methods=['GET'])
def get_project_board_data(project_id):
    project = project_app.service.get_by_id(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    tickets = kanban_ticket_service.get_by_project_id(project_id, include_archived=False)
    return jsonify(_serialize_board_tickets(project, tickets)), 200

@project_app.blueprint.route('/<int:project_id>/timeline', methods=['GET'])
def get_timeline(project_id):
    items = timeline_service.get_by_project_id(project_id)
    return jsonify([item.dict() for item in items])

@project_app.blueprint.route('/<int:project_id>/timeline', methods=['POST'])
@write_access_required
def add_timeline_item(project_id):
    data = request.json
    try:
        project = project_app.service.get_by_id(project_id)
        if not project:
            return jsonify({"error": "Project not found"}), 404

        # Validate and create
        item = TimelineItem(
            user_id=project.user_id,
            project_id=project_id,
            content=data.get('content'),
            item_type=data.get('item_type', 'Update')
        )
        timeline_service.create(item)
        
        # Update project's last_updated time and progress count
        project.last_updated = datetime.now()
        if item.item_type == 'Update':
            project.progress_count += 1
        project_app.service.update(project)

        # Create a progress event
        project_name_dashed = project.name.lower().replace(" ", "-")
        event_type = f"project:{project_name_dashed}"
        new_event = Event(
            user_id=project.user_id,
            event_type=event_type,
            timestamp=datetime.now(),
            description=f"Timeline update for project: {project.name}",
            tags=[
                "progress",
                f"project:{project_name_dashed}",
                f"project_work:{project_name_dashed}",
                *(project.focus_tags or []),
            ]
        )
        event_service.create(new_event)
            
        return jsonify({"message": "Timeline item added"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400
