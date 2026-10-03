import pytest

from app.errors import InvalidURLError, UnsafeURLError, UnsupportedSourceError
from app.security import (
    check_redirect_safety,
    is_safe_netloc,
    is_supported_domain,
    validate_and_normalise_url,
    validate_fetch_url,
)


class TestValidateFetchUrl:
    def test_valid_article_url(self):
        result = validate_fetch_url("https://example.beehiiv.com/p/my-post")
        assert result == "https://example.beehiiv.com/p/my-post"

    def test_private_ip_rejected(self):
        with pytest.raises(UnsafeURLError):
            validate_fetch_url("http://192.168.0.5/p/post")

    def test_non_beehiiv_rejected(self):
        with pytest.raises(UnsupportedSourceError):
            validate_fetch_url("https://example.com/p/post")

    def test_dns_rebinding_blocked(self, monkeypatch):
        import socket

        def fake_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
            if host == "rebind.beehiiv.com":
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))]
            raise OSError("unexpected host")

        monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)
        assert is_safe_netloc("rebind.beehiiv.com") is False
        with pytest.raises(UnsafeURLError):
            validate_fetch_url("https://rebind.beehiiv.com/p/post")


class TestValidateAndNormaliseUrl:
    def test_valid_beehiiv_url(self):
        result = validate_and_normalise_url("https://example.beehiiv.com")
        assert result == "https://example.beehiiv.com"

    def test_valid_custom_subdomain(self):
        result = validate_and_normalise_url("https://my-newsletter.beehiiv.com")
        assert result == "https://my-newsletter.beehiiv.com"

    def test_http_accepted(self):
        result = validate_and_normalise_url("http://example.beehiiv.com")
        assert result.startswith("http://")

    def test_empty_url(self):
        with pytest.raises(InvalidURLError):
            validate_and_normalise_url("")

    def test_whitespace_only(self):
        with pytest.raises(InvalidURLError):
            validate_and_normalise_url("   ")

    def test_no_protocol(self):
        with pytest.raises(InvalidURLError):
            validate_and_normalise_url("example.beehiiv.com")

    def test_ftp_rejected(self):
        with pytest.raises(InvalidURLError):
            validate_and_normalise_url("ftp://example.beehiiv.com")

    def test_localhost_rejected(self):
        with pytest.raises(UnsafeURLError):
            validate_and_normalise_url("http://localhost:8000")

    def test_loopback_rejected(self):
        with pytest.raises(UnsafeURLError):
            validate_and_normalise_url("http://127.0.0.1:8000")

    def test_private_ip_rejected(self):
        with pytest.raises(UnsafeURLError):
            validate_and_normalise_url("http://192.168.1.1")

    def test_non_beehiiv_domain_rejected(self):
        with pytest.raises(UnsupportedSourceError):
            validate_and_normalise_url("https://example.com")

    def test_substack_rejected(self):
        with pytest.raises(UnsupportedSourceError):
            validate_and_normalise_url("https://example.substack.com")


class TestIsSafeNetloc:
    def test_localhost(self):
        assert is_safe_netloc("localhost") is False

    def test_loopback(self):
        assert is_safe_netloc("127.0.0.1") is False

    def test_private_ip(self):
        assert is_safe_netloc("10.0.0.1") is False
        assert is_safe_netloc("172.16.0.1") is False
        assert is_safe_netloc("192.168.1.1") is False

    def test_link_local(self):
        assert is_safe_netloc("169.254.1.1") is False

    def test_public_ip(self):
        assert is_safe_netloc("93.184.216.34") is True

    def test_public_domain(self):
        assert is_safe_netloc("example.com") is True

    def test_beehiiv_domain(self):
        assert is_safe_netloc("test.beehiiv.com") is True

    def test_none(self):
        assert is_safe_netloc(None) is False

    def test_empty(self):
        assert is_safe_netloc("") is False

    def test_cloud_metadata(self):
        assert is_safe_netloc("metadata.google.internal") is False


class TestIsSupportedDomain:
    def test_beehiiv_com(self):
        assert is_supported_domain("test.beehiiv.com") is True

    def test_subdomain_beehiiv_com(self):
        assert is_supported_domain("my-newsletter.beehiiv.com") is True

    def test_non_beehiiv(self):
        assert is_supported_domain("example.com") is False

    def test_substack(self):
        assert is_supported_domain("example.substack.com") is False

    def test_none(self):
        assert is_supported_domain(None) is False

    def test_bad_prefix(self):
        assert is_supported_domain("-bad.beehiiv.com") is False


class TestCheckRedirectSafety:
    def test_safe_redirect(self):
        result = check_redirect_safety("https://example.beehiiv.com/p/post")
        assert result == "https://example.beehiiv.com/p/post"

    def test_redirect_to_localhost(self):
        with pytest.raises(UnsafeURLError):
            check_redirect_safety("http://localhost:8000/evil")

    def test_redirect_to_private_ip(self):
        with pytest.raises(UnsafeURLError):
            check_redirect_safety("http://192.168.1.1/admin")

    def test_redirect_to_non_beehiiv_rejected(self):
        with pytest.raises(UnsupportedSourceError):
            check_redirect_safety("https://example.com/p/post")

    def test_redirect_to_ftp(self):
        with pytest.raises(InvalidURLError):
            check_redirect_safety("ftp://example.com/file")
