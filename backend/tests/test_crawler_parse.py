from app.crawlers.httpx_crawler import HttpxCrawler


class TestHttpxCrawlerParse:
    def test_parse_empty_html(self):
        crawler = HttpxCrawler()
        products = crawler._parse_html("<html></html>", None)
        assert products == []

    def test_parse_html_with_no_results(self):
        crawler = HttpxCrawler()
        html = "<html><body><div class='no-result'>暂无相关商品</div></body></html>"
        products = crawler._parse_html(html, "digital")
        assert products == []
