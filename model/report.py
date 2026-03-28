from datetime import datetime
from typing import Optional, List, Dict, Any, Literal

from pydantic import Field

from gabru.flask.model import WidgetUIModel


class Report(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    report_type: Literal["daily", "weekly", "monthly"] = Field(
        default="daily",
        widget_enabled=True,
        description="Cadence of the report: daily pulse, weekly narrative, or monthly audit."
    )
    anchor_date: str = Field(
        default="",
        edit_enabled=False,
        widget_enabled=True,
        description="Calendar date the report is anchored to, formatted as YYYY-MM-DD."
    )
    period_start: datetime = Field(
        default_factory=datetime.now,
        edit_enabled=False,
        description="Start of the period covered by the report."
    )
    period_end: datetime = Field(
        default_factory=datetime.now,
        edit_enabled=False,
        description="End of the period covered by the report."
    )
    generated_at: datetime = Field(
        default_factory=datetime.now,
        edit_enabled=False,
        widget_enabled=True,
        description="When Rasbhari generated the report."
    )
    title: str = Field(
        default="",
        widget_enabled=True,
        description="Human-friendly title shown in the dashboard and report detail pages."
    )
    integrity_score: int = Field(
        default=0,
        widget_enabled=True,
        description="Behavioral alignment score for the period, from 0 to 100."
    )
    headline: str = Field(
        default="",
        widget_enabled=True,
        description="Primary takeaway from the period."
    )
    observations: List[str] = Field(
        default_factory=list,
        description="Short reflective observations generated from the report data."
    )
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        edit_enabled=False,
        description="Structured metrics used by the dashboard and printable report."
    )
    sections: Dict[str, Any] = Field(
        default_factory=dict,
        edit_enabled=False,
        description="Longer structured report content grouped into named sections."
    )
