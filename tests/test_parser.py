from app.parser import parse_article, parse_publication

FIXTURES_DIR = "tests/fixtures"


def _load(name: str) -> str:
    path = f"{FIXTURES_DIR}/{name}"
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestParsePublication:
    def test_title_from_og_site_name(self):
        html = _load("homepage.html")
        pub = parse_publication(html, "https://tech-weekly.beehiiv.com")
        assert pub.title == "Tech Weekly"

    def test_description_from_meta(self):
        html = _load("homepage.html")
        pub = parse_publication(html, "https://tech-weekly.beehiiv.com")
        assert "weekly newsletter" in pub.description

    def test_language_from_html(self):
        html = _load("homepage.html")
        pub = parse_publication(html, "https://tech-weekly.beehiiv.com")
        assert pub.language == "en"

    def test_fallback_title_uses_netloc(self):
        html = "<html><head></head><body></body></html>"
        pub = parse_publication(html, "https://test.beehiiv.com")
        assert pub.title == "test.beehiiv.com"


class TestParseArticle:
    def test_article_with_jsonld(self):
        html = _load("article_with_jsonld.html")
        article = parse_article(html, "https://tech-weekly.beehiiv.com/p/jsonld-article")
        assert article is not None
        assert article.title == "JSON-LD Article"
        assert article.published_at is not None
        assert article.author == "Jane Doe"
        assert article.hero_image_url is not None

    def test_article_with_og(self):
        html = _load("article_with_og.html")
        article = parse_article(html, "https://tech-weekly.beehiiv.com/p/og-article")
        assert article is not None
        assert article.title == "OG Article Title"
        assert article.published_at is not None
        assert "relative link" in article.html_content

    def test_article_fallback(self):
        html = _load("article_fallback.html")
        article = parse_article(html, "https://tech-weekly.beehiiv.com/p/fallback")
        assert article is not None
        assert article.title == "Fallback Article"
        assert "bold" in article.html_content
        assert "Item one" in article.html_content

    def test_article_no_date(self):
        html = _load("article_no_date.html")
        article = parse_article(html, "https://tech-weekly.beehiiv.com/p/no-date")
        assert article is not None
        assert article.published_at is None

    def test_article_no_author(self):
        html = _load("article_fallback.html")
        article = parse_article(html, "https://tech-weekly.beehiiv.com/p/fallback")
        assert article is not None
        assert article.author is None

    def test_relative_images_converted(self):
        html = _load("article_with_jsonld.html")
        article = parse_article(html, "https://tech-weekly.beehiiv.com/p/jsonld-article")
        assert article is not None
        assert "https://tech-weekly.beehiiv.com/images/photo.png" in article.html_content

    def test_relative_links_converted(self):
        html = _load("article_with_og.html")
        article = parse_article(html, "https://tech-weekly.beehiiv.com/p/og-article")
        assert article is not None
        assert "https://tech-weekly.beehiiv.com/relative/link" in article.html_content

    def test_scripts_removed(self):
        html = _load("article_with_jsonld.html")
        article = parse_article(html, "https://tech-weekly.beehiiv.com/p/jsonld-article")
        assert article is not None
        assert "alert" not in article.html_content
        assert "<script>" not in article.html_content

    def test_subscribe_cta_removed(self):
        html = _load("article_with_jsonld.html")
        article = parse_article(html, "https://tech-weekly.beehiiv.com/p/jsonld-article")
        assert article is not None
        assert "subscribe-cta" not in article.html_content

    def test_social_share_removed(self):
        html = _load("article_with_jsonld.html")
        article = parse_article(html, "https://tech-weekly.beehiiv.com/p/jsonld-article")
        assert article is not None
        assert "social-share" not in article.html_content

    def test_empty_html(self):
        article = parse_article("<html></html>", "https://test.beehiiv.com/p/post")
        assert article is None

    def test_no_title(self):
        html = "<html><body><p>No title here</p></body></html>"
        article = parse_article(html, "https://test.beehiiv.com/p/post")
        assert article is None

    def test_canonical_url_extracted(self):
        html = _load("article_with_jsonld.html")
        article = parse_article(html, "https://tech-weekly.beehiiv.com/p/jsonld-article")
        assert article is not None
        assert article.url == "https://tech-weekly.beehiiv.com/p/jsonld-article"
        assert article.guid == article.url

    def test_description_extracted(self):
        html = _load("article_with_jsonld.html")
        article = parse_article(html, "https://tech-weekly.beehiiv.com/p/jsonld-article")
        assert article is not None
        assert "detailed article" in article.description

    def test_utf8_and_special_chars(self):
        html = _load("article_utf8.html")
        article = parse_article(html, "https://tech-weekly.beehiiv.com/p/french-article")
        assert article is not None
        assert "éèêëàâäùûüôöîïç" in article.html_content
        assert "Article en Français" in article.title
