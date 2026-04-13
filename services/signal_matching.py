from dataclasses import dataclass
from typing import Iterable, Optional

from model.promise import Promise


@dataclass(frozen=True)
class SignalMatchResult:
    matched: bool
    matched_tags: tuple[str, ...] = ()
    reason: str = ""


def normalize_signal_value(value: object) -> str:
    return str(value or "").strip().lower()


def normalize_signal_tags(tags: Optional[Iterable[object]]) -> list[str]:
    normalized = []
    for tag in tags or []:
        value = normalize_signal_value(tag)
        if value and value not in normalized:
            normalized.append(value)
    return normalized


def normalize_skill_key(value: object) -> str:
    return "".join(char for char in normalize_signal_value(value).lstrip("#") if char.isalnum())


def promise_target_signature(promise: Promise) -> dict:
    target_type = normalize_signal_value(promise.target_event_type)
    target_tags = normalize_signal_tags([promise.target_event_tag, *(promise.target_event_tags or [])])

    # Historical project promises used target_event_type as a scope marker.
    # Treat that shape as a tag target so linkers can stay event-source agnostic.
    if target_type.startswith("project:"):
        target_tags = normalize_signal_tags([*target_tags, target_type])
        target_type = ""

    return {
        "target_event_type": target_type,
        "target_tags": target_tags,
        "tag_match_mode": normalize_signal_value(promise.target_event_tags_match_mode) or "any",
    }


def match_signal(
    *,
    signal_event_types: Optional[Iterable[object]] = None,
    signal_tags: Optional[Iterable[object]] = None,
    target_event_type: Optional[object] = None,
    target_tags: Optional[Iterable[object]] = None,
    tag_match_mode: Optional[str] = "any",
) -> SignalMatchResult:
    event_types = set(normalize_signal_tags(signal_event_types))
    source_tags = set(normalize_signal_tags(signal_tags))
    required_type = normalize_signal_value(target_event_type)
    required_tags = normalize_signal_tags(target_tags)
    mode = normalize_signal_value(tag_match_mode) or "any"

    if required_type and required_type not in event_types:
        return SignalMatchResult(False, reason="event type did not match")

    if required_tags:
        matched_tags = tuple(tag for tag in required_tags if tag in source_tags)
        if mode == "all":
            if len(matched_tags) != len(required_tags):
                return SignalMatchResult(False, matched_tags=matched_tags, reason="required tags missing")
            return SignalMatchResult(True, matched_tags=matched_tags, reason="all tags matched")
        if not matched_tags:
            return SignalMatchResult(False, reason="no required tags matched")
        return SignalMatchResult(True, matched_tags=matched_tags, reason="tag matched")

    if required_type:
        return SignalMatchResult(True, reason="event type matched")

    return SignalMatchResult(False, reason="no target signal")
