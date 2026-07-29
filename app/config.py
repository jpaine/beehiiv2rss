import os


class Settings:
    max_articles: int = int(os.environ.get("MAX_ARTICLES", "30"))
    request_timeout_seconds: int = int(os.environ.get("REQUEST_TIMEOUT_SECONDS", "15"))
    max_response_bytes: int = int(os.environ.get("MAX_RESPONSE_BYTES", "5000000"))
    max_redirects: int = int(os.environ.get("MAX_REDIRECTS", "5"))
    fetch_concurrency: int = int(os.environ.get("FETCH_CONCURRENCY", "5"))
    user_agent: str = os.environ.get("USER_AGENT", "Beehiiv2RSS/0.1")
    log_level: str = os.environ.get("LOG_LEVEL", "INFO")


settings = Settings()
