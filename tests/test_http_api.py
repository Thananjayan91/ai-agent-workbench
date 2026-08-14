import pytest

from backend.tools.http_api import UnsafeUrlError, _assert_safe_url


def test_rejects_non_http_scheme():
    with pytest.raises(UnsafeUrlError):
        _assert_safe_url("file:///etc/passwd")


def test_rejects_loopback_address():
    with pytest.raises(UnsafeUrlError):
        _assert_safe_url("http://127.0.0.1/admin")


def test_rejects_localhost_hostname():
    with pytest.raises(UnsafeUrlError):
        _assert_safe_url("http://localhost:8000/secrets")


def test_rejects_link_local_metadata_address():
    with pytest.raises(UnsafeUrlError):
        _assert_safe_url("http://169.254.169.254/latest/meta-data/")


def test_allows_public_domain(monkeypatch):
    from backend.tools import http_api

    monkeypatch.setattr(http_api.socket, "gethostbyname", lambda host: "93.184.216.34")
    _assert_safe_url("https://example.com/page")  # should not raise


def test_domain_allowlist_blocks_other_domains(monkeypatch):
    from backend import config

    monkeypatch.setattr(config.settings, "http_tool_allowed_domains", "example.com")
    with pytest.raises(UnsafeUrlError):
        _assert_safe_url("https://other-domain.test/page")
