from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Iterable, Optional

from model.recommendation import Recommendation
from services.activities import ActivityService
from services.kanban_tickets import KanbanTicketService
from services.projects import ProjectService
from services.promises import PromiseService
from services.skills import SkillService


RecommendationDetector = Callable[[int], Iterable[Recommendation]]


class RecommendationEngineService:
    def __init__(
        self,
        project_service: Optional[ProjectService] = None,
        kanban_ticket_service: Optional[KanbanTicketService] = None,
        promise_service: Optional[PromiseService] = None,
        skill_service: Optional[SkillService] = None,
        activity_service: Optional[ActivityService] = None,
        detectors: Optional[list[RecommendationDetector]] = None,
    ):
        self.project_service = project_service or ProjectService()
        self.kanban_ticket_service = kanban_ticket_service or KanbanTicketService()
        self.promise_service = promise_service or PromiseService()
        self.skill_service = skill_service or SkillService()
        self.activity_service = activity_service or ActivityService()
        self.detectors = detectors or [
            self._detect_promise_tag_links,
            self._detect_activity_tag_links,
            self._detect_skill_signal_links,
            self._detect_missing_project_skills,
            self._detect_missing_project_promises,
            self._detect_projects_without_open_tickets,
            self._detect_stale_projects,
        ]

    def get_recommendations(
        self,
        user_id: int,
        *,
        app_name: Optional[str] = None,
        scope_id: Optional[int] = None,
        limit: int = 8,
    ) -> list[Recommendation]:
        recommendations: list[Recommendation] = []
        for detector in self.detectors:
            recommendations.extend(detector(user_id))

        deduped: list[Recommendation] = []
        seen_ids: set[str] = set()
        for item in sorted(recommendations, key=lambda rec: (-rec.priority, -rec.confidence, rec.title)):
            if app_name and item.app_name != app_name:
                continue
            if scope_id is not None and item.scope_id != scope_id:
                continue
            if item.id in seen_ids:
                continue
            seen_ids.add(item.id)
            deduped.append(item)
            if len(deduped) >= limit:
                break
        return deduped

    def _detect_promise_tag_links(self, user_id: int) -> Iterable[Recommendation]:
        promises = self.promise_service.find_all(filters={"user_id": user_id}, sort_by={"name": "ASC"})
        activities = self.activity_service.find_all(filters={"user_id": user_id}, sort_by={"name": "ASC"})
        activities_by_event_type: dict[str, list] = {}
        for activity in activities:
            event_type = str(activity.event_type or "").strip().lower()
            if event_type:
                activities_by_event_type.setdefault(event_type, []).append(activity)

        output: list[Recommendation] = []
        for promise in promises:
            if promise.target_event_tag or not promise.target_event_type:
                continue
            matching_activities = activities_by_event_type.get(str(promise.target_event_type).strip().lower(), [])
            candidate_tags: list[str] = []
            for activity in matching_activities:
                for tag in (activity.tags or []):
                    normalized = str(tag).strip().lower()
                    if normalized and normalized not in candidate_tags:
                        candidate_tags.append(normalized)
            if not candidate_tags:
                continue
            chosen_tag = candidate_tags[0]
            output.append(
                Recommendation(
                    id=f"promise-link:{promise.id}:{chosen_tag}",
                    app_name="Promises",
                    scope="item",
                    scope_id=promise.id,
                    priority=88,
                    confidence=0.78,
                    title=f"Link promise {promise.name} to `{chosen_tag}`",
                    body=f"Activities already emit `{promise.target_event_type}` with the `{chosen_tag}` tag. Add that tag so the relationship stays visible across Rasbhari.",
                    reasoning="The promise already watches this event type, and matching activities consistently carry the suggested tag.",
                    kind="stage_action",
                    action="update_promise_target_tag",
                    action_label="Link Tag",
                    payload={
                        "promise_id": promise.id,
                        "promise_name": promise.name,
                        "promise_target_event_type": promise.target_event_type,
                        "promise_target_event_tag": chosen_tag,
                    },
                    tags=["promises", "linking", chosen_tag],
                )
            )
        return output

    def _detect_activity_tag_links(self, user_id: int) -> Iterable[Recommendation]:
        promises = self.promise_service.find_all(filters={"user_id": user_id}, sort_by={"name": "ASC"})
        skills = self.skill_service.find_all(filters={"user_id": user_id}, sort_by={"name": "ASC"})
        activities = self.activity_service.find_all(filters={"user_id": user_id}, sort_by={"name": "ASC"})

        promise_tags = {str(p.target_event_tag).strip().lower() for p in promises if p.target_event_tag}
        skill_tags = set()
        for skill in skills:
            skill_tags.update(self.skill_service.get_match_keys(skill))
        candidate_tags = sorted({tag for tag in [*promise_tags, *skill_tags] if tag})

        output: list[Recommendation] = []
        for activity in activities:
            existing_tags = {str(tag).strip().lower() for tag in (activity.tags or []) if str(tag).strip()}
            tokens = self._extract_match_tokens(activity.name or "", activity.event_type or "")
            matching_tag = next((tag for tag in candidate_tags if tag not in existing_tags and tag in tokens), None)
            if not matching_tag:
                continue
            output.append(
                Recommendation(
                    id=f"activity-link:{activity.id}:{matching_tag}",
                    app_name="Activities",
                    scope="item",
                    scope_id=activity.id,
                    priority=84,
                    confidence=0.76,
                    title=f"Add `{matching_tag}` to {activity.name}",
                    body=f"{activity.name} already reads like `{matching_tag}` work, but the activity is not tagged that way yet. Add the tag so promises and skills can react consistently.",
                    reasoning="The activity name or event type already matches an existing promise or skill tag.",
                    kind="stage_action",
                    action="append_activity_tags",
                    action_label="Add Tag",
                    payload={
                        "activity_id": activity.id,
                        "activity_name": activity.name,
                        "activity_tag_updates": [matching_tag],
                    },
                    tags=["activities", "linking", matching_tag],
                )
            )
        return output

    def _detect_skill_signal_links(self, user_id: int) -> Iterable[Recommendation]:
        skills = self.skill_service.find_all(filters={"user_id": user_id}, sort_by={"name": "ASC"})
        activities = self.activity_service.find_all(filters={"user_id": user_id}, sort_by={"name": "ASC"})
        projects = self.project_service.find_all(filters={"user_id": user_id, "state": "Active"}, sort_by={"last_updated": "DESC"})

        output: list[Recommendation] = []
        for skill in skills:
            match_keys = self.skill_service.get_match_keys(skill)
            if not match_keys:
                continue

            matching_activities = []
            for activity in activities:
                activity_keys = {
                    self.skill_service.normalize_skill_tag(str(tag))
                    for tag in (activity.tags or [])
                    if str(tag).strip()
                }
                activity_keys.update(self._extract_match_tokens(activity.name or "", activity.event_type or ""))
                if match_keys.intersection({key for key in activity_keys if key}):
                    matching_activities.append(activity)

            matching_projects = []
            for project in projects:
                project_keys = {
                    self.skill_service.normalize_skill_tag(str(tag))
                    for tag in (getattr(project, "focus_tags", None) or [])
                    if str(tag).strip()
                }
                project_name_key = self.skill_service.normalize_skill_tag(getattr(project, "name", "") or "")
                if project_name_key:
                    project_keys.add(project_name_key)
                if match_keys.intersection({key for key in project_keys if key}):
                    matching_projects.append(project)

            if not matching_activities and not matching_projects:
                continue

            parts = []
            if matching_activities:
                parts.append(f"{len(matching_activities)} activit{'y' if len(matching_activities) == 1 else 'ies'}")
            if matching_projects:
                parts.append(f"{len(matching_projects)} active project{'s' if len(matching_projects) != 1 else ''}")

            examples = []
            if matching_activities:
                examples.append(matching_activities[0].name)
            if matching_projects:
                examples.append(matching_projects[0].name)
            example_text = f" Signals already exist in {', '.join(examples[:2])}." if examples else ""

            output.append(
                Recommendation(
                    id=f"skill-signal:{skill.id}",
                    app_name="Skills",
                    scope="item",
                    scope_id=skill.id,
                    priority=72,
                    confidence=0.74,
                    title=f"Connect {skill.name} more explicitly",
                    body=f"{skill.name} already has matching signal in {' and '.join(parts)}.{example_text} Keep tags stable so this growth area stays legible across Rasbhari.",
                    reasoning="Matching activities or active projects already carry tags or names that align with this skill.",
                    kind="info",
                    action=None,
                    action_label=None,
                    payload={},
                    tags=["skills", "linking", skill.tag_key or skill.name],
                )
            )
        return output

    def _detect_missing_project_skills(self, user_id: int) -> Iterable[Recommendation]:
        projects = self.project_service.find_all(filters={"user_id": user_id, "state": "Active"}, sort_by={"last_updated": "ASC"})
        skills = self.skill_service.find_all(filters={"user_id": user_id}, sort_by={"name": "ASC"})
        skill_tags = set()
        for skill in skills:
            skill_tags.update(self.skill_service.get_match_keys(skill))

        output: list[Recommendation] = []
        for project in projects:
            focus_tags = [str(tag).strip().lower() for tag in (project.focus_tags or []) if str(tag).strip()]
            for focus_tag in focus_tags:
                normalized_skill_tag = self.skill_service.normalize_skill_tag(focus_tag)
                if normalized_skill_tag and normalized_skill_tag not in skill_tags:
                    output.append(
                        Recommendation(
                            id=f"skill:{project.id}:{focus_tag}",
                            app_name="Projects",
                            scope="item",
                            scope_id=project.id,
                            priority=82,
                            confidence=0.82,
                            title=f"Create skill for {focus_tag}",
                            body=f"Project work on {project.name} already emits `{focus_tag}`. Turn it into a tracked skill so progress becomes visible.",
                            reasoning="This project already has a stable focus tag but no matching skill.",
                            kind="stage_action",
                            action="create_skill",
                            action_label="Stage Skill",
                            payload={
                                "skill_name": focus_tag.replace("-", " ").title(),
                                "skill_tag_key": normalized_skill_tag,
                                "skill_aliases": [focus_tag] if focus_tag != normalized_skill_tag else [],
                            },
                            tags=["projects", "skills", focus_tag],
                        )
                    )
                    break
        return output

    def _detect_missing_project_promises(self, user_id: int) -> Iterable[Recommendation]:
        projects = self.project_service.find_all(filters={"user_id": user_id, "state": "Active"}, sort_by={"last_updated": "ASC"})
        promises = self.promise_service.find_all(filters={"user_id": user_id}, sort_by={"name": "ASC"})
        promise_tags = {str(p.target_event_tag).strip().lower() for p in promises if p.target_event_tag}
        output: list[Recommendation] = []
        for project in projects:
            focus_tags = [str(tag).strip().lower() for tag in (project.focus_tags or []) if str(tag).strip()]
            for focus_tag in focus_tags:
                if focus_tag not in promise_tags:
                    output.append(
                        Recommendation(
                            id=f"promise:{project.id}:{focus_tag}",
                            app_name="Projects",
                            scope="item",
                            scope_id=project.id,
                            priority=77,
                            confidence=0.74,
                            title=f"Protect {focus_tag} with a promise",
                            body=f"Work on {project.name} uses `{focus_tag}`, but no promise currently watches that tag.",
                            reasoning="The work signal exists, but there is no explicit commitment tied to it yet.",
                            kind="stage_action",
                            action="create_promise",
                            action_label="Stage Promise",
                            payload={
                                "promise_name": f"Keep {focus_tag.replace('-', ' ')} moving",
                                "promise_description": f"Create regular evidence for {focus_tag} work through project activity.",
                                "promise_frequency": "daily",
                                "promise_target_event_tag": focus_tag,
                                "promise_required_count": 1,
                            },
                            tags=["projects", "promises", focus_tag],
                        )
                    )
                    break
        return output

    def _detect_projects_without_open_tickets(self, user_id: int) -> Iterable[Recommendation]:
        projects = self.project_service.find_all(filters={"user_id": user_id, "state": "Active"}, sort_by={"last_updated": "ASC"})
        output: list[Recommendation] = []
        for project in projects:
            tickets = self.kanban_ticket_service.get_by_project_id(project.id, include_archived=False)
            open_tickets = [ticket for ticket in tickets if getattr(ticket, "state", None) != "shipped"]
            if open_tickets:
                continue
            output.append(
                Recommendation(
                    id=f"ticket:{project.id}",
                    app_name="Projects",
                    scope="item",
                    scope_id=project.id,
                    priority=73,
                    confidence=0.69,
                    title=f"Create the next ticket for {project.name}",
                    body=f"{project.name} has no active board work. Add one concrete ticket so the project can move visibly.",
                    reasoning="The project is active but the board has no open tickets.",
                    kind="stage_action",
                    action="create_ticket",
                    action_label="Stage Ticket",
                    payload={
                        "ticket_project_id": project.id,
                        "ticket_title": f"Define next step for {project.name}",
                        "ticket_description": f"Add the next concrete unit of work for {project.name}.",
                        "ticket_state": "backlog",
                    },
                    tags=["projects", "kanban"],
                )
            )
        return output

    def _detect_stale_projects(self, user_id: int) -> Iterable[Recommendation]:
        projects = self.project_service.find_all(filters={"user_id": user_id, "state": "Active"}, sort_by={"last_updated": "ASC"})
        stale_cutoff = datetime.now() - timedelta(days=7)
        output: list[Recommendation] = []
        for project in projects:
            if project.last_updated is not None and project.last_updated >= stale_cutoff:
                continue
            output.append(
                Recommendation(
                    id=f"update:{project.id}",
                    app_name="Projects",
                    scope="item",
                    scope_id=project.id,
                    priority=70,
                    confidence=0.71,
                    title=f"Post a project update for {project.name}",
                    body=f"{project.name} has not had a recent visible update. Add a short progress note so the timeline reflects reality.",
                    reasoning="The project looks stale from its last updated timestamp.",
                    kind="stage_action",
                    action="create_project_update",
                    action_label="Stage Update",
                    payload={
                        "project_id": project.id,
                        "project_update_content": f"Progress update for {project.name}: captured the next visible step and current state.",
                        "project_update_type": "Update",
                    },
                    tags=["projects", "timeline"],
                )
            )
        return output

    @staticmethod
    def _extract_match_tokens(*parts: str) -> set[str]:
        tokens = set()
        for part in parts:
            normalized = str(part).strip().lower().replace(":", " ").replace("-", " ").replace("_", " ")
            tokens.update(token for token in normalized.split() if token)
        return tokens
