import os
import unittest
from datetime import datetime, timezone
from unittest import mock

os.environ.setdefault("LOG_DIR", "/tmp/rasbhari-test-logs")

from model.event import Event
from model.promise import Promise
from processes.promise_processor import PromiseProcessor


class PromiseProcessorProjectWorkTests(unittest.TestCase):
    def setUp(self):
        patchers = [
            mock.patch("processes.promise_processor.PromiseService"),
            mock.patch("processes.promise_processor.EventService"),
            mock.patch("gabru.qprocessor.qprocessor.QueueService"),
        ]
        self.addCleanup(mock.patch.stopall)
        for patcher in patchers:
            patcher.start()

        self.processor = PromiseProcessor(enabled=False)

    def test_event_matches_project_target_from_project_work_tags(self):
        event = Event(
            id=10,
            user_id=1,
            event_type="kanban:ticket_moved",
            description="Moved ticket",
            timestamp=datetime(2026, 4, 2, 10, 0, 0),
            tags=["kanban", "project_work", "project:rasbhari", "project_work:rasbhari", "ticket_state:in_progress"],
        )
        promise = Promise(
            id=4,
            user_id=1,
            name="Advance Rasbhari project",
            description="",
            frequency="daily",
            target_event_type="project:rasbhari",
            required_count=1,
        )

        self.assertTrue(self.processor._event_matches_promise(event, promise))

    def test_count_matching_events_supports_project_target_event_type(self):
        promise = Promise(
            id=4,
            user_id=1,
            name="Advance Rasbhari project",
            description="",
            frequency="daily",
            target_event_type="project:rasbhari",
            required_count=1,
        )
        matching_event = Event(
            id=10,
            user_id=1,
            event_type="kanban:ticket_moved",
            description="Moved ticket",
            timestamp=datetime(2026, 4, 2, 10, 0, 0),
            tags=["project_work:rasbhari"],
        )
        non_matching_event = Event(
            id=11,
            user_id=1,
            event_type="kanban:ticket_moved",
            description="Moved another ticket",
            timestamp=datetime(2026, 4, 2, 11, 0, 0),
            tags=["project_work:other-project"],
        )
        self.processor.event_service.find_all = mock.Mock(return_value=[matching_event, non_matching_event])

        count = self.processor._count_matching_events(
            promise,
            datetime(2026, 4, 2, 9, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 4, 2, 12, 0, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(count, 1)
        self.processor.event_service.find_all.assert_called_once()
        filters = self.processor.event_service.find_all.call_args.kwargs["filters"]
        self.assertNotIn("event_type", filters)


if __name__ == "__main__":
    unittest.main()
