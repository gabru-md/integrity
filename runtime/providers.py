from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Optional

from flask import has_request_context
from gabru.auth import PermissionManager
from gabru.contracts import (
    AdminOpsProvider,
    AppStatusStore,
    AssistantCommandProvider,
    AuthProvider,
    AuthenticatedUser,
    DashboardDataProvider,
    TimelineEventView,
)
from gabru.qprocessor.qservice import QueueService
from services.applications import ApplicationService
from services.dependency_health import DependencyHealthService
from services.devices import DeviceService
from services.events import EventService
from services.notifications import NotificationService
from services.assistant_command import AssistantCommandService
from services.skill_level_history import SkillLevelHistoryService
from services.skills import SkillService
from services.timeline import TimelineService
from services.activities import ActivityService
from services.admin_updates import AdminUpdateService
from services.reports import ReportService
from services.users import UserService


class RasbhariAuthProvider(AuthProvider):
    def __init__(self, user_service: Optional[UserService] = None):
        self.user_service = user_service or UserService()

    def authenticate_credentials(self, username: str, password: str) -> Optional[AuthenticatedUser]:
        user = self.user_service.authenticate(username, password)
        return self._to_authenticated_user(user)

    def authenticate_api_key(self, api_key: str) -> Optional[AuthenticatedUser]:
        user = self.user_service.authenticate_api_key(api_key)
        return self._to_authenticated_user(user)

    def get_by_username(self, username: str):
        return self.user_service.get_by_username(username)

    def create_user(
        self,
        username: str,
        display_name: str,
        password: str,
        is_admin: bool,
        is_active: bool,
        is_approved: bool,
    ) -> Optional[AuthenticatedUser]:
        from model.user import User

        user = User(
            username=username,
            display_name=display_name or username,
            password=password,
            is_admin=is_admin,
            is_active=is_active,
            is_approved=is_approved,
        )
        user_id = self.user_service.create(user)
        if not user_id:
            return None
        user.id = user_id
        refreshed = self.user_service.get_by_id(user_id) or user
        return self._to_authenticated_user(refreshed)

    def count_users(self) -> int:
        return self.user_service.count()

    @staticmethod
    def _to_authenticated_user(user) -> Optional[AuthenticatedUser]:
        if not user:
            return None
        return AuthenticatedUser(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            is_admin=user.is_admin,
            api_key=getattr(user, "api_key", None),
            onboarding_completed=getattr(user, "onboarding_completed", False),
            experience_mode=getattr(user, "experience_mode", "everyday") or "everyday",
        )


class RasbhariAppStatusStore(AppStatusStore):
    def __init__(self, application_service: Optional[ApplicationService] = None):
        self.application_service = application_service or ApplicationService()

    def get_app_state(self, app_name: str) -> Optional[bool]:
        db_app = self.application_service.get_by_name(app_name)
        if not db_app:
            return None
        return db_app.is_active

    def set_app_state(self, app_name: str, is_active: bool) -> bool:
        return self.application_service.set_active_status(app_name, is_active)


class RasbhariAdminOpsProvider(AdminOpsProvider):
    def __init__(self, admin_update_service: Optional[AdminUpdateService] = None):
        self.admin_update_service = admin_update_service or AdminUpdateService()

    def get_update_status(self) -> dict[str, object]:
        return self.admin_update_service.get_update_status()

    def trigger_update(self, actor_username: Optional[str] = None) -> dict[str, object]:
        return self.admin_update_service.trigger_update(actor_username=actor_username)


class RasbhariDashboardDataProvider(DashboardDataProvider):
    def __init__(
        self,
        event_service: Optional[EventService] = None,
        notification_service: Optional[NotificationService] = None,
        device_service: Optional[DeviceService] = None,
        queue_service: Optional[QueueService] = None,
        skill_history_service: Optional[SkillLevelHistoryService] = None,
        skill_service: Optional[SkillService] = None,
        timeline_service: Optional[TimelineService] = None,
        activity_service: Optional[ActivityService] = None,
        report_service: Optional[ReportService] = None,
        user_service: Optional[UserService] = None,
    ):
        self.event_service = event_service or EventService()
        self.notification_service = notification_service or NotificationService()
        self.device_service = device_service or DeviceService()
        self.queue_service = queue_service or QueueService()
        self.skill_history_service = skill_history_service or SkillLevelHistoryService()
        self.skill_service = skill_service or SkillService()
        self.timeline_service = timeline_service or TimelineService()
        self.activity_service = activity_service or ActivityService()
        self.report_service = report_service or ReportService()
        self.user_service = user_service

    def get_notification_center_data(self) -> dict[str, object]:
        current_user = PermissionManager.get_current_user() if has_request_context() else None
        current_user_id = current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "id", None)
        if not current_user_id:
            return {"items": [], "unread_count": 0}

        experience_mode = UserService.normalize_experience_mode(
            current_user.get("experience_mode", "everyday")
            if isinstance(current_user, dict)
            else getattr(current_user, "experience_mode", "everyday")
        )
        if experience_mode == "everyday":
            limit = 4
        elif experience_mode == "structured":
            limit = 6
        else:
            limit = 8

        persisted_items = self.notification_service.get_in_app_notifications(current_user_id, limit=limit)
        items = [
            {
                "id": f"in-app:{item.id}",
                "notification_id": item.id,
                "title": item.title or "Notice",
                "body": item.notification_data,
                "href": item.href,
                "class": item.notification_class or "today",
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "created_at_display": item.created_at.strftime("%b %d, %H:%M") if item.created_at else "",
                "is_system": False,
            }
            for item in persisted_items
        ]
        unread_count = self.notification_service.count_unread_in_app_notifications(current_user_id)
        return {
            "items": items,
            "unread_count": unread_count,
            "has_items": bool(items),
        }

    def mark_notification_read(self, notification_id: int) -> bool:
        current_user_id = PermissionManager.get_current_user_id() if has_request_context() else None
        if not current_user_id:
            return False
        return self.notification_service.mark_as_read(notification_id, current_user_id)

    def mark_all_notifications_read(self) -> bool:
        current_user_id = PermissionManager.get_current_user_id() if has_request_context() else None
        if not current_user_id:
            return False
        return self.notification_service.mark_all_as_read(current_user_id)

    def get_capture_data(self) -> dict[str, object]:
        recent_activities = []
        for activity in self.activity_service.get_recent_items(8):
            recent_activities.append({
                "id": activity.id,
                "name": activity.name,
                "event_type": activity.event_type,
                "description": activity.description,
                "tags": activity.tags or [],
            })

        recent_events = self.event_service.get_recent_items(25)
        suggested_event_types: list[str] = []
        suggested_tags: list[str] = []
        for event in recent_events:
            event_type = (getattr(event, "event_type", "") or "").strip()
            if event_type and event_type not in suggested_event_types:
                suggested_event_types.append(event_type)
            for tag in getattr(event, "tags", None) or []:
                normalized_tag = str(tag).strip()
                if normalized_tag and normalized_tag not in suggested_tags:
                    suggested_tags.append(normalized_tag)
            if len(suggested_event_types) >= 6 and len(suggested_tags) >= 10:
                break

        latest_event = next(iter(recent_events), None)
        return {
            "recent_activities": recent_activities,
            "suggested_event_types": suggested_event_types[:6],
            "suggested_tags": suggested_tags[:10],
            "latest_event": {
                "event_type": latest_event.event_type,
                "description": latest_event.description,
                "timestamp": latest_event.timestamp.isoformat() if latest_event and latest_event.timestamp else None,
            } if latest_event else None,
        }

    def get_dependency_health_data(self) -> list[dict]:
        try:
            return DependencyHealthService().get_checks()
        except Exception as exc:
            return [{
                "name": "Dependency Health",
                "status": "Broken",
                "summary": "Health checks failed",
                "detail": str(exc),
            }]

    def get_reliability_data(self, processes_data: list[dict]) -> list[dict]:
        latest_event = next(iter(self.event_service.get_recent_items(1)), None)
        latest_event_id = latest_event.id if latest_event else 0
        latest_event_age = self._format_age(latest_event.timestamp if latest_event else None)

        running_processes = sum(1 for process in processes_data if process.get('is_alive'))
        total_processes = len(processes_data)
        process_status = "Healthy"
        if total_processes == 0:
            process_status = "Paused"
        elif running_processes == 0:
            process_status = "Broken"
        elif running_processes < total_processes:
            process_status = "Delayed"

        queue_stats = self.queue_service.get_all()
        queue_lags = [max(0, latest_event_id - (stat.last_consumed_id or 0)) for stat in queue_stats]
        max_queue_lag = max(queue_lags) if queue_lags else 0
        queue_status = "Healthy"
        if max_queue_lag > 100:
            queue_status = "Broken"
        elif max_queue_lag > 20:
            queue_status = "Delayed"
        elif not queue_stats:
            queue_status = "Paused"

        recent_notifications = self.notification_service.get_recent_items(5)
        courier_failures = self._count_recent_log_failures("Courier.log")
        notification_status = "Healthy"
        if courier_failures > 0:
            notification_status = "Delayed"
        if not any(process['name'] == 'Courier' and process['is_alive'] for process in processes_data):
            notification_status = "Broken"

        enabled_devices = self.device_service.count(filters={"enabled": True})
        device_processes = [process for process in processes_data if process["owner_app"] == "Devices"]
        active_device_processes = sum(1 for process in device_processes if process.get("is_alive"))
        device_status = "Healthy" if enabled_devices > 0 else "Paused"
        if enabled_devices > 0 and active_device_processes == 0:
            device_status = "Delayed"

        return [
            {
                "name": "Process Health",
                "status": process_status,
                "summary": f"{running_processes}/{total_processes} processes running" if total_processes else "No processes registered",
                "detail": "Background workers that power event handling and automation.",
                "href": "/processes",
            },
            {
                "name": "Event Flow",
                "status": "Healthy" if latest_event else "Paused",
                "summary": f"Last event {latest_event_age}" if latest_event else "No events recorded yet",
                "detail": f"Latest event id: {latest_event_id}" if latest_event else "The event stream is currently empty.",
                "href": "/events/home",
            },
            {
                "name": "Queue Health",
                "status": queue_status,
                "summary": f"Max backlog: {max_queue_lag} events",
                "detail": f"Tracking {len(queue_stats)} queue processors against event stream id {latest_event_id}.",
                "href": "/processes",
            },
            {
                "name": "Notifications",
                "status": notification_status,
                "summary": f"{len(recent_notifications)} recent deliveries, {courier_failures} recent failures",
                "detail": "Courier sends ntfy.sh by default and email when the event carries the email tag.",
                "href": "/processes",
            },
            {
                "name": "Devices",
                "status": device_status,
                "summary": f"{enabled_devices} enabled devices, {active_device_processes}/{len(device_processes)} device processes active",
                "detail": "Tracks sensor/device availability and the workers that monitor them.",
                "href": "/devices",
            },
        ]

    def get_admin_health_data(self, processes_data: list[dict]) -> dict[str, object]:
        reliability_cards = self.get_reliability_data(processes_data)
        latest_event = next(iter(self.event_service.get_recent_items(1)), None)
        latest_event_id = latest_event.id if latest_event else 0
        latest_event_age = self._format_age(latest_event.timestamp if latest_event else None)
        queue_stats = self.queue_service.get_all()
        dependency_cards = self.get_dependency_health_data()
        unhealthy_dependencies = [item for item in dependency_cards if item.get("status") not in {"Healthy", "Configured"}]

        queue_drift_processors = []
        for process in processes_data:
            if process.get("type") != "QueueProcessor":
                continue
            last_consumed_id = process.get("last_consumed_id") or 0
            lag = max(0, latest_event_id - last_consumed_id)
            queue_drift_processors.append({
                "name": process.get("name"),
                "owner_app": process.get("owner_app"),
                "last_consumed_id": last_consumed_id,
                "lag": lag,
                "status": "Healthy" if lag <= 20 else ("Delayed" if lag <= 100 else "Broken"),
            })

        queue_drift_processors.sort(key=lambda item: item["lag"], reverse=True)
        max_queue_lag = queue_drift_processors[0]["lag"] if queue_drift_processors else 0
        queue_drift_status = "Healthy"
        if max_queue_lag > 100:
            queue_drift_status = "Broken"
        elif max_queue_lag > 20:
            queue_drift_status = "Delayed"
        elif not queue_stats:
            queue_drift_status = "Paused"

        checked_at = datetime.now(timezone.utc)
        return {
            "checked_at": checked_at.isoformat(),
            "checked_at_display": checked_at.strftime("%Y-%m-%d %H:%M UTC"),
            "host": os.getenv("HOSTNAME") or os.uname().nodename,
            "server": {
                "status": "Healthy",
                "summary": "Admin surface reachable now",
                "detail": "If you can load this page over Tailscale, the Pi-hosted Rasbhari server is currently responding.",
            },
            "event_flow": {
                "status": "Healthy" if latest_event else "Paused",
                "summary": f"Last event {latest_event_age}" if latest_event else "No events recorded yet",
                "detail": f"Latest event id: {latest_event_id}" if latest_event else "The event stream is currently empty.",
            },
            "queue_drift": {
                "status": queue_drift_status,
                "summary": f"Max lag {max_queue_lag} events",
                "detail": f"{len(queue_drift_processors)} queue processor(s) tracked against event stream id {latest_event_id}.",
                "processors": queue_drift_processors[:5],
            },
            "dependencies": {
                "status": "Healthy" if not unhealthy_dependencies else ("Delayed" if len(unhealthy_dependencies) == 1 else "Broken"),
                "summary": f"{len(unhealthy_dependencies)} issue(s) detected",
                "detail": "Dependency health reflects services like ntfy, SendGrid, and OpenWebUI.",
            },
            "reliability_cards": reliability_cards,
        }

    def get_universal_timeline_data(self, limit: int = 20) -> list[dict]:
        items = []

        for item in self.skill_history_service.get_recent_history(limit=6):
            items.append({
                "source": "Skills",
                "category": "Growth",
                "title": item.summary,
                "subtitle": f"{item.total_xp} XP total",
                "timestamp": item.reached_at,
                "href": "/skills/home",
            })

        for item in self.timeline_service.get_recent_items(6):
            items.append({
                "source": "Projects",
                "category": "Projects",
                "title": item.content[:80] + ("..." if len(item.content) > 80 else ""),
                "subtitle": f"{item.item_type} on project #{item.project_id}",
                "timestamp": item.timestamp,
                "href": f"/projects/{item.project_id}/view",
            })

        for item in self.notification_service.get_recent_items(6):
            items.append({
                "source": "Courier",
                "category": "Notifications",
                "title": item.title or f"{item.notification_class.title()} via {item.notification_type}",
                "subtitle": item.notification_data,
                "timestamp": item.created_at,
                "href": "/processes",
            })

        for item in self.event_service.get_recent_items(20):
            if item.event_type == "skill:level_up":
                continue
            view = TimelineEventView(
                event_type=item.event_type,
                tags=item.tags or [],
                description=item.description or item.event_type,
                timestamp=item.timestamp,
            )
            items.append({
                "source": "Events",
                "category": self._categorize_event(view),
                "title": view.description,
                "subtitle": view.event_type,
                "timestamp": view.timestamp,
                "href": "/events/home",
            })

        items.sort(key=lambda item: self._normalize_datetime(item.get("timestamp")), reverse=True)
        return [
            {
                **item,
                "timestamp": self._normalize_datetime(item.get("timestamp")).isoformat() if self._normalize_datetime(item.get("timestamp")) else None
            }
            for item in items[:limit]
        ]

    @staticmethod
    def _categorize_event(event: TimelineEventView) -> str:
        tags = set(event.tags or [])
        if event.event_type.startswith("project:") or "progress" in tags:
            return "Projects"
        if event.event_type.startswith("device:") or "device" in tags:
            return "Devices"
        if event.event_type.startswith("skill:") or "skill" in tags:
            return "Growth"
        if "notification" in tags or "email" in tags:
            return "Notifications"
        if "activity" in event.event_type or any(tag.startswith("triggered_by:activity:") for tag in tags):
            return "Activity"
        return "Events"

    @staticmethod
    def _normalize_datetime(value) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except Exception:
            return None

    @classmethod
    def _format_age(cls, value) -> str:
        dt_value = cls._normalize_datetime(value)
        if not dt_value:
            return "unknown"
        delta = datetime.now(timezone.utc) - dt_value
        seconds = max(0, int(delta.total_seconds()))
        if seconds < 60:
            return f"{seconds}s ago"
        if seconds < 3600:
            return f"{seconds // 60}m ago"
        if seconds < 86400:
            return f"{seconds // 3600}h ago"
        return f"{seconds // 86400}d ago"

    @staticmethod
    def _count_recent_log_failures(filename: str, line_limit: int = 200) -> int:
        log_dir = os.getenv('LOG_DIR')
        if not log_dir:
            return 0
        log_path = os.path.join(log_dir, filename)
        if not os.path.exists(log_path):
            return 0
        try:
            with open(log_path, 'r') as log_file:
                lines = log_file.readlines()[-line_limit:]
        except Exception:
            return 0
        failure_markers = (
            "returned error",
            "Could not send",
            "Failed to send",
        )
        return sum(1 for line in lines if any(marker in line for marker in failure_markers))


class RasbhariAssistantCommandProvider(AssistantCommandProvider):
    def __init__(self, assistant_command_service: Optional[AssistantCommandService] = None):
        self.assistant_command_service = assistant_command_service or AssistantCommandService()

    def handle(
        self,
        user_id: int,
        message: str,
        confirm: bool = False,
        cancel: bool = False,
        change_action: Optional[str] = None,
    ):
        return self.assistant_command_service.handle(
            user_id=user_id,
            message=message,
            confirm=confirm,
            cancel=cancel,
            change_action=change_action,
        )

    def handle_recommendation(self, user_id: int, recommendation: dict, execute: bool = False):
        return self.assistant_command_service.handle_recommendation(user_id=user_id, recommendation=recommendation, execute=execute)
