from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from services.kanban_tickets import KanbanTicketService
from services.projects import ProjectService
from services.promises import PromiseService
from services.skills import SkillService
from services.activities import ActivityService


class RecommendationFollowUpService:
    def __init__(
        self,
        project_service: Optional[ProjectService] = None,
        kanban_ticket_service: Optional[KanbanTicketService] = None,
        promise_service: Optional[PromiseService] = None,
        skill_service: Optional[SkillService] = None,
        activity_service: Optional[ActivityService] = None,
    ):
        self.project_service = project_service or ProjectService()
        self.kanban_ticket_service = kanban_ticket_service or KanbanTicketService()
        self.promise_service = promise_service or PromiseService()
        self.skill_service = skill_service or SkillService()
        self.activity_service = activity_service or ActivityService()

    def get_follow_ups(self, user_id: int, limit: int = 4) -> list[dict]:
        projects = self.project_service.find_all(filters={"user_id": user_id, "state": "Active"}, sort_by={"last_updated": "ASC"})
        promises = self.promise_service.find_all(filters={"user_id": user_id}, sort_by={"name": "ASC"})
        skills = self.skill_service.find_all(filters={"user_id": user_id}, sort_by={"name": "ASC"})
        activities = self.activity_service.find_all(filters={"user_id": user_id}, sort_by={"name": "ASC"})

        promise_tags = {str(p.target_event_tag).strip().lower() for p in promises if p.target_event_tag}
        promise_tags_by_event_type = {}
        for promise in promises:
            if promise.target_event_type and promise.target_event_tag:
                promise_tags_by_event_type.setdefault(str(promise.target_event_type).strip().lower(), set()).add(str(promise.target_event_tag).strip().lower())
        skill_tags = set()
        for skill in skills:
            skill_tags.update(self.skill_service.get_match_keys(skill))

        follow_ups = []
        follow_ups.extend(self._build_promise_link_follow_ups(promises, activities))
        follow_ups.extend(self._build_activity_link_follow_ups(activities, promise_tags, skill_tags))

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

    def _build_promise_link_follow_ups(self, promises, activities) -> list[dict]:
        follow_ups = []
        activities_by_event_type = {}
        for activity in activities:
            event_type = str(activity.event_type or "").strip().lower()
            if not event_type:
                continue
            activities_by_event_type.setdefault(event_type, []).append(activity)

        for promise in promises:
            if promise.target_event_tag or not promise.target_event_type:
                continue
            matching_activities = activities_by_event_type.get(str(promise.target_event_type).strip().lower(), [])
            candidate_tags = []
            for activity in matching_activities:
                for tag in (activity.tags or []):
                    normalized = str(tag).strip().lower()
                    if normalized and normalized not in candidate_tags:
                        candidate_tags.append(normalized)
            if not candidate_tags:
                continue
            chosen_tag = candidate_tags[0]
            follow_ups.append({
                "id": f"promise-link:{promise.id}:{chosen_tag}",
                "title": f"Link promise {promise.name} to `{chosen_tag}`",
                "body": f"Activities already emit `{promise.target_event_type}` with the `{chosen_tag}` tag. Add that tag to the promise so the relationship stays visible across Rasbhari.",
                "action": "update_promise_target_tag",
                "confidence": 0.78,
                "reasoning": "The promise already watches this event type, and matching activities consistently carry the suggested tag.",
                "payload": {
                    "promise_id": promise.id,
                    "promise_name": promise.name,
                    "promise_target_event_type": promise.target_event_type,
                    "promise_target_event_tag": chosen_tag,
                },
            })
        return follow_ups

    def _build_activity_link_follow_ups(self, activities, promise_tags: set[str], skill_tags: set[str]) -> list[dict]:
        follow_ups = []
        candidate_tags = sorted({tag for tag in [*promise_tags, *skill_tags] if tag})
        for activity in activities:
            existing_tags = {str(tag).strip().lower() for tag in (activity.tags or []) if str(tag).strip()}
            tokens = self._extract_match_tokens(activity)
            matching_tag = next((tag for tag in candidate_tags if tag not in existing_tags and tag in tokens), None)
            if not matching_tag:
                continue
            follow_ups.append({
                "id": f"activity-link:{activity.id}:{matching_tag}",
                "title": f"Add `{matching_tag}` to {activity.name}",
                "body": f"{activity.name} already reads like `{matching_tag}` work, but the activity is not tagged that way yet. Add the tag so promises and skills can react consistently.",
                "action": "append_activity_tags",
                "confidence": 0.76,
                "reasoning": "The activity name or event type already matches an existing promise or skill tag.",
                "payload": {
                    "activity_id": activity.id,
                    "activity_name": activity.name,
                    "activity_tag_updates": [matching_tag],
                },
            })
        return follow_ups

    @staticmethod
    def _extract_match_tokens(activity) -> set[str]:
        raw_parts = [activity.name or "", activity.event_type or ""]
        tokens = set()
        for part in raw_parts:
            normalized = str(part).strip().lower().replace(":", " ").replace("-", " ").replace("_", " ")
            tokens.update(token for token in normalized.split() if token)
        return tokens
