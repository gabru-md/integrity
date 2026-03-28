from datetime import datetime
from typing import Optional

from pydantic import Field

from gabru.flask.model import WidgetUIModel


class User(WidgetUIModel):
    id: Optional[int] = Field(default=None, edit_enabled=False)
    username: str = Field(default="", widget_enabled=True, description="Unique username used to sign in.")
    display_name: str = Field(default="", widget_enabled=True, description="Friendly name shown in the interface.")
    password: Optional[str] = Field(default=None, widget_enabled=False, ui_enabled=False, description="Temporary plain password used only when creating or resetting a user.")
    is_admin: bool = Field(default=False, widget_enabled=True, description="Whether this account can access Rasbhari admin panels.")
    is_active: bool = Field(default=True, widget_enabled=True, description="Whether this account can sign in.")
    is_approved: bool = Field(default=False, widget_enabled=True, description="Whether this account has been approved by an admin.")
    ntfy_topic: Optional[str] = Field(default=None, widget_enabled=True, description="Personal ntfy.sh topic for notifications. If empty, uses system default.")
    encrypted_data_key: Optional[str] = Field(default=None, edit_enabled=False, ui_enabled=False)
    key_version: int = Field(default=1, edit_enabled=False, ui_enabled=False)
    created_at: datetime = Field(default_factory=datetime.now, edit_enabled=False, description="When this account was created.")
    updated_at: datetime = Field(default_factory=datetime.now, edit_enabled=False, description="When this account was last updated.")
