from __future__ import annotations

from dataclasses import dataclass

from model.event import Event


NOTIFICATION_CLASSES = {"urgent", "today", "review", "suggestion", "digest", "system"}

DEFAULT_NOTIFICATION_CLASS = "today"

CLASS_CONFIG = {
    "urgent": {"priority": "5", "emoji_tags": "rotating_light,warning", "title_prefix": "Urgent"},
    "today": {"priority": "4", "emoji_tags": "calendar,white_check_mark", "title_prefix": "Today"},
    "review": {"priority": "3", "emoji_tags": "memo,mag", "title_prefix": "Review"},
    "suggestion": {"priority": "2", "emoji_tags": "bulb,robot", "title_prefix": "Suggestion"},
    "digest": {"priority": "1", "emoji_tags": "newspaper,robot", "title_prefix": "Digest"},
    "system": {"priority": "3", "emoji_tags": "gear,warning", "title_prefix": "System"},
}


@dataclass(frozen=True)
class NotificationIntent:
    notification_class: str
    delivery_channel: str
    title: str


def resolve_notification_class(tags: list[str] | None, event_type: str | None = None) -> str:
    normalized_tags = set(tags or [])

    for tag in normalized_tags:
        if tag.startswith("notification_class:"):
            candidate = tag.split(":", 1)[1].strip().lower()
            if candidate in NOTIFICATION_CLASSES:
                return candidate

    for candidate in NOTIFICATION_CLASSES:
        if candidate in normalized_tags:
            return candidate

    if event_type and event_type.startswith("report:"):
        return "review"
    if event_type and event_type.startswith("skill:"):
        return "today"
    return DEFAULT_NOTIFICATION_CLASS


def resolve_delivery_channel(tags: list[str] | None) -> str:
    normalized_tags = set(tags or [])
    if "email" in normalized_tags:
        return "email"
    return "ntfy"


def build_notification_title(event: Event, notification_class: str) -> str:
    config = CLASS_CONFIG.get(notification_class, CLASS_CONFIG[DEFAULT_NOTIFICATION_CLASS])
    if event.description:
        return event.description[:80]
    return f"{config['title_prefix']}: {event.event_type}"


def resolve_notification_intent(event: Event) -> NotificationIntent:
    notification_class = resolve_notification_class(event.tags, event.event_type)
    return NotificationIntent(
        notification_class=notification_class,
        delivery_channel=resolve_delivery_channel(event.tags),
        title=build_notification_title(event, notification_class),
    )
