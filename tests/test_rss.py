from datetime import datetime, timezone

from lxml import etree

from app.models import Article, FeedResult, Publication
from app.rss import generate_rss


class TestGenerateRss:
    def _parse(self, rss: str):
        return etree.fromstring(rss.encode("utf-8"))

    def test_feed_has_required_channel_elements(self):
        pub = Publication(title="Test Pub", url="https://test.beehiiv.com", description="A test")
        result = FeedResult(publication=pub)
        rss = generate_rss(result)
        root = self._parse(rss)
        channel = root.find("channel")
        assert channel.findtext("title") == "Test Pub"
        assert channel.findtext("link") == "https://test.beehiiv.com"
        assert channel.findtext("description") == "A test"

    def test_feed_has_self_reference_link(self):
        pub = Publication(title="Test", url="https://test.beehiiv.com", description="desc")
        result = FeedResult(publication=pub)
        rss = generate_rss(result, feed_url="https://example.com/feed?url=test.beehiiv.com")
        assert 'rel="self"' in rss

    def test_article_items_present(self):
        pub = Publication(title="Test", url="https://test.beehiiv.com", description="desc")
        articles = [
            Article(
                title="Post 1",
                url="https://test.beehiiv.com/p/1",
                guid="https://test.beehiiv.com/p/1",
            ),
            Article(
                title="Post 2",
                url="https://test.beehiiv.com/p/2",
                guid="https://test.beehiiv.com/p/2",
            ),
        ]
        result = FeedResult(publication=pub, articles=articles)
        rss = generate_rss(result)
        root = self._parse(rss)
        items = root.findall(".//item")
        assert len(items) == 2
        assert items[0].findtext("title") == "Post 1"
        assert items[1].findtext("title") == "Post 2"

    def test_items_have_required_elements(self):
        pub = Publication(title="Test", url="https://test.beehiiv.com", description="desc")
        article = Article(
            title="My Post",
            url="https://test.beehiiv.com/p/my-post",
            guid="https://test.beehiiv.com/p/my-post",
            author="Test Author",
        )
        result = FeedResult(publication=pub, articles=[article])
        rss = generate_rss(result)
        root = self._parse(rss)
        item = root.find(".//item")
        assert item.findtext("title") == "My Post"
        assert item.findtext("link") == "https://test.beehiiv.com/p/my-post"
        assert item.findtext("author") == "Test Author"
        guid = item.find("guid")
        assert guid is not None
        assert guid.get("isPermaLink") == "true"

    def test_content_encoded_present(self):
        ns = "http://purl.org/rss/1.0/modules/content/"
        pub = Publication(title="Test", url="https://test.beehiiv.com", description="desc")
        article = Article(
            title="Post",
            url="https://test.beehiiv.com/p/post",
            guid="https://test.beehiiv.com/p/post",
            html_content="<p>Hello world</p>",
        )
        result = FeedResult(publication=pub, articles=[article])
        rss = generate_rss(result)
        root = self._parse(rss)
        item = root.find(".//item")
        encoded = item.find(f"{{{ns}}}encoded")
        assert encoded is not None
        assert "<p>Hello world</p>" in encoded.text

    def test_articles_sorted_newest_first(self):
        pub = Publication(title="Test", url="https://test.beehiiv.com", description="desc")
        articles = [
            Article(
                title="Older",
                url="https://test.beehiiv.com/p/1",
                guid="https://test.beehiiv.com/p/1",
                published_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            ),
            Article(
                title="Newer",
                url="https://test.beehiiv.com/p/2",
                guid="https://test.beehiiv.com/p/2",
                published_at=datetime(2025, 2, 1, tzinfo=timezone.utc),
            ),
        ]
        result = FeedResult(publication=pub, articles=articles)
        rss = generate_rss(result)
        root = self._parse(rss)
        items = root.findall(".//item")
        assert items[0].findtext("title") == "Newer"
        assert items[1].findtext("title") == "Older"

    def test_rss_validates_as_xml(self):
        pub = Publication(title="Test", url="https://test.beehiiv.com", description="desc")
        article = Article(
            title="Test Post",
            url="https://test.beehiiv.com/p/test",
            guid="https://test.beehiiv.com/p/test",
        )
        result = FeedResult(publication=pub, articles=[article])
        rss = generate_rss(result)
        self._parse(rss)

    def test_feed_with_language(self):
        pub = Publication(
            title="Test", url="https://test.beehiiv.com", language="en", description="desc"
        )
        result = FeedResult(publication=pub)
        rss = generate_rss(result)
        root = self._parse(rss)
        channel = root.find("channel")
        assert channel.findtext("language") == "en"

    def test_xml_special_chars_escaped(self):
        pub = Publication(title="Test & Co.", url="https://test.beehiiv.com", description="desc")
        article = Article(
            title="AT&T <Test>",
            url="https://test.beehiiv.com/p/1",
            guid="https://test.beehiiv.com/p/1",
            description="A&B > C",
        )
        result = FeedResult(publication=pub, articles=[article])
        rss = generate_rss(result)
        assert "&amp;" in rss
        assert "&lt;" in rss
