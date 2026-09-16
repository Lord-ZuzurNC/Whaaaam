import os
import time
import json
import requests
import urllib.parse
import re
from datetime import timedelta
from dotenv import load_dotenv
from providers import cache_path, is_cache_expired
from providers.http import request as http_request
from compat import normalize_loader, is_release_version

load_dotenv()
API_BASE = "https://api.curseforge.com/v1"
GAME_ID = 432
CACHE_TTL = timedelta(hours=24)

API_KEY = os.getenv("CF_API_KEY")
if not API_KEY:
    raise EnvironmentError("Missing CF_API_KEY in environment")

HEADERS = {"Accept": "application/json", "x-api-key": API_KEY}


def safe_request(url, params=None, retries=3, delay=1, timeout=10):
    return http_request("CurseForge", url, headers=HEADERS, params=params,
                        retries=retries, delay=delay, timeout=timeout)


def cached_fetch(provider, slug, id, page, url, params):
    """Returns (data, from_cache). Callers throttle only on a real request."""
    cache_file = cache_path(provider, slug, id, page)
    if os.path.exists(cache_file) and not is_cache_expired(cache_file, 24):
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f), True

    r = safe_request(url, params=params)
    data = r.json()
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return data, False


def version_key(v):
    # ensure v is a string
    v = str(v)
    # split by ., -, +, _
    parts = re.split(r"[.\-+_]", v)
    key = []
    for p in parts:
        try:
            key.append(int(p))
        except ValueError:
            key.append(float('inf'))
    return tuple(key)


def normalize_slug(raw_slug: str) -> str:
    # Decode any percent-encoding
    slug = urllib.parse.unquote(raw_slug)
    # Remove emoji / non-ASCII chars
    slug = re.sub(r"[^\x00-\x7F]+", "", slug)
    # Trim whitespace / odd symbols
    return slug.strip(" /")


# CurseForge's modLoader enum. 0=Any, 2=Cauldron and 3=LiteLoader are not part
# of this product's loader vocabulary.
MOD_LOADER = {1: "Forge", 4: "Fabric", 5: "Quilt", 6: "NeoForge"}


def index_pairs(mod):
    """(version, loader) pairs from `latestFilesIndexes`, which ships with the
    search response we already made. One request instead of one per 50 files."""
    pairs = set()
    for entry in mod.get("latestFilesIndexes") or []:
        version = str(entry.get("gameVersion", ""))
        loader = MOD_LOADER.get(entry.get("modLoader"))
        if loader and is_release_version(version):
            pairs.add((version, loader))
    return pairs


def loaders_for_file(file_entry):
    """Infer loaders from a file's version tags, then its filename. A file we
    cannot attribute contributes nothing: an unattributable ancient jar is not a
    compatibility fact, and naming it "Unknown" put a fake loader in the verdict."""
    found = set()
    for token in (str(t).lower() for t in file_entry.get("gameVersions", [])):
        if "fabric" in token:
            found.add("Fabric")
        if "neoforge" in token or "neo-forge" in token:
            found.add("NeoForge")
        if "quilt" in token:
            found.add("Quilt")
        if "forge" in token and "neoforge" not in token and "neo-forge" not in token:
            found.add("Forge")
    if found:
        return found

    name = str(file_entry.get("fileName", "")).lower()
    if "fabric" in name:
        return {"Fabric"}
    if "neoforge" in name or "neo-forge" in name:
        return {"NeoForge"}
    if "quilt" in name:
        return {"Quilt"}
    if "forge" in name:
        return {"Forge"}
    return set()


def paged_pairs(slug, id):
    """Fallback: walk every file. Only used when a mod has no latestFilesIndexes."""
    all_files = []
    page = 0
    page_size = 50
    while True:
        files_url = f"{API_BASE}/mods/{id}/files"
        params = {"index": page * page_size, "pageSize": page_size}
        data, from_cache = cached_fetch("curseforge", slug, id, page, files_url, params)
        files = data.get("data", [])
        if not files:
            break
        all_files.extend(files)
        if len(files) < page_size:
            break
        page += 1
        if not from_cache:
            time.sleep(0.2)  # be polite to the API, but never to the local disk

    pairs = set()
    for entry in all_files:
        loaders = loaders_for_file(entry)
        if not loaders:
            continue
        for version in entry.get("gameVersions", []):
            if is_release_version(version):
                for loader in loaders:
                    pairs.add((str(version), normalize_loader(loader)))
    return pairs


def get_mod_data(url: str) -> dict:
    raw_slug = url.rstrip("/").split("/")[-1]
    slug = normalize_slug(raw_slug)

    # resolve mod id via search
    search_url = f"{API_BASE}/mods/search"
    params = {"gameId": GAME_ID, "slug": slug}
    resp = safe_request(search_url, params=params)
    mods = resp.json().get("data", [])
    if not mods:
        raise ValueError(f"No mod called '{slug}' on CurseForge")

    best_mod = max(mods, key=lambda m: (m.get("downloadCount", 0), m.get("name", "")))
    id = str(best_mod["id"])
    mod_name = best_mod.get("name", slug)

    pairs = index_pairs(best_mod)

    # The index covers every real release pair for every mod tested. Paging the
    # full file list is the fallback for the rare mod that has no index.
    if not pairs:
        pairs = paged_pairs(slug, id)

    sorted_pairs = sorted(pairs, key=lambda x: (version_key(x[0]), x[1]), reverse=True)

    return {
        "name": mod_name,
        "id": id,
        "slug": slug,
        "provider": "curseforge",
        "versions": sorted_pairs,
        "url": url,
    }
