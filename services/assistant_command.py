import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from typing import List, Optional

from gabru.log import Logger
from model.assistant_command import AssistantAction, AssistantCommandPlan, AssistantCommandResult
from model.event import Event
from model.kanban_ticket import KanbanTicket
from model.promise import Promise
from model.skill import Skill
from model.thought import Thought
from services.activities import ActivityService
from services.assistant_resolvers import (
    ActivityCommandResolver,
    AnswerCommandResolver,
    EventCommandResolver,
    PromiseCommandResolver,
    ThoughtCommandResolver,
)
from services.events import EventService
from services.kanban_tickets import KanbanTicketService
from services.project_updates import ProjectUpdateService
from services.promises import PromiseService
from services.skills import SkillService
from services.thoughts import ThoughtService


class AssistantCommandService:
    SAFE_AUTO_EXECUTE_THRESHOLDS = {
        "create_event": 0.58,
        "trigger_activity": 0.58,
        "create_thought": 0.58,
        "create_promise": 0.72,
        "create_skill": 0.72,
        "create_ticket": 0.68,
        "create_project_update": 0.68,
        "answer": 0.0,
    }
    AFFIRMATIVE_MESSAGES = {
        "yes",
        "y",
        "ok",
        "okay",
        "do it",
        "go ahead",
        "confirm",
        "approved",
        "sounds good",
        "thanks",
        "thank you",
    }

    def __init__(
        self,
        event_service: Optional[EventService] = None,
        activity_service: Optional[ActivityService] = None,
        thought_service: Optional[ThoughtService] = None,
        promise_service: Optional[PromiseService] = None,
        skill_service: Optional[SkillService] = None,
        kanban_ticket_service: Optional[KanbanTicketService] = None,
        project_update_service: Optional[ProjectUpdateService] = None,
        ollama_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ):
        self.event_service = event_service or EventService()
        self.activity_service = activity_service or ActivityService()
        self.thought_service = thought_service or ThoughtService()
        self.promise_service = promise_service or PromiseService()
        self.skill_service = skill_service or SkillService()
        self.kanban_ticket_service = kanban_ticket_service
        self.project_update_service = project_update_service
        self.ollama_url = (ollama_url or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")
        self.model_name = model_name or os.getenv("OLLAMA_COMMAND_MODEL") or os.getenv("OLLAMA_MODEL") or ""
        self.timeout_seconds = timeout_seconds or float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "20"))
        self.log = Logger.get_log("AssistantCommand")
        self.pending_plans = {}
        self.resolvers = [
            PromiseCommandResolver(),
            ThoughtCommandResolver(),
            ActivityCommandResolver(match_activity=self._resolve_activity_for_route),
            EventCommandResolver(),
            AnswerCommandResolver(),
        ]

    def handle(
        self,
        user_id: int,
        message: str,
        confirm: bool = False,
        cancel: bool = False,
        change_action: Optional[str] = None,
    ) -> AssistantCommandResult:
        raw_text = (message or "").strip()
        if not raw_text and not cancel and not change_action:
            return AssistantCommandResult(ok=False, user_message="", response="Message is required.")

        pending_entry = self.pending_plans.get(user_id)
        if cancel:
            if pending_entry:
                self.pending_plans.pop(user_id, None)
                return AssistantCommandResult(
                    ok=True,
                    executed=False,
                    requires_confirmation=False,
                    action="answer",
                    confidence=1.0,
                    user_message=raw_text,
                    summary="Ignored pending action.",
                    response="Ignored the staged action. You can enter a new command now.",
                )
            return AssistantCommandResult(
                ok=True,
                executed=False,
                requires_confirmation=False,
                action="answer",
                confidence=1.0,
                user_message=raw_text,
                summary="No pending action.",
                response="There is no staged action to ignore.",
            )
        if pending_entry and change_action:
            return self._change_pending_action(user_id, pending_entry, change_action)
        if pending_entry and (confirm or self._is_affirmation(raw_text)):
            result = self._execute_plan(user_id, pending_entry["user_message"], pending_entry["plan"])
            if result.ok and result.executed:
                self.pending_plans.pop(user_id, None)
            return result
        if pending_entry and not confirm:
            pending_plan = pending_entry["plan"]
            return AssistantCommandResult(
                ok=True,
                executed=False,
                requires_confirmation=True,
                action=pending_plan.action,
                confidence=pending_plan.confidence,
                summary=pending_plan.summary,
                reasoning=pending_plan.reasoning,
                user_message=raw_text,
                response="There is already a staged action waiting. Confirm it or ignore it before sending a new command.",
                payload=self._payload_for_plan(pending_plan),
            )

        if not self.model_name:
            return AssistantCommandResult(
                ok=False,
                user_message=raw_text,
                response="OLLAMA_COMMAND_MODEL is not configured.",
            )

        context = self._build_context(user_id)
        try:
            plan = self._call_ollama(raw_text, context)
        except Exception as exc:
            self.log.exception("Assistant command failed: %s", exc)
            return AssistantCommandResult(
                ok=False,
                user_message=raw_text,
                response="The assistant could not interpret that command right now.",
                reasoning="Ollama request failed.",
            )

        plan = self._route_plan(user_id, raw_text, plan, context)

        if plan.action == "answer":
            return AssistantCommandResult(
                ok=True,
                executed=False,
                requires_confirmation=False,
                action=plan.action,
                confidence=plan.confidence,
                summary=plan.summary,
                reasoning=plan.reasoning,
                user_message=raw_text,
                response=self._format_answer_response(plan),
                payload=self._payload_for_plan(plan),
            )

        self.pending_plans[user_id] = {"plan": plan, "user_message": raw_text}
        return AssistantCommandResult(
            ok=True,
            executed=False,
            requires_confirmation=True,
            action=plan.action,
            confidence=plan.confidence,
            summary=plan.summary,
            reasoning=plan.reasoning,
            user_message=raw_text,
            response=self._format_staged_response(plan),
            payload=self._payload_for_plan(plan),
        )

    def handle_recommendation(self, user_id: int, recommendation: dict) -> AssistantCommandResult:
        pending_entry = self.pending_plans.get(user_id)
        if pending_entry:
            pending_plan = pending_entry["plan"]
            return AssistantCommandResult(
                ok=True,
                executed=False,
                requires_confirmation=True,
                action=pending_plan.action,
                confidence=pending_plan.confidence,
                summary=pending_plan.summary,
                reasoning=pending_plan.reasoning,
                user_message=str(recommendation.get("title") or ""),
                response="There is already a staged action waiting. Confirm it or ignore it before staging a recommendation follow-up.",
                payload=self._payload_for_plan(pending_plan),
            )

        plan = self._plan_from_recommendation(recommendation)
        if plan is None:
            return AssistantCommandResult(
                ok=False,
                executed=False,
                user_message=str(recommendation.get("title") or ""),
                response="This recommendation could not be turned into an actionable follow-up.",
            )

        user_message = str(recommendation.get("title") or plan.summary or "Recommendation follow-up")
        self.pending_plans[user_id] = {"plan": plan, "user_message": user_message}
        return AssistantCommandResult(
            ok=True,
            executed=False,
            requires_confirmation=True,
            action=plan.action,
            confidence=plan.confidence,
            summary=plan.summary,
            reasoning=plan.reasoning,
            user_message=user_message,
            response=self._format_staged_response(plan),
            payload=self._payload_for_plan(plan),
        )

    def _build_context(self, user_id: int) -> dict:
        activities = self.activity_service.find_all(filters={"user_id": user_id}, sort_by={"name": "ASC"})
        promises = self.promise_service.find_all(filters={"user_id": user_id}, sort_by={"name": "ASC"})
        skills = self.skill_service.find_all(filters={"user_id": user_id}, sort_by={"name": "ASC"})
        return {
            "activities": [
                {
                    "id": activity.id,
                    "name": activity.name,
                    "event_type": activity.event_type,
                    "description": activity.description or "",
                    "tags": activity.tags or [],
                }
                for activity in activities
            ],
            "promises": [
                {
                    "name": promise.name,
                    "frequency": promise.frequency,
                    "target_event_type": promise.target_event_type,
                    "target_event_tag": promise.target_event_tag,
                    "required_count": promise.required_count,
                    "is_negative": promise.is_negative,
                }
                for promise in promises
            ],
            "skills": [
                {
                    "name": skill.name,
                    "tag_key": skill.tag_key,
                    "aliases": skill.aliases or [],
                }
                for skill in skills
            ],
        }

    def _call_ollama(self, message: str, context: dict) -> AssistantCommandPlan:
        system_prompt, user_prompt = self._build_chat_messages(message, context)
        request_body = json.dumps(
            {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.1,
                },
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.ollama_url}/api/chat",
            data=request_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Failed to reach Ollama at {self.ollama_url}") from exc

        raw_response = ((payload.get("message") or {}).get("content") or "").strip()
        if not raw_response:
            raise ValueError("Ollama returned an empty response")

        try:
            parsed = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise ValueError("Ollama returned invalid JSON") from exc

        if isinstance(parsed, dict) and any(key in parsed for key in ("task", "rules", "output_schema")):
            raise ValueError("Model echoed instructions instead of returning a plan")
        if not isinstance(parsed, dict):
            raise ValueError("Model response was not a JSON object")

        parsed = self._normalize_plan_payload(parsed)
        return AssistantCommandPlan.model_validate(parsed)

    def _build_chat_messages(self, message: str, context: dict) -> tuple[str, str]:
        system_prompt = (
            "You are Rasbhari AI, the command layer for an event-driven personal operating system.\n"
            "Return exactly one JSON object and nothing else.\n"
            "Do not echo instructions or schema.\n"
            "Choose exactly one action from: create_event, trigger_activity, create_thought, create_promise, answer.\n"
            "Always check existing activities first before inventing a raw event.\n"
            "If the user's command clearly matches an existing activity by meaning, choose trigger_activity instead of create_event.\n"
            "Prefer create_event only when there is no strong matching activity and downstream promises or skills should react through tags.\n"
            "Use create_thought for notes or reflections.\n"
            "Use create_promise only when the user is clearly creating a commitment.\n"
            "Use answer only for informational or conversational replies.\n"
            "When creating an event, include helpful tags that align with activities, promises, and skills when they are clearly relevant.\n"
            "Confidence must be a number between 0 and 1.\n"
            "JSON keys you may use: action, confidence, reasoning, summary, event_type, description, tags, activity_id, activity_name, thought_message, promise_name, promise_description, promise_frequency, promise_target_event_type, promise_target_event_tag, promise_required_count, response."
        )
        user_prompt = (
            f"User command:\n{json.dumps(message, ensure_ascii=True)}\n\n"
            f"Rasbhari context:\n{json.dumps(context, ensure_ascii=True)}\n\n"
            "Return the JSON plan now."
        )
        return system_prompt, user_prompt

    def _route_plan(self, user_id: int, raw_text: str, plan: AssistantCommandPlan, context: dict) -> AssistantCommandPlan:
        best_score = -1.0
        best_plan = plan
        for resolver in self.resolvers:
            decision = resolver.route(user_id=user_id, raw_text=raw_text, plan=plan, context=context)
            if decision.score > best_score:
                best_score = decision.score
                best_plan = decision.plan

        if best_plan.action != plan.action:
            best_plan = best_plan.model_copy(update={"confidence": max(plan.confidence, best_plan.confidence)})
        if best_plan.action == "create_event":
            matched_activity = self._resolve_activity_for_route(
                user_id=user_id,
                activity_name=best_plan.activity_name,
                event_type=best_plan.event_type,
                raw_text=raw_text,
            )
            if matched_activity:
                best_plan = best_plan.model_copy(
                    update={
                        "action": "trigger_activity",
                        "activity_id": matched_activity.id,
                        "activity_name": matched_activity.name,
                        "event_type": matched_activity.event_type,
                        "confidence": max(best_plan.confidence, 0.7),
                        "reasoning": (
                            f"{best_plan.reasoning} Routed through the existing activity '{matched_activity.name}'."
                            if best_plan.reasoning else
                            f"Routed through the existing activity '{matched_activity.name}'."
                        ),
                        "response": best_plan.response or f"I matched that to the existing activity `{matched_activity.name}`.",
                        "summary": best_plan.summary or f"Trigger activity {matched_activity.name}.",
                    }
                )
        return best_plan

    def _execute_plan(self, user_id: int, raw_text: str, plan: AssistantCommandPlan) -> AssistantCommandResult:
        if plan.action == "create_event":
            tags = self._normalize_tags(plan.tags)
            event = Event(
                user_id=user_id,
                event_type=(plan.event_type or "").strip(),
                timestamp=datetime.now(),
                description=(plan.description or raw_text).strip(),
                tags=tags,
            )
            event_id = self.event_service.create(event)
            if not event_id:
                return self._execution_failure(plan, raw_text, "Failed to create event.")
            return AssistantCommandResult(
                ok=True,
                executed=True,
                action=plan.action,
                confidence=plan.confidence,
                summary=plan.summary or f"Created event {event.event_type}.",
                reasoning=plan.reasoning,
                user_message=raw_text,
                response=self._format_executed_response(
                    title="Event created",
                    action_line=f"Created `{event.event_type}`.",
                    plan=plan,
                    details=[
                        f"Description: {(plan.description or raw_text).strip()}",
                        f"Tags: {', '.join(tags) if tags else 'none'}",
                    ],
                ),
                payload={"event_id": event_id, "event_type": event.event_type, "tags": tags},
            )

        if plan.action == "trigger_activity":
            activity = self._match_activity(user_id, plan.activity_id, plan.activity_name)
            if not activity:
                return self._execution_failure(plan, raw_text, "Could not find the requested activity.")
            triggered_id = self.activity_service.trigger_activity(
                activity.id,
                override_payload={
                    "description": plan.description or raw_text,
                    "tags": self._normalize_tags(plan.tags),
                },
            )
            if not triggered_id:
                return self._execution_failure(plan, raw_text, "Failed to trigger activity.")
            return AssistantCommandResult(
                ok=True,
                executed=True,
                action=plan.action,
                confidence=plan.confidence,
                summary=plan.summary or f"Triggered activity {activity.name}.",
                reasoning=plan.reasoning,
                user_message=raw_text,
                response=self._format_executed_response(
                    title="Activity triggered",
                    action_line=f"Triggered `{activity.name}`.",
                    plan=plan,
                    details=[
                        f"Event type: {activity.event_type}",
                        f"Description: {plan.description or raw_text}",
                    ],
                ),
                payload={"activity_id": activity.id, "activity_name": activity.name, "event_type": activity.event_type},
            )

        if plan.action == "create_thought":
            thought = Thought(user_id=user_id, message=(plan.thought_message or raw_text).strip(), created_at=datetime.now())
            thought_id = self.thought_service.create(thought)
            if not thought_id:
                return self._execution_failure(plan, raw_text, "Failed to save thought.")
            return AssistantCommandResult(
                ok=True,
                executed=True,
                action=plan.action,
                confidence=plan.confidence,
                summary=plan.summary or "Saved thought.",
                reasoning=plan.reasoning,
                user_message=raw_text,
                response=self._format_executed_response(
                    title="Thought saved",
                    action_line="Saved the note.",
                    plan=plan,
                    details=[f"Message: {(plan.thought_message or raw_text).strip()}"],
                ),
                payload={"thought_id": thought_id},
            )

        if plan.action == "create_promise":
            promise = Promise(
                user_id=user_id,
                name=(plan.promise_name or "").strip(),
                description=(plan.promise_description or "").strip() or None,
                frequency=(plan.promise_frequency or "daily").strip() or "daily",
                target_event_type=(plan.promise_target_event_type or "").strip() or None,
                target_event_tag=(plan.promise_target_event_tag or "").strip() or None,
                required_count=plan.promise_required_count or 1,
            )
            promise_id = self.promise_service.create(promise)
            if not promise_id:
                return self._execution_failure(plan, raw_text, "Failed to create promise.")
            return AssistantCommandResult(
                ok=True,
                executed=True,
                action=plan.action,
                confidence=plan.confidence,
                summary=plan.summary or f"Created promise {promise.name}.",
                reasoning=plan.reasoning,
                user_message=raw_text,
                response=self._format_executed_response(
                    title="Promise created",
                    action_line=f"Created promise `{promise.name}`.",
                    plan=plan,
                    details=[
                        f"Frequency: {promise.frequency}",
                        f"Target event type: {promise.target_event_type or 'none'}",
                        f"Target event tag: {promise.target_event_tag or 'none'}",
                    ],
                ),
                payload={
                    "promise_id": promise_id,
                    "name": promise.name,
                    "target_event_type": promise.target_event_type,
                    "target_event_tag": promise.target_event_tag,
                },
            )

        if plan.action == "create_skill":
            skill = Skill(
                user_id=user_id,
                name=(plan.skill_name or "").strip(),
                tag_key=(plan.skill_tag_key or "").strip(),
                aliases=self._normalize_tags(plan.skill_aliases),
            )
            skill_id = self.skill_service.create(skill)
            if not skill_id:
                return self._execution_failure(plan, raw_text, "Failed to create skill.")
            return AssistantCommandResult(
                ok=True,
                executed=True,
                action=plan.action,
                confidence=plan.confidence,
                summary=plan.summary or f"Created skill {skill.name}.",
                reasoning=plan.reasoning,
                user_message=raw_text,
                response=self._format_executed_response(
                    title="Skill created",
                    action_line=f"Created skill `{skill.name}`.",
                    plan=plan,
                    details=[
                        f"Tag key: {skill.tag_key}",
                        f"Aliases: {', '.join(skill.aliases) if skill.aliases else 'none'}",
                    ],
                ),
                payload={"skill_id": skill_id, "skill_name": skill.name, "skill_tag_key": skill.tag_key},
            )

        if plan.action == "create_ticket":
            ticket_service = self.kanban_ticket_service or KanbanTicketService()
            ticket = KanbanTicket(
                user_id=user_id,
                project_id=plan.ticket_project_id or 0,
                title=(plan.ticket_title or "").strip(),
                description=(plan.ticket_description or "").strip(),
                state=(plan.ticket_state or "backlog").strip().lower(),
            )
            ticket_id = ticket_service.create(ticket)
            if not ticket_id:
                return self._execution_failure(plan, raw_text, "Failed to create ticket.")
            return AssistantCommandResult(
                ok=True,
                executed=True,
                action=plan.action,
                confidence=plan.confidence,
                summary=plan.summary or f"Created ticket {ticket.title}.",
                reasoning=plan.reasoning,
                user_message=raw_text,
                response=self._format_executed_response(
                    title="Ticket created",
                    action_line=f"Created ticket `{ticket.title}`.",
                    plan=plan,
                    details=[
                        f"Project ID: {ticket.project_id}",
                        f"State: {ticket.state}",
                    ],
                ),
                payload={"ticket_id": ticket_id, "project_id": ticket.project_id, "title": ticket.title},
            )

        if plan.action == "create_project_update":
            project_update_service = self.project_update_service or ProjectUpdateService(event_service=self.event_service)
            timeline_id = project_update_service.create_update(
                user_id=user_id,
                project_id=plan.project_id or 0,
                content=(plan.project_update_content or raw_text).strip(),
                item_type=(plan.project_update_type or "Update").strip() or "Update",
            )
            if not timeline_id:
                return self._execution_failure(plan, raw_text, "Failed to create project update.")
            return AssistantCommandResult(
                ok=True,
                executed=True,
                action=plan.action,
                confidence=plan.confidence,
                summary=plan.summary or "Created project update.",
                reasoning=plan.reasoning,
                user_message=raw_text,
                response=self._format_executed_response(
                    title="Project update created",
                    action_line=f"Created project update for project #{plan.project_id}.",
                    plan=plan,
                    details=[
                        f"Item type: {plan.project_update_type or 'Update'}",
                        f"Content: {(plan.project_update_content or raw_text).strip()}",
                    ],
                ),
                payload={"timeline_id": timeline_id, "project_id": plan.project_id},
            )

        return AssistantCommandResult(
            ok=True,
            executed=False,
            action="answer",
            confidence=plan.confidence,
            summary=plan.summary,
            reasoning=plan.reasoning,
            user_message=raw_text,
            response=self._format_answer_response(plan),
            payload=self._payload_for_plan(plan),
        )

    def _match_activity(self, user_id: int, activity_id: Optional[int], activity_name: Optional[str]):
        activities = self.activity_service.find_all(filters={"user_id": user_id}, sort_by={"name": "ASC"})
        if activity_id is not None:
            for activity in activities:
                if activity.id == activity_id:
                    return activity
        normalized = self._normalize(activity_name)
        if normalized:
            for activity in activities:
                if self._normalize(activity.name) == normalized:
                    return activity
        return None

    def _resolve_activity_for_route(
        self,
        user_id: int,
        activity_name: Optional[str],
        event_type: Optional[str],
        raw_text: str,
    ):
        activities = self.activity_service.find_all(filters={"user_id": user_id}, sort_by={"name": "ASC"})
        return self._best_matching_activity(
            activities,
            activity_name=activity_name,
            event_type=event_type,
            raw_text=raw_text,
        )

    def _best_matching_activity(self, activities, activity_name: Optional[str], event_type: Optional[str], raw_text: str):
        if activity_name:
            normalized_name = self._normalize(activity_name)
            for activity in activities:
                if self._normalize(activity.name) == normalized_name:
                    return activity

        if event_type:
            normalized_event_type = self._normalize(event_type)
            for activity in activities:
                if self._normalize(activity.event_type) == normalized_event_type:
                    return activity

        input_tokens = set(self._normalize(raw_text).replace(":", " ").split())
        best_activity = None
        best_score = 0
        for activity in activities:
            tokens = set()
            for item in (activity.name, activity.event_type, activity.description):
                tokens.update(self._normalize(item).replace(":", " ").split())
            for tag in (activity.tags or []):
                tokens.update(self._normalize(tag).replace(":", " ").split())
            score = len(input_tokens & tokens)
            if score > best_score:
                best_score = score
                best_activity = activity

        if best_activity and best_score >= 2:
            return best_activity
        return None

    def _normalize_plan_payload(self, payload: dict) -> dict:
        normalized = dict(payload)
        normalized["action"] = self._normalize_action_value(normalized)

        response = normalized.get("response")
        if isinstance(response, dict):
            for key in ("answer", "message", "text", "content", "response"):
                value = response.get(key)
                if isinstance(value, str) and value.strip():
                    normalized["response"] = value.strip()
                    break
            else:
                normalized["response"] = json.dumps(response, ensure_ascii=True)
        elif response is not None and not isinstance(response, str):
            normalized["response"] = str(response)

        for key in ("reasoning", "summary", "description", "thought_message", "promise_name", "promise_description"):
            value = normalized.get(key)
            if value is not None and not isinstance(value, str):
                normalized[key] = str(value)

        tags = normalized.get("tags")
        if isinstance(tags, str):
            normalized["tags"] = [tag.strip() for tag in tags.split(",") if tag.strip()]
        elif isinstance(tags, list):
            normalized["tags"] = [str(tag).strip() for tag in tags if str(tag).strip()]
        elif tags is None:
            normalized["tags"] = []

        skill_aliases = normalized.get("skill_aliases")
        if isinstance(skill_aliases, str):
            normalized["skill_aliases"] = [item.strip() for item in skill_aliases.split(",") if item.strip()]
        elif isinstance(skill_aliases, list):
            normalized["skill_aliases"] = [str(item).strip() for item in skill_aliases if str(item).strip()]
        elif skill_aliases is None:
            normalized["skill_aliases"] = []

        return normalized

    def _normalize_action_value(self, payload: dict) -> str:
        raw_signal = " ".join(
            str(value) for value in (
                payload.get("action"),
                payload.get("summary"),
                payload.get("reasoning"),
                payload.get("response"),
                payload.get("description"),
                payload.get("thought_message"),
            )
            if value is not None
        ).lower()

        if payload.get("promise_name") or payload.get("promise_target_event_type") or payload.get("promise_target_event_tag") or "promise" in raw_signal:
            return "create_promise"
        if payload.get("skill_name") or payload.get("skill_tag_key") or "create skill" in raw_signal:
            return "create_skill"
        if payload.get("ticket_project_id") or payload.get("ticket_title") or "create ticket" in raw_signal:
            return "create_ticket"
        if payload.get("project_id") or payload.get("project_update_content") or "project update" in raw_signal:
            return "create_project_update"
        if payload.get("thought_message") or "note that" in raw_signal or raw_signal.startswith("note "):
            return "create_thought"

        action = payload.get("action")
        if isinstance(action, str):
            candidate = action.strip().lower()
            if candidate in self.SAFE_AUTO_EXECUTE_THRESHOLDS:
                return candidate
            alias_map = {
                "event": "create_event",
                "create event": "create_event",
                "log event": "create_event",
                "activity": "trigger_activity",
                "trigger activity": "trigger_activity",
                "thought": "create_thought",
                "create thought": "create_thought",
                "note": "create_thought",
                "promise": "create_promise",
                "create promise": "create_promise",
                "skill": "create_skill",
                "create skill": "create_skill",
                "ticket": "create_ticket",
                "create ticket": "create_ticket",
                "project update": "create_project_update",
                "create project update": "create_project_update",
                "reply": "answer",
                "respond": "answer",
            }
            if candidate in alias_map:
                return alias_map[candidate]

        if payload.get("activity_id") or payload.get("activity_name") or ("activity" in raw_signal and not (payload.get("promise_name") or payload.get("promise_target_event_type") or payload.get("promise_target_event_tag"))):
            return "trigger_activity"
        if payload.get("event_type") or payload.get("tags"):
            return "create_event"
        return "answer"

    def _payload_for_plan(self, plan: AssistantCommandPlan) -> dict:
        payload = plan.model_dump()
        payload.pop("response", None)
        return payload

    def _execution_failure(self, plan: AssistantCommandPlan, raw_text: str, response: str) -> AssistantCommandResult:
        return AssistantCommandResult(
            ok=False,
            executed=False,
            action=plan.action,
            confidence=plan.confidence,
            summary=plan.summary,
            reasoning=plan.reasoning,
            user_message=raw_text,
            response=response,
            payload=self._payload_for_plan(plan),
        )

    def _change_pending_action(self, user_id: int, pending_entry: dict, change_action: str) -> AssistantCommandResult:
        raw_action = (change_action or "").strip()
        if raw_action not in ("create_event", "trigger_activity", "create_thought", "create_promise", "create_skill", "create_ticket", "create_project_update"):
            return AssistantCommandResult(
                ok=False,
                executed=False,
                requires_confirmation=True,
                action=pending_entry["plan"].action,
                confidence=pending_entry["plan"].confidence,
                summary=pending_entry["plan"].summary,
                reasoning=pending_entry["plan"].reasoning,
                user_message=pending_entry["user_message"],
                response="That action type is not supported for staged changes.",
                payload=self._payload_for_plan(pending_entry["plan"]),
            )

        revised_plan = self._coerce_plan_to_action(
            user_id=user_id,
            raw_text=pending_entry["user_message"],
            plan=pending_entry["plan"],
            target_action=raw_action,
        )
        if revised_plan is None:
            return AssistantCommandResult(
                ok=False,
                executed=False,
                requires_confirmation=True,
                action=pending_entry["plan"].action,
                confidence=pending_entry["plan"].confidence,
                summary=pending_entry["plan"].summary,
                reasoning=pending_entry["plan"].reasoning,
                user_message=pending_entry["user_message"],
                response=f"Could not restage this command as `{raw_action}`.",
                payload=self._payload_for_plan(pending_entry["plan"]),
            )

        self.pending_plans[user_id] = {"plan": revised_plan, "user_message": pending_entry["user_message"]}
        return AssistantCommandResult(
            ok=True,
            executed=False,
            requires_confirmation=True,
            action=revised_plan.action,
            confidence=revised_plan.confidence,
            summary=revised_plan.summary,
            reasoning=revised_plan.reasoning,
            user_message=pending_entry["user_message"],
            response=self._format_staged_response(revised_plan),
            payload=self._payload_for_plan(revised_plan),
        )

    def _coerce_plan_to_action(
        self,
        user_id: int,
        raw_text: str,
        plan: AssistantCommandPlan,
        target_action: AssistantAction,
    ) -> Optional[AssistantCommandPlan]:
        base_updates = {
            "action": target_action,
            "confidence": min(0.99, max(plan.confidence, 0.7)),
        }

        if target_action == "create_event":
            event_type = plan.event_type
            if not event_type and plan.activity_name:
                activity = self._match_activity(user_id, plan.activity_id, plan.activity_name)
                event_type = getattr(activity, "event_type", None) if activity else None
            if not event_type:
                event_type = "report"
            return plan.model_copy(
                update={
                    **base_updates,
                    "event_type": event_type,
                    "description": plan.description or plan.thought_message or raw_text,
                    "summary": f"Create event `{event_type}`.",
                    "reasoning": f"Restaged by user as `{target_action}`.",
                    "response": None,
                }
            )

        if target_action == "trigger_activity":
            activity = self._resolve_activity_for_route(
                user_id=user_id,
                activity_name=plan.activity_name,
                event_type=plan.event_type,
                raw_text=raw_text,
            )
            if not activity:
                return None
            return plan.model_copy(
                update={
                    **base_updates,
                    "activity_id": activity.id,
                    "activity_name": activity.name,
                    "event_type": activity.event_type,
                    "summary": f"Trigger activity {activity.name}.",
                    "reasoning": f"Restaged by user as `{target_action}`.",
                    "response": None,
                }
            )

        if target_action == "create_thought":
            thought_message = plan.thought_message or plan.description or raw_text
            return plan.model_copy(
                update={
                    **base_updates,
                    "thought_message": thought_message,
                    "summary": "Save a thought.",
                    "reasoning": f"Restaged by user as `{target_action}`.",
                    "response": None,
                }
            )

        if target_action == "create_promise":
            if not (plan.promise_name or plan.promise_target_event_type or plan.promise_target_event_tag):
                return None
            return plan.model_copy(
                update={
                    **base_updates,
                    "promise_name": plan.promise_name or (plan.activity_name or plan.event_type or raw_text.title()),
                    "promise_frequency": plan.promise_frequency or "daily",
                    "promise_required_count": plan.promise_required_count or 1,
                    "summary": f"Create promise `{plan.promise_name or (plan.activity_name or raw_text)}`.",
                    "reasoning": f"Restaged by user as `{target_action}`.",
                    "response": None,
                }
            )

        if target_action == "create_skill":
            skill_name = plan.skill_name or plan.promise_target_event_tag or (plan.ticket_title or raw_text).title()
            skill_tag_key = plan.skill_tag_key or self.skill_service.normalize_skill_tag(skill_name)
            return plan.model_copy(
                update={
                    **base_updates,
                    "skill_name": skill_name,
                    "skill_tag_key": skill_tag_key,
                    "summary": f"Create skill `{skill_name}`.",
                    "reasoning": f"Restaged by user as `{target_action}`.",
                    "response": None,
                }
            )

        if target_action == "create_ticket":
            if not plan.ticket_project_id and not plan.project_id:
                return None
            title = plan.ticket_title or plan.summary or f"Follow up on {raw_text}"
            return plan.model_copy(
                update={
                    **base_updates,
                    "ticket_project_id": plan.ticket_project_id or plan.project_id,
                    "ticket_title": title,
                    "ticket_description": plan.ticket_description or plan.description or raw_text,
                    "ticket_state": plan.ticket_state or "backlog",
                    "summary": f"Create ticket `{title}`.",
                    "reasoning": f"Restaged by user as `{target_action}`.",
                    "response": None,
                }
            )

        if target_action == "create_project_update":
            if not plan.project_id and not plan.ticket_project_id:
                return None
            return plan.model_copy(
                update={
                    **base_updates,
                    "project_id": plan.project_id or plan.ticket_project_id,
                    "project_update_content": plan.project_update_content or plan.description or raw_text,
                    "project_update_type": plan.project_update_type or "Update",
                    "summary": "Create a project update.",
                    "reasoning": f"Restaged by user as `{target_action}`.",
                    "response": None,
                }
            )

        return None

    def _format_staged_response(self, plan: AssistantCommandPlan) -> str:
        lines = [
            "Planned action",
            f"Type: {plan.action}",
            f"Confidence: {plan.confidence:.2f}",
        ]
        details = self._plan_details(plan)
        if details:
            lines.extend(details)
        if plan.summary:
            lines.append(f"Summary: {plan.summary}")
        if plan.reasoning:
            lines.append(f"Why: {plan.reasoning}")
        lines.append("Reply with 'yes', 'thanks', or use Confirm Action to commit it.")
        return "\n".join(lines)

    def _format_executed_response(self, title: str, action_line: str, plan: AssistantCommandPlan, details: List[str]) -> str:
        lines = [title, action_line]
        lines.extend([line for line in details if line])
        if plan.summary:
            lines.append(f"Summary: {plan.summary}")
        if plan.reasoning:
            lines.append(f"Why: {plan.reasoning}")
        return "\n".join(lines)

    def _format_answer_response(self, plan: AssistantCommandPlan) -> str:
        lines = [plan.response or plan.summary or "I understood the request."]
        if plan.summary and plan.response != plan.summary:
            lines.append(f"Summary: {plan.summary}")
        if plan.reasoning:
            lines.append(f"Why: {plan.reasoning}")
        return "\n".join(lines)

    def _plan_details(self, plan: AssistantCommandPlan) -> List[str]:
        if plan.action == "create_event":
            return [
                f"Event type: {plan.event_type or 'unspecified'}",
                f"Description: {plan.description or 'none'}",
                f"Tags: {', '.join(plan.tags) if plan.tags else 'none'}",
            ]
        if plan.action == "trigger_activity":
            return [
                f"Activity: {plan.activity_name or 'unspecified'}",
                f"Event type: {plan.event_type or 'unspecified'}",
                f"Description: {plan.description or 'none'}",
            ]
        if plan.action == "create_thought":
            return [f"Message: {plan.thought_message or plan.description or 'none'}"]
        if plan.action == "create_promise":
            return [
                f"Promise: {plan.promise_name or 'unspecified'}",
                f"Frequency: {plan.promise_frequency or 'daily'}",
                f"Target event type: {plan.promise_target_event_type or 'none'}",
                f"Target event tag: {plan.promise_target_event_tag or 'none'}",
            ]
        if plan.action == "create_skill":
            return [
                f"Skill: {plan.skill_name or 'unspecified'}",
                f"Tag key: {plan.skill_tag_key or 'none'}",
                f"Aliases: {', '.join(plan.skill_aliases) if plan.skill_aliases else 'none'}",
            ]
        if plan.action == "create_ticket":
            return [
                f"Project ID: {plan.ticket_project_id or 'unspecified'}",
                f"Ticket: {plan.ticket_title or 'unspecified'}",
                f"State: {plan.ticket_state or 'backlog'}",
            ]
        if plan.action == "create_project_update":
            return [
                f"Project ID: {plan.project_id or 'unspecified'}",
                f"Type: {plan.project_update_type or 'Update'}",
                f"Content: {plan.project_update_content or 'none'}",
            ]
        return []

    def _is_affirmation(self, message: str) -> bool:
        normalized = self._normalize(message)
        return normalized in self.AFFIRMATIVE_MESSAGES

    @staticmethod
    def _normalize(value: Optional[str]) -> str:
        return " ".join((value or "").strip().lower().split())

    @staticmethod
    def _normalize_tags(tags: List[str]) -> List[str]:
        return list(dict.fromkeys(tag.strip() for tag in (tags or []) if tag and tag.strip()))

    def _plan_from_recommendation(self, recommendation: dict) -> Optional[AssistantCommandPlan]:
        if not isinstance(recommendation, dict):
            return None
        payload = {
            "action": recommendation.get("action"),
            "confidence": recommendation.get("confidence", 0.7),
            "reasoning": recommendation.get("reasoning", ""),
            "summary": recommendation.get("title") or recommendation.get("summary") or "",
            "response": recommendation.get("body") or recommendation.get("response"),
        }
        payload.update(recommendation.get("payload") or {})
        payload = self._normalize_plan_payload(payload)
        try:
            return AssistantCommandPlan.model_validate(payload)
        except Exception:
            return None
