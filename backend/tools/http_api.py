import ipaddress
import socket
from urllib.parse import urlparse

import requests

from backend.config import settings

_MAX_RESPONSE_CHARS = 4000


class UnsafeUrlError(ValueError):
    pass


def _assert_safe_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeUrlError(f"Unsupported scheme: {parsed.scheme}")
    if not parsed.hostname:
        raise UnsafeUrlError("URL has no hostname")

    allowed = settings.http_allowed_domains
    if allowed and parsed.hostname.lower() not in allowed:
        raise UnsafeUrlError(f"Domain not in allowlist: {parsed.hostname}")

    try:
        resolved_ip = socket.gethostbyname(parsed.hostname)
    except socket.gaierror as e:
        raise UnsafeUrlError(f"Could not resolve host: {parsed.hostname}") from e

    ip = ipaddress.ip_address(resolved_ip)
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
        raise UnsafeUrlError(f"Refusing to call non-public address: {resolved_ip}")


def http_get(url: str, params: dict | None = None) -> dict:
    _assert_safe_url(url)
    response = requests.get(url, params=params, timeout=15)
    text = response.text[:_MAX_RESPONSE_CHARS]
    return {"status_code": response.status_code, "body": text}


SCHEMA = {
    "type": "function",
    "function": {
        "name": "http_get",
        "description": (
            "Make an HTTP GET request to a public API or webpage and return the response body "
            "(truncated). Cannot reach private/internal/loopback addresses."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Full URL, must be http or https"},
                "params": {
                    "type": "object",
                    "description": "Optional query string parameters",
                },
            },
            "required": ["url"],
        },
    },
}


def execute(url: str, params: dict | None = None) -> dict:
    return http_get(url, params)
