from typing import Optional

from pydantic import BaseModel


class QueueStats(BaseModel):
    name: Optional[str] = ""
    last_consumed_id: int = 0
