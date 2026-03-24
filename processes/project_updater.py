from __future__ import annotations

from datetime import datetime
from gabru.qprocessor.qprocessor import QueueProcessor
from model.event import Event
from model.project import Project, ProjectState
from services.projects import ProjectService
from services.events import EventService


class ProjectUpdater(QueueProcessor[Event]):
    """
    Background process to update projects based on system events.
    Listens for:
    - Event Type: 'project:<project-name-dashed>' with Tag: 'progress' -> increments progress_count
    - Tags: 'project:state:<new_state>:<project-name-dashed>' -> changes project state
    """

    def __init__(self, **kwargs):
        self.event_service = EventService()
        self.project_service = ProjectService()
        super().__init__(name="ProjectUpdater", service=self.event_service, **kwargs)

    def filter_item(self, event: Event) -> Event | None:
        # We only care about project events or state change tags
        if event.event_type.startswith("project:"):
            return event
        if any(tag.startswith("project:state:") or tag.startswith("progress:update:") for tag in event.tags):
            return event
        return None

    def _process_item(self, event: Event) -> bool:
        try:
            # 1. Try to get project name from event_type or tags
            project_name_dashed = self._get_project_name(event)
            if not project_name_dashed:
                return True # Not for us

            # 2. Find the project
            # We need to find by dashed name or exact name. 
            # Our ProjectService has get_by_name, but it might not be dashed in DB.
            # We'll try to match it.
            project = self._find_project(project_name_dashed)
            if not project:
                self.log.warning(f"Project '{project_name_dashed}' not found for event {event.id}")
                return True

            # 3. Handle Progress
            if "progress" in event.tags or any(tag.startswith("progress:update:") for tag in event.tags):
                self._handle_progress_update(project)
            
            # 4. Handle State Change
            state_tag = next((tag for tag in event.tags if tag.startswith("project:state:")), None)
            if state_tag:
                self._handle_state_change(state_tag, project)

            return True
        except Exception as e:
            self.log.exception(e)
            return False

    def _find_project(self, dashed_name: str) -> Project | None:
        all_projects = self.project_service.get_all()
        for p in all_projects:
            if p.name.lower().replace(" ", "-") == dashed_name.lower():
                return p
        return None

    def _get_project_name(self, event: Event) -> str | None:
        """Extracts the project name from event_type or tags."""
        # Check event_type first: project:my-cool-project
        if event.event_type.startswith("project:"):
            parts = event.event_type.split(':')
            if len(parts) >= 2:
                # Could be project:name or project:name:created
                return parts[1]

        # Fallback to tags (Legacy/Alternative)
        for tag in event.tags:
            parts = tag.split(':')
            if parts[0] in ['progress', 'project'] and len(parts) >= 2:
                return parts[-1]
        
        return None

    def _handle_state_change(self, state_tag: str, project: Project):
        try:
            # project:state:completed:my-project
            parts = state_tag.split(":")
            if len(parts) >= 3:
                new_state_str = parts[2]
                # Map string to Enum
                for state in ProjectState:
                    if state.value.lower().replace(" ", "") == new_state_str.lower().replace("_", ""):
                        project.state = state
                        break
                
                project.last_updated = datetime.now()
                self.project_service.update(project)
                self.log.info(f"Changed state of project '{project.name}' to '{project.state.value}'.")
        except Exception as e:
            self.log.warning(f"Failed to handle state change for {project.name}: {e}")

    def _handle_progress_update(self, project: Project):
        project.last_updated = datetime.now()
        project.progress_count += 1
        self.project_service.update(project)
        self.log.info(f"Logged progress for project '{project.name}'. New count: {project.progress_count}.")
