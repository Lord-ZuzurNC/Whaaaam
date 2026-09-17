import json
import os
import re
import threading
import time
from typing import Optional
from urllib.parse import urlparse, urlunparse


# --- safe name + cache path helpers (defined before importing providers) ---

# The one definition. `cache_path` used to join from the literal "cache", which
# resolves against the *working directory*, while `modlist` derived an absolute
# path from its own location: start the app from anywhere but the repository root
# and the two disagreed, so clearing the cache silently missed the real one.
CACHE_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")

# Oldest-first eviction keeps the cache from growing without limit. The TTL
# governs freshness; nothing governed size, and one full request can write ~92 MB.
CACHE_MAX_BYTES = 256 * 1024 * 1024


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", str(name))


def cache_path(provider: str, slug: str, mod_id: str, page: int | None = None) -> str:
    folder = os.path.join(CACHE_ROOT, safe_name(provider),
                          f"{safe_name(slug)}_{safe_name(mod_id)}")
    # safe_name permits ".", so ".." survives it. Nothing reachable produces a
    # bare ".." component today — the trailing _{id} prevents it — but that is a
    # property of string concatenation, not an intention. Assert the intention.
    if not os.path.realpath(folder).startswith(os.path.realpath(CACHE_ROOT) + os.sep):
        raise ValueError("cache path escaped the cache root")
    os.makedirs(folder, exist_ok=True)
    if page is None:
        return folder
    return os.path.join(folder, f"page-{page}.json")


def write_cache(path: str, data) -> None:
    """Write a cache file atomically.

    Eight workers share this tree with no lock, and `dedupe()` runs after
    fetching, so two threads in one request can write the same file. Writing
    straight to the final path left truncated JSON that the next read raised on.
    A rename within the same directory is atomic.
    """
    tmp = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def enforce_cache_budget(max_bytes: int = CACHE_MAX_BYTES) -> int:
    """Delete the oldest cache files until the tree fits in `max_bytes`.

    Returns the number of files removed. Called after a write, so the cost is
    paid only on a real fetch.

    ponytail: walks the whole tree per write, which is fine at this budget
    (~1k files); if the budget grows by an order of magnitude, keep a running
    total in a sidecar file instead of re-walking.
    """
    entries, total = [], 0
    for root, _dirs, files in os.walk(CACHE_ROOT):
        for name in files:
            path = os.path.join(root, name)
            try:
                stat = os.stat(path)
            except OSError:
                continue
            entries.append((stat.st_mtime, stat.st_size, path))
            total += stat.st_size

    if total <= max_bytes:
        return 0

    removed = 0
    for _mtime, size, path in sorted(entries):
        try:
            os.remove(path)
        except OSError:
            continue
        total -= size
        removed += 1
        if total <= max_bytes:
            break
    return removed


def is_cache_expired(path: str, ttl_hours: int = 24) -> bool:
    if not os.path.exists(path):
        return True
    return (time.time() - os.path.getmtime(path)) > (ttl_hours * 3600)


# --- provider detection ---

# The one place that decides which hosts this product accepts. `modlist.is_valid_mod_url`
# defers to it, so a host can never be allowed by one check and refused by the other.
ALLOWED_HOSTS = {
    "curseforge.com": "curseforge",
    "www.curseforge.com": "curseforge",
    "modrinth.com": "modrinth",
    "www.modrinth.com": "modrinth",
}


def detect_provider(url: str) -> Optional[str]:
    """Exact host match, never a substring one.

    `"curseforge.com" in url` accepted `curseforge.com.attacker.example` and
    `http://curseforge.com@10.0.0.1/`, which urlparse reads as the hosts
    `attacker.example` and `10.0.0.1`. Matching on `.hostname` drops userinfo
    and the port, so only the registrable host is compared.
    """
    if not url or not isinstance(url, str):
        return None
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    if parsed.scheme not in ("http", "https"):
        return None
    try:
        parsed.port  # lazily validated; raises for a port outside 0-65535
    except ValueError:
        return None
    return ALLOWED_HOSTS.get((parsed.hostname or "").lower())


def canonical_url(url: str) -> str:
    """The URL the browser renders as the mod's link, rebuilt from its parts.

    The path is kept — it is what identifies the mod, and it varies by section
    (mc-mods, modpacks, shaders) so it cannot be reconstructed from the slug.
    Userinfo, query and fragment are dropped and the host is lowercased, so
    nothing decorative survives into an <a href> or an export.
    """
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        # .port parses lazily and raises for an out-of-range value, so reading it
        # outside this try made a function written to be total raise instead.
        port = parsed.port
    except ValueError:
        return url
    if not host:
        return url
    if port:
        host = f"{host}:{port}"
    return urlunparse((parsed.scheme.lower(), host, parsed.path, "", "", ""))


# --- import provider implementations (AFTER helpers are defined to avoid circular import) ---
from .curseforge import get_mod_data as curseforge_get_mod_data
from .modrinth import get_mod_data as modrinth_get_mod_data

PROVIDERS = {
    "curseforge": curseforge_get_mod_data,
    "modrinth": modrinth_get_mod_data,
}
