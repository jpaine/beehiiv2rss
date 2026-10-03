# Beehiiv2RSS

Convert a public Beehiiv newsletter into a standard RSS 2.0 feed.

A lightweight, stateless web service built with FastAPI. Provide any public Beehiiv publication URL and receive a valid RSS feed containing all its articles.

## What it does

- Accepts a Beehiiv publication URL via query parameter
- Discovers article links on the publication homepage
- Fetches each article and extracts metadata + full HTML content
- Returns a valid RSS 2.0 feed with `content:encoded` support
- Filters out navigation, ads, subscribe forms, and tracking elements

## Use cases

### Integrate Beehiiv content into any RSS reader

Point any RSS reader (NetNewsWire, Feedly, Miniflux, etc.) at the `/feed` endpoint instead of requiring users to visit the newsletter website.

### Pull Beehiiv articles into a mobile app

```tsx
// React Native — works with any RSS parsing library
const response = await fetch('https://your-server.com/feed?url=https://newsletter.beehiiv.com');
const feed = await parse(await response.text());
// feed.title, feed.items[0].title, feed.items[0].content, etc.
```

Same approach works for web apps, desktop apps, static site generators, or any HTTP-capable client.

### Save feeds as static files via cron

```cron
*/15 * * * * curl -fsS "http://localhost:8000/feed?url=https://newsletter.beehiiv.com" > /var/www/feeds/newsletter.xml
```

Serve the XML files directly from a web server — no Python process needed at read time.

### Embed newsletter content in your own website

Fetch the RSS server-side and render articles on your site. The `content:encoded` field contains full cleaned HTML ready to display.

## What it does not do

- Does not store anything permanently
- Does not include a scheduler or cron job
- Does not authenticate users
- Does not support non-Beehiiv websites in V1
- Does not use a database, Redis, or any external state
- Does not execute JavaScript

## Quick start

```bash
git clone https://github.com/jpaine/beehiiv2rss
cd beehiiv2rss
uv sync                # runtime dependencies
uv sync --all-extras   # include dev dependencies (pytest, ruff)
```

## Usage

Start the server:

```bash
uv run uvicorn app.main:app --reload
```

Test it:

```bash
curl "http://localhost:8000/feed?url=https://example-newsletter.beehiiv.com"
```

The response is RSS XML with `Content-Type: application/rss+xml; charset=utf-8`.

### Health check

```bash
curl http://localhost:8000/health
```

## Configuration

All configuration is optional. Set these environment variables to override defaults:

| Variable | Default | Description |
|---|---|---|
| `MAX_ARTICLES` | `30` | Maximum number of articles per feed |
| `REQUEST_TIMEOUT_SECONDS` | `15` | HTTP request timeout |
| `MAX_RESPONSE_BYTES` | `5000000` | Maximum response body size |
| `MAX_REDIRECTS` | `5` | Maximum redirects to follow |
| `FETCH_CONCURRENCY` | `5` | Concurrent article fetches |
| `USER_AGENT` | `Beehiiv2RSS/0.1` | HTTP User-Agent header |
| `LOG_LEVEL` | `INFO` | Logging level |

Copy `.env.example` to `.env` or export variables directly.

## Testing

Tests use local HTML fixtures. No live websites required.

```bash
uv sync --all-extras
uv run pytest
```

## Linting

```bash
uv run ruff check
uv run ruff format --check
```

## Self-hosting

See [DEPLOY.md](DEPLOY.md) for a Docker build/run path.

### Production

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Using cron

The application does not include a scheduler. Run your own cron job to periodically refresh feeds:

```cron
*/15 * * * * curl -fsS "http://localhost:8000/feed?url=https://example-newsletter.beehiiv.com" > /path/to/feed.xml
```

Or configure your news reader to poll the `/feed` endpoint directly.

## API

### `GET /feed?url=<beehiiv-publication-url>`

Returns RSS 2.0 XML.

Errors return JSON:

| Status | Error | Description |
|---|---|---|
| 400 | `invalid_url` | URL is malformed or missing |
| 400 | `unsafe_url` | SSRF guard triggered |
| 400 | `unsupported_source` | Not a Beehiiv publication |
| 404 | `no_articles_found` | No articles could be discovered |
| 422 | `parse_error` | Publication could not be parsed |
| 502 | `upstream_error` | Upstream website error |
| 504 | `upstream_timeout` | Upstream timed out |
| 500 | `internal_error` | Unexpected error |

### `GET /health`

```json
{"status": "ok"}
```

## Known limitations

- Only `*.beehiiv.com` subdomains are supported. Custom domains are not yet detectable unless they use standard Beehiiv markup.
- Article discovery relies on the homepage HTML. If Beehiiv changes its page structure, discovery may break.
- Pages rendered entirely by JavaScript are not supported.
- Articles without a clear title are skipped.

## Security

- Private IP ranges, localhost, link-local addresses, and carrier-grade NAT space are blocked
- Hostnames are resolved before fetch; all resolved addresses must be public (DNS rebinding protection)
- Homepage URLs, discovered article links, and every redirect hop are validated before outbound HTTP
- Redirect targets must stay on supported Beehiiv domains and pass the same safety checks
- HTTP and HTTPS only
- Cloud metadata hostnames are blocked
- Input validation happens before any HTTP request is made
- Stack traces are never exposed to API users

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run `ruff check` and `ruff format`
5. Run `pytest`
6. Submit a pull request

## License

MIT
