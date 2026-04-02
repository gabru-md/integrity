from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


RecommendationScope = Literal["global", "app", "item"]
RecommendationKind = Literal["info", "stage_action", "quick_apply"]


class Recommendation(BaseModel):
    id: str
    app_name: str = Field(description="Primary app surface this recommendation belongs to.")
    scope: RecommendationScope = "app"
    scope_id: Optional[int] = None
    priority: int = Field(default=50, ge=0, le=100)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    title: str
    body: str
    reasoning: str = ""
    kind: RecommendationKind = "stage_action"
    action: Optional[str] = None
    action_label: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)

