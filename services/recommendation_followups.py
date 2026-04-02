from __future__ import annotations

from typing import Optional

from services.activities import ActivityService
from services.kanban_tickets import KanbanTicketService
from services.projects import ProjectService
from services.promises import PromiseService
from services.recommendation_engine import RecommendationEngineService
from services.skills import SkillService


class RecommendationFollowUpService:
    def __init__(
        self,
        project_service: Optional[ProjectService] = None,
        kanban_ticket_service: Optional[KanbanTicketService] = None,
        promise_service: Optional[PromiseService] = None,
        skill_service: Optional[SkillService] = None,
        activity_service: Optional[ActivityService] = None,
        recommendation_engine: Optional[RecommendationEngineService] = None,
    ):
        self.recommendation_engine = recommendation_engine or RecommendationEngineService(
            project_service=project_service,
            kanban_ticket_service=kanban_ticket_service,
            promise_service=promise_service,
            skill_service=skill_service,
            activity_service=activity_service,
        )

    def get_follow_ups(self, user_id: int, limit: int = 4) -> list[dict]:
        recommendations = self.recommendation_engine.get_recommendations(user_id=user_id, limit=limit)
        return [self._to_follow_up_payload(item) for item in recommendations if item.action]

    @staticmethod
    def _to_follow_up_payload(item) -> dict:
        return {
            "id": item.id,
            "title": item.title,
            "body": item.body,
            "action": item.action,
            "confidence": item.confidence,
            "reasoning": item.reasoning,
            "payload": item.payload,
            "scope": item.scope,
            "scope_id": item.scope_id,
            "app_name": item.app_name,
            "priority": item.priority,
            "kind": item.kind,
            "action_label": item.action_label,
            "tags": item.tags,
        }
