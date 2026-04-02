from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from gabru.qprocessor.qprocessor import QueueProcessor
from model.event import Event
from services.eventing import emit_event_safely
from services.events import EventService


SESSION_APP_RULES = {
    "coding": {
        "pycharm",
        "intellij-idea",
        "webstorm",
        "goland",
        "rubymine",
        "vscode",
        "cursor",
        "terminal",
        "iterm2",
        "xcode",
        "android-studio",
    },
    "writing": {
        "ia-writer",
        "ulysses",
        "obsidian",
        "bear",
        "notes",
        "pages",
    },
    "research": {
        "google-chrome",
        "arc",
        "safari",
        "firefox",
        "brave-browser",
    },
    "planning": {
        "logseq",
        "notion",
        "things",
        "todoist",
        "calendar",
        "fantastical",
    },
}


SESSION_PRIORITY = ["coding", "writing", "planning", "research"]


@dataclass
class ActiveSession:
    session_type: str
    started_at: datetime
    last_signal_at: datetime
    active_apps: set[str] = field(default_factory=set)


class SessionInferenceProcessor(QueueProcessor[Event]):
    def __init__(self, **kwargs):
        self.event_service = EventService()
        self.active_sessions: dict[int, ActiveSession] = {}
        super().__init__(service=self.event_service, **kwargs)

    def filter_item(self, event: Event) -> Optional[Event]:
        if not event.user_id:
            return None
        if event.event_type in {"local:app:opened", "local:app:closed", "local:user:idle", "local:machine:woke"}:
            return event
        return None

    def _process_item(self, event: Event) -> bool:
        if event.event_type == "local:user:idle":
            self._end_session(event.user_id, event.timestamp or datetime.now(), "idle")
            return True

        if event.event_type == "local:machine:woke":
            self._end_session(event.user_id, event.timestamp or datetime.now(), "machine_woke")
            return True

        app_slug = self._extract_app_slug(event)
        if not app_slug:
            return True

        timestamp = event.timestamp or datetime.now()
        if event.event_type == "local:app:opened":
            self._handle_app_opened(event.user_id, app_slug, timestamp)
            return True

        if event.event_type == "local:app:closed":
            self._handle_app_closed(event.user_id, app_slug, timestamp)
            return True

        return True

    @staticmethod
    def infer_session_type(app_slug: Optional[str]) -> Optional[str]:
        if not app_slug:
            return None
        for session_type in SESSION_PRIORITY:
            if app_slug in SESSION_APP_RULES.get(session_type, set()):
                return session_type
        return None

    @staticmethod
    def _extract_app_slug(event: Event) -> Optional[str]:
        for tag in event.tags or []:
            if tag.startswith("app:"):
                return tag.split(":", 1)[1]
        return None

    def _handle_app_opened(self, user_id: int, app_slug: str, timestamp: datetime) -> None:
        session_type = self.infer_session_type(app_slug)
        if not session_type:
            return

        current = self.active_sessions.get(user_id)
        if current and current.session_type != session_type:
            self._end_session(user_id, timestamp, "context_switch")
            current = None

        if not current:
            self.active_sessions[user_id] = ActiveSession(
                session_type=session_type,
                started_at=timestamp,
                last_signal_at=timestamp,
                active_apps={app_slug},
            )
            self._emit_session_boundary(user_id, session_type, "start", timestamp, [f"app:{app_slug}"])
            return

        current.active_apps.add(app_slug)
        current.last_signal_at = timestamp

    def _handle_app_closed(self, user_id: int, app_slug: str, timestamp: datetime) -> None:
        current = self.active_sessions.get(user_id)
        if not current:
            return
        current.active_apps.discard(app_slug)
        current.last_signal_at = timestamp
        if current.session_type != self.infer_session_type(app_slug):
            return
        if current.active_apps:
            return
        self._end_session(user_id, timestamp, "apps_closed")

    def _end_session(self, user_id: int, timestamp: datetime, reason: str) -> None:
        current = self.active_sessions.pop(user_id, None)
        if not current:
            return
        duration_minutes = max(0, int((timestamp - current.started_at).total_seconds() // 60))
        tags = [
            f"session:{current.session_type}",
            f"reason:{reason}",
            *(f"app:{app_slug}" for app_slug in sorted(current.active_apps)),
        ]
        self._emit_session_boundary(
            user_id,
            current.session_type,
            "end",
            timestamp,
            tags,
            duration_minutes=duration_minutes,
        )

    def _emit_session_boundary(
        self,
        user_id: int,
        session_type: str,
        action: str,
        timestamp: datetime,
        tags: list[str],
        *,
        duration_minutes: Optional[int] = None,
    ) -> None:
        description = f"{session_type.title()} session {action}ed"
        if action == "end" and duration_minutes is not None:
            description = f"{session_type.title()} session ended after {duration_minutes} minute(s)"
        emit_event_safely(
            self.log,
            user_id=user_id,
            event_type=f"{session_type}:session:{action}",
            timestamp=timestamp,
            description=description,
            tags=[
                "inference:session",
                f"session:{session_type}",
                f"session_action:{action}",
                *tags,
            ],
        )
