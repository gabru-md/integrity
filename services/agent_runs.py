from __future__ import annotations

from datetime import datetime
import json
from typing import List, Optional

from gabru.db.db import DB
from gabru.db.service import CRUDService
from gabru.log import Logger
from model.agent_run import AgentRun, AgentRunStatus
from model.event import Event
from services.events import EventService
from services.kanban_tickets import KanbanTicketService
from services.project_updates import ProjectUpdateService
from services.projects import ProjectService


class AgentRunService(CRUDService[AgentRun]):
    TERMINAL_STATUSES = {AgentRunStatus.COMPLETED.value, AgentRunStatus.FAILED.value, AgentRunStatus.CANCELLED.value}

    def __init__(self):
        super().__init__("agent_runs", DB("rasbhari"), user_scoped=True)
        self.project_service = ProjectService()
        self.ticket_service = KanbanTicketService()
        self.project_update_service = ProjectUpdateService()
        self.event_service = EventService()
        self.log = Logger.get_log("AgentRunService")

    def _create_table(self):
        if self.db.conn:
            with self.db.conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS agent_runs (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        project_id INTEGER NOT NULL,
                        ticket_id INTEGER NOT NULL,
                        workspace_key VARCHAR(128) NOT NULL DEFAULT '',
                        agent_kind VARCHAR(64) NOT NULL DEFAULT 'dry-run',
                        status VARCHAR(32) NOT NULL DEFAULT 'queued',
                        prompt TEXT NOT NULL DEFAULT '',
                        result_summary TEXT NOT NULL DEFAULT '',
                        changed_files TEXT NOT NULL DEFAULT '[]',
                        error_message TEXT NOT NULL DEFAULT '',
                        worker_name VARCHAR(128) NOT NULL DEFAULT '',
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        claimed_at TIMESTAMP,
                        started_at TIMESTAMP,
                        completed_at TIMESTAMP,
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                    """
                )
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_runs_status ON agent_runs(status, created_at)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_runs_ticket ON agent_runs(ticket_id, created_at DESC)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_runs_project ON agent_runs(project_id, created_at DESC)")
                self.db.conn.commit()

    def _to_tuple(self, entity: AgentRun) -> tuple:
        status = entity.status.value if hasattr(entity.status, "value") else entity.status
        return (
            entity.user_id,
            entity.project_id,
            entity.ticket_id,
            entity.workspace_key,
            entity.agent_kind,
            status,
            entity.prompt,
            entity.result_summary,
            json.dumps(entity.changed_files or []),
            entity.error_message,
            entity.worker_name,
            entity.created_at,
            entity.claimed_at,
            entity.started_at,
            entity.completed_at,
            entity.updated_at,
        )

    def _to_object(self, row: tuple) -> AgentRun:
        return AgentRun(
            id=row[0],
            user_id=row[1],
            project_id=row[2],
            ticket_id=row[3],
            workspace_key=row[4] or "",
            agent_kind=row[5] or "dry-run",
            status=row[6] or AgentRunStatus.QUEUED,
            prompt=row[7] or "",
            result_summary=row[8] or "",
            changed_files=self._parse_changed_files(row[9]),
            error_message=row[10] or "",
            worker_name=row[11] or "",
            created_at=row[12],
            claimed_at=row[13],
            started_at=row[14],
            completed_at=row[15],
            updated_at=row[16],
        )

    def _get_columns_for_insert(self) -> List[str]:
        return [
            "user_id", "project_id", "ticket_id", "workspace_key", "agent_kind", "status", "prompt",
            "result_summary", "changed_files", "error_message", "worker_name", "created_at", "claimed_at",
            "started_at", "completed_at", "updated_at",
        ]

    def _get_columns_for_update(self) -> List[str]:
        return self._get_columns_for_insert()

    def _get_columns_for_select(self) -> List[str]:
        return [
            "id", "user_id", "project_id", "ticket_id", "workspace_key", "agent_kind", "status", "prompt",
            "result_summary", "changed_files", "error_message", "worker_name", "created_at", "claimed_at",
            "started_at", "completed_at", "updated_at",
        ]

    def queue_for_ticket(self, *, user_id: int, ticket_id: int, workspace_key: str = "integrity", agent_kind: str = "dry-run") -> Optional[int]:
        ticket = self.ticket_service.get_by_id(ticket_id)
        if not ticket or ticket.user_id != user_id:
            return None
        project = self.project_service.get_by_id(ticket.project_id)
        if not project or project.user_id != user_id:
            return None

        existing = self.latest_for_ticket(ticket_id)
        if existing and (existing.status.value if hasattr(existing.status, "value") else existing.status) not in self.TERMINAL_STATUSES:
            return existing.id

        now = datetime.now()
        prompt = self._build_prompt(project, ticket)
        return self.create(AgentRun(
            user_id=user_id,
            project_id=ticket.project_id,
            ticket_id=ticket_id,
            workspace_key=(workspace_key or "integrity").strip(),
            agent_kind=(agent_kind or "dry-run").strip(),
            status=AgentRunStatus.QUEUED,
            prompt=prompt,
            created_at=now,
            updated_at=now,
        ))

    def next_queued(self, *, workspace_key: Optional[str] = None, agent_kind: Optional[str] = None) -> Optional[AgentRun]:
        filters = {"status": AgentRunStatus.QUEUED.value}
        if workspace_key:
            filters["workspace_key"] = workspace_key
        if agent_kind:
            filters["agent_kind"] = agent_kind
        items = self.find_all(filters=filters, sort_by={"created_at": "ASC"})
        return items[0] if items else None

    def latest_for_ticket(self, ticket_id: int) -> Optional[AgentRun]:
        items = self.find_all(filters={"ticket_id": ticket_id}, sort_by={"created_at": "DESC"})
        return items[0] if items else None

    def claim(self, run_id: int, worker_name: str) -> Optional[AgentRun]:
        run = self.get_by_id(run_id)
        if not run or run.status != AgentRunStatus.QUEUED:
            return None
        now = datetime.now()
        run.status = AgentRunStatus.CLAIMED
        run.worker_name = (worker_name or "unknown-worker").strip()
        run.claimed_at = now
        run.updated_at = now
        if self.update(run):
            return self.get_by_id(run_id)
        return None

    def start(self, run_id: int) -> Optional[AgentRun]:
        run = self.get_by_id(run_id)
        if not run or run.status not in {AgentRunStatus.CLAIMED, AgentRunStatus.QUEUED}:
            return None
        now = datetime.now()
        run.status = AgentRunStatus.RUNNING
        run.started_at = now
        run.updated_at = now
        if self.update(run):
            return self.get_by_id(run_id)
        return None

    def complete(self, run_id: int, *, result_summary: str, changed_files: Optional[list[str]] = None) -> Optional[AgentRun]:
        run = self.get_by_id(run_id)
        if not run or run.status in {AgentRunStatus.COMPLETED, AgentRunStatus.CANCELLED}:
            return None
        now = datetime.now()
        run.status = AgentRunStatus.COMPLETED
        run.result_summary = (result_summary or "").strip()
        run.changed_files = [str(path).strip() for path in (changed_files or []) if str(path).strip()]
        run.completed_at = now
        run.updated_at = now
        if not self.update(run):
            return None
        completed = self.get_by_id(run_id)
        if completed:
            self._record_completion(completed)
        return completed

    def fail(self, run_id: int, *, error_message: str) -> Optional[AgentRun]:
        run = self.get_by_id(run_id)
        if not run or run.status in {AgentRunStatus.COMPLETED, AgentRunStatus.CANCELLED}:
            return None
        now = datetime.now()
        run.status = AgentRunStatus.FAILED
        run.error_message = (error_message or "Worker failed without details.").strip()
        run.completed_at = now
        run.updated_at = now
        if not self.update(run):
            return None
        failed = self.get_by_id(run_id)
        if failed:
            self._record_failure(failed)
        return failed

    def cancel(self, run_id: int) -> Optional[AgentRun]:
        run = self.get_by_id(run_id)
        if not run or run.status in {AgentRunStatus.COMPLETED, AgentRunStatus.FAILED, AgentRunStatus.CANCELLED}:
            return None
        run.status = AgentRunStatus.CANCELLED
        run.updated_at = datetime.now()
        if self.update(run):
            return self.get_by_id(run_id)
        return None

    def to_payload(self, run: AgentRun, *, include_prompt: bool = False) -> dict:
        payload = run.model_dump() if hasattr(run, "model_dump") else run.dict()
        payload["status"] = run.status.value if hasattr(run.status, "value") else run.status
        if not include_prompt:
            payload.pop("prompt", None)
        return payload

    def _build_prompt(self, project, ticket) -> str:
        code = f"{ticket.ticket_code} " if getattr(ticket, "ticket_code", None) else ""
        focus_tags = ", ".join(getattr(project, "focus_tags", None) or []) or "none"
        return "\n".join([
            "You are working from a Rasbhari Kanban ticket.",
            "",
            f"Project: {project.name}",
            f"Project type: {getattr(project, 'project_type', None) or 'Other'}",
            f"Project focus tags: {focus_tags}",
            f"Ticket: {code}{ticket.title}",
            f"Ticket id: {ticket.id}",
            "",
            "Description:",
            ticket.description or "No description provided.",
            "",
            "Instructions:",
            "- Make the smallest coherent code change that satisfies the ticket.",
            "- Do not touch unrelated files.",
            "- Run relevant lightweight validation when practical.",
            "- Return a short merge-request-style summary of the user-visible or behavioral change.",
            "- Do not paste full command output, full diffs, or implementation logs into the summary.",
            "- End your final answer with a machine-readable Rasbhari summary block exactly like:",
            "RASBHARI_RESULT_BEGIN",
            "{\"summary\":\"One or two sentences describing the feature or bug change for the project timeline.\"}",
            "RASBHARI_RESULT_END",
            "- Report changed files separately if your tool supports it.",
        ])

    def _record_completion(self, run: AgentRun):
        ticket = self.ticket_service.get_by_id(run.ticket_id)
        title = getattr(ticket, "title", f"ticket #{run.ticket_id}") if ticket else f"ticket #{run.ticket_id}"
        summary = self._timeline_summary(run.result_summary)
        content = "\n".join([
            f"Ticket \"{title}\" is done.",
            "",
            "What changed:",
            summary,
            "",
            "Next:",
            "Review the result and move the ticket forward if accepted.",
        ])
        self.project_update_service.create_update(
            user_id=run.user_id,
            project_id=run.project_id,
            title=f"Agent completed: {title}",
            content=content,
            item_type="Update",
        )
        self._emit_agent_event(run, "agent:run_completed", f"Agent completed ticket '{title}'")

    def _record_failure(self, run: AgentRun):
        ticket = self.ticket_service.get_by_id(run.ticket_id)
        title = getattr(ticket, "title", f"ticket #{run.ticket_id}") if ticket else f"ticket #{run.ticket_id}"
        content = "\n".join([
            f"Agent failed ticket \"{title}\".",
            "",
            "Error:",
            run.error_message or "No error reported.",
        ])
        self.project_update_service.create_update(
            user_id=run.user_id,
            project_id=run.project_id,
            title=f"Agent failed: {title}",
            content=content,
            item_type="Update",
        )
        self._emit_agent_event(run, "agent:run_failed", f"Agent failed ticket '{title}'")

    def _emit_agent_event(self, run: AgentRun, event_type: str, description: str):
        try:
            self.event_service.create(Event(
                user_id=run.user_id,
                event_type=event_type,
                timestamp=datetime.now(),
                description=description,
                tags=[
                    "agent",
                    f"agent:{run.agent_kind}",
                    f"worker:{run.worker_name}" if run.worker_name else "worker:unknown",
                    f"project:{run.project_id}",
                    f"ticket:{run.ticket_id}",
                    f"workspace:{run.workspace_key}",
                ],
                payload={
                    "agent_run_id": run.id,
                    "project_id": run.project_id,
                    "ticket_id": run.ticket_id,
                    "status": run.status.value if hasattr(run.status, "value") else run.status,
                    "changed_files": run.changed_files,
                },
            ))
        except Exception as exc:
            self.log.warning("Failed to emit agent event for run %s: %s", run.id, exc)

    @staticmethod
    def _timeline_summary(raw_summary: str) -> str:
        summary = (raw_summary or "").strip()
        if not summary:
            return "The requested change was completed."

        noisy_prefixes = (
            "```",
            "diff --git",
            "index ",
            "--- ",
            "+++ ",
            "@@",
            "stdout:",
            "stderr:",
            "warning:",
            "traceback",
        )
        useful_lines = []
        for line in summary.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            lowered = stripped.lower()
            if lowered.startswith(noisy_prefixes):
                continue
            if stripped.startswith(("+", "-")) and len(stripped) > 1 and not stripped.startswith(("- ", "+ ")):
                continue
            useful_lines.append(stripped)
            if len(useful_lines) >= 4:
                break

        compact = " ".join(useful_lines).strip() or "The requested change was completed."
        if len(compact) > 500:
            compact = compact[:497].rstrip() + "..."
        return compact

    @staticmethod
    def _parse_changed_files(raw_value) -> list[str]:
        if raw_value in (None, ""):
            return []
        if isinstance(raw_value, list):
            return [str(item) for item in raw_value if str(item).strip()]
        try:
            parsed = json.loads(raw_value)
        except (TypeError, ValueError):
            return []
        if not isinstance(parsed, list):
            return []
        return [str(item) for item in parsed if str(item).strip()]
