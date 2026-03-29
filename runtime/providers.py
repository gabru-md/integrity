from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Optional

from gabru.contracts import (
    AppStatusStore,
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
from services.skill_level_history import SkillLevelHistoryService
from services.timeline import TimelineService
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


class RasbhariDashboardDataProvider(DashboardDataProvider):
    def __init__(
        self,
        event_service: Optional[EventService] = None,
        notification_service: Optional[NotificationService] = None,
        device_service: Optional[DeviceService] = None,
        queue_service: Optional[QueueService] = None,
        skill_history_service: Optional[SkillLevelHistoryService] = None,
        timeline_service: Optional[TimelineService] = None,
    ):
        self.event_service = event_service or EventService()
        self.notification_service = notification_service or NotificationService()
        self.device_service = device_service or DeviceService()
        self.queue_service = queue_service or QueueService()
        self.skill_history_service = skill_history_service or SkillLevelHistoryService()
        self.timeline_service = timeline_service or TimelineService()

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
                "title": f"{item.notification_type.upper()} notification sent",
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
