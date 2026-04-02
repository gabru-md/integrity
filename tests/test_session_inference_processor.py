import os
import unittest
from datetime import datetime, timedelta
from unittest import mock

os.environ.setdefault("LOG_DIR", "/tmp/rasbhari-test-logs")

from model.event import Event
from processes.session_inference_processor import SessionInferenceProcessor


class SessionInferenceProcessorTests(unittest.TestCase):
    def setUp(self):
        with mock.patch("processes.session_inference_processor.EventService"), \
             mock.patch("gabru.qprocessor.qprocessor.QueueService"):
            self.processor = SessionInferenceProcessor(enabled=False)
        self.processor.log = mock.Mock()

    def test_infer_session_type_matches_known_apps(self):
        self.assertEqual(self.processor.infer_session_type("pycharm"), "coding")
        self.assertEqual(self.processor.infer_session_type("logseq"), "planning")
        self.assertEqual(self.processor.infer_session_type("google-chrome"), "research")
        self.assertIsNone(self.processor.infer_session_type("spotify"))

    def test_app_open_and_close_emit_session_boundaries(self):
        start = datetime(2026, 4, 2, 9, 0, 0)
        opened = Event(user_id=7, event_type="local:app:opened", timestamp=start, tags=["app:pycharm"])
        closed = Event(user_id=7, event_type="local:app:closed", timestamp=start + timedelta(minutes=42), tags=["app:pycharm"])

        with mock.patch("processes.session_inference_processor.emit_event_safely") as emit_mock:
            self.processor._process_item(opened)
            self.processor._process_item(closed)

        self.assertEqual(emit_mock.call_count, 2)
        self.assertEqual(emit_mock.call_args_list[0].kwargs["event_type"], "coding:session:start")
        self.assertEqual(emit_mock.call_args_list[1].kwargs["event_type"], "coding:session:end")
        self.assertIn("reason:apps_closed", emit_mock.call_args_list[1].kwargs["tags"])

    def test_idle_event_ends_active_session(self):
        start = datetime(2026, 4, 2, 9, 0, 0)
        opened = Event(user_id=7, event_type="local:app:opened", timestamp=start, tags=["app:logseq"])
        idle = Event(user_id=7, event_type="local:user:idle", timestamp=start + timedelta(minutes=8), tags=[])

        with mock.patch("processes.session_inference_processor.emit_event_safely") as emit_mock:
            self.processor._process_item(opened)
            self.processor._process_item(idle)

        self.assertEqual(emit_mock.call_args_list[0].kwargs["event_type"], "planning:session:start")
        self.assertEqual(emit_mock.call_args_list[1].kwargs["event_type"], "planning:session:end")
        self.assertIn("reason:idle", emit_mock.call_args_list[1].kwargs["tags"])

    def test_context_switch_ends_previous_session_before_starting_new_one(self):
        start = datetime(2026, 4, 2, 9, 0, 0)
        coding_event = Event(user_id=7, event_type="local:app:opened", timestamp=start, tags=["app:pycharm"])
        planning_event = Event(user_id=7, event_type="local:app:opened", timestamp=start + timedelta(minutes=10), tags=["app:logseq"])

        with mock.patch("processes.session_inference_processor.emit_event_safely") as emit_mock:
            self.processor._process_item(coding_event)
            self.processor._process_item(planning_event)

        emitted_types = [call.kwargs["event_type"] for call in emit_mock.call_args_list]
        self.assertEqual(emitted_types, ["coding:session:start", "coding:session:end", "planning:session:start"])
        self.assertIn("reason:context_switch", emit_mock.call_args_list[1].kwargs["tags"])


if __name__ == "__main__":
    unittest.main()
