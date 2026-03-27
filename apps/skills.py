from flask import jsonify

from gabru.flask.app import App
from model.skill import Skill
from processes.skill_xp_processor import SkillXPProcessor
from services.skill_level_history import SkillLevelHistoryService
from services.skills import SkillService


class SkillsApp(App[Skill]):
    def __init__(self):
        self.skill_service = SkillService()
        self.skill_history_service = SkillLevelHistoryService()
        super().__init__(
            "Skills",
            service=self.skill_service,
            model_class=Skill,
            widget_type="skill_tree",
            widget_recent_limit=5,
        )

    def widget_data(self):
        if not self.widget_enabled:
            return None, None

        skills = self.skill_service.get_all()
        history = self.skill_history_service.get_recent_history(limit=self.widget_recent_limit)
        progress_rings = [
            self.skill_service.get_progress_snapshot(skill)
            for skill in sorted(skills, key=lambda item: (-item.total_xp, item.name.lower()))
        ]

        return {
            "progress_rings": progress_rings[:4],
            "history": [item.dict() for item in history],
        }, self.model_class_attributes


skills_app = SkillsApp()
skills_app.register_process(SkillXPProcessor, enabled=True)


@skills_app.blueprint.route('/history', methods=['GET'])
def get_skill_history():
    history = skills_app.skill_history_service.get_recent_history(limit=25)
    return jsonify([item.dict() for item in history]), 200
