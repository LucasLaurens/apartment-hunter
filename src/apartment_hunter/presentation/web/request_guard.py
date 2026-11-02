"""Who may talk to the local web server: the page it serves, and nobody else.

Binding to 127.0.0.1 only keeps other machines out. A page the hunter visits elsewhere
can still reach it, two ways:

- DNS rebinding: the page re-points its own domain at 127.0.0.1 and reads the API as
  same-origin. The Host header then names that domain, so only known hosts are let in.
- Cross-site writes: a plain `<form method=post>` needs no CORS preflight. A write is
  refused when the browser says it comes from another site.
"""

import os
from typing import Final
from urllib.parse import urlsplit

# Set by `hunt serve` before uvicorn imports the app, so a --host other than loopback
# is let in too; read here because uvicorn builds the app from its import string.
SERVE_HOST_ENV: Final = "APARTMENT_HUNTER_SERVE_HOST"
_LOOPBACK_HOSTS: Final = ("127.0.0.1", "localhost")
_EVERY_INTERFACE: Final = "0.0.0.0"
_READ_ONLY_METHODS: Final = frozenset({"GET", "HEAD", "OPTIONS"})
# `none` is the hunter typing the URL or opening a bookmark.
_TRUSTED_FETCH_SITES: Final = frozenset({"same-origin", "none"})


def list_allowed_hosts() -> list[str]:
    served = os.environ.get(SERVE_HOST_ENV, "")
    extra = [served] if served and served not in (*_LOOPBACK_HOSTS, _EVERY_INTERFACE) else []
    return [*_LOOPBACK_HOSTS, *extra]


def is_cross_site_write(method: str, host: str, origin: str | None, fetch_site: str | None) -> bool:
    """True for a write the browser reports as coming from another site.

    `Sec-Fetch-Site` answers first when the browser sends it; `Origin` otherwise. A
    request carrying neither is not from a browser page (curl, the CLI), so it passes.
    """
    if method.upper() in _READ_ONLY_METHODS:
        return False
    if fetch_site:
        return fetch_site not in _TRUSTED_FETCH_SITES
    if origin:
        return urlsplit(origin).netloc != host
    return False
