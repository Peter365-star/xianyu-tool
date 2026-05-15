import logging
from typing import List, Optional

from app.crawlers.base import CrawledProduct
from app.crawlers.httpx_crawler import HttpxCrawler
from app.crawlers.playwright_crawler import PlaywrightCrawler

logger = logging.getLogger(__name__)


class CrawlerService:
    def __init__(self):
        self.httpx_crawler = HttpxCrawler()
        self.playwright_crawler = PlaywrightCrawler()

    async def crawl(self, keyword: str, category: Optional[str] = None) -> List[CrawledProduct]:
        """Run crawl with L1 -> L2 fallback."""

        # L1: httpx fast crawl
        try:
            products = await self.httpx_crawler.search(keyword, category)
            if products:
                logger.info(f"L1 success: {len(products)} products for '{keyword}'")
                return products
        except Exception as e:
            logger.warning(f"L1 failed for '{keyword}': {e}")

        # L2: Playwright browser fallback
        try:
            logger.info(f"Falling back to L2 for '{keyword}'")
            products = await self.playwright_crawler.search(keyword, category)
            if products:
                return products
        except Exception as e:
            logger.error(f"L2 failed for '{keyword}': {e}")

        # L3: cool down — handled by caller (scheduler)
        logger.error(f"All levels failed for '{keyword}'")
        return []
