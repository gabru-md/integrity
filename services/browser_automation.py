from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from model.event import Event
from services.activities import ActivityService
from services.browser_actions import BrowserActionService
from services.browser_rules import BrowserRuleService
from services.events import EventService
from services.project_updates import ProjectUpdateService


class BrowserAutomationService:
    def __init__(
        self,
        *,
        browser_action_service: Optional[BrowserActionService] = None,
        browser_rule_service: Optional[BrowserRuleService] = None,
        activity_service: Optional[ActivityService] = None,
        event_service: Optional[EventService] = None,
        project_update_service: Optional[ProjectUpdateService] = None,
    ):
        self.browser_action_service = browser_action_service or BrowserActionService()
        self.browser_rule_service = browser_rule_service or BrowserRuleService()
        self.activity_service = activity_service or ActivityService()
        self.event_service = event_service or EventService()
        self.project_update_service = project_update_service or ProjectUpdateService()

    def build_sync_package(self) -> dict[str, Any]:
        actions = [
            action.dict()
            for action in self.browser_action_service.find_all(sort_by={"name": "ASC"})
            if action.enabled
        ]
        rules = [
            rule.dict()
            for rule in self.browser_rule_service.find_all(sort_by={"priority": "ASC", "id": "ASC"})
            if rule.enabled
        ]
        return {
            "actions": actions,
            "rules": rules,
            "synced_at": datetime.utcnow().isoformat() + "Z",
        }

    def execute_browser_action(
        self,
        *,
        user_id: int,
        browser_action_id: int,
        browser_context: Optional[dict[str, Any]] = None,
        override_payload: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        action = self.browser_action_service.get_by_id(browser_action_id)
        if not action or not action.enabled:
            raise ValueError("Browser action not found or disabled")

        merged_payload = {}
        if action.default_payload:
            merged_payload.update(action.default_payload)
        if browser_context:
            merged_payload.update(browser_context)
        if override_payload:
            merged_payload.update(override_payload)

        if action.target_type == "activity":
            if not action.target_activity_id:
                raise ValueError("Browser action is missing an Activity target")
            activity = self.activity_service.get_by_id(action.target_activity_id)
            if not activity:
                raise ValueError("Activity target not found")
            triggered_id = self.activity_service.trigger_activity(
                action.target_activity_id,
                override_payload=merged_payload,
            )
            if not triggered_id:
                raise ValueError("Failed to trigger Activity target")
            return {
                "execution_type": "activity",
                "status": "ok",
                "browser_action_id": action.id,
                "activity_id": action.target_activity_id,
                "activity_name": activity.name,
            }

        if action.target_type == "event":
            event_tags = list(action.target_tags or [])
            browser_tags = merged_payload.pop("tags", [])
            if isinstance(browser_tags, str):
                browser_tags = [tag.strip() for tag in browser_tags.split(",") if tag.strip()]
            if isinstance(browser_tags, list):
                event_tags.extend(str(tag).strip() for tag in browser_tags if str(tag).strip())
            event_description = str(merged_payload.pop("description", "") or action.target_description or action.description or "").strip()
            event = Event(
                user_id=user_id,
                event_type=action.target_event_type or "browser:captured",
                timestamp=datetime.now(),
                description=event_description,
                tags=list(dict.fromkeys(event_tags)),
                payload=merged_payload,
            )
            event_id = self.event_service.create(event)
            if not event_id:
                raise ValueError("Failed to create browser-backed event")
            return {
                "execution_type": "event",
                "status": "ok",
                "browser_action_id": action.id,
                "event_id": event_id,
                "event_type": event.event_type,
            }

        if action.target_type == "project_update":
            if not action.target_project_id:
                raise ValueError("Browser action is missing a Project target")
            browser_title = str(merged_payload.get("title") or "").strip()
            browser_url = str(merged_payload.get("url") or "").strip()
            content_parts = [part for part in [action.target_description or action.description, browser_title, browser_url] if part]
            content = "\n".join(content_parts).strip() or "Browser-sourced project update"
            timeline_id = self.project_update_service.create_update(
                user_id=user_id,
                project_id=action.target_project_id,
                content=content,
            )
            if not timeline_id:
                raise ValueError("Failed to create Project update")
            return {
                "execution_type": "project_update",
                "status": "ok",
                "browser_action_id": action.id,
                "project_id": action.target_project_id,
                "timeline_id": timeline_id,
            }

        if action.target_type == "quick_log":
            return {
                "execution_type": "quick_log",
                "status": "prefill_required",
                "browser_action_id": action.id,
                "prefill": {
                    "browser_action_id": action.id,
                    "browser_action_name": action.name,
                    "description": action.target_description or action.description or "",
                    "payload": merged_payload,
                    "capture_url": "/capture",
                },
            }

        raise ValueError("Unsupported browser action target type")
