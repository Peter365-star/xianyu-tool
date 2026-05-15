import random
import re
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

logger = logging.getLogger(__name__)


def parse_publish_time(text: str) -> Optional[datetime]:
    """Parse Chinese time expressions like '3小时前发布', '2天前发布', '48小时内发布'."""
    if not text:
        return None
    now = datetime.utcnow()
    text = text.strip()

    # "刚刚发布" → just now
    if "刚刚" in text:
        return now

    # "X分钟前发布", "X分钟前"
    m = re.search(r"(\d+)\s*分钟前", text)
    if m:
        return now - timedelta(minutes=int(m.group(1)))

    # "X小时前发布", "X小时内发布", "X小时前"
    m = re.search(r"(\d+)\s*小时(?:前|内)", text)
    if m:
        return now - timedelta(hours=int(m.group(1)))

    # "X天前发布", "X天前"
    m = re.search(r"(\d+)\s*天前", text)
    if m:
        return now - timedelta(days=int(m.group(1)))

    # "X天内发布" → published within X days, assume X/2 days ago
    m = re.search(r"(\d+)\s*天内发布", text)
    if m:
        return now - timedelta(days=int(m.group(1)) // 2)

    # "X小时内发布"
    m = re.search(r"(\d+)\s*小时内发布", text)
    if m:
        return now - timedelta(hours=int(m.group(1)) // 2)

    # "今天发布" / "昨天发布"
    if "今天" in text:
        return now - timedelta(hours=12)
    if "昨天" in text:
        return now - timedelta(days=1)

    return None


@dataclass
class CrawledProduct:
    xianyu_id: str
    title: str
    price: float
    original_price: Optional[float] = None
    images: List[str] = field(default_factory=list)
    seller_name: Optional[str] = None
    seller_level: Optional[str] = None
    want_count: int = 0
    view_count: int = 0
    category: Optional[str] = None
    publish_time: Optional[datetime] = None
    link: str = ""


class BaseCrawler(ABC):
    user_agents = [
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; SM-S9080) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.163 Mobile Safari/537.36",
    ]

    def __init__(self):
        self._consecutive_failures = 0

    @abstractmethod
    async def search(self, keyword: str, category: Optional[str] = None) -> List[CrawledProduct]:
        ...

    def random_delay(self):
        from app.config import settings
        delay = random.uniform(settings.crawler_request_delay_min, settings.crawler_request_delay_max)
        time.sleep(delay)

    def random_ua(self) -> str:
        return random.choice(self.user_agents)
