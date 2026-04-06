from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class ResourceService(Protocol):
    def create(self, obj: Any) -> Optional[int]:
        ...

    def get_recent_items(self, limit: int = 10) -> list[Any]:
        ...

    def get_by_id(self, entity_id: int) -> Any:
        ...

    def update(self, obj: Any) -> bool:
        ...

    def delete(self, entity_id: int) -> bool:
        ...

    def count(self, filters: Optional[dict[str, Any]] = None) -> int:
        ...


@dataclass
class AuthenticatedUser:
    id: int
    username: str
    display_name: str
    is_admin: bool
    api_key: Optional[str] = None
    onboarding_completed: bool = False
    experience_mode: str = "everyday"


@runtime_checkable
class AuthProvider(Protocol):
    def authenticate_credentials(self, username: str, password: str) -> Optional[AuthenticatedUser]:
        ...

    def authenticate_api_key(self, api_key: str) -> Optional[AuthenticatedUser]:
        ...

    def get_by_username(self, username: str) -> Any:
        ...

    def create_user(
        self,
        username: str,
        display_name: str,
        password: str,
        is_admin: bool,
        is_active: bool,
        is_approved: bool,
    ) -> Optional[AuthenticatedUser]:
        ...

    def count_users(self) -> int:
        ...


@runtime_checkable
class AppStatusStore(Protocol):
    def get_app_state(self, app_name: str) -> Optional[bool]:
        ...

    def set_app_state(self, app_name: str, is_active: bool) -> bool:
        ...


@runtime_checkable
class DashboardDataProvider(Protocol):
    def get_today_data(self) -> dict[str, Any]:
        ...

    def get_notification_center_data(self) -> dict[str, Any]:
        ...

    def get_capture_data(self) -> dict[str, Any]:
        ...

    def get_dependency_health_data(self) -> list[dict]:
        ...

    def get_reliability_data(self, processes_data: list[dict]) -> list[dict]:
        ...

    def get_admin_health_data(self, processes_data: list[dict]) -> dict[str, Any]:
        ...

    def get_universal_timeline_data(self, limit: int = 20) -> list[dict]:
        ...

    def mark_notification_read(self, notification_id: int) -> bool:
        ...

    def mark_all_notifications_read(self) -> bool:
        ...


@runtime_checkable
class AssistantCommandProvider(Protocol):
    def handle(
        self,
        user_id: int,
        message: str,
        confirm: bool = False,
        cancel: bool = False,
        change_action: Optional[str] = None,
    ) -> Any:
        ...

    def handle_recommendation(self, user_id: int, recommendation: dict[str, Any], execute: bool = False) -> Any:
        ...


@runtime_checkable
class AdminOpsProvider(Protocol):
    def get_update_status(self) -> dict[str, Any]:
        ...

    def trigger_update(self, actor_username: Optional[str] = None) -> dict[str, Any]:
        ...


@dataclass
class TimelineEventView:
    event_type: str
    tags: list[str]
    description: str
    timestamp: datetime
