from typing import Optional

from gabru.qprocessor.qprocessor import QueueProcessor
from model.event import Event
from services.events import EventService
from services.report_aggregator import ReportAggregator


class ReportProcessor(QueueProcessor[Event]):
    def __init__(self, **kwargs):
        self.event_service = EventService()
        self.report_aggregator = ReportAggregator()
        super().__init__(service=self.event_service, **kwargs)

    def filter_item(self, event: Event) -> Optional[Event]:
        return event if event.event_type == "report:generate_requested" else None

    def _process_item(self, event: Event) -> bool:
        from model.event import Event as EventModel

        report_type, anchor_date = self.report_aggregator.parse_request_payload(event.description, event.tags)
        report = self.report_aggregator.build_and_store_report(report_type, anchor_date)
        created_event = EventModel(
            event_type="report:generated",
            timestamp=report.generated_at,
            description=f"{report.title} generated with integrity score {report.integrity_score}",
            tags=[
                "report",
                f"report_type:{report.report_type}",
                f"anchor_date:{report.anchor_date}",
                "notification",
            ],
        )
        self.event_service.create(created_event)
        return True
