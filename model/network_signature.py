from pydantic import Field
from typing import Optional, List
from gabru.flask.model import WidgetUIModel

class NetworkSignature(WidgetUIModel):
    """Data model for a network signature to be used by the sniffer."""
    id: Optional[int] = Field(default=None, edit_enabled=False)
    user_id: Optional[int] = Field(default=None, edit_enabled=False, ui_enabled=False)
    name: str = Field(..., widget_enabled=True, description="Human-readable name for this signature")
    mac_address: str = Field(..., widget_enabled=True, description="The MAC address of the device to watch")
    domain_pattern: Optional[str] = Field(None, widget_enabled=True, description="Optional DNS domain pattern to match (e.g., *ubereats.com)")
    event_type: str = Field("network_activity", widget_enabled=True, description="The type of event to generate when matched")
    tags: List[str] = Field(default_factory=list, widget_enabled=True, description="Tags to add to the generated event")
    is_active: bool = Field(True, widget_enabled=True, description="Whether this signature is currently being monitored")
