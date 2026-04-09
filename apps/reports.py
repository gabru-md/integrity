from datetime import datetime

from flask import jsonify, request

from apps.user_docs import build_app_user_guidance
from gabru.auth import PermissionManager, write_access_required
from gabru.flask.app import App
from gabru.flask.util import render_flask_template
from model.event import Event
from model.report import Report
from processes.report_processor import ReportProcessor
from services.events import EventService
from services.notifications import NotificationService
from services.report_aggregator import ReportAggregator
from services.reports import ReportService


class ReportsApp(App[Report]):
    def __init__(self):
        self.report_service = ReportService()
        self.event_service = EventService()
        self.notification_service = NotificationService()
        self.report_aggregator = ReportAggregator()
        super().__init__(
            name="Reports",
            service=self.report_service,
            model_class=Report,
            home_template="reports.html",
            get_recent_limit=20,
            widget_type="basic",
            widget_recent_limit=3,
            user_guidance=build_app_user_guidance("Reports"),
        )
        self.register_process(ReportProcessor, enabled=True)

    def setup_home_route(self):
        @self.blueprint.route('/home')
        def home():
            reports = self.service.get_recent_items(12)
            return render_flask_template(
                self.home_template,
                model_class_attributes=self.model_class_attributes,
                model_class_name=self.model_class.__name__,
                app_name=self.name,
                user_guidance=self.user_guidance,
                reports=reports,
                today=datetime.now().date().isoformat(),
            )

        @self.blueprint.route('/generate', methods=['POST'])
        @write_access_required
        def generate_report():
            data = request.json or {}
            report_type = (data.get("report_type") or "daily").lower()
            anchor_date = data.get("anchor_date")
            async_mode = data.get("async_mode", True)
            user_id = PermissionManager.get_current_user_id()

            if async_mode:
                request_event = Event(
                    user_id=user_id,
                    event_type="report:generate_requested",
                    timestamp=datetime.now(),
                    description=f"Queued {report_type} report generation",
                    tags=[
                        "report",
                        f"report_type:{report_type}",
                        f"anchor_date:{anchor_date or datetime.now().date().isoformat()}",
                        f"user_id:{user_id}",
                    ],
                    payload={
                        "user_id": user_id,
                        "report_type": report_type,
                        "anchor_date": anchor_date or datetime.now().date().isoformat(),
                    },
                )
                event_id = self.event_service.create(request_event)
                if user_id:
                    self.notification_service.create_in_app_notification(
                        user_id=user_id,
                        title="Report generation started",
                        body=f"{report_type.title()} report is queued now. Rasbhari will let you know when it is ready.",
                        href="/reports/home",
                        notification_class="review",
                    )
                return jsonify({
                    "message": "Report generation queued",
                    "event_id": event_id,
                    "report_type": report_type,
                    "anchor_date": anchor_date,
                }), 202

            report = self.report_aggregator.build_and_store_report(report_type, anchor_date, user_id=user_id)
            self.event_service.create(Event(
                user_id=user_id,
                event_type="report:generated",
                timestamp=report.generated_at,
                description=f"{report.title} generated with integrity score {report.integrity_score}",
                tags=[
                    "report",
                    f"report_type:{report.report_type}",
                    f"anchor_date:{report.anchor_date}",
                    f"user_id:{user_id}",
                ],
            ))
            return jsonify(report.dict()), 201

        @self.blueprint.route('/<int:report_id>/view', methods=['GET'])
        def view_report(report_id):
            report = self.service.get_by_id(report_id)
            if not report:
                return "Report not found", 404
            return render_flask_template("report_detail.html", report=report)

        @self.blueprint.route('/<int:report_id>/print', methods=['GET'])
        def print_report(report_id):
            report = self.service.get_by_id(report_id)
            if not report:
                return "Report not found", 404
            return render_flask_template("report_print.html", report=report)


reports_app = ReportsApp()
