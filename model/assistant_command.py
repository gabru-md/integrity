from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


AssistantAction = Literal[
    "create_event",
    "trigger_activity",
    "create_thought",
    "create_promise",
    "create_skill",
    "create_ticket",
    "create_project_update",
    "answer",
]


class AssistantCommandPlan(BaseModel):
    action: AssistantAction = "answer"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning: str = ""
    summary: str = ""
    event_type: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    activity_id: Optional[int] = None
    activity_name: Optional[str] = None
    thought_message: Optional[str] = None
    promise_name: Optional[str] = None
    promise_description: Optional[str] = None
    promise_frequency: Optional[str] = None
    promise_target_event_type: Optional[str] = None
    promise_target_event_tag: Optional[str] = None
    promise_required_count: Optional[int] = None
    skill_name: Optional[str] = None
    skill_tag_key: Optional[str] = None
    skill_aliases: List[str] = Field(default_factory=list)
    ticket_project_id: Optional[int] = None
    ticket_title: Optional[str] = None
    ticket_description: Optional[str] = None
    ticket_state: Optional[str] = None
    project_id: Optional[int] = None
    project_update_content: Optional[str] = None
    project_update_type: Optional[str] = None
    response: Optional[str] = None


class AssistantCommandResult(BaseModel):
    ok: bool = True
    executed: bool = False
    requires_confirmation: bool = False
    action: AssistantAction = "answer"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    summary: str = ""
    reasoning: str = ""
    user_message: str = ""
    response: str = ""
    payload: Dict[str, Any] = Field(default_factory=dict)
