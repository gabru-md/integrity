import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from typing import Dict, List, Optional, Tuple

from model.event import Event
from model.connection import Connection
from model.connection_interaction import ConnectionInteraction
from model.project import Project, ProjectState
from model.report import Report
from model.skill import Skill
from model.thought import Thought
from services.connection_interactions import ConnectionInteractionService
from services.connections import ConnectionService
from services.events import EventService
from services.projects import ProjectService
from services.reports import ReportService
from services.skill_level_history import SkillLevelHistoryService
from services.skills import SkillService
from services.thoughts import ThoughtService


NEGATIVE_THOUGHT_MARKERS = {
    "anxious", "anxiety", "overwhelmed", "stressed", "stress", "tired", "panic",
    "sad", "angry", "burned", "burnout", "frustrated", "lonely"
}
POSITIVE_THOUGHT_MARKERS = {
    "calm", "focused", "grateful", "energized", "happy", "clear", "good", "steady"
}
WORK_TAG_MARKERS = {
    "work", "career", "job", "coding", "build", "project", "deepwork", "study"
}


@dataclass
class ReportWindow:
    report_type: str
    anchor_date: date
    start: datetime
    end: datetime
    label: str


class ReportAggregator:
    def __init__(self, xp_per_match: int = 20):
        self.event_service = EventService()
        self.connection_service = ConnectionService()
        self.connection_interaction_service = ConnectionInteractionService()
        self.project_service = ProjectService()
        self.thought_service = ThoughtService()
        self.skill_service = SkillService()
        self.skill_history_service = SkillLevelHistoryService()
        self.report_service = ReportService()
        self.xp_per_match = xp_per_match

    def build_and_store_report(self, report_type: str, anchor_date: Optional[str] = None, user_id: Optional[int] = None) -> Report:
        if user_id is None:
            raise ValueError("user_id is required to build a report")
        window = self._resolve_window(report_type, anchor_date)
        report = self.build_report(window, user_id=user_id)
        report_id = self.report_service.upsert(report)
        stored = self.report_service.get_by_id(report_id)
        return stored or report

    def build_report(self, window: ReportWindow, user_id: int) -> Report:
        events = self.event_service.find_all(
            filters={"user_id": user_id, "timestamp": {"$gt": window.start, "$lt": window.end}},
            sort_by={"timestamp": "ASC"}
        )
        thoughts = self.thought_service.find_all(
            filters={"user_id": user_id, "created_at": {"$gt": window.start, "$lt": window.end}},
            sort_by={"created_at": "ASC"}
        )
        connections = self.connection_service.find_all(filters={"user_id": user_id, "active": True}, sort_by={"last_contact_at": "ASC"})
        interactions = self.connection_interaction_service.find_all(
            filters={"user_id": user_id, "created_at": {"$gt": window.start, "$lt": window.end}},
            sort_by={"created_at": "ASC"}
        )
        projects = self.project_service.find_all(filters={"user_id": user_id})
        skills = self.skill_service.find_all(filters={"user_id": user_id})
        skill_history = self.skill_history_service.find_all(
            filters={"user_id": user_id, "reached_at": {"$gt": window.start, "$lt": window.end}},
            sort_by={"reached_at": "ASC"}
        )

        tag_breakdown = self._build_tag_breakdown(events)
        skill_xp = self._build_skill_xp(events, skills)
        social_summary = self._build_social_summary(connections, interactions, window.end)
        neglected_connections = self._find_neglected_connections(connections, window.end)
        stalled_projects = self._find_stalled_projects(projects, events)
        mood_summary = self._build_mood_summary(thoughts)
        unfinished_loops = self._find_unfinished_loops(events)
        lead_project = self._find_lead_project(projects)
        lead_project_touched = bool(lead_project and self._project_has_activity(lead_project, events))
        integrity_score, score_breakdown = self._compute_integrity_score(
            stalled_projects=stalled_projects,
            skill_xp=skill_xp,
            social_summary=social_summary,
            neglected_connections=neglected_connections,
            mood_summary=mood_summary,
            lead_project_touched=lead_project_touched,
            event_count=len(events)
        )
        observations = self._build_observations(
            window=window,
            thoughts=thoughts,
            stalled_projects=stalled_projects,
            skill_xp=skill_xp,
            social_summary=social_summary,
            neglected_connections=neglected_connections,
            mood_summary=mood_summary,
            lead_project=lead_project,
            lead_project_touched=lead_project_touched,
            unfinished_loops=unfinished_loops,
            tag_breakdown=tag_breakdown,
            skill_history=skill_history,
        )

        headline = observations[0] if observations else "No strong behavioral signals were detected in this window."
        metrics = {
            "event_count": len(events),
            "thought_count": len(thoughts),
            "integrity_score_breakdown": score_breakdown,
            "time_allocation": tag_breakdown,
            "xp_earned": {
                "total": sum(item["xp"] for item in skill_xp),
                "skills": skill_xp,
            },
            "social_summary": social_summary,
            "mood_summary": mood_summary,
            "stalled_intent_count": len(stalled_projects),
            "unfinished_loop_count": len(unfinished_loops),
            "social_signal_available": bool(connections),
        }
        sections = {
            "snapshot": {
                "one_big_thing": {
                    "project_name": lead_project.name if lead_project else None,
                    "completed": lead_project_touched,
                    "detail": self._lead_project_detail(lead_project, lead_project_touched),
                },
                "unfinished_loops": unfinished_loops,
                "stalled_intents": stalled_projects,
                "neglected_connections": neglected_connections,
            },
            "patterns": {
                "skill_growth": skill_xp,
                "level_ups": [item.dict() for item in skill_history],
                "mood_mapping": mood_summary,
                "social_coverage": social_summary,
            },
            "identity_shift": {
                "top_tags": tag_breakdown[:5],
                "focus_mode": self._infer_focus_mode(tag_breakdown, skill_xp),
                "data_gaps": [] if connections else [
                    "No active connections are configured yet, so social coverage cannot be scored."
                ],
            },
            "inputs": {
                "events": [self._event_preview(event) for event in events[-10:]],
                "thoughts": [self._thought_preview(thought) for thought in thoughts[-10:]],
            },
        }

        return Report(
            user_id=user_id,
            report_type=window.report_type,
            anchor_date=window.anchor_date.isoformat(),
            period_start=window.start,
            period_end=window.end,
            generated_at=datetime.now(),
            title=f"{window.label} Behavioral Mirror",
            integrity_score=integrity_score,
            headline=headline,
            observations=observations,
            metrics=metrics,
            sections=sections,
        )

    def build_request_payload(self, report_type: str, anchor_date: Optional[str] = None, user_id: Optional[int] = None) -> str:
        return json.dumps({
            "user_id": user_id,
            "report_type": report_type,
            "anchor_date": anchor_date or date.today().isoformat(),
        })

    def parse_request_payload(self, description: Optional[str], tags: Optional[List[str]] = None) -> Tuple[Optional[int], str, Optional[str]]:
        if description:
            try:
                payload = json.loads(description)
                return payload.get("user_id"), payload.get("report_type", "daily"), payload.get("anchor_date")
            except json.JSONDecodeError:
                pass

        tags = tags or []
        report_type = "daily"
        anchor_date = None
        user_id = None
        for tag in tags:
            if tag.startswith("report_type:"):
                report_type = tag.split(":", 1)[1]
            elif tag.startswith("anchor_date:"):
                anchor_date = tag.split(":", 1)[1]
            elif tag.startswith("user_id:"):
                try:
                    user_id = int(tag.split(":", 1)[1])
                except ValueError:
                    user_id = None
        return user_id, report_type, anchor_date

    def _resolve_window(self, report_type: str, anchor_date: Optional[str]) -> ReportWindow:
        safe_type = (report_type or "daily").lower()
        anchor = date.fromisoformat(anchor_date) if anchor_date else date.today()

        if safe_type == "weekly":
            start_date = anchor - timedelta(days=anchor.weekday())
            end_date = start_date + timedelta(days=7)
            label = f"Week of {start_date.isoformat()}"
        elif safe_type == "monthly":
            start_date = anchor.replace(day=1)
            if start_date.month == 12:
                end_date = start_date.replace(year=start_date.year + 1, month=1)
            else:
                end_date = start_date.replace(month=start_date.month + 1)
            label = start_date.strftime("%B %Y")
        else:
            safe_type = "daily"
            start_date = anchor
            end_date = anchor + timedelta(days=1)
            label = anchor.strftime("%Y-%m-%d")

        return ReportWindow(
            report_type=safe_type,
            anchor_date=anchor,
            start=datetime.combine(start_date, time.min),
            end=datetime.combine(end_date, time.min),
            label=label,
        )

    def _build_tag_breakdown(self, events: List[Event]) -> List[Dict]:
        counts = Counter()
        for event in events:
            for tag in event.tags or []:
                safe_tag = (tag or "").strip().lower().lstrip("#")
                if not safe_tag or safe_tag.startswith("triggered_by:") or safe_tag.startswith("skill:level:"):
                    continue
                counts[safe_tag] += 1

        total = sum(counts.values())
        if total == 0:
            return []

        return [
            {
                "tag": tag,
                "count": count,
                "percent": round((count / total) * 100, 1),
            }
            for tag, count in counts.most_common(8)
        ]

    def _build_skill_xp(self, events: List[Event], skills: List[Skill]) -> List[Dict]:
        xp_counter = defaultdict(int)
        for event in events:
            normalized_tags = {
                self.skill_service.normalize_skill_tag(tag)
                for tag in (event.tags or [])
                if tag and not tag.startswith("triggered_by:")
            }
            for skill in skills:
                if self.skill_service.get_match_keys(skill).intersection(normalized_tags):
                    xp_counter[skill.name] += self.xp_per_match

        return [
            {"skill": skill.name, "xp": xp_counter[skill.name], "level": skill.level}
            for skill in sorted(skills, key=lambda item: (-xp_counter[item.name], item.name.lower()))
            if xp_counter[skill.name] > 0
        ]

    def _build_social_summary(self, connections: List[Connection], interactions: List[ConnectionInteraction], period_end: datetime) -> Dict:
        interaction_count = len(interactions)
        total_minutes = sum(max(0, item.duration_minutes or 0) for item in interactions)
        unique_people = len({item.connection_id for item in interactions})

        by_type_counter = Counter(item.interaction_type for item in interactions if item.interaction_type)
        by_relationship_counter = Counter()
        for connection in connections:
            by_relationship_counter[connection.relationship_type] += 1

        overdue_count = len(self._find_neglected_connections(connections, period_end))
        return {
            "interaction_count": interaction_count,
            "total_minutes": total_minutes,
            "unique_people": unique_people,
            "configured_connections": len(connections),
            "overdue_connections": overdue_count,
            "by_interaction_type": [
                {"name": name, "count": count} for name, count in by_type_counter.most_common(5)
            ],
            "by_relationship_type": [
                {"name": name, "count": count} for name, count in by_relationship_counter.most_common()
            ],
        }

    def _find_neglected_connections(self, connections: List[Connection], period_end: datetime) -> List[Dict]:
        neglected = []
        for connection in connections:
            if not connection.active:
                continue
            if not connection.last_contact_at:
                neglected.append({
                    "name": connection.name,
                    "relationship_type": connection.relationship_type,
                    "days_since_contact": None,
                    "cadence_days": connection.cadence_days,
                    "status": "Never Contacted",
                })
                continue

            days_since_contact = max(0, (period_end - connection.last_contact_at).days)
            if days_since_contact > connection.cadence_days:
                neglected.append({
                    "name": connection.name,
                    "relationship_type": connection.relationship_type,
                    "days_since_contact": days_since_contact,
                    "cadence_days": connection.cadence_days,
                    "status": "Overdue",
                })
        return sorted(
            neglected,
            key=lambda item: (
                item["days_since_contact"] is None,
                item["days_since_contact"] or 9999
            ),
            reverse=True
        )[:5]

    def _find_stalled_projects(self, projects: List[Project], events: List[Event]) -> List[Dict]:
        stalled = []
        for project in projects:
            if project.state not in {ProjectState.ACTIVE, ProjectState.ON_HOLD, "Active", "On Hold"}:
                continue
            if self._project_has_activity(project, events):
                continue
            stalled.append({
                "project_name": project.name,
                "state": str(project.state),
                "progress_count": project.progress_count,
                "last_updated": project.last_updated.isoformat() if project.last_updated else None,
                "status": "Stalled Intent",
            })
        return stalled[:5]

    def _project_has_activity(self, project: Project, events: List[Event]) -> bool:
        dashed_name = project.name.lower().replace(" ", "-")
        normalized_name = self._normalize_key(project.name)
        for event in events:
            if (event.event_type or "").lower().startswith(f"project:{dashed_name}"):
                return True
            event_tags = {self._normalize_key(tag) for tag in (event.tags or [])}
            if normalized_name in event_tags:
                return True
        return False

    def _build_mood_summary(self, thoughts: List[Thought]) -> dict:
        negative = 0
        positive = 0
        keywords = Counter()
        for thought in thoughts:
            lowered = (thought.message or "").lower()
            for word in NEGATIVE_THOUGHT_MARKERS:
                if word in lowered:
                    negative += 1
                    keywords[word] += 1
            for word in POSITIVE_THOUGHT_MARKERS:
                if word in lowered:
                    positive += 1
                    keywords[word] += 1
        dominant = "neutral"
        if negative > positive:
            dominant = "strained"
        elif positive > negative:
            dominant = "steady"
        return {
            "negative_thoughts": negative,
            "positive_thoughts": positive,
            "dominant_mood": dominant,
            "keywords": [{"term": term, "count": count} for term, count in keywords.most_common(5)],
        }

    def _find_unfinished_loops(self, events: List[Event]) -> List[Dict]:
        starts = []
        finished_keys = set()
        for event in events:
            safe_type = (event.event_type or "").lower()
            if any(token in safe_type for token in ("finish", "complete", "done", "closed")):
                finished_keys.add(self._normalize_loop_key(safe_type))
            if any(token in safe_type for token in ("start", "begin", "open", "resume")):
                starts.append(event)

        loops = []
        for event in starts:
            loop_key = self._normalize_loop_key((event.event_type or "").lower())
            if loop_key in finished_keys:
                continue
            loops.append({
                "event_type": event.event_type,
                "timestamp": event.timestamp.isoformat() if event.timestamp else None,
                "description": event.description or "Started but no matching completion event was found.",
            })
        return loops[:5]

    def _find_lead_project(self, projects: List[Project]) -> Optional[Project]:
        active_projects = [
            project for project in projects
            if project.state in {ProjectState.ACTIVE, "Active"}
        ]
        if not active_projects:
            return None
        return sorted(
            active_projects,
            key=lambda item: (
                item.progress_count or 0,
                item.last_updated or datetime.min,
                item.start_date or datetime.min,
            ),
            reverse=True
        )[0]

    def _compute_integrity_score(self, *, stalled_projects: List[Dict], skill_xp: List[Dict], social_summary: Dict,
                                 neglected_connections: List[Dict], mood_summary: Dict,
                                 lead_project_touched: bool, event_count: int) -> Tuple[int, Dict]:
        breakdown = {
            "base": 100,
            "stalled_intent_penalty": min(40, len(stalled_projects) * 12),
            "no_skill_growth_penalty": 15 if not skill_xp else 0,
            "social_neglect_penalty": min(25, len(neglected_connections) * 6),
            "social_absence_penalty": 10 if social_summary.get("configured_connections") and social_summary.get("interaction_count", 0) == 0 else 0,
            "strained_mood_penalty": 10 if mood_summary.get("dominant_mood") == "strained" else 0,
            "lead_project_penalty": 12 if event_count > 0 and not lead_project_touched else 0,
            "activity_bonus": 5 if event_count >= 5 else 0,
            "social_bonus": 5 if social_summary.get("interaction_count", 0) >= 2 else 0,
        }
        score = (
            breakdown["base"]
            - breakdown["stalled_intent_penalty"]
            - breakdown["no_skill_growth_penalty"]
            - breakdown["social_neglect_penalty"]
            - breakdown["social_absence_penalty"]
            - breakdown["strained_mood_penalty"]
            - breakdown["lead_project_penalty"]
            + breakdown["activity_bonus"]
            + breakdown["social_bonus"]
        )
        return max(0, min(100, score)), breakdown

    def _build_observations(self, *, window: ReportWindow, thoughts: List[Thought], stalled_projects: List[Dict],
                            skill_xp: List[Dict], social_summary: Dict, neglected_connections: List[Dict],
                            mood_summary: Dict, lead_project: Optional[Project],
                            lead_project_touched: bool, unfinished_loops: List[Dict], tag_breakdown: List[Dict],
                            skill_history: List) -> List[str]:
        observations = []
        if stalled_projects:
            stalled_names = ", ".join(item["project_name"] for item in stalled_projects[:3])
            observations.append(f"Stalled intent detected: {stalled_names} stayed active without matching progress signals in this {window.report_type} window.")
        if lead_project:
            if lead_project_touched:
                observations.append(f"Your lead project was {lead_project.name}, and it did receive progress activity in this window.")
            else:
                observations.append(f"Your lead project was {lead_project.name}, but it did not receive a matching progress signal.")
        if skill_xp:
            top_skill = skill_xp[0]
            observations.append(f"Growth was real: {top_skill['skill']} earned {top_skill['xp']} XP during this window.")
        if neglected_connections:
            names = ", ".join(item["name"] for item in neglected_connections[:3])
            observations.append(f"Relationship cadence slipped for {names}. Those connections are past the rhythm you set.")
        elif social_summary.get("interaction_count", 0) > 0:
            observations.append(f"Social coverage was active: {social_summary['interaction_count']} interaction(s) across {social_summary['unique_people']} connection(s).")
        if skill_history:
            observations.append(f"Level-up momentum showed up {len(skill_history)} time(s), which means behavior translated into durable progression.")
        if thoughts and mood_summary.get("dominant_mood") == "strained":
            work_pressure = sum(item["count"] for item in tag_breakdown if item["tag"] in WORK_TAG_MARKERS)
            observations.append(f"Thoughts leaned strained, and work-like tags appeared {work_pressure} time(s); this is a possible effort-versus-state mismatch.")
        if social_summary.get("configured_connections") and social_summary.get("interaction_count", 0) == 0:
            observations.append("You maintain a relationship ledger now, but this window logged no social touchpoints at all.")
        if unfinished_loops:
            observations.append(f"You opened {len(unfinished_loops)} loop(s) without a matching finish signal. That usually creates hidden drag.")
        if not thoughts:
            observations.append("No thoughts were captured in this window, so the mirror can see actions but not much inner state.")
        if social_summary.get("configured_connections", 0) == 0:
            observations.append("No active connections are configured yet, so social balance is still effectively untracked.")
        return observations[:5]

    def _lead_project_detail(self, lead_project: Optional[Project], touched: bool) -> str:
        if not lead_project:
            return "No active project was available to score as the current lead focus."
        if touched:
            return f"{lead_project.name} appears to have received matching progress evidence."
        return f"{lead_project.name} was the current lead focus, but no matching progress evidence was found."

    def _infer_focus_mode(self, tag_breakdown: List[Dict], skill_xp: List[Dict]) -> str:
        top_tag = tag_breakdown[0]["tag"] if tag_breakdown else None
        total_xp = sum(item["xp"] for item in skill_xp)
        if total_xp >= 100:
            return "Builder"
        if top_tag in WORK_TAG_MARKERS:
            return "Worker"
        if top_tag:
            return f"{top_tag.title()}-Weighted"
        return "Undetermined"

    def _event_preview(self, event: Event) -> dict:
        return {
            "event_type": event.event_type,
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
            "description": event.description,
            "tags": event.tags or [],
        }

    def _thought_preview(self, thought: Thought) -> dict:
        return {
            "message": thought.message,
            "created_at": thought.created_at.isoformat() if thought.created_at else None,
        }

    def _normalize_key(self, value: Optional[str]) -> str:
        return re.sub(r"[^a-z0-9]+", "", (value or "").strip().lower())

    def _normalize_loop_key(self, value: str) -> str:
        value = re.sub(r"(start|begin|open|resume|finish|complete|done|closed)", "", value)
        return self._normalize_key(value)
