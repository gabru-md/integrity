from datetime import datetime
from typing import Optional

from pydantic import Field

from gabru.flask.model import WidgetUIModel


class User(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    username: str = Field(default="", widget_enabled=True, description="Unique username used to sign in.")
    display_name: str = Field(default="", widget_enabled=True, description="Friendly name shown in the interface.")
    password: Optional[str] = Field(default=None, widget_enabled=False, ui_enabled=False, description="Temporary plain password used only when creating or resetting a user.")
    api_key: Optional[str] = Field(default=None, edit_enabled=False, widget_enabled=False, ui_enabled=False, description="Short API key used for header-based access to Rasbhari routes.")
    is_admin: bool = Field(default=False, widget_enabled=True, description="Whether this account can access Rasbhari admin panels.")
    is_active: bool = Field(default=True, widget_enabled=True, description="Whether this account can sign in.")
    is_approved: bool = Field(default=False, widget_enabled=True, description="Whether this account has been approved by an admin.")
    onboarding_completed: bool = Field(default=False, widget_enabled=True, description="Whether the guided product tutorial has been completed for this user.")
    ntfy_topic: Optional[str] = Field(default=None, widget_enabled=True, description="Personal ntfy.sh topic for notifications. If empty, uses system default.")
    experience_mode: str = Field(default="everyday", widget_enabled=True, description="How much of the Rasbhari system should feel primary in the UI. Supported values are everyday, structured, and system.")
    recommendations_enabled: bool = Field(default=True, widget_enabled=True, description="Whether contextual recommendations are shown across Rasbhari.")
    recommendation_limit: int = Field(default=2, widget_enabled=True, description="Maximum number of contextual recommendations shown across Rasbhari. Set to 0 to hide them.")
    encrypted_data_key: Optional[str] = Field(default=None, edit_enabled=False, ui_enabled=False)
    key_version: int = Field(default=1, edit_enabled=False, ui_enabled=False)
    created_at: datetime = Field(default_factory=datetime.now, edit_enabled=False, description="When this account was created.")
    updated_at: datetime = Field(default_factory=datetime.now, edit_enabled=False, description="When this account was last updated.")
