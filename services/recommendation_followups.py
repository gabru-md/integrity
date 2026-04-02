from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from services.kanban_tickets import KanbanTicketService
from services.projects import ProjectService
from services.promises import PromiseService
from services.skills import SkillService


class RecommendationFollowUpService:
    def __init__(
        self,
        project_service: Optional[ProjectService] = None,
        kanban_ticket_service: Optional[KanbanTicketService] = None,
        promise_service: Optional[PromiseService] = None,
        skill_service: Optional[SkillService] = None,
    ):
        self.project_service = project_service or ProjectService()
        self.kanban_ticket_service = kanban_ticket_service or KanbanTicketService()
        self.promise_service = promise_service or PromiseService()
        self.skill_service = skill_service or SkillService()

    def get_follow_ups(self, user_id: int, limit: int = 4) -> list[dict]:
        projects = self.project_service.find_all(filters={"user_id": user_id, "state": "Active"}, sort_by={"last_updated": "ASC"})
        promises = self.promise_service.find_all(filters={"user_id": user_id}, sort_by={"name": "ASC"})
        skills = self.skill_service.find_all(filters={"user_id": user_id}, sort_by={"name": "ASC"})

        promise_tags = {str(p.target_event_tag).strip().lower() for p in promises if p.target_event_tag}
        skill_tags = set()
        for skill in skills:
            skill_tags.update(self.skill_service.get_match_keys(skill))

        follow_ups = []
        now = datetime.now()
        for project in projects:
            project_slug = project.name.lower().replace(" ", "-")
            focus_tags = [str(tag).strip().lower() for tag in (project.focus_tags or []) if str(tag).strip()]
            tickets = self.kanban_ticket_service.get_by_project_id(project.id, include_archived=False)
            open_tickets = [ticket for ticket in tickets if getattr(ticket, "state", None) != "shipped"]

            for focus_tag in focus_tags:
                normalized_skill_tag = self.skill_service.normalize_skill_tag(focus_tag)
                if normalized_skill_tag and normalized_skill_tag not in skill_tags:
                    follow_ups.append({
                        "id": f"skill:{project.id}:{focus_tag}",
                        "title": f"Create skill for {focus_tag}",
                        "body": f"Project work on {project.name} already emits `{focus_tag}`. Turn it into a tracked skill so progress becomes visible.",
                        "action": "create_skill",
                        "confidence": 0.82,
                        "reasoning": "This project already has a stable focus tag but no matching skill.",
                        "payload": {
                            "skill_name": focus_tag.replace("-", " ").title(),
                            "skill_tag_key": normalized_skill_tag,
                            "skill_aliases": [focus_tag] if focus_tag != normalized_skill_tag else [],
                        },
                    })
                    break

            for focus_tag in focus_tags:
                if focus_tag not in promise_tags:
                    follow_ups.append({
                        "id": f"promise:{project.id}:{focus_tag}",
                        "title": f"Protect {focus_tag} with a promise",
                        "body": f"Work on {project.name} uses `{focus_tag}`, but no promise currently watches that tag.",
                        "action": "create_promise",
                        "confidence": 0.74,
                        "reasoning": "The work signal exists, but there is no explicit commitment tied to it yet.",
                        "payload": {
                            "promise_name": f"Keep {focus_tag.replace('-', ' ')} moving",
                            "promise_description": f"Create regular evidence for {focus_tag} work through project activity.",
                            "promise_frequency": "daily",
                            "promise_target_event_tag": focus_tag,
                            "promise_required_count": 1,
                        },
                    })
                    break

            if not open_tickets:
                follow_ups.append({
                    "id": f"ticket:{project.id}",
                    "title": f"Create the next ticket for {project.name}",
                    "body": f"{project.name} has no active board work. Add one concrete ticket so the project can move visibly.",
                    "action": "create_ticket",
                    "confidence": 0.69,
                    "reasoning": "The project is active but the board has no open tickets.",
                    "payload": {
                        "ticket_project_id": project.id,
                        "ticket_title": f"Define next step for {project.name}",
                        "ticket_description": f"Add the next concrete unit of work for {project.name}.",
                        "ticket_state": "backlog",
                    },
                })

            stale_cutoff = now - timedelta(days=7)
            if project.last_updated is None or project.last_updated < stale_cutoff:
                follow_ups.append({
                    "id": f"update:{project.id}",
                    "title": f"Post a project update for {project.name}",
                    "body": f"{project.name} has not had a recent visible update. Add a short progress note so the timeline reflects reality.",
                    "action": "create_project_update",
                    "confidence": 0.71,
                    "reasoning": "The project looks stale from its last updated timestamp.",
                    "payload": {
                        "project_id": project.id,
                        "project_update_content": f"Progress update for {project.name}: captured the next visible step and current state.",
                        "project_update_type": "Update",
                    },
                })

            if len(follow_ups) >= limit:
                break

        deduped = []
        seen_ids = set()
        for item in follow_ups:
            if item["id"] in seen_ids:
                continue
            seen_ids.add(item["id"])
            deduped.append(item)
            if len(deduped) >= limit:
                break
        return deduped
