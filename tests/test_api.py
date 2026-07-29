import pytest

from app.main import app

FIXTURES_DIR = "tests/fixtures"


def _load(name: str) -> str:
    path = f"{FIXTURES_DIR}/{name}"
    with open(path, encoding="utf-8") as f:
        return f.read()


@pytest.fixture
async def api_client():
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealth:
    async def test_health_returns_ok(self, api_client):
        response = await api_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data == {"status": "ok"}


class TestFeed:
    async def test_missing_url_param(self, api_client):
        response = await api_client.get("/feed")
        assert response.status_code == 422

    async def test_invalid_url(self, api_client):
        response = await api_client.get("/feed?url=not-a-url")
        assert response.status_code == 400

    async def test_unsupported_source(self, api_client):
        response = await api_client.get("/feed?url=https://example.com")
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "unsupported_source"

    async def test_localhost_rejected(self, api_client):
        response = await api_client.get("/feed?url=http://localhost:8000")
        assert response.status_code == 400

    async def test_private_ip_rejected(self, api_client):
        response = await api_client.get("/feed?url=http://192.168.1.1")
        assert response.status_code == 400

    async def test_no_articles_found(self, api_client):
        homepage = _load("homepage_no_articles.html")
        app.state.client = _mock_client({"https://empty.beehiiv.com": homepage})
        response = await api_client.get("/feed?url=https://empty.beehiiv.com")
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "no_articles_found"

    async def test_successful_feed(self, api_client):
        homepage = _load("homepage.html")
        article1 = _load("article_with_jsonld.html")
        article2 = _load("article_with_og.html")
        article3 = _load("article_fallback.html")

        routes = {
            "https://tech-weekly.beehiiv.com": homepage,
            "https://tech-weekly.beehiiv.com/p/third-post": article1,
            "https://tech-weekly.beehiiv.com/p/second-post": article2,
            "https://tech-weekly.beehiiv.com/p/first-post": article3,
        }
        app.state.client = _mock_client(routes)
        response = await api_client.get("/feed?url=https://tech-weekly.beehiiv.com")
        assert response.status_code == 200
        assert "application/rss+xml" in response.headers["content-type"]
        assert "<rss" in response.text
        assert "<item>" in response.text

    async def test_feed_returns_rss_xml(self, api_client):
        homepage = _load("homepage.html")
        article1 = _load("article_with_jsonld.html")
        routes = {
            "https://tech-weekly.beehiiv.com": homepage,
            "https://tech-weekly.beehiiv.com/p/third-post": article1,
            "https://tech-weekly.beehiiv.com/p/second-post": article1,
            "https://tech-weekly.beehiiv.com/p/first-post": article1,
        }
        app.state.client = _mock_client(routes)
        response = await api_client.get("/feed?url=https://tech-weekly.beehiiv.com")
        assert "<?xml" in response.text
        assert "<rss" in response.text
        assert "</rss>" in response.text

    async def test_error_not_expose_stacktrace(self, api_client):
        response = await api_client.get("/feed?url=http://localhost:8000")
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "message" in data
        assert "traceback" not in str(data).lower()


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
        else:
            mock_resp.status_code = 404
            mock_resp.text = "<html><body>Not Found</body></html>"
            mock_resp.is_redirect = False
            mock_resp.is_permanent_redirect = False
            mock_resp.raise_for_status = MagicMock(side_effect=Exception("Not found"))
            mock_resp.headers = {"location": ""}
        return mock_resp

    client = MagicMock()
    client.get = AsyncMock(side_effect=mock_get)
    return client
