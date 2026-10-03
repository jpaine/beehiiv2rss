import httpx
import pytest

from app.errors import UnsafeURLError, UnsupportedSourceError, UpstreamError
from app.fetcher import fetch_page
from app.main import app


@pytest.fixture
async def http_client():
    async with httpx.AsyncClient(
        follow_redirects=False,
        headers={"User-Agent": "Beehiiv2RSS-test"},
    ) as client:
        yield client


class TestFetcherSsrf:
    async def test_rejects_private_ip_article_url(self, http_client):
        with pytest.raises(UnsafeURLError):
            await fetch_page("http://192.168.1.50/p/internal-post", http_client)

    async def test_rejects_non_beehiiv_article_url(self, http_client):
        with pytest.raises(UnsupportedSourceError):
            await fetch_page("https://example.com/p/post", http_client)

    async def test_rejects_redirect_to_loopback(self, http_client, httpx_mock):
        httpx_mock.add_response(
            url="https://news.beehiiv.com/p/post",
            status_code=302,
            headers={"Location": "http://127.0.0.1/secret"},
        )
        with pytest.raises(UnsafeURLError):
            await fetch_page("https://news.beehiiv.com/p/post", http_client)

    async def test_rejects_redirect_chain_to_private_ip(self, http_client, httpx_mock):
        httpx_mock.add_response(
            url="https://news.beehiiv.com/p/post",
            status_code=302,
            headers={"Location": "https://news.beehiiv.com/p/step2"},
        )
        httpx_mock.add_response(
            url="https://news.beehiiv.com/p/step2",
            status_code=302,
            headers={"Location": "http://10.0.0.8/admin"},
        )
        with pytest.raises(UnsafeURLError):
            await fetch_page("https://news.beehiiv.com/p/post", http_client)

    async def test_follows_safe_redirect_on_beehiiv(self, http_client, httpx_mock):
        httpx_mock.add_response(
            url="https://news.beehiiv.com/p/post",
            status_code=302,
            headers={"Location": "/p/final"},
        )
        httpx_mock.add_response(
            url="https://news.beehiiv.com/p/final",
            status_code=200,
            text="<html><body>ok</body></html>",
        )
        html = await fetch_page("https://news.beehiiv.com/p/post", http_client)
        assert "ok" in html

    async def test_too_many_redirects(self, http_client, httpx_mock, monkeypatch):
        monkeypatch.setattr("app.config.settings.max_redirects", 1)
        httpx_mock.add_response(
            url="https://news.beehiiv.com/p/a",
            status_code=302,
            headers={"Location": "https://news.beehiiv.com/p/b"},
        )
        httpx_mock.add_response(
            url="https://news.beehiiv.com/p/b",
            status_code=302,
            headers={"Location": "https://news.beehiiv.com/p/c"},
        )
        with pytest.raises(UpstreamError, match="Too many redirects"):
            await fetch_page("https://news.beehiiv.com/p/a", http_client)


class TestDiscoverySsrfFiltering:
    def test_skips_unsafe_discovered_links(self):
        from app.discovery import discover_articles

        html = """
        <html><body>
          <a href="/p/safe-post">Safe</a>
          <a href="http://127.0.0.1/p/evil-post">Evil</a>
          <a href="https://evil.com/p/remote-post">Remote</a>
        </body></html>
        """
        urls = discover_articles(html, "https://news.beehiiv.com")
        assert urls == ["https://news.beehiiv.com/p/safe-post"]

    async def test_feed_does_not_fetch_blocked_discovered_urls(self, api_client):
        from app.main import app

        homepage = """
        <html><body>
          <a href="/p/good">Good</a>
          <a href="http://169.254.169.254/latest/meta-data/p/leak">Metadata</a>
        </body></html>
        """
        article = "<html><head><title>Good</title></head><body><h1>Good</h1></body></html>"
        routes = {
            "https://news.beehiiv.com": homepage,
            "https://news.beehiiv.com/p/good": article,
        }
        app.state.client = _mock_client(routes)
        response = await api_client.get("/feed?url=https://news.beehiiv.com")
        assert response.status_code == 200
        assert "169.254.169.254" not in response.text


@pytest.fixture
async def api_client():
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _mock_client(routes: dict):
    from unittest.mock import AsyncMock, MagicMock

    async def mock_get(url, **kwargs):
        mock_resp = MagicMock()
        if url in routes:
            mock_resp.text = routes[url]
            mock_resp.status_code = 200
            mock_resp.is_redirect = False
            mock_resp.is_permanent_redirect = False
            mock_resp.raise_for_status = MagicMock()
            mock_resp.headers = {"location": ""}
            mock_resp.url = url
        else:
            mock_resp.status_code = 404
            mock_resp.text = "<html><body>Not Found</body></html>"
            mock_resp.is_redirect = False
            mock_resp.is_permanent_redirect = False
            mock_resp.raise_for_status = MagicMock(side_effect=Exception("Not found"))
            mock_resp.headers = {"location": ""}
            mock_resp.url = url
        return mock_resp

    client = MagicMock()
    client.get = AsyncMock(side_effect=mock_get)
    return client
