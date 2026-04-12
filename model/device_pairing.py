from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DevicePairing(BaseModel):
    id: Optional[int] = Field(default=None, description="Primary key")
    token: str = Field(..., description="Opaque one-time pairing token shown in QR URL.")
    requested_path: str = Field(default="/", description="Internal route to open after consume.")
    user_id: Optional[int] = Field(default=None, description="User that authorized this pairing.")
    status: str = Field(default="pending", description="pending | authorized | consumed | expired | denied")
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime
    authorized_at: Optional[datetime] = None
    consumed_at: Optional[datetime] = None
    requester_ip: Optional[str] = None
    requester_user_agent: Optional[str] = None
