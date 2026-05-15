from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class ProductOut(BaseModel):
    id: UUID
    xianyu_id: str
    title: str
    price: float
    original_price: Optional[float] = None
    images: Optional[List[str]] = None
    seller_name: Optional[str] = None
    seller_level: Optional[str] = None
    want_count: int
    view_count: int
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    link: Optional[str] = None
    days_ago: Optional[int] = None
    hotness: Optional[float] = None
    publish_time: Optional[datetime] = None
    fetched_at: datetime

    model_config = {"from_attributes": True}


class HotProductOut(ProductOut):
    score: float
    want_velocity: float
    price_advantage: float
    engagement_rate: float


class ProductSearchParams(BaseModel):
    keyword: Optional[str] = None
    category: Optional[str] = None
    industry: Optional[str] = None
    page: int = 1
    page_size: int = 20
    sort: str = "hot_score"


class ProductSearchResult(BaseModel):
    items: List[HotProductOut]
    total: int
    page: int
    page_size: int
