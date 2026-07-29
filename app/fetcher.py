import logging

import httpx

from app.config import settings
from app.errors import UpstreamError, UpstreamTimeoutError

logger = logging.getLogger(__name__)


async def fetch_page(url: str, client: httpx.AsyncClient) -> str:
    try:
        response = await client.get(
            url,
            follow_redirects=True,
            timeout=httpx.Timeout(settings.request_timeout_seconds),
        )
        response.raise_for_status()
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
