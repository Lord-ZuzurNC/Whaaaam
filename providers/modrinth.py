import os
import json
import re
import urllib.parse
from providers.http import ProviderError
from providers.http import request as http_request
from compat import normalize_loader, is_release_version
from providers import (cache_path, canonical_url, enforce_cache_budget,
                       is_cache_expired, write_cache)


API_BASE = "https://api.modrinth.com/v2"
CACHE_TTL_HOURS = 24


def safe_request(url: str, retries: int = 3, delay: int = 1, timeout: int = 10):
    return http_request("Modrinth", url, retries=retries, delay=delay, timeout=timeout)


# Modrinth's own slug charset. Anything outside it is not a slug, so it is not
# worth a request — and it must never reach the URL builder below.
SLUG_RE = re.compile(r"""^[\w!@$()`.+,"'-]{3,64}$""")


def slug_from_url(url: str) -> str | None:
    """The project slug, or None when the last path segment is not one.

    Read from the parsed *path*, so a query string or fragment is discarded
    rather than becoming part of the slug. The old fallback split the raw URL on
    "/", which kept both: `sodium?bogus=1` went straight into the API URL and
    appended a query to the upstream call. A shared link carrying `?utm_source=`
    still resolves to `sodium`, which is the common case and must keep working.
    """
    if not url or not isinstance(url, str):
        return None
    path = urllib.parse.urlparse(url.strip()).path.rstrip("/")
    m = re.search(r"/(project|mod|mods)/([^/]+)$", path)
    slug = urllib.parse.unquote(m.group(2) if m else path.split("/")[-1])
    return slug if SLUG_RE.match(slug) else None


def cached_fetch(provider, slug, id, page, url):
    cache_file = cache_path(provider, slug, id, page)
    if os.path.exists(cache_file) and not is_cache_expired(cache_file, CACHE_TTL_HOURS):
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)

    data = safe_request(url).json()
    write_cache(cache_file, data)
    enforce_cache_budget()
    return data


def version_key(v: str):
    if not isinstance(v, str):
        v = str(v)

    parts = re.split(r"[.\-+_]", v)
    key = []
    for p in parts:
        if p.isdigit():
            key.append(int(p))
        else:
            key.append(float("inf"))
    return tuple(key)


def get_mod_data(url: str) -> dict:
    slug = slug_from_url(url)
    if not slug:
        raise ProviderError("Not a Modrinth mod link")

    quoted = urllib.parse.quote(slug, safe="")
    project_url = f"{API_BASE}/project/{quoted}"
    proj = safe_request(project_url).json()
    mod_name = proj.get("title") or proj.get("name") or slug
    id = str(proj.get("id"))

    # Pagination (even though Modrinth usually returns all at once)
    all_versions = []
    page = 0
    page_size = 100

    while True:
        versions_url = (f"{API_BASE}/project/{quoted}/version"
                        f"?offset={page*page_size}&limit={page_size}")
        data = cached_fetch("modrinth", slug, id, page, versions_url)
        if isinstance(data, dict) and data.get("data"):
            items = data["data"]
        else:
            items = data
        if not items:
            break
        all_versions.extend(items)
        if len(items) < page_size:
            break
        page += 1

    pairs = set()
    for v in all_versions:
        game_versions = v.get("game_versions", []) if isinstance(v, dict) else []
        loaders = v.get("loaders", []) if isinstance(v, dict) else []
        for gv in game_versions:
            if not is_release_version(gv):
                continue
            for loader in loaders:
                # normalize_loader, not capitalize(): the latter produced
                # "Neoforge", which disagreed with the CurseForge spelling.
                pairs.add((str(gv), normalize_loader(str(loader))))

    sorted_pairs = sorted(pairs, key=lambda x: (version_key(x[0]), x[1]), reverse=True)

    return {
        "name": mod_name,
        "id": id,
        "slug": slug,
        "provider": "modrinth",
        "versions": sorted_pairs,
        "url": canonical_url(url),
    }
