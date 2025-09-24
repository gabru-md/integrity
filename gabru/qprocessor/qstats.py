from typing import Optional

from pydantic import BaseModel


class QueueStats(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = ""
    last_consumed_id: int = 0
