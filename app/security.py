import ipaddress
import re
from urllib.parse import urlparse

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
]

_PRIVATE_BLOCKS = [ipaddress.ip_network(n) for n in _PRIVATE_NETWORKS]


def validate_and_normalise_url(raw_url: str) -> str:
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

    if not is_supported_domain(parsed.hostname):
        raise UnsupportedSourceError("Only Beehiiv publications are supported.")

    normalised = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
    return normalised


def is_safe_netloc(hostname: str | None) -> bool:
    if not hostname:
        return False
    if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "metadata.google.internal"):
        return False
    try:
        addr = ipaddress.ip_address(hostname)
        for block in _PRIVATE_BLOCKS:
            if addr in block:
                return False
        return True
    except ValueError:
        pass
    try:
        import socket

        addr = socket.getaddrinfo(hostname, 80, family=socket.AF_INET)[0][4][0]
        ip = ipaddress.ip_address(addr)
        for block in _PRIVATE_BLOCKS:
            if ip in block:
                return False
        return True
    except (OSError, IndexError):
        return False


def is_supported_domain(hostname: str | None) -> bool:
    if not hostname:
        return False
    if BEEHIIV_DOMAIN_RE.match(hostname):
        return True
    return False


def check_redirect_safety(redirect_url: str) -> str:
    parsed = urlparse(redirect_url)
    if not parsed.scheme or not parsed.netloc:
        raise UnsafeURLError("Redirect target is invalid.")
    if parsed.scheme not in ("http", "https"):
        raise UnsafeURLError("Redirect target uses an unsupported protocol.")
    if not is_safe_netloc(parsed.hostname):
        raise UnsafeURLError("Redirect target is unsafe.")
    return redirect_url
