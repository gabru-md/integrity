import os
import unittest
from unittest import mock

os.environ.setdefault("LOG_DIR", "/tmp/rasbhari-test-logs")

from model.activity import Activity
from model.event import Event
from services.activities import ActivityService
from services.report_aggregator import ReportAggregator


class EventPayloadSupportTests(unittest.TestCase):
    def test_report_request_payload_prefers_structured_event_payload(self):
        aggregator = ReportAggregator()

        user_id, report_type, anchor_date = aggregator.parse_request_payload(
            {"user_id": 7, "report_type": "weekly", "anchor_date": "2026-04-07"},
            "Queued weekly report generation",
            ["report"],
        )

        self.assertEqual(user_id, 7)
        self.assertEqual(report_type, "weekly")
        self.assertEqual(anchor_date, "2026-04-07")

    def test_activity_trigger_creates_event_with_structured_payload(self):
        with mock.patch.object(ActivityService, "_ensure_schema", return_value=None), \
             mock.patch("services.activities.EventService") as event_service_cls:
            service = ActivityService()
            created_events = []
            event_service_cls.return_value.create.side_effect = lambda event: created_events.append(event) or 99
            service.event_service = event_service_cls.return_value
            service.get_by_id = mock.Mock(return_value=Activity(
                id=3,
                user_id=4,
                name="Research Capture",
                event_type="research:captured",
                description="Saved browser research",
                tags=["research"],
                default_payload={"source": "browser", "url": "https://example.com"},
            ))

            result = service.trigger_activity(3, override_payload={
                "title": "Interesting Page",
                "tags": ["important"],
                "description": "Saved important page",
            })

        self.assertEqual(result, 3)
        self.assertEqual(len(created_events), 1)
        created_event = created_events[0]
        self.assertIsInstance(created_event, Event)
        self.assertEqual(created_event.description, "Saved important page")
        self.assertEqual(set(created_event.tags), {"research", "important", "triggered_by:activity:Research Capture"})
        self.assertEqual(created_event.payload, {
            "source": "browser",
            "url": "https://example.com",
            "title": "Interesting Page",
        })


if __name__ == "__main__":
    unittest.main()
