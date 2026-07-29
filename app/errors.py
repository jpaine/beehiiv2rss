from dataclasses import dataclass


@dataclass
class AppError(Exception):
    status_code: int
    error: str
    message: str


class InvalidURLError(AppError):
    def __init__(self, message: str = "The provided URL is invalid or malformed."):
        super().__init__(status_code=400, error="invalid_url", message=message)


class UnsupportedSourceError(AppError):
    def __init__(self, message: str = "The provided URL is not a supported Beehiiv publication."):
        super().__init__(status_code=400, error="unsupported_source", message=message)


class UnsafeURLError(AppError):
    def __init__(self, message: str = "The provided URL is unsafe."):
        super().__init__(status_code=400, error="unsafe_url", message=message)


class NoArticlesFoundError(AppError):
    def __init__(self, message: str = "No public Beehiiv articles could be found."):
        super().__init__(status_code=404, error="no_articles_found", message=message)


class ParseError(AppError):
    def __init__(self, message: str = "The publication could not be parsed."):
        super().__init__(status_code=422, error="parse_error", message=message)


class UpstreamError(AppError):
    def __init__(self, message: str = "The upstream website returned an error."):
        super().__init__(status_code=502, error="upstream_error", message=message)


class UpstreamTimeoutError(AppError):
    def __init__(self, message: str = "The upstream website timed out."):
        super().__init__(status_code=504, error="upstream_timeout", message=message)
