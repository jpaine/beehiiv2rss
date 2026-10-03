import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse, Response

from app.config import settings
from app.discovery import discover_articles
from app.errors import AppError, NoArticlesFoundError
from app.fetcher import fetch_page
from app.models import FeedResult
from app.parser import parse_article, parse_publication
from app.rss import generate_rss
from app.security import validate_and_normalise_url

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.client = httpx.AsyncClient(
        follow_redirects=False,
        max_redirects=settings.max_redirects,
        headers={"User-Agent": settings.user_agent},
        timeout=httpx.Timeout(settings.request_timeout_seconds),
    )
    yield
    await app.state.client.aclose()


app = FastAPI(title="Beehiiv2RSS", version="0.1.0", lifespan=lifespan)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error, "message": exc.message},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/feed")
async def feed(
    request: Request, url: str = Query(..., description="URL of the Beehiiv publication")
):
    normalised = validate_and_normalise_url(url)

    client: httpx.AsyncClient = app.state.client

    try:
        homepage_html = await fetch_page(normalised, client)
    except AppError:
        raise

    article_urls = discover_articles(homepage_html, normalised)
    if not article_urls:
        raise NoArticlesFoundError()

    article_urls = article_urls[: settings.max_articles]

    semaphore = asyncio.Semaphore(settings.fetch_concurrency)

    async def fetch_article(article_url: str) -> tuple[str, str | None]:
        async with semaphore:
            try:
                html = await fetch_page(article_url, client)
                return article_url, html
            except AppError as e:
                logger.warning("Failed to fetch article %s: %s", article_url, e.message)
                return article_url, None

    fetch_results = await asyncio.gather(*[fetch_article(u) for u in article_urls])

    publication = parse_publication(homepage_html, normalised)
    articles = []
    for article_url, html_page in fetch_results:
        if not html_page:
            continue
        article = parse_article(html_page, article_url)
        if article:
            articles.append(article)

    articles.sort(
        key=lambda a: a.published_at or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    feed_url_str = str(request.url)
    feed_result = FeedResult(publication=publication, articles=articles)
    rss_xml = generate_rss(feed_result, feed_url=feed_url_str)

    return Response(content=rss_xml, media_type="application/rss+xml; charset=utf-8")
