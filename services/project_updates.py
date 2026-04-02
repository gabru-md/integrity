from __future__ import annotations

from datetime import datetime
from typing import Optional

from model.event import Event
from model.timeline import TimelineItem
from services.events import EventService
from services.projects import ProjectService
from services.timeline import TimelineService


class ProjectUpdateService:
    def __init__(
        self,
        project_service: Optional[ProjectService] = None,
        timeline_service: Optional[TimelineService] = None,
        event_service: Optional[EventService] = None,
    ):
        self.project_service = project_service or ProjectService()
        self.timeline_service = timeline_service or TimelineService()
        self.event_service = event_service or EventService()

    def create_update(
        self,
        *,
        user_id: int,
        project_id: int,
        content: str,
        item_type: str = "Update",
    ) -> Optional[int]:
        project = self.project_service.get_by_id(project_id)
        if not project or project.user_id != user_id:
            return None

        timestamp = datetime.now()
        timeline_item = TimelineItem(
            user_id=user_id,
            project_id=project_id,
            content=content,
            timestamp=timestamp,
            item_type=item_type,
        )
        timeline_id = self.timeline_service.create(timeline_item)
        if not timeline_id:
            return None

        project.last_updated = timestamp
        if item_type == "Update":
            project.progress_count += 1
        self.project_service.update(project)

        project_slug = project.name.lower().replace(" ", "-")
        event = Event(
            user_id=user_id,
            event_type=f"project:{project_slug}",
            timestamp=timestamp,
            description=f"Timeline update for project: {project.name}",
            tags=[
                "progress",
                f"project:{project_slug}",
                f"project_work:{project_slug}",
                *(project.focus_tags or []),
            ],
        )
        self.event_service.create(event)
        return timeline_id
