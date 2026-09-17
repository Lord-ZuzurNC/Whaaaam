"""Turning a list of pasted URLs into checked mod results.

Shared by both interfaces so they cannot drift: `web.py` serves this over HTTP,
`main.py` calls it directly. Every entry that goes in comes back out — a URL that
could not be resolved returns an `error` entry rather than disappearing.
"""

import logging
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, wait

from providers import CACHE_ROOT, PROVIDERS, detect_provider
from providers.http import ProviderError

log = logging.getLogger(__name__)

MAX_WORKERS = 8

# A whole check is bounded, not just its length. Without this, 200 URLs against
# unresponsive upstreams held one worker for ~14 minutes, and four such requests
# denied the service to everyone else. The browser gives up at 60s, so finish first.
CHECK_DEADLINE = 45

NOT_A_MOD_LINK = "Not a CurseForge or Modrinth link"
TOOK_TOO_LONG = "Not fetched before the check ran out of time"


def is_valid_mod_url(url):
    """A URL is valid exactly when a provider claims its host.

    This used to carry its own substring host test, which disagreed with
    `detect_provider` about what counted as a CurseForge link. One check now.
    """
    return detect_provider(url) is not None


def fetch_mod_info(url):
    provider_name = detect_provider(url)
    if not provider_name:
        return {"url": url, "error": NOT_A_MOD_LINK}

    get_mod_data = PROVIDERS.get(provider_name)
    if get_mod_data is None:
        return {"url": url, "error": "That site is not supported yet"}

    try:
        mod_info = get_mod_data(url)
    except ProviderError as exc:
        # The one exception type that means "a sentence written for the person
        # who pasted the URL". Everything else is internal and gets suppressed.
        return {"url": url, "error": str(exc)}
    except Exception:
        # Anything else stringifies with internal detail — an OSError from the
        # cache write carries the absolute path, which the results table would
        # render verbatim. Log it; tell the user only what they can act on.
        log.exception("check failed for %s", url)
        return {"url": url, "error": "This mod could not be checked right now"}

    return {
        "name": mod_info.get("name"),
        "provider": mod_info.get("provider"),
        "id": mod_info.get("id"),
        "slug": mod_info.get("slug"),
        "versions": mod_info.get("versions", []),
        "url": mod_info.get("url") or url,
    }


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


def check_urls(urls, max_workers=MAX_WORKERS, deadline=CHECK_DEADLINE):
    """Check every URL, preserving input order so results are reproducible.

    Bounded in time: a mod still being fetched when the deadline passes comes
    back as a row saying so. It is never dropped — an unchecked mod stays in the
    table and in the verdict's denominator (Invariant 1), and "took too long" is
    a reason like any other.
    """
    # Deduped up front rather than only in `dedupe()` afterwards: a URL pasted
    # twice used to cost two outbound requests, and if one copy finished while
    # the other hit the deadline the same mod produced two rows — one checked,
    # one not — inflating the verdict's denominator.
    urls = list(dict.fromkeys(urls))
    results = [None] * len(urls)
    pool = ThreadPoolExecutor(max_workers=max_workers)
    try:
        jobs = {}
        for i, url in enumerate(urls):
            if is_valid_mod_url(url):
                jobs[pool.submit(fetch_mod_info, url)] = i
            else:
                results[i] = {"url": url, "error": NOT_A_MOD_LINK}

        done, _pending = wait(jobs, timeout=deadline)
        for future, i in jobs.items():
            if future in done:
                results[i] = future.result()
            else:
                future.cancel()
                # Flagged, not just worded: the verdict has to tell an unfetched
                # mod apart from an unresolvable one.
                results[i] = {"url": urls[i], "error": TOOK_TOO_LONG, "timed_out": True}
    finally:
        # Never wait here: the whole point of the deadline is that the response
        # does not block on work that has already overrun it. `with` would.
        pool.shutdown(wait=False, cancel_futures=True)
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
