import os
import unittest
from unittest import mock

os.environ.setdefault("LOG_DIR", "/tmp/rasbhari-test-logs")

from model.event import Event
from services import eventing


class EmitEventSafelyTests(unittest.TestCase):
    def test_emit_event_returns_created_id(self):
        fake_log = mock.Mock()
        fake_service = mock.Mock()
        fake_service.create.return_value = 11

        with mock.patch.object(eventing, "get_event_service", return_value=fake_service):
            created_id = eventing.emit_event_safely(
                fake_log,
                user_id=7,
                event_type="project:updated",
                timestamp="2026-04-02T12:00:00",
                description="Updated project",
                tags=["project"],
            )

        self.assertEqual(created_id, 11)
        created_event = fake_service.create.call_args.args[0]
        self.assertIsInstance(created_event, Event)
        self.assertEqual(created_event.event_type, "project:updated")

    def test_emit_event_logs_and_returns_none_on_failure(self):
        fake_log = mock.Mock()
        fake_service = mock.Mock()
        fake_service.create.side_effect = RuntimeError("db down")

        with mock.patch.object(eventing, "get_event_service", return_value=fake_service):
            created_id = eventing.emit_event_safely(
                fake_log,
                user_id=7,
                event_type="project:updated",
                timestamp="2026-04-02T12:00:00",
                description="Updated project",
                tags=["project"],
            )

        self.assertIsNone(created_id)
        fake_log.warning.assert_called_once()


if __name__ == "__main__":
    unittest.main()
