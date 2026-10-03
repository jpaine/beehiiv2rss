import logging

import httpx

from app.config import settings
from app.errors import UpstreamError, UpstreamTimeoutError
from app.security import resolve_redirect_target, validate_fetch_url

logger = logging.getLogger(__name__)


async def fetch_page(url: str, client: httpx.AsyncClient) -> str:
    try:
        response = await _get_with_safe_redirects(url, client)
        content = response.text
        if len(content.encode("utf-8")) > settings.max_response_bytes:
            content = content[: settings.max_response_bytes]
        return content
    except httpx.TimeoutException as e:
        raise UpstreamTimeoutError(str(e))
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (502, 503, 504):
            raise UpstreamError("Upstream website temporarily unavailable.")
        raise UpstreamError(f"Upstream returned HTTP {e.response.status_code}.")
    except httpx.RequestError as e:
        raise UpstreamError(str(e))


async def _get_with_safe_redirects(url: str, client: httpx.AsyncClient) -> httpx.Response:
    current_url = validate_fetch_url(url)
    timeout = httpx.Timeout(settings.request_timeout_seconds)
    response: httpx.Response | None = None

    for _ in range(settings.max_redirects + 1):
        response = await client.get(current_url, follow_redirects=False, timeout=timeout)
        if response.is_redirect:
            location = response.headers.get("location", "")
            redirect_target = resolve_redirect_target(str(response.url), location)
            current_url = validate_fetch_url(redirect_target)
            continue
        response.raise_for_status()
        return response

    raise UpstreamError("Too many redirects while fetching upstream content.")
