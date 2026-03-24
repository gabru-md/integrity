from __future__ import annotations

from datetime import datetime
from gabru.process import Process
from model.event import Event
from model.project import Project, ProjectState
from services.projects import ProjectService


class ProjectUpdater(Process):
    """
    Background process to update projects based on system events.
    Listens for:
    - 'progress:update:{project_name}' to log progress.
    - 'project:state:{new_state}:{project_name}' to change a project's state.
    """

    def __init__(self, **kwargs):
        super().__init__(daemon=True, **kwargs)
        self.project_service = ProjectService()

    def handle(self, event: Event):
        project_name = self._get_project_name_from_tags(event.tags)
        if not project_name:
            return

        project = self.project_service.get_by_name(project_name)
        if not project:
            self.logger.error(f"Could not find a project with name '{project_name}'.")
            return

        # Handle state change events like 'project:state:completed:my-app'
        if any(tag.startswith("project:state:") for tag in event.tags):
            self._handle_state_change(event, project)
        # Handle progress update events like 'progress:update:my-app'
        elif any(tag.startswith("progress:update:") for tag in event.tags):
            self._handle_progress_update(project)

    def _handle_state_change(self, event: Event, project: Project):
        try:
            state_tag = next(tag for tag in event.tags if tag.startswith("project:state:"))
            new_state_str = state_tag.split(":")[2]
            new_state = ProjectState(new_state_str.replace("_", " ").title())

            project.state = new_state
            project.last_updated = datetime.now()
            self.project_service.update(project.id, project)
            self.logger.info(f"Changed state of project '{project.name}' to '{new_state.value}'.")
        except (StopIteration, IndexError):
            self.logger.warning(f"Malformed state change tag in event: {event.tags}")
        except ValueError:
            self.logger.warning(f"Invalid state '{new_state_str}' found in event tags.")

    def _handle_progress_update(self, project: Project):
        project.last_updated = datetime.now()
        project.progress_count += 1
        self.project_service.update(project.id, project)
        self.logger.info(f"Logged progress for project '{project.name}'. New count: {project.progress_count}.")

    def _get_project_name_from_tags(self, tags: list) -> str | None:
        """Extracts the project name from the event tags."""
        for tag in tags:
            parts = tag.split(':')
            if parts[0] in ['progress', 'project'] and len(parts) > 2:
                return parts[-1]  # Assumes project name is always the last part
        self.logger.debug(f"No project name found in tags: {tags}")
        return None

