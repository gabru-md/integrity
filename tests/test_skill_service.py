import os
import unittest

os.environ.setdefault("LOG_DIR", "/tmp/rasbhari-test-logs")

from model.skill import Skill
from services.skills import SkillService


class SkillServiceLogicTests(unittest.TestCase):
    def test_normalize_skill_tag_strips_case_prefix_and_symbols(self):
        self.assertEqual(SkillService.normalize_skill_tag("  #Py_thon!! "), "python")

    def test_get_match_keys_uses_name_tag_key_and_aliases(self):
        skill = Skill(name="System Design", tag_key="system_design", aliases=["Architecture", "sys-design"])
        self.assertEqual(
            SkillService.get_match_keys(skill),
            {"systemdesign", "architecture", "sysdesign"},
        )

    def test_get_progress_snapshot_derives_level_progress_and_remaining_xp(self):
        skill = Skill(name="Python", tag_key="python", total_xp=250, requirement="Ship one more feature")
        snapshot = SkillService.get_progress_snapshot(skill)

        self.assertEqual(snapshot["level"], 2)
        self.assertEqual(snapshot["xp_into_level"], 150)
        self.assertEqual(snapshot["xp_for_next_level"], 200)
        self.assertEqual(snapshot["progress_percent"], 75)
        self.assertEqual(snapshot["xp_remaining"], 50)


if __name__ == "__main__":
    unittest.main()
