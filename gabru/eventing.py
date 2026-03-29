from typing import Any, Optional

from model.event import Event
from services.events import EventService


_event_service: Optional[EventService] = None


def get_event_service() -> EventService:
    global _event_service
    if _event_service is None:
        _event_service = EventService()
    return _event_service


def emit_event_safely(log, **event_data: Any) -> Optional[int]:
    try:
        return get_event_service().create(Event(**event_data))
    except Exception as exc:
        event_type = event_data.get("event_type", "unknown")
        log.warning("Failed to emit event %s: %s", event_type, exc)
        return None
