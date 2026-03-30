import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest import mock


SCRIPT_PATH = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "rasbhari_mac_agent.py"
SPEC = importlib.util.spec_from_file_location("rasbhari_mac_agent", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class RasbhariMacAgentTests(unittest.TestCase):
    def test_normalize_rule_applies_defaults(self):
        rule = MODULE.normalize_rule(
            {
                "app_name": "Netflix",
                "trigger": "opened",
                "event_type": "entertainment:netflix",
            }
        )
        self.assertEqual(rule["app_name"], "Netflix")
        self.assertEqual(rule["trigger"], "opened")
        self.assertEqual(rule["event_type"], "entertainment:netflix")
        self.assertEqual(rule["cooldown_seconds"], 300)
        self.assertTrue(rule["enabled"])
        self.assertTrue(rule["id"])

    def test_slugify_normalizes_names(self):
        self.assertEqual(MODULE.slugify("PyCharm CE"), "pycharm-ce")
        self.assertEqual(MODULE.slugify("Netflix"), "netflix")

    def test_prompt_choice_returns_default(self):
        with mock.patch("builtins.input", return_value=""):
            value = MODULE.prompt_choice("Trigger", ["opened", "closed"], "opened")
        self.assertEqual(value, "opened")

    def test_prompt_int_retries_until_valid(self):
        with mock.patch("builtins.input", side_effect=["bad", "",]):
            value = MODULE.prompt_int("Cooldown", 300)
        self.assertEqual(value, 300)

    def test_post_event_sends_comma_separated_tags(self):
        config = {
            "rasbhari_url": "http://localhost:5000",
            "api_key": "abc123",
            "machine_name": "gabru-md.home",
        }
        rule = {
            "event_type": "mac:pycharm:open",
            "description": "Opened {app_name}",
            "trigger": "opened",
            "tags": ["python", "projects"],
        }

        class DummyResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        with mock.patch("urllib.request.urlopen", return_value=DummyResponse()) as urlopen_mock:
            MODULE.post_event(config, rule, "pycharm")

        request = urlopen_mock.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(
            payload["tags"],
            "python, projects, source:mac_agent, app:pycharm, machine:gabru-md-home",
        )

    def test_cleanup_stale_pid_removes_dead_process_file(self):
        with mock.patch.object(MODULE, "is_process_running", return_value=False):
            with tempfile.TemporaryDirectory() as temp_dir:
                pid_path = pathlib.Path(temp_dir) / "agent.pid"
                pid_path.write_text("12345", encoding="utf-8")
                MODULE.cleanup_stale_pid(pid_path)
                self.assertFalse(pid_path.exists())

    def test_cleanup_stale_pid_keeps_live_process_file(self):
        with mock.patch.object(MODULE, "is_process_running", return_value=True):
            with tempfile.TemporaryDirectory() as temp_dir:
                pid_path = pathlib.Path(temp_dir) / "agent.pid"
                pid_path.write_text("12345", encoding="utf-8")
                MODULE.cleanup_stale_pid(pid_path)
                self.assertTrue(pid_path.exists())


if __name__ == "__main__":
    unittest.main()
