from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class CrawlTriggerRequest(BaseModel):
    keyword: str
    category: Optional[str] = None
    duration_minutes: Optional[int] = None
    source: str = "manual"


class CrawlTaskOut(BaseModel):
    id: UUID
    keyword: str
    category: Optional[str] = None
    status: str
    items_found: int
    level: Optional[str] = None
    duration_minutes: Optional[int] = None
    products_data: Optional[list] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}
