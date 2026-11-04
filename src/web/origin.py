"""Dashboard public origin, independent of forwarded-header and client-IP trust.

``PUBLIC_BASE_URL`` is optional. Without it the dashboard works out its own address from
what the *browser* proves about the request (``Origin`` + ``Sec-Fetch-Site: same-origin``),
so it also works behind an HTTPS reverse proxy that forwards plain HTTP and no forwarded
headers. No ``X-Forwarded-*`` header is ever trusted.
"""

from __future__ import annotations

import re
from ipaddress import IPv4Address
from urllib.parse import urlsplit

from pydantic import AnyHttpUrl
from starlette.requests import HTTPConnection


_ORIGIN = re.compile(r"https?://(?:\[[0-9a-fA-F:.]+\]|[A-Za-z0-9_.-]+)(?::[0-9]{1,5})?")


class DashboardOrigin:
    def __init__(self, public_base_url: str = ""):
        self.public_origin = self._parse(public_base_url) if public_base_url else None

    @staticmethod
    def _parse(value: str) -> str:
        try:
            # Reject characters URL parsers may silently discard or reinterpret.
            if any(char.isspace() or ord(char) < 32 or char in "\\%?#" for char in value):
                raise ValueError
            parts = urlsplit(value)
            # Use browser-compatible serialization, including mapped IPv6 and IDNA.
            url = AnyHttpUrl(value)
            if (
                parts.scheme not in ("http", "https")
                or not parts.netloc
                or parts.path not in ("", "/")
                or parts.username is not None
                or parts.password is not None
                or not re.fullmatch(r"(?:\[[0-9a-fA-F:.]+\]|[^:\[\]]+)(?::[0-9]+)?", parts.netloc)
                or not url.host
                or parts.netloc.endswith(":")
                or url.port is None
                or not 1 <= url.port <= 65535
                or (":" not in url.host and not re.fullmatch(r"[a-z0-9_.-]+", url.host))
            ):
                raise ValueError
            host = parts.hostname or ""
            if ":" not in host and re.fullmatch(r"[0-9]+|0x[0-9a-f]*", host.removesuffix(".").rsplit(".", 1)[-1]):
                # Require dotted decimal instead of legacy short/octal/hex IPv4 forms.
                IPv4Address(host.removesuffix("."))
            return str(url).removesuffix("/")
        except (ValueError, UnicodeError):
            # The supplied URL could contain accidentally pasted credentials.
            raise ValueError(
                "PUBLIC_BASE_URL must be one absolute http(s) root URL without "
                "credentials, a path, query, or fragment"
            ) from None

    @staticmethod
    def _browser_origin(connection: HTTPConnection) -> str | None:
        """Return the page origin when the browser itself vouches that it is same-origin.

        ``Sec-Fetch-Site`` is set by the browser (scripts and other sites cannot forge or
        override it), and ``same-origin`` means the requesting page's origin is exactly the
        origin it is talking to. Together with the ``Origin`` header this reveals the real
        public scheme/host/port even when a proxy rewrites Host or downgrades HTTPS to HTTP.
        Older browsers that do not send it fall back to the request-derived value.
        """
        if connection.headers.get("sec-fetch-site") != "same-origin":
            return None
        origin = connection.headers.get("origin", "")
        return origin.lower() if _ORIGIN.fullmatch(origin) else None

    def expected(self, connection: HTTPConnection) -> str:
        if self.public_origin is not None:
            return self.public_origin
        if (proven := self._browser_origin(connection)) is not None:
            return proven
        scheme = "https" if connection.scope["scheme"] in ("https", "wss") else "http"
        return f"{scheme}://{connection.headers.get('host', '')}"

    def secure_cookie(self, connection: HTTPConnection) -> bool:
        if self.public_origin is not None:
            return self.public_origin.startswith("https://")
        if (proven := self._browser_origin(connection)) is not None:
            return proven.startswith("https://")
        return connection.scope["scheme"] in ("https", "wss")


def lenient_origin(value: str) -> str:
    """Best-effort public origin from a loosely written value; ``""`` if it is not one.

    Used for fallback variables such as ``DATABASE_URL`` on hosts that only offer a
    generic variable list. Accepts ``https://site.example/``, ``site.example`` (https is
    assumed) and drops any path/query. Database URLs (``postgres://...``), credentials and
    anything else that is not a web address yield ``""`` instead of raising.
    """
    value = value.strip().strip("\"'")
    if not value:
        return ""
    if "://" not in value:
        value = "https://" + value
    try:
        parts = urlsplit(value)
        if parts.scheme.lower() not in ("http", "https") or not parts.netloc:
            return ""
        return DashboardOrigin._parse(f"{parts.scheme.lower()}://{parts.netloc}")
    except ValueError:
        return ""
