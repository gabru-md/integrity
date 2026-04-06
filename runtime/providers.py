from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Optional

from flask import has_request_context
from gabru.auth import PermissionManager
from gabru.contracts import (
    AdminOpsProvider,
    AppStatusStore,
    AssistantCommandProvider,
    AuthProvider,
    AuthenticatedUser,
    DashboardDataProvider,
    TimelineEventView,
)
from gabru.qprocessor.qservice import QueueService
from services.applications import ApplicationService
from services.dependency_health import DependencyHealthService
from services.devices import DeviceService
from services.events import EventService
from services.notifications import NotificationService
from services.assistant_command import AssistantCommandService
from services.skill_level_history import SkillLevelHistoryService
from services.skills import SkillService
from services.timeline import TimelineService
from services.activities import ActivityService
from services.admin_updates import AdminUpdateService
from services.connections import ConnectionService
from services.kanban_tickets import KanbanTicketService
from services.projects import ProjectService
from services.promises import PromiseService
from services.recommendation_followups import RecommendationFollowUpService
from services.reports import ReportService
from services.users import UserService


class RasbhariAuthProvider(AuthProvider):
    def __init__(self, user_service: Optional[UserService] = None):
        self.user_service = user_service or UserService()

    def authenticate_credentials(self, username: str, password: str) -> Optional[AuthenticatedUser]:
        user = self.user_service.authenticate(username, password)
        return self._to_authenticated_user(user)

    def authenticate_api_key(self, api_key: str) -> Optional[AuthenticatedUser]:
        user = self.user_service.authenticate_api_key(api_key)
        return self._to_authenticated_user(user)

    def get_by_username(self, username: str):
        return self.user_service.get_by_username(username)

    def create_user(
        self,
        username: str,
        display_name: str,
        password: str,
        is_admin: bool,
        is_active: bool,
        is_approved: bool,
    ) -> Optional[AuthenticatedUser]:
        from model.user import User

        user = User(
            username=username,
            display_name=display_name or username,
            password=password,
            is_admin=is_admin,
            is_active=is_active,
            is_approved=is_approved,
        )
        user_id = self.user_service.create(user)
        if not user_id:
            return None
        user.id = user_id
        refreshed = self.user_service.get_by_id(user_id) or user
        return self._to_authenticated_user(refreshed)

    def count_users(self) -> int:
        return self.user_service.count()

    @staticmethod
    def _to_authenticated_user(user) -> Optional[AuthenticatedUser]:
        if not user:
            return None
        return AuthenticatedUser(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            is_admin=user.is_admin,
            api_key=getattr(user, "api_key", None),
            onboarding_completed=getattr(user, "onboarding_completed", False),
            experience_mode=getattr(user, "experience_mode", "everyday") or "everyday",
        )


class RasbhariAppStatusStore(AppStatusStore):
    def __init__(self, application_service: Optional[ApplicationService] = None):
        self.application_service = application_service or ApplicationService()

    def get_app_state(self, app_name: str) -> Optional[bool]:
        db_app = self.application_service.get_by_name(app_name)
        if not db_app:
            return None
        return db_app.is_active

    def set_app_state(self, app_name: str, is_active: bool) -> bool:
        return self.application_service.set_active_status(app_name, is_active)


class RasbhariAdminOpsProvider(AdminOpsProvider):
    def __init__(self, admin_update_service: Optional[AdminUpdateService] = None):
        self.admin_update_service = admin_update_service or AdminUpdateService()

    def get_update_status(self) -> dict[str, object]:
        return self.admin_update_service.get_update_status()

    def trigger_update(self, actor_username: Optional[str] = None) -> dict[str, object]:
        return self.admin_update_service.trigger_update(actor_username=actor_username)


class RasbhariDashboardDataProvider(DashboardDataProvider):
    def __init__(
        self,
        event_service: Optional[EventService] = None,
        notification_service: Optional[NotificationService] = None,
        device_service: Optional[DeviceService] = None,
        queue_service: Optional[QueueService] = None,
        skill_history_service: Optional[SkillLevelHistoryService] = None,
        skill_service: Optional[SkillService] = None,
        timeline_service: Optional[TimelineService] = None,
        promise_service: Optional[PromiseService] = None,
        connection_service: Optional[ConnectionService] = None,
        activity_service: Optional[ActivityService] = None,
        project_service: Optional[ProjectService] = None,
        kanban_ticket_service: Optional[KanbanTicketService] = None,
        report_service: Optional[ReportService] = None,
        recommendation_followup_service: Optional[RecommendationFollowUpService] = None,
        user_service: Optional[UserService] = None,
    ):
        self.event_service = event_service or EventService()
        self.notification_service = notification_service or NotificationService()
        self.device_service = device_service or DeviceService()
        self.queue_service = queue_service or QueueService()
        self.skill_history_service = skill_history_service or SkillLevelHistoryService()
        self.skill_service = skill_service or SkillService()
        self.timeline_service = timeline_service or TimelineService()
        self.promise_service = promise_service or PromiseService()
        self.connection_service = connection_service or ConnectionService()
        self.activity_service = activity_service or ActivityService()
        self.project_service = project_service or ProjectService()
        self.kanban_ticket_service = kanban_ticket_service or KanbanTicketService()
        self.report_service = report_service or ReportService()
        self.user_service = user_service
        self.recommendation_followup_service = recommendation_followup_service or RecommendationFollowUpService(
            project_service=self.project_service,
            kanban_ticket_service=self.kanban_ticket_service,
            promise_service=self.promise_service,
            skill_service=self.skill_service,
        )

    def get_today_data(self) -> dict[str, object]:
        promise_index = self._build_promise_index()
        skill_index = self._build_skill_index()
        active_projects = self.project_service.find_all(filters={"state": "Active"}, sort_by={"last_updated": "DESC"})
        active_project_ids = [project.id for project in active_projects if project.id is not None]

        active_work = []
        prioritized_work = []
        for project in active_projects:
            tickets = self.kanban_ticket_service.get_by_project_id(project.id, include_archived=False)
            project_summary = {
                "id": project.id,
                "name": project.name,
                "state": project.state,
                "last_updated": project.last_updated.isoformat() if project.last_updated else None,
                "progress_count": project.progress_count,
                "href": f"/projects/{project.id}/board",
            }
            for ticket in tickets:
                shared_tags = self._build_project_shared_tags(project)
                linked_promises = self._match_promises_for_tags(shared_tags, promise_index)
                linked_skills = self._match_skills_for_tags(shared_tags, skill_index)
                ticket_data = {
                    "id": ticket.id,
                    "project_id": project.id,
                    "project_name": project.name,
                    "ticket_code": ticket.ticket_code,
                    "title": ticket.title,
                    "description": ticket.description,
                    "state": ticket.state.value if hasattr(ticket.state, "value") else ticket.state,
                    "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
                    "state_changed_at": ticket.state_changed_at.isoformat() if ticket.state_changed_at else None,
                    "href": f"/projects/{project.id}/board",
                    "focus_tags": shared_tags,
                    "linked_promises": linked_promises,
                    "linked_skills": linked_skills,
                    "contribution_summary": self._build_contribution_summary(linked_promises, linked_skills),
                }
                if ticket_data["state"] == "in_progress":
                    active_work.append(ticket_data)
                elif ticket_data["state"] == "prioritized":
                    prioritized_work.append(ticket_data)

        due_promises = []
        for promise in self.promise_service.get_due_promises():
            due_promises.append({
                "id": promise.id,
                "name": promise.name,
                "description": promise.description,
                "frequency": promise.frequency,
                "next_check_at": promise.next_check_at.isoformat() if promise.next_check_at else None,
                "streak": promise.streak,
                "status": promise.status,
                "href": "/promises/home",
            })

        neglected_connections = []
        now = datetime.now()
        for connection in self.connection_service.get_active():
            if connection.last_contact_at is None:
                days_since_contact = None
                overdue_days = connection.cadence_days
            else:
                days_since_contact = max(0, (now - connection.last_contact_at).days)
                overdue_days = days_since_contact - connection.cadence_days
            if overdue_days >= 0:
                neglected_connections.append({
                    "id": connection.id,
                    "name": connection.name,
                    "priority": connection.priority,
                    "relationship_type": connection.relationship_type,
                    "cadence_days": connection.cadence_days,
                    "days_since_contact": days_since_contact,
                    "overdue_days": overdue_days,
                    "href": "/connections/home",
                })
        neglected_connections.sort(key=lambda item: (-self._priority_rank(item["priority"]), -item["overdue_days"], item["name"]))

        suggested_activities = []
        for activity in self.activity_service.get_recent_items(6):
            suggested_activities.append({
                "id": activity.id,
                "name": activity.name,
                "event_type": activity.event_type,
                "description": activity.description,
                "tags": activity.tags or [],
                "href": "/activities/home",
            })

        latest_report = next(iter(self.report_service.get_recent_items(1)), None)
        report_summary = None
        if latest_report:
            report_summary = {
                "title": latest_report.title,
                "headline": latest_report.headline,
                "integrity_score": latest_report.integrity_score,
                "generated_at": latest_report.generated_at.isoformat() if latest_report.generated_at else None,
                "href": f"/reports/{latest_report.id}/view" if latest_report.id else "/reports/home",
            }

        recent_events_today = self.event_service.find_all(
            filters={"timestamp": {"$gt": datetime(now.year, now.month, now.day)}},
            sort_by={"timestamp": "DESC"},
        )
        guidance = self._build_today_guidance(
            active_work=active_work,
            prioritized_work=prioritized_work,
            due_promises=due_promises,
            neglected_connections=neglected_connections,
            suggested_activities=suggested_activities,
            active_projects=active_projects,
            report_summary=report_summary,
            recent_events_today=recent_events_today,
        )
        setup_checklist = self._build_setup_checklist()
        recommended_follow_ups = self._get_recommended_follow_ups(active_projects=active_projects)

        return {
            "active_work": active_work[:6],
            "prioritized_work": prioritized_work[:6],
            "due_promises": due_promises[:5],
            "neglected_connections": neglected_connections[:5],
            "suggested_activities": suggested_activities[:4],
            "guidance": guidance,
            "setup_checklist": setup_checklist,
            "recommended_follow_ups": recommended_follow_ups,
            "active_project_count": len(active_project_ids),
            "latest_report": report_summary,
            "events_today_count": len(recent_events_today),
        }

    def get_capture_data(self) -> dict[str, object]:
        recent_activities = []
        for activity in self.activity_service.get_recent_items(8):
            recent_activities.append({
                "id": activity.id,
                "name": activity.name,
                "event_type": activity.event_type,
                "description": activity.description,
                "tags": activity.tags or [],
            })

        recent_events = self.event_service.get_recent_items(25)
        suggested_event_types: list[str] = []
        suggested_tags: list[str] = []
        for event in recent_events:
            event_type = (getattr(event, "event_type", "") or "").strip()
            if event_type and event_type not in suggested_event_types:
                suggested_event_types.append(event_type)
            for tag in getattr(event, "tags", None) or []:
                normalized_tag = str(tag).strip()
                if normalized_tag and normalized_tag not in suggested_tags:
                    suggested_tags.append(normalized_tag)
            if len(suggested_event_types) >= 6 and len(suggested_tags) >= 10:
                break

        latest_event = next(iter(recent_events), None)
        return {
            "recent_activities": recent_activities,
            "suggested_event_types": suggested_event_types[:6],
            "suggested_tags": suggested_tags[:10],
            "latest_event": {
                "event_type": latest_event.event_type,
                "description": latest_event.description,
                "timestamp": latest_event.timestamp.isoformat() if latest_event and latest_event.timestamp else None,
            } if latest_event else None,
        }

    def _build_promise_index(self) -> list[dict]:
        promises = self.promise_service.find_all(sort_by={"name": "ASC"})
        indexed = []
        for promise in promises:
            match_values = []
            if promise.target_event_tag:
                match_values.append(str(promise.target_event_tag).strip().lower())
            if promise.target_event_type and promise.target_event_type.startswith("project:"):
                match_values.append(promise.target_event_type.split(":", 1)[1].strip().lower())
            if match_values:
                indexed.append({
                    "id": promise.id,
                    "name": promise.name,
                    "href": "/promises/home",
                    "match_values": set(match_values),
                })
        return indexed

    def _build_skill_index(self) -> list[dict]:
        skills = self.skill_service.find_all(sort_by={"name": "ASC"})
        return [
            {
                "id": skill.id,
                "name": skill.name,
                "href": "/skills/home",
                "match_values": self.skill_service.get_match_keys(skill),
            }
            for skill in skills
        ]

    @staticmethod
    def _build_project_shared_tags(project) -> list[str]:
        tags = []
        if getattr(project, "name", None):
            tags.append(project.name.strip().lower().replace(" ", "-"))
        tags.extend(str(tag).strip().lower() for tag in (getattr(project, "focus_tags", None) or []) if str(tag).strip())
        deduped = []
        for tag in tags:
            if tag not in deduped:
                deduped.append(tag)
        return deduped

    @staticmethod
    def _match_promises_for_tags(tags: list[str], promise_index: list[dict]) -> list[dict]:
        tag_set = set(tags)
        return [
            {"id": item["id"], "name": item["name"], "href": item["href"]}
            for item in promise_index
            if item["match_values"].intersection(tag_set)
        ][:3]

    @staticmethod
    def _match_skills_for_tags(tags: list[str], skill_index: list[dict]) -> list[dict]:
        normalized_tags = {"".join(char for char in tag if char.isalnum()) for tag in tags if tag}
        return [
            {"id": item["id"], "name": item["name"], "href": item["href"]}
            for item in skill_index
            if item["match_values"].intersection(normalized_tags)
        ][:3]

    @staticmethod
    def _build_contribution_summary(linked_promises: list[dict], linked_skills: list[dict]) -> Optional[str]:
        parts = []
        if linked_promises:
            parts.append(f"{len(linked_promises)} promise{'s' if len(linked_promises) != 1 else ''}")
        if linked_skills:
            parts.append(f"{len(linked_skills)} skill{'s' if len(linked_skills) != 1 else ''}")
        if not parts:
            return None
        return "Supports " + " and ".join(parts)

    def _get_recommended_follow_ups(self, *, active_projects: list) -> list[dict]:
        user = None
        current_user_id = PermissionManager.get_current_user_id() if has_request_context() else None
        if current_user_id and self.user_service:
            user = self.user_service.get_by_id(current_user_id)

        limit = UserService.recommendation_limit_for_user(user, default_limit=2)
        if limit <= 0:
            return []

        follow_up_user_id = None
        if user and user.id is not None:
            follow_up_user_id = user.id
        elif active_projects:
            follow_up_user_id = getattr(active_projects[0], "user_id", None)

        if not follow_up_user_id:
            return []

        return self.recommendation_followup_service.get_follow_ups(user_id=follow_up_user_id)[:limit]

    @staticmethod
    def _priority_rank(priority: str) -> int:
        return {"High": 3, "Medium": 2, "Low": 1}.get(priority, 0)

    def _build_setup_checklist(self) -> dict[str, object]:
        activity_count = self.activity_service.count()
        project_count = self.project_service.count()
        promise_count = self.promise_service.count()
        skill_count = self.skill_service.count()
        ticket_count = self.kanban_ticket_service.count()
        ticket_items = self.kanban_ticket_service.find_all(sort_by={"id": "DESC"}) if ticket_count else []
        moved_ticket_count = sum(
            1
            for ticket in ticket_items
            if (ticket.state.value if hasattr(ticket.state, "value") else ticket.state) != "backlog"
        )

        items = [
            {
                "title": "Create one activity",
                "description": "Activities make repeated actions easy to capture as clean events.",
                "href": "/activities/home",
                "completed": activity_count > 0,
            },
            {
                "title": "Create one project",
                "description": "Projects give larger work a home so Today, reports, and kanban have context.",
                "href": "/projects/home",
                "completed": project_count > 0,
            },
            {
                "title": "Create one promise",
                "description": "Promises turn intent into something Rasbhari can verify against event evidence.",
                "href": "/promises/home",
                "completed": promise_count > 0,
            },
            {
                "title": "Create one skill",
                "description": "Skills let repeated tagged work turn into visible growth instead of staying implicit.",
                "href": "/skills/home",
                "completed": skill_count > 0,
            },
            {
                "title": "Create one ticket",
                "description": "A ticket makes project execution concrete enough for Today and reports to reflect.",
                "href": "/kanbantickets/home",
                "completed": ticket_count > 0,
            },
            {
                "title": "Move one ticket forward",
                "description": "Move a ticket out of backlog once so Rasbhari sees a real execution signal.",
                "href": "/kanbantickets/home",
                "completed": moved_ticket_count > 0,
            },
        ]
        completed_count = sum(1 for item in items if item["completed"])
        return {
            "title": "Minimal Useful Setup",
            "summary": "Get one small loop working first: capture, structure, commit, grow, then move one ticket so Today has something real to reason about.",
            "items": items,
            "completed_count": completed_count,
            "total_count": len(items),
            "is_complete": completed_count == len(items),
        }

    def _build_today_guidance(
        self,
        *,
        active_work: list[dict],
        prioritized_work: list[dict],
        due_promises: list[dict],
        neglected_connections: list[dict],
        suggested_activities: list[dict],
        active_projects: list,
        report_summary: Optional[dict],
        recent_events_today: list,
    ) -> list[dict]:
        guidance = []
        if active_work:
            guidance.append({
                "title": "Close the loop on current work",
                "body": f"{len(active_work)} ticket(s) are already in progress. Finish or move one before pulling in more work.",
                "href": active_work[0]["href"],
            })
        elif prioritized_work:
            first_ticket = prioritized_work[0]
            guidance.append({
                "title": "Start the next concrete ticket",
                "body": f"'{first_ticket['title']}' is prioritized and ready to become the first active ticket today.",
                "href": first_ticket["href"],
            })

        if due_promises:
            guidance.append({
                "title": "A promise needs evidence today",
                "body": f"{len(due_promises)} promise check(s) are due. Log the work or refresh promise status before the day drifts.",
                "href": "/promises/home",
            })

        if neglected_connections:
            top_connection = neglected_connections[0]
            guidance.append({
                "title": "Repair a neglected relationship",
                "body": f"{top_connection['name']} is overdue for contact. A small message today would reduce relationship drift.",
                "href": top_connection["href"],
            })

        if not recent_events_today and suggested_activities:
            first_activity = suggested_activities[0]
            guidance.append({
                "title": "Seed the day with one tracked action",
                "body": f"No events have been logged yet today. Trigger '{first_activity['name']}' or log one meaningful action to start the record.",
                "href": first_activity["href"],
            })

        if report_summary:
            guidance.append({
                "title": "Use the latest mirror as calibration",
                "body": f"{report_summary['title']} is your latest behavioral snapshot. Check it before deciding what to ignore today.",
                "href": report_summary["href"],
            })

        if not guidance and active_projects:
            guidance.append({
                "title": "Pick one active project and move it visibly",
                "body": f"You have {len(active_projects)} active project(s). Add one ticket move, update, or event so the day leaves a trace.",
                "href": "/projects/home",
            })

        return guidance[:4]

    def get_dependency_health_data(self) -> list[dict]:
        try:
            return DependencyHealthService().get_checks()
        except Exception as exc:
            return [{
                "name": "Dependency Health",
                "status": "Broken",
                "summary": "Health checks failed",
                "detail": str(exc),
            }]

    def get_reliability_data(self, processes_data: list[dict]) -> list[dict]:
        latest_event = next(iter(self.event_service.get_recent_items(1)), None)
        latest_event_id = latest_event.id if latest_event else 0
        latest_event_age = self._format_age(latest_event.timestamp if latest_event else None)

        running_processes = sum(1 for process in processes_data if process.get('is_alive'))
        total_processes = len(processes_data)
        process_status = "Healthy"
        if total_processes == 0:
            process_status = "Paused"
        elif running_processes == 0:
            process_status = "Broken"
        elif running_processes < total_processes:
            process_status = "Delayed"

        queue_stats = self.queue_service.get_all()
        queue_lags = [max(0, latest_event_id - (stat.last_consumed_id or 0)) for stat in queue_stats]
        max_queue_lag = max(queue_lags) if queue_lags else 0
        queue_status = "Healthy"
        if max_queue_lag > 100:
            queue_status = "Broken"
        elif max_queue_lag > 20:
            queue_status = "Delayed"
        elif not queue_stats:
            queue_status = "Paused"

        recent_notifications = self.notification_service.get_recent_items(5)
        courier_failures = self._count_recent_log_failures("Courier.log")
        notification_status = "Healthy"
        if courier_failures > 0:
            notification_status = "Delayed"
        if not any(process['name'] == 'Courier' and process['is_alive'] for process in processes_data):
            notification_status = "Broken"

        enabled_devices = self.device_service.count(filters={"enabled": True})
        device_processes = [process for process in processes_data if process["owner_app"] == "Devices"]
        active_device_processes = sum(1 for process in device_processes if process.get("is_alive"))
        device_status = "Healthy" if enabled_devices > 0 else "Paused"
        if enabled_devices > 0 and active_device_processes == 0:
            device_status = "Delayed"

        return [
            {
                "name": "Process Health",
                "status": process_status,
                "summary": f"{running_processes}/{total_processes} processes running" if total_processes else "No processes registered",
                "detail": "Background workers that power event handling and automation.",
                "href": "/processes",
            },
            {
                "name": "Event Flow",
                "status": "Healthy" if latest_event else "Paused",
                "summary": f"Last event {latest_event_age}" if latest_event else "No events recorded yet",
                "detail": f"Latest event id: {latest_event_id}" if latest_event else "The event stream is currently empty.",
                "href": "/events/home",
            },
            {
                "name": "Queue Health",
                "status": queue_status,
                "summary": f"Max backlog: {max_queue_lag} events",
                "detail": f"Tracking {len(queue_stats)} queue processors against event stream id {latest_event_id}.",
                "href": "/processes",
            },
            {
                "name": "Notifications",
                "status": notification_status,
                "summary": f"{len(recent_notifications)} recent deliveries, {courier_failures} recent failures",
                "detail": "Courier sends ntfy.sh by default and email when the event carries the email tag.",
                "href": "/processes",
            },
            {
                "name": "Devices",
                "status": device_status,
                "summary": f"{enabled_devices} enabled devices, {active_device_processes}/{len(device_processes)} device processes active",
                "detail": "Tracks sensor/device availability and the workers that monitor them.",
                "href": "/devices",
            },
        ]

    def get_admin_health_data(self, processes_data: list[dict]) -> dict[str, object]:
        reliability_cards = self.get_reliability_data(processes_data)
        latest_event = next(iter(self.event_service.get_recent_items(1)), None)
        latest_event_id = latest_event.id if latest_event else 0
        latest_event_age = self._format_age(latest_event.timestamp if latest_event else None)
        queue_stats = self.queue_service.get_all()
        dependency_cards = self.get_dependency_health_data()
        unhealthy_dependencies = [item for item in dependency_cards if item.get("status") not in {"Healthy", "Configured"}]

        queue_drift_processors = []
        for process in processes_data:
            if process.get("type") != "QueueProcessor":
                continue
            last_consumed_id = process.get("last_consumed_id") or 0
            lag = max(0, latest_event_id - last_consumed_id)
            queue_drift_processors.append({
                "name": process.get("name"),
                "owner_app": process.get("owner_app"),
                "last_consumed_id": last_consumed_id,
                "lag": lag,
                "status": "Healthy" if lag <= 20 else ("Delayed" if lag <= 100 else "Broken"),
            })

        queue_drift_processors.sort(key=lambda item: item["lag"], reverse=True)
        max_queue_lag = queue_drift_processors[0]["lag"] if queue_drift_processors else 0
        queue_drift_status = "Healthy"
        if max_queue_lag > 100:
            queue_drift_status = "Broken"
        elif max_queue_lag > 20:
            queue_drift_status = "Delayed"
        elif not queue_stats:
            queue_drift_status = "Paused"

        checked_at = datetime.now(timezone.utc)
        return {
            "checked_at": checked_at.isoformat(),
            "checked_at_display": checked_at.strftime("%Y-%m-%d %H:%M UTC"),
            "host": os.getenv("HOSTNAME") or os.uname().nodename,
            "server": {
                "status": "Healthy",
                "summary": "Admin surface reachable now",
                "detail": "If you can load this page over Tailscale, the Pi-hosted Rasbhari server is currently responding.",
            },
            "event_flow": {
                "status": "Healthy" if latest_event else "Paused",
                "summary": f"Last event {latest_event_age}" if latest_event else "No events recorded yet",
                "detail": f"Latest event id: {latest_event_id}" if latest_event else "The event stream is currently empty.",
            },
            "queue_drift": {
                "status": queue_drift_status,
                "summary": f"Max lag {max_queue_lag} events",
                "detail": f"{len(queue_drift_processors)} queue processor(s) tracked against event stream id {latest_event_id}.",
                "processors": queue_drift_processors[:5],
            },
            "dependencies": {
                "status": "Healthy" if not unhealthy_dependencies else ("Delayed" if len(unhealthy_dependencies) == 1 else "Broken"),
                "summary": f"{len(unhealthy_dependencies)} issue(s) detected",
                "detail": "Dependency health reflects services like ntfy, SendGrid, and OpenWebUI.",
            },
            "reliability_cards": reliability_cards,
        }

    def get_universal_timeline_data(self, limit: int = 20) -> list[dict]:
        items = []

        for item in self.skill_history_service.get_recent_history(limit=6):
            items.append({
                "source": "Skills",
                "category": "Growth",
                "title": item.summary,
                "subtitle": f"{item.total_xp} XP total",
                "timestamp": item.reached_at,
                "href": "/skills/home",
            })

        for item in self.timeline_service.get_recent_items(6):
            items.append({
                "source": "Projects",
                "category": "Projects",
                "title": item.content[:80] + ("..." if len(item.content) > 80 else ""),
                "subtitle": f"{item.item_type} on project #{item.project_id}",
                "timestamp": item.timestamp,
                "href": f"/projects/{item.project_id}/view",
            })

        for item in self.notification_service.get_recent_items(6):
            items.append({
                "source": "Courier",
                "category": "Notifications",
                "title": item.title or f"{item.notification_class.title()} via {item.notification_type}",
                "subtitle": item.notification_data,
                "timestamp": item.created_at,
                "href": "/processes",
            })

        for item in self.event_service.get_recent_items(20):
            if item.event_type == "skill:level_up":
                continue
            view = TimelineEventView(
                event_type=item.event_type,
                tags=item.tags or [],
                description=item.description or item.event_type,
                timestamp=item.timestamp,
            )
            items.append({
                "source": "Events",
                "category": self._categorize_event(view),
                "title": view.description,
                "subtitle": view.event_type,
                "timestamp": view.timestamp,
                "href": "/events/home",
            })

        items.sort(key=lambda item: self._normalize_datetime(item.get("timestamp")), reverse=True)
        return [
            {
                **item,
                "timestamp": self._normalize_datetime(item.get("timestamp")).isoformat() if self._normalize_datetime(item.get("timestamp")) else None
            }
            for item in items[:limit]
        ]

    @staticmethod
    def _categorize_event(event: TimelineEventView) -> str:
        tags = set(event.tags or [])
        if event.event_type.startswith("project:") or "progress" in tags:
            return "Projects"
        if event.event_type.startswith("device:") or "device" in tags:
            return "Devices"
        if event.event_type.startswith("skill:") or "skill" in tags:
            return "Growth"
        if "notification" in tags or "email" in tags:
            return "Notifications"
        if "activity" in event.event_type or any(tag.startswith("triggered_by:activity:") for tag in tags):
            return "Activity"
        return "Events"

    @staticmethod
    def _normalize_datetime(value) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except Exception:
            return None

    @classmethod
    def _format_age(cls, value) -> str:
        dt_value = cls._normalize_datetime(value)
        if not dt_value:
            return "unknown"
        delta = datetime.now(timezone.utc) - dt_value
        seconds = max(0, int(delta.total_seconds()))
        if seconds < 60:
            return f"{seconds}s ago"
        if seconds < 3600:
            return f"{seconds // 60}m ago"
        if seconds < 86400:
            return f"{seconds // 3600}h ago"
        return f"{seconds // 86400}d ago"

    @staticmethod
    def _count_recent_log_failures(filename: str, line_limit: int = 200) -> int:
        log_dir = os.getenv('LOG_DIR')
        if not log_dir:
            return 0
        log_path = os.path.join(log_dir, filename)
        if not os.path.exists(log_path):
            return 0
        try:
            with open(log_path, 'r') as log_file:
                lines = log_file.readlines()[-line_limit:]
        except Exception:
            return 0
        failure_markers = (
            "returned error",
            "Could not send",
            "Failed to send",
        )
        return sum(1 for line in lines if any(marker in line for marker in failure_markers))


class RasbhariAssistantCommandProvider(AssistantCommandProvider):
    def __init__(self, assistant_command_service: Optional[AssistantCommandService] = None):
        self.assistant_command_service = assistant_command_service or AssistantCommandService()

    def handle(
        self,
        user_id: int,
        message: str,
        confirm: bool = False,
        cancel: bool = False,
        change_action: Optional[str] = None,
    ):
        return self.assistant_command_service.handle(
            user_id=user_id,
            message=message,
            confirm=confirm,
            cancel=cancel,
            change_action=change_action,
        )

    def handle_recommendation(self, user_id: int, recommendation: dict, execute: bool = False):
        return self.assistant_command_service.handle_recommendation(user_id=user_id, recommendation=recommendation, execute=execute)
