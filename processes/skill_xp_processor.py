from datetime import datetime
from typing import Optional

from gabru.qprocessor.qprocessor import QueueProcessor
from model.event import Event
from model.skill_level_history import SkillLevelHistory
from services.events import EventService
from services.skill_level_history import SkillLevelHistoryService
from services.skills import SkillService


class SkillXPProcessor(QueueProcessor[Event]):
    def __init__(self, xp_per_match: int = 20, **kwargs):
        self.event_service = EventService()
        self.skill_service = SkillService()
        self.skill_history_service = SkillLevelHistoryService()
        self.xp_per_match = xp_per_match
        super().__init__(service=self.event_service, **kwargs)

    def filter_item(self, event: Event) -> Optional[Event]:
        if event.event_type == "skill:level_up":
            return None
        return event if event.tags else None

    def _process_item(self, event: Event) -> bool:
        normalized_tags = {
            self.skill_service.normalize_skill_tag(tag)
            for tag in (event.tags or [])
            if tag and self.skill_service.normalize_skill_tag(tag)
        }
        if not normalized_tags:
            return True

        skills = self.skill_service.get_all()
        if not skills:
            return True

        matched_skills = [
            skill for skill in skills
            if self.skill_service.normalize_skill_tag(skill.name) in normalized_tags
        ]
        if not matched_skills:
            return True

        for skill in matched_skills:
            old_level = self.skill_service.derive_level(skill.total_xp)
            skill.total_xp += self.xp_per_match
            skill.level = self.skill_service.derive_level(skill.total_xp)
            self.skill_service.update(skill)

            if skill.level > old_level:
                self._record_level_ups(skill, old_level, event.timestamp or datetime.now())

            self.log.info(
                f"Awarded {self.xp_per_match} XP to {skill.name} from event {event.id}. "
                f"New total: {skill.total_xp}, level: {skill.level}"
            )

        return True

    def _record_level_ups(self, skill, old_level: int, reached_at: datetime):
        for new_level in range(old_level + 1, skill.level + 1):
            summary = f"Reached Level {new_level} in {skill.name}"
            history_item = SkillLevelHistory(
                skill_id=skill.id,
                skill_name=skill.name,
                level=new_level,
                total_xp=skill.total_xp,
                reached_at=reached_at,
                summary=summary,
            )
            self.skill_history_service.create(history_item)

            level_up_event = Event(
                event_type="skill:level_up",
                timestamp=reached_at,
                description=summary,
                tags=[
                    "notification",
                    "skill",
                    "level_up",
                    f"skill:{self.skill_service.normalize_skill_tag(skill.name)}",
                    f"skill:level:{new_level}",
                ],
            )
            self.event_service.create(level_up_event)
