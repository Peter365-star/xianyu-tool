import logging
from typing import List, Optional

import httpx

from app.crawlers.base import BaseCrawler, CrawledProduct

logger = logging.getLogger(__name__)


class HttpxCrawler(BaseCrawler):
    """L1 crawler: direct HTTP requests to Xianyu mobile search."""

    async def search(self, keyword: str, category: Optional[str] = None) -> List[CrawledProduct]:
        headers = {
            "User-Agent": self.random_ua(),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, trust_env=False) as client:
                # Try goofish API
                try:
                    response = await client.get(
                        "https://h5api.m.goofish.com/h5/mtop.taobao.idle.awesome.post.search/1.0/",
                        params={"q": keyword},
                        headers=headers,
                    )
                    if response.status_code == 200:
                        products = self._parse_json(response.json(), category)
                        if products:
                            logger.info(f"HttpxCrawler found {len(products)} products for '{keyword}' (API)")
                            return products
                except Exception:
                    pass

                # Try web search
                try:
                    response = await client.get(
                        "https://www.goofish.com/search",
                        params={"q": keyword},
                        headers=headers,
                    )
                    if response.status_code == 200:
                        products = self._parse_html(response.text, category)
                        if products:
                            logger.info(f"HttpxCrawler found {len(products)} products for '{keyword}' (web)")
                            return products
                except Exception:
                    pass

                # Legacy URL
                try:
                    response = await client.get(
                        "https://s.2.taobao.com/list/list.htm",
                        params={"q": keyword, "stype": "1"},
                        headers=headers,
                    )
                    if response.status_code == 200:
                        products = self._parse_html(response.text, category)
                        if products:
                            logger.info(f"HttpxCrawler found {len(products)} products for '{keyword}' (legacy)")
                            return products
                except Exception:
                    pass

        except Exception as e:
            logger.warning(f"HttpxCrawler error for '{keyword}': {e}")
            self._consecutive_failures += 1
            raise

        logger.warning(f"HttpxCrawler: no data for '{keyword}'")
        return []

    def _parse_json(self, data: dict, category: Optional[str]) -> List[CrawledProduct]:
        products = []
        try:
            items = data.get("data", {}).get("result", [])
            if not items:
                items = data.get("data", {}).get("items", [])
            if not items:
                items = data.get("result", [])

            for item in items[:30]:
                try:
                    item_data = item.get("item", item)
                    price_str = item_data.get("price", "0")
                    try:
                        price = float(price_str)
                    except (ValueError, TypeError):
                        price = 0

                    products.append(CrawledProduct(
                        xianyu_id=str(item_data.get("itemId", item_data.get("id", ""))),
                        title=item_data.get("title", ""),
                        price=price,
                        original_price=float(item_data.get("originalPrice", 0)) or None,
                        images=item_data.get("images", item_data.get("picList", [])),
                        seller_name=item_data.get("sellerNick", item_data.get("nick", "")),
                        want_count=int(item_data.get("wantCount", 0)),
                        view_count=int(item_data.get("viewCount", 0)),
                        category=category,
                    ))
                except Exception:
                    continue
        except Exception:
            pass
        return products

    def _parse_html(self, html: str, category: Optional[str]) -> List[CrawledProduct]:
        return []
