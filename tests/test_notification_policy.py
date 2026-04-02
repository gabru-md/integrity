import os
import unittest
from datetime import datetime
from unittest import mock

os.environ.setdefault("LOG_DIR", "/tmp/rasbhari-test-logs")

from gabru.qprocessor.qprocessor import QueueProcessor
from model.event import Event
from processes.courier.courier import Courier
from services.notification_policy import resolve_notification_class, resolve_notification_intent


class NotificationPolicyTests(unittest.TestCase):
    def test_resolve_notification_class_prefers_explicit_tag(self):
        notification_class = resolve_notification_class(["notification", "notification_class:urgent"], "report:generated")
        self.assertEqual(notification_class, "urgent")

    def test_resolve_notification_class_falls_back_from_event_type(self):
        self.assertEqual(resolve_notification_class(["notification"], "report:generated"), "review")
        self.assertEqual(resolve_notification_class(["notification"], "skill:level_up"), "today")

    def test_resolve_notification_intent_maps_email_and_title(self):
        event = Event(
            user_id=1,
            event_type="system:alert",
            description="Database reconnect failed twice",
            timestamp=datetime(2026, 4, 2, 9, 0, 0),
            tags=["notification", "notification_class:system", "email"],
        )
        intent = resolve_notification_intent(event)
        self.assertEqual(intent.notification_class, "system")
        self.assertEqual(intent.delivery_channel, "email")
        self.assertEqual(intent.title, "Database reconnect failed twice")


class QueueProcessorDefaultNameTests(unittest.TestCase):
    def test_queue_processor_uses_class_name_by_default(self):
        class ExampleProcessor(QueueProcessor[Event]):
            def filter_item(self, item):
                return item

            def _process_item(self, next_item):
                return True

        with mock.patch("gabru.qprocessor.qprocessor.QueueService"):
            processor = ExampleProcessor(service=mock.Mock(), enabled=False)

        self.assertEqual(processor.name, "ExampleProcessor")


class CourierNotificationTests(unittest.TestCase):
    def setUp(self):
        patchers = [
            mock.patch("processes.courier.courier.EventService"),
            mock.patch("processes.courier.courier.NotificationService"),
            mock.patch("processes.courier.courier.UserService"),
            mock.patch("gabru.qprocessor.qprocessor.QueueService"),
        ]
        self.addCleanup(mock.patch.stopall)
        for patcher in patchers:
            patcher.start()

        self.courier = Courier(enabled=False)
        self.courier.log = mock.Mock()

    def test_send_ntfy_uses_class_aware_headers(self):
        event = Event(
            id=10,
            user_id=1,
            event_type="report:generated",
            description="Weekly review ready",
            timestamp=datetime(2026, 4, 2, 9, 0, 0),
            tags=["notification", "notification_class:review", "report"],
        )
        self.courier.get_ntfy_url_for_event = mock.Mock(return_value="https://ntfy.example/topic")

        response = mock.Mock(status_code=200)
        with mock.patch("processes.courier.courier.requests.post", return_value=response) as post_mock:
            self.assertTrue(self.courier.send_ntfy_notification(event, "review", "Weekly review ready"))

        headers = post_mock.call_args.kwargs["headers"]
        self.assertEqual(headers["Title"], "Weekly review ready")
        self.assertEqual(headers["Priority"], "3")
        self.assertIn("memo,mag", headers["Tags"])


if __name__ == "__main__":
    unittest.main()
