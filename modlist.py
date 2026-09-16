"""Turning a list of pasted URLs into checked mod results.

Shared by both interfaces so they cannot drift: `web.py` serves this over HTTP,
`main.py` calls it directly. Every entry that goes in comes back out — a URL that
could not be resolved returns an `error` entry rather than disappearing.
"""

import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from providers import PROVIDERS, detect_provider

MAX_WORKERS = 8
CACHE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")

NOT_A_MOD_LINK = "Not a CurseForge or Modrinth link"


def is_valid_mod_url(url):
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return False
        host = parsed.netloc.lower()
        return "curseforge.com" in host or "modrinth.com" in host
    except Exception:
        return False


def fetch_mod_info(url):
    provider_name = detect_provider(url)
    if not provider_name:
        return {"url": url, "error": NOT_A_MOD_LINK}

    get_mod_data = PROVIDERS.get(provider_name)
    if get_mod_data is None:
        return {"url": url, "error": "That site is not supported yet"}

    try:
        mod_info = get_mod_data(url)
        return {
            "name": mod_info.get("name"),
            "provider": mod_info.get("provider"),
            "id": mod_info.get("id"),
            "slug": mod_info.get("slug"),
            "versions": mod_info.get("versions", []),
            "url": mod_info.get("url") or url,
        }
    except Exception as exc:
        return {"url": url, "error": str(exc)}


def dedupe(results):
    """One row per mod. Failures key on their URL, or every failed lookup would
    collapse into a single row."""
    seen, out = set(), []
    for mod in results:
        if mod.get("provider") and (mod.get("slug") or mod.get("id")):
            key = f"{mod['provider']}|{mod.get('slug') or mod.get('id')}"
        else:
            key = f"url|{mod.get('url')}"
        if key not in seen:
            seen.add(key)
            out.append(mod)
    return out


def check_urls(urls, max_workers=MAX_WORKERS):
    """Check every URL, preserving input order so results are reproducible."""
    results = [None] * len(urls)
    jobs = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for i, url in enumerate(urls):
            if is_valid_mod_url(url):
                jobs[pool.submit(fetch_mod_info, url)] = i
            else:
                results[i] = {"url": url, "error": NOT_A_MOD_LINK}
        for future, i in jobs.items():
            results[i] = future.result()
    return dedupe(results)


def clear_cache():
    """Returns the number of provider directories removed."""
    if not os.path.isdir(CACHE_ROOT):
        return 0
    removed = len([n for n in os.listdir(CACHE_ROOT)
                   if os.path.isdir(os.path.join(CACHE_ROOT, n))])
    shutil.rmtree(CACHE_ROOT)
    os.makedirs(CACHE_ROOT, exist_ok=True)
    return removed
