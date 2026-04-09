from typing import Optional, Dict, Any, List, Literal

from pydantic import Field

from gabru.flask.model import WidgetUIModel


BrowserRuleTriggerMode = Literal["manual", "confirm", "automatic"]
BrowserRuleConditionType = Literal[
    "popup_action",
    "context_menu",
    "toolbar_click",
    "selection_exists",
    "page_loaded",
    "active_duration",
]
BrowserRulePayloadBehavior = Literal[
    "merge_browser_context",
    "merge_selected_fields",
    "minimal_context",
]


class BrowserRule(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    user_id: Optional[int] = Field(default=None, edit_enabled=False, ui_enabled=False)
    name: str = Field(default="", widget_enabled=True, description="Human-readable label for the rule, such as Save Docs Research On Confirm.")
    browser_action_id: Optional[int] = Field(default=None, widget_type="select", widget_options=[], description="Which Browser Action this rule should trigger when it matches.")
    trigger_mode: BrowserRuleTriggerMode = Field(default="confirm", widget_enabled=True, description="Whether the extension should wait for manual use, ask for confirmation, or trigger automatically.")
    condition_type: BrowserRuleConditionType = Field(default="popup_action", widget_enabled=True, description="The browser-side condition this rule listens for.")
    active_duration_seconds: Optional[int] = Field(default=None, description="Optional active-tab duration threshold for duration-based rules.")
    domain_equals: Optional[str] = Field(default="", description="Only match on exactly this domain when set.")
    domain_suffix: Optional[str] = Field(default="", description="Optional domain suffix match such as example.com.")
    domain_in: List[str] = Field(default_factory=list, widget_enabled=True, description="Optional allowed domain list for this rule.")
    url_contains: Optional[str] = Field(default="", description="Optional substring the URL must contain.")
    url_prefix: Optional[str] = Field(default="", description="Optional URL prefix this rule should match.")
    selection_required: bool = Field(default=False, widget_enabled=True, description="Whether the rule should only match when the user has selected text.")
    payload_behavior: BrowserRulePayloadBehavior = Field(default="merge_browser_context", widget_enabled=True, description="How browser context should be forwarded into Rasbhari when the rule runs.")
    payload_mapping: Dict[str, Any] = Field(default_factory=dict, widget_enabled=False, description="Optional rule-specific payload mapping or overrides.")
    priority: int = Field(default=100, widget_enabled=True, description="Relative precedence when more than one rule matches. Lower numbers win.")
    enabled: bool = Field(default=True, widget_enabled=True, description="Whether this rule should be active for future extension sync.")
