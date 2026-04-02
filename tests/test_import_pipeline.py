import os
import unittest
from datetime import datetime

os.environ.setdefault("LOG_DIR", "/tmp/rasbhari-test-logs")

from services.import_pipeline import ImportBatchResult, ImportPipelineService, NormalizedImportItem


class FakeImportRecordService:
    def __init__(self):
        self.records = []

    def create(self, record):
        record.id = len(self.records) + 1
        self.records.append(record)
        return record.id

    def update(self, record):
        return True

    def get_by_source_key(self, *, user_id, source_type, source_name, external_id):
        for record in self.records:
            if (
                record.user_id == user_id
                and record.source_type == source_type
                and record.source_name == source_name
                and record.external_id == external_id
            ):
                return record
        return None

    def get_by_fingerprint(self, *, user_id, source_type, source_name, fingerprint):
        for record in self.records:
            if (
                record.user_id == user_id
                and record.source_type == source_type
                and record.source_name == source_name
                and record.fingerprint == fingerprint
            ):
                return record
        return None


class FakeEventService:
    def __init__(self):
        self.events = []

    def create(self, event):
        self.events.append(event)
        return len(self.events)


class FakeCalendarAdapter:
    def fetch_records(self, user_id, since=None):
        return [
            NormalizedImportItem(
                source_type="Calendar",
                source_name="Work Calendar",
                external_id="evt-1",
                occurred_at=datetime(2026, 4, 2, 9, 0, 0),
                title="Team sync",
                description="Weekly team sync",
                tags=["meeting", "calendar"],
                raw_payload={"source": "calendar", "id": "evt-1"},
                normalized_event_type="calendar:event",
            ),
            NormalizedImportItem(
                source_type="Calendar",
                source_name="Work Calendar",
                external_id="evt-1",
                occurred_at=datetime(2026, 4, 2, 9, 0, 0),
                title="Team sync",
                description="Weekly team sync",
                tags=["meeting", "calendar"],
                raw_payload={"source": "calendar", "id": "evt-1"},
                normalized_event_type="calendar:event",
            ),
        ]


class ImportPipelineTests(unittest.TestCase):
    def setUp(self):
        self.record_service = FakeImportRecordService()
        self.event_service = FakeEventService()
        self.pipeline = ImportPipelineService(
            import_record_service=self.record_service,
            event_service=self.event_service,
        )

    def test_normalizes_source_and_emits_import_tags(self):
        item = NormalizedImportItem(
            source_type="Device Feed",
            source_name="Home Presence",
            external_id="abc-1",
            occurred_at=datetime(2026, 4, 2, 8, 0, 0),
            title="Phone seen",
            tags=["presence", "home"],
            raw_payload={},
            normalized_event_type="presence:seen",
        )
        record = self.pipeline._to_import_record(user_id=7, item=item)
        tags = self.pipeline.build_event_tags(record)

        self.assertEqual(record.source_type, "device-feed")
        self.assertEqual(record.source_name, "home-presence")
        self.assertIn("imported", tags)
        self.assertIn("source:device-feed", tags)
        self.assertIn("source_name:home-presence", tags)
        self.assertIn("presence", tags)

    def test_import_from_adapter_dedupes_and_emits_once(self):
        result = self.pipeline.import_from_adapter(user_id=7, adapter=FakeCalendarAdapter(), emit_events=True)

        self.assertEqual(result.fetched, 2)
        self.assertEqual(result.imported, 1)
        self.assertEqual(result.skipped, 1)
        self.assertEqual(result.emitted_events, 1)
        self.assertEqual(self.event_service.events[0].event_type, "calendar:event")
        self.assertIn("source:calendar", self.event_service.events[0].tags)


if __name__ == "__main__":
    unittest.main()
