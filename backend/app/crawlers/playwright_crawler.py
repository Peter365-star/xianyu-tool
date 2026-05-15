import logging
import os
import glob
import uuid
from datetime import datetime
from typing import List, Optional

from app.crawlers.base import BaseCrawler, CrawledProduct

logger = logging.getLogger(__name__)

_USER_DATA_DIR = os.path.join(
    os.path.expanduser("~"), "Library", "Caches", "xianyu-browser-data"
)


def _find_chromium() -> Optional[str]:
    patterns = [
        os.path.expanduser(
            "~/Library/Caches/ms-playwright/chromium-*/chrome-mac*/"
            "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
        ),
        os.path.expanduser("~/Library/Caches/ms-playwright/chromium-*/chrome-mac/Chromium"),
    ]
    for pattern in patterns:
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[-1]
    return None


class PlaywrightCrawler(BaseCrawler):
    """Crawl Xianyu search results via Playwright visible browser."""

    async def search(self, keyword: str, category: Optional[str] = None) -> List[CrawledProduct]:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("Playwright not installed.")
            return []

        executable_path = _find_chromium()
        if not executable_path:
            logger.error("Chromium not found.")
            return []

        os.makedirs(_USER_DATA_DIR, exist_ok=True)

        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=_USER_DATA_DIR,
                headless=False,
                executable_path=executable_path,
                args=["--no-sandbox", "--disable-gpu", "--disable-blink-features=AutomationControlled"],
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1440, "height": 900},
                locale="zh-CN",
            )
            page = context.pages[0] if context.pages else await context.new_page()
            await page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            try:
                products = await self._do_crawl(page, keyword, category)
                logger.info(f"PlaywrightCrawler: {len(products)} products for '{keyword}'")
                return products
            except Exception as e:
                logger.error(f"PlaywrightCrawler error: {e}")
                return []
            finally:
                await context.close()

    async def _do_crawl(
        self, page, keyword: str, category: Optional[str]
    ) -> List[CrawledProduct]:
        # Go to homepage
        await page.goto("https://www.goofish.com", wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(3000)

        # Dismiss login popup using multiple approaches
        await page.wait_for_timeout(2000)
        try:
            # Try JS to close modal
            await page.evaluate("""
                () => {
                    // Remove login modal if present
                    const modals = document.querySelectorAll('[class*="login-modal"], [class*="modal-wrap"]');
                    modals.forEach(m => m.remove());
                }
            """)
            await page.wait_for_timeout(500)
        except Exception:
            pass
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(500)

        # Type keyword into search box and press Enter
        search_input = await page.query_selector('[class*="search-input"]')
        if search_input:
            try:
                await search_input.click(force=True)
            except Exception:
                await search_input.click()
            await page.wait_for_timeout(300)
            await search_input.fill(keyword)
            await page.wait_for_timeout(300)
            await search_input.press("Enter")
        else:
            logger.warning("No search input, navigating directly")
            await page.goto(
                f"https://www.goofish.com/search?q={keyword}",
                wait_until="domcontentloaded", timeout=20000,
            )

        # Wait and scroll
        await page.wait_for_timeout(5000)
        for _ in range(8):
            await page.wait_for_timeout(1500)
            await page.evaluate("window.scrollBy(0, 500)")

        # Collect item IDs first (these are always unique and valid)
        item_ids = await page.evaluate("""
            () => {
                const ids = []; const seen = new Set();
                document.querySelectorAll('a[href*="/item"]').forEach(a => {
                    const m = a.href.match(/[?&]id=(\\d+)/);
                    if (m && !seen.has(m[1])) { seen.add(m[1]); ids.push(m[1]); }
                });
                return ids.slice(0, 30);
            }
        """)

        if not item_ids:
            logger.warning("No item IDs found on search page")
            return []

        # Visit each item page to get full details
        all_products = []
        for item_id in item_ids[:5]:  # visit 5 items to get recommendations
            try:
                await page.goto(
                    f"https://www.goofish.com/item?id={item_id}",
                    wait_until="domcontentloaded", timeout=15000,
                )
                await page.wait_for_timeout(4000)

                # Extract main product
                main = await page.evaluate("""
                    () => {
                        const text = document.body.innerText;
                        const lines = text.split('\\n').map(l => l.trim()).filter(l => l);

                        let price = '', title = '', wantCount = 0, viewCount = 0, sellerName = '', publishTime = '';
                        let foundPrice = false;

                        const skipWords = ['包邮', '想要', '浏览', '退货', '承诺', '闲鱼币',
                            '担保交易', '举报', '小时前来过', '来闲鱼', '卖出', '好评率',
                            '闲鱼号', '搜索', '网页版', '聊一聊', '立即购买', '收藏',
                            '展开', '为你推荐', '福利发放', '质量保障', '快递运输'];

                        for (let i = 0; i < Math.min(lines.length, 40); i++) {
                            const line = lines[i];
                            if (line === '为你推荐') continue;
                            if (line.length <= 2 && line !== '¥') continue;

                            // === DATA EXTRACTION (must come before skip) ===

                            // Want count: "528人想要", "2万+人想要"
                            const wm = line.match(/([\\d.]+)万?人想要/);
                            if (wm) {
                                const num = parseFloat(wm[1]);
                                wantCount = wm[0].includes('万') ? Math.round(num * 10000) : Math.round(num);
                                continue;
                            }
                            // View count: "2万浏览"
                            const vm = line.match(/([\\d.]+)万?浏览/);
                            if (vm) {
                                const num = parseFloat(vm[1]);
                                viewCount = vm[0].includes('万') ? Math.round(num * 10000) : Math.round(num);
                                continue;
                            }

                            // Publish time: "72小时内发布", "3天前发布"
                            if ((line.includes('发布') || line.includes('天前')) && !line.includes('网页版')) {
                                publishTime = line; continue;
                            }

                            // Seller: line before "X小时前来过"
                            if (line.includes('小时前来过') && i > 0) {
                                sellerName = lines[i - 1]; continue;
                            }
                            if (line.includes('分钟前来过') && i > 0) {
                                sellerName = lines[i - 1]; continue;
                            }

                            // === SKIP UI LINES ===
                            let skip = false;
                            for (const w of skipWords) {
                                if (line.includes(w)) { skip = true; break; }
                            }
                            if (skip) continue;
                            if (line.startsWith('品牌：') || line.startsWith('成色：')
                                || line.startsWith('尺码：') || line.startsWith('规格：')) continue;
                            if (line.startsWith('显') && line.includes('存')) continue;
                            if (line.startsWith('功') && line.includes('能')) continue;

                            // Price
                            if (line === '¥' && !foundPrice) {
                                foundPrice = true;
                                if (i + 1 < lines.length) {
                                    const pm = lines[i + 1].match(/^([\\d.]+)/);
                                    if (pm) price = pm[1];
                                }
                                continue;
                            }
                            if (!foundPrice && line.startsWith('¥')) {
                                foundPrice = true;
                                const pm = line.replace('¥', '').trim().match(/^([\\d.]+)/);
                                if (pm) price = pm[1];
                                continue;
                            }

                            // Skip numeric continuation lines after price
                            if (foundPrice && !title && /^\\d/.test(line)) continue;

                            // Title: first substantial text after price
                            if (foundPrice && !title && line.length > 6) {
                                title = line.substring(0, 300);
                            }
                        }
                        return { title, price, wantCount, viewCount, sellerName, publishTime };
                    }
                """)

                if main["title"] and main.get("price"):
                    try:
                        price = round(float(main["price"]), 2)
                        if price > 0:
                            pub_time = None
                            if main.get("publishTime"):
                                from app.crawlers.base import parse_publish_time
                                pub_time = parse_publish_time(main["publishTime"])
                            all_products.append(CrawledProduct(
                                xianyu_id=f"xy_{item_id}",
                                title=main["title"][:500],
                                price=price,
                                seller_name=main.get("sellerName", ""),
                                want_count=main.get("wantCount", 0),
                                view_count=main.get("viewCount", 0),
                                category=category,
                                publish_time=pub_time,
                                link=f"https://www.goofish.com/item?id={item_id}",
                            ))
                    except (ValueError, TypeError):
                        pass

                # Extract recommendations (these ARE related to the searched item)
                recs = await page.evaluate("""
                    () => {
                        const text = document.body.innerText;
                        const idx = text.indexOf('为你推荐');
                        if (idx < 0) return [];
                        const recText = text.substring(idx + 5);
                        const lines = recText.split('\\n').map(l => l.trim()).filter(l => l);

                        const results = [];
                        let currentTitle = '';

                        for (let i = 0; i < lines.length; i++) {
                            const line = lines[i];

                            if (line === '¥' && currentTitle) {
                                if (i + 1 < lines.length) {
                                    const pm = lines[i + 1].match(/^([\\d.]+)/);
                                    if (pm) {
                                        results.push({ title: currentTitle, price: pm[1] });
                                        currentTitle = '';
                                    }
                                }
                                continue;
                            }

                            if (line.includes('人想要') || line.includes('浏览')
                                || line.includes('卖家信用') || line.includes('回头客')
                                || line.includes('小时前') || line.includes('累计降价')
                                || line.includes('发布') || line.length <= 2
                                || /^[\\d.]+$/.test(line) || line.startsWith('¥')) continue;

                            if (line.length > 4 && !currentTitle) {
                                currentTitle = line.substring(0, 200);
                            }
                        }
                        return results;
                    }
                """)

                for rec in recs:
                    try:
                        price = round(float(rec["price"]), 2)
                        if price <= 0 or len(rec["title"]) < 2:
                            continue
                        pub_time = None
                        if rec.get("publishTime"):
                            from app.crawlers.base import parse_publish_time
                            pub_time = parse_publish_time(rec["publishTime"])
                        all_products.append(CrawledProduct(
                            xianyu_id=f"xyr_{uuid.uuid4().hex[:16]}",
                            title=rec["title"][:500],
                            price=price,
                            category=category,
                            want_count=rec.get("wantCount", 0),
                            view_count=rec.get("viewCount", 0),
                            publish_time=pub_time,
                            link="",
                        ))
                    except (ValueError, TypeError):
                        pass

            except Exception as e:
                logger.debug(f"Item {item_id} failed: {e}")
                continue

        return all_products
