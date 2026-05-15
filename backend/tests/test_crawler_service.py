import pytest
from unittest.mock import AsyncMock
from app.services.crawler import CrawlerService
from app.crawlers.base import CrawledProduct


class TestCrawlerServiceDecision:
    @pytest.mark.asyncio
    async def test_l1_success_no_fallback(self):
        svc = CrawlerService()
        svc.httpx_crawler.search = AsyncMock(return_value=[
            CrawledProduct(xianyu_id="1", title="Test", price=10, want_count=5)
        ])
        svc.playwright_crawler.search = AsyncMock()

        products = await svc.crawl("test_keyword", "digital")
        assert len(products) == 1
        svc.httpx_crawler.search.assert_called_once()
        svc.playwright_crawler.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_l1_fails_fallsback_to_l2(self):
        svc = CrawlerService()
        svc.httpx_crawler.search = AsyncMock(side_effect=Exception("blocked"))
        svc.playwright_crawler.search = AsyncMock(return_value=[
            CrawledProduct(xianyu_id="2", title="Fallback", price=20, want_count=3)
        ])

        products = await svc.crawl("test_keyword", "digital")
        assert len(products) == 1
        assert products[0].title == "Fallback"

    @pytest.mark.asyncio
    async def test_l2_fails_returns_empty(self):
        svc = CrawlerService()
        svc.httpx_crawler.search = AsyncMock(side_effect=Exception("blocked"))
        svc.playwright_crawler.search = AsyncMock(side_effect=Exception("timeout"))

        products = await svc.crawl("test_keyword", "digital")
        assert products == []
