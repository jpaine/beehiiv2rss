# Deploy with Docker

Build the image from the repository root:

```bash
docker build -t beehiiv2rss .
```

Run the container (port 8000):

```bash
docker run --rm -p 8000:8000 beehiiv2rss
```

Optional environment variables (see README configuration table):

```bash
docker run --rm -p 8000:8000 \
  -e MAX_ARTICLES=20 \
  -e REQUEST_TIMEOUT_SECONDS=20 \
  beehiiv2rss
```

Health check:

```bash
curl http://localhost:8000/health
```

Fetch a feed:

```bash
curl "http://localhost:8000/feed?url=https://example-newsletter.beehiiv.com"
```

For production, place the container behind a reverse proxy with TLS and rate limiting. This project does not ship secrets, schedulers, or paid hosting integrations.
