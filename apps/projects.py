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
from model.event import Event
from processes.project_updater import ProjectUpdater
from datetime import datetime
from gabru.flask.util import render_flask_template

timeline_service = TimelineService()
event_service = EventService()
kanban_ticket_service = KanbanTicketService()

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
    tickets = kanban_ticket_service.get_by_project_id(project_id)
    return render_flask_template(
        'project_board.html',
        project=project,
        initial_tickets=[ticket.dict() for ticket in tickets],
        board_states=KanbanTicketService.STATE_ORDER,
        ticket_state_labels={state.value: state.value.replace("_", " ").title() for state in KanbanTicketState},
    )

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
            tags=["progress"]
        )
        event_service.create(new_event)
            
        return jsonify({"message": "Timeline item added"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400
