from flask import request, jsonify, render_template
from gabru.flask.app import App
from model.project import Project
from model.timeline import TimelineItem
from services.projects import ProjectService
from services.timeline import TimelineService
from processes.project_updater import ProjectUpdater
from datetime import datetime

timeline_service = TimelineService()

project_app = App(
    'Projects',
    service=ProjectService(),
    model_class=Project,
    widget_enabled=True,
    get_recent_limit=10,
    home_template="project_crud.html"
)

project_app.register_process(ProjectUpdater, enabled=True)

@project_app.blueprint.route('/<int:project_id>/view', methods=['GET'])
def view_project(project_id):
    project = project_app.service.get_by_id(project_id)
    if not project:
        return "Project not found", 404
    return render_template('project_details.html', project=project)

@project_app.blueprint.route('/<int:project_id>/timeline', methods=['GET'])
def get_timeline(project_id):
    items = timeline_service.get_by_project_id(project_id)
    return jsonify([item.dict() for item in items])

@project_app.blueprint.route('/<int:project_id>/timeline', methods=['POST'])
def add_timeline_item(project_id):
    data = request.json
    try:
        # Validate and create
        item = TimelineItem(
            project_id=project_id,
            content=data.get('content'),
            item_type=data.get('item_type', 'Update')
        )
        timeline_service.create(item)
        
        # Update project's last_updated time and progress count
        project = project_app.service.get_by_id(project_id)
        if project:
            project.last_updated = datetime.now()
            if item.item_type == 'Update':
                project.progress_count += 1
            project_app.service.update(project)
            
        return jsonify({"message": "Timeline item added"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400
