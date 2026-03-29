from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from model.assistant_command import AssistantCommandPlan


@dataclass
class ResolverDecision:
    score: float
    plan: AssistantCommandPlan


class BaseAssistantResolver:
    action_name = "answer"

    def route(
        self,
        user_id: int,
        raw_text: str,
        plan: AssistantCommandPlan,
        context: dict,
    ) -> ResolverDecision:
        return ResolverDecision(score=0.0, plan=plan)

    @staticmethod
    def _normalize(value: Optional[str]) -> str:
        return " ".join((value or "").strip().lower().split())


class PromiseCommandResolver(BaseAssistantResolver):
    action_name = "create_promise"

    def route(self, user_id: int, raw_text: str, plan: AssistantCommandPlan, context: dict) -> ResolverDecision:
        signal = " ".join(
            filter(
                None,
                [
                    raw_text,
                    plan.summary,
                    plan.reasoning,
                    plan.description,
                    plan.promise_name,
                    plan.promise_description,
                    plan.promise_frequency,
                    plan.promise_target_event_type,
                    plan.promise_target_event_tag,
                ],
            )
        ).lower()

        score = 0.0
        if plan.action == self.action_name:
            score += 0.65
        if plan.promise_name:
            score += 0.25
        if plan.promise_target_event_type or plan.promise_target_event_tag:
            score += 0.2
        if any(token in signal for token in ("promise", "every day", "daily", "weekly", "monthly", "commitment")):
            score += 0.2

        if score < 0.55:
            return ResolverDecision(score=score, plan=plan)

        routed_plan = plan.model_copy(
            update={
                "action": self.action_name,
                "response": plan.response or f"I can create the promise `{plan.promise_name or 'that promise'}`.",
            }
        )
        return ResolverDecision(score=min(score, 1.0), plan=routed_plan)


class ThoughtCommandResolver(BaseAssistantResolver):
    action_name = "create_thought"

    def route(self, user_id: int, raw_text: str, plan: AssistantCommandPlan, context: dict) -> ResolverDecision:
        signal = " ".join(
            filter(None, [raw_text, plan.summary, plan.reasoning, plan.thought_message, plan.response])
        ).lower()

        score = 0.0
        if plan.action == self.action_name:
            score += 0.65
        if plan.thought_message:
            score += 0.25
        if any(token in signal for token in ("note that", "remember that", "thought", "journal", "note to self")):
            score += 0.25

        if score < 0.55:
            return ResolverDecision(score=score, plan=plan)

        routed_plan = plan.model_copy(
            update={
                "action": self.action_name,
                "thought_message": plan.thought_message or raw_text,
                "response": plan.response or "Saved that thought.",
            }
        )
        return ResolverDecision(score=min(score, 1.0), plan=routed_plan)


class ActivityCommandResolver(BaseAssistantResolver):
    action_name = "trigger_activity"

    def __init__(self, match_activity: Callable[..., object]):
        self.match_activity = match_activity

    def route(self, user_id: int, raw_text: str, plan: AssistantCommandPlan, context: dict) -> ResolverDecision:
        if plan.action in ("create_promise", "create_thought"):
            return ResolverDecision(score=0.0, plan=plan)

        matched_activity = self.match_activity(
            user_id=user_id,
            activity_name=plan.activity_name,
            event_type=plan.event_type,
            raw_text=raw_text,
        )
        if not matched_activity:
            return ResolverDecision(score=0.0, plan=plan)

        score = 0.72
        if plan.action == self.action_name:
            score += 0.15
        if plan.action == "create_event":
            score += 0.18
        if plan.activity_id == getattr(matched_activity, "id", None) or self._normalize(plan.activity_name) == self._normalize(getattr(matched_activity, "name", None)):
            score += 0.2
        if self._normalize(plan.event_type) == self._normalize(getattr(matched_activity, "event_type", None)):
            score += 0.15

        response = plan.response or f"I matched that to the existing activity `{matched_activity.name}`."
        reasoning = plan.reasoning or ""
        if plan.action != self.action_name:
            suffix = f" Routed through the existing activity '{matched_activity.name}'."
            reasoning = f"{reasoning}{suffix}".strip()

        routed_plan = plan.model_copy(
            update={
                "action": self.action_name,
                "activity_id": matched_activity.id,
                "activity_name": matched_activity.name,
                "event_type": getattr(matched_activity, "event_type", None),
                "response": response,
                "reasoning": reasoning,
                "summary": plan.summary or f"Trigger activity {matched_activity.name}.",
            }
        )
        return ResolverDecision(score=min(score, 1.0), plan=routed_plan)


class EventCommandResolver(BaseAssistantResolver):
    action_name = "create_event"

    def route(self, user_id: int, raw_text: str, plan: AssistantCommandPlan, context: dict) -> ResolverDecision:
        if plan.action in ("create_promise", "create_thought"):
            return ResolverDecision(score=0.0, plan=plan)

        score = 0.0
        if plan.action == self.action_name:
            score += 0.55
        if plan.event_type:
            score += 0.2
        if plan.tags:
            score += 0.1
        if plan.description:
            score += 0.05
        if not plan.event_type and not plan.tags:
            return ResolverDecision(score=score, plan=plan)

        routed_plan = plan.model_copy(
            update={
                "action": self.action_name,
                "description": plan.description or raw_text,
            }
        )
        return ResolverDecision(score=min(score, 1.0), plan=routed_plan)


class AnswerCommandResolver(BaseAssistantResolver):
    action_name = "answer"

    def route(self, user_id: int, raw_text: str, plan: AssistantCommandPlan, context: dict) -> ResolverDecision:
        score = 0.15
        if plan.action == self.action_name:
            score = 0.75
        if not any(
            [
                plan.event_type,
                plan.activity_id,
                plan.activity_name,
                plan.thought_message,
                plan.promise_name,
                plan.promise_target_event_type,
                plan.promise_target_event_tag,
            ]
        ):
            score += 0.15

        routed_plan = plan.model_copy(
            update={
                "action": self.action_name,
                "response": plan.response or plan.summary or "I understood the request.",
            }
        )
        return ResolverDecision(score=min(score, 1.0), plan=routed_plan)
