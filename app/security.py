import ipaddress
import re
import socket
from urllib.parse import urljoin, urlparse

from app.errors import InvalidURLError, UnsafeURLError, UnsupportedSourceError

BEEHIIV_DOMAIN_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?\.beehiiv\.com$")

_PRIVATE_NETWORKS = [
    "127.0.0.0/8",
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "::1/128",
    "fc00::/7",
    "fe80::/10",
    "169.254.0.0/16",
    "100.64.0.0/10",
]

_BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "::1",
        "metadata.google.internal",
        "metadata.goog",
    }
)

_PRIVATE_BLOCKS = [ipaddress.ip_network(n) for n in _PRIVATE_NETWORKS]


def validate_and_normalise_url(raw_url: str) -> str:
    parsed = _parse_http_url(raw_url)
    if not is_supported_domain(parsed.hostname):
        raise UnsupportedSourceError("Only Beehiiv publications are supported.")
    return _normalise_parsed_url(parsed)


def validate_fetch_url(raw_url: str) -> str:
    """Validate a Beehiiv URL immediately before an outbound HTTP fetch."""
    parsed = _parse_http_url(raw_url)
    if not is_supported_domain(parsed.hostname):
        raise UnsupportedSourceError("Only Beehiiv publication URLs may be fetched.")
    return _normalise_parsed_url(parsed)


def _parse_http_url(raw_url: str) -> urlparse:
    url = raw_url.strip()
    if not url:
        raise InvalidURLError("No URL provided.")

    if not url.startswith(("http://", "https://")):
        raise InvalidURLError("Only http:// and https:// URLs are supported.")

    parsed = urlparse(url)
    if not parsed.netloc:
        raise InvalidURLError("The provided URL is malformed.")

    if not is_safe_netloc(parsed.hostname):
        raise UnsafeURLError("The provided URL is unsafe.")

    return parsed


def _normalise_parsed_url(parsed: urlparse) -> str:
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"


def is_safe_netloc(hostname: str | None) -> bool:
    if not hostname:
        return False
    host = hostname.strip().lower().rstrip(".")
    if host in _BLOCKED_HOSTNAMES:
        return False
    try:
        addr = ipaddress.ip_address(host)
        return _is_safe_ip(addr)
    except ValueError:
        pass

    resolved_any = False
    for family in (socket.AF_INET, socket.AF_INET6):
        try:
            infos = socket.getaddrinfo(
                host,
                None,
                family=family,
                type=socket.SOCK_STREAM,
            )
        except OSError:
            continue
        for info in infos:
            resolved_any = True
            ip_str = info[4][0]
            try:
                addr = ipaddress.ip_address(ip_str)
            except ValueError:
                return False
            if not _is_safe_ip(addr):
                return False

    return resolved_any


def _is_safe_ip(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    for block in _PRIVATE_BLOCKS:
        if addr in block:
            return False
    return True


def is_supported_domain(hostname: str | None) -> bool:
    if not hostname:
        return False
    if BEEHIIV_DOMAIN_RE.match(hostname):
        return True
    return False


def resolve_redirect_target(response_url: str, location: str) -> str:
    if not location:
        raise UnsafeURLError("Redirect target is missing.")
    return urljoin(response_url, location.strip())


def check_redirect_safety(redirect_url: str) -> str:
    return validate_fetch_url(redirect_url)
