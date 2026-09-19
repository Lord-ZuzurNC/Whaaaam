"""The HTTP edge: input limits, host matching, and what leaks in an error.

Run: python test_web.py

Nothing here touches the network. `providers.http.requests.get` is replaced with
a function that fails the test, so a regression that starts making real requests
shows up as a failure rather than a slow, flaky pass.
"""

import json
import logging
import os
import shutil
import tempfile
import time

import modlist
import providers
import providers.http
import web
from providers import canonical_url, detect_provider


def _no_network(*args, **kwargs):
    raise AssertionError("the test suite made a real HTTP request")


providers.http.requests.get = _no_network

client = web.app.test_client()


def post(body, raw=False):
    if raw:
        return client.post("/analyze", data=body, content_type="application/json")
    return client.post("/analyze", json=body)


def check_input_limits():
    """Bad shapes are refused with a sentence, not a 500."""
    for body in ([1, 2, 3], "hello", {"urls": 5}, {"urls": {"a": "b"}},
                 {"urls": [1, 2]}, {"urls": ["ok", 7]}):
        r = post(body)
        assert r.status_code == 400, f"{body!r} returned {r.status_code}, expected 400"
        assert r.get_json()["error"], f"{body!r} returned no reason"

    # Not JSON at all, and a Content-Type that lies about it.
    assert post("{not json", raw=True).status_code == 400
    assert client.post("/analyze", data="urls=x").status_code == 400

    # Empty list keeps its own message.
    assert post({"urls": []}).status_code == 400

    # One over the cap is refused before any provider is reached — which is the
    # point: every URL past the cap would spend the operator's API key.
    over = {"urls": ["https://modrinth.com/mod/sodium"] * (web.MAX_URLS + 1)}
    r = post(over)
    assert r.status_code == 413, f"{web.MAX_URLS + 1} URLs returned {r.status_code}"
    assert str(web.MAX_URLS) in r.get_json()["error"]

    # A body over MAX_CONTENT_LENGTH is refused by Werkzeug before the handler.
    huge = json.dumps({"urls": ["https://modrinth.com/mod/x" + "a" * 1000] * 400})
    assert len(huge) > web.app.config["MAX_CONTENT_LENGTH"]
    assert post(huge, raw=True).status_code == 413

    print(f"input limits: bad shapes 400, over {web.MAX_URLS} URLs 413, oversized body 413")


def check_host_allowlist():
    """A host is matched exactly. A substring test accepted all of these."""
    spoofed = [
        "http://curseforge.com@169.254.169.254/latest/meta-data/",
        "https://curseforge.com.attacker.example/minecraft/mc-mods/jei",
        "https://modrinth.com.attacker.example/mod/sodium",
        "https://attacker.example/?ref=modrinth.com",
        "https://attacker.example/curseforge.com/jei",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "",
    ]
    for url in spoofed:
        assert detect_provider(url) is None, f"{url!r} was accepted"
        assert not modlist.is_valid_mod_url(url), f"{url!r} passed is_valid_mod_url"

    legitimate = {
        "https://www.curseforge.com/minecraft/mc-mods/jei": "curseforge",
        "https://curseforge.com/minecraft/mc-mods/jei": "curseforge",
        "https://modrinth.com/mod/sodium": "modrinth",
        "https://www.modrinth.com/mod/sodium": "modrinth",
    }
    for url, want in legitimate.items():
        assert detect_provider(url) == want, f"{url!r} -> {detect_provider(url)!r}"
        assert modlist.is_valid_mod_url(url), f"{url!r} was rejected"

    # The two checks must never disagree; that is why one now calls the other.
    for url in spoofed + list(legitimate):
        assert modlist.is_valid_mod_url(url) == (detect_provider(url) is not None)

    # A spoofed host reaches the results table as an unchecked row, not a lookup.
    results = modlist.check_urls(["https://curseforge.com.attacker.example/mc-mods/jei"])
    assert results[0]["error"] == modlist.NOT_A_MOD_LINK
    assert "versions" not in results[0]

    print(f"host allowlist: {len(spoofed)} spoofed hosts refused, "
          f"{len(legitimate)} real ones accepted")


def check_canonical_url():
    """The echoed URL is rebuilt, so nothing decorative survives into an <a href>."""
    cases = {
        "https://WWW.CurseForge.com/minecraft/mc-mods/jei":
            "https://www.curseforge.com/minecraft/mc-mods/jei",
        "https://modrinth.com/mod/sodium?utm=x#frag":
            "https://modrinth.com/mod/sodium",
        "https://user:pw@modrinth.com/mod/sodium":
            "https://modrinth.com/mod/sodium",
    }
    for raw, want in cases.items():
        got = canonical_url(raw)
        assert got == want, f"{raw!r} -> {got!r}, expected {want!r}"

    # `.port` parses lazily and raises out of range. canonical_url is documented
    # as total, so it must not raise for anything, and an unusable port must be
    # refused at the gate rather than after a request has been spent on it.
    for hostile in ("https://modrinth.com:99999/mod/sodium", "", "not a url",
                    "http://[::1/x", "https://modrinth.com:0/mod/x"):
        canonical_url(hostile)  # must not raise
    assert detect_provider("https://modrinth.com:99999/mod/sodium") is None
    leaked = modlist.fetch_mod_info("https://modrinth.com:99999/mod/sodium")["error"]
    assert "Port out of range" not in leaked, leaked

    print(f"canonical url: {len(cases)} forms normalised, hostile ports refused")


def check_error_copy():
    """An internal failure never returns its own text to the browser."""
    leaky = "/home/someone/Lab/Whaaaam/cache/curseforge/jei_238222/page-0.json"
    original = providers.PROVIDERS["curseforge"]

    # Capture the log rather than let it print: the detail belonging in the log
    # and not in the response is the whole property under test, so assert both.
    records = []

    class _Capture(logging.Handler):
        def emit(self, record):
            records.append(self.format(record))

    handler = _Capture()
    modlist.log.addHandler(handler)
    modlist.log.propagate = False

    providers.PROVIDERS["curseforge"] = lambda url: (_ for _ in ()).throw(
        OSError(f"[Errno 28] No space left on device: '{leaky}'"))
    try:
        result = modlist.fetch_mod_info("https://www.curseforge.com/minecraft/mc-mods/jei")
    finally:
        providers.PROVIDERS["curseforge"] = original

    assert any(leaky in r for r in records), "the failure was not logged anywhere"
    assert leaky not in result["error"], "the absolute cache path reached the client"
    assert "Errno" not in result["error"], "a raw errno reached the client"
    assert result["error"] == "This mod could not be checked right now"

    # Provider copy is written for the user and still comes through untouched.
    from providers.http import ProviderError
    providers.PROVIDERS["curseforge"] = lambda url: (_ for _ in ()).throw(
        ProviderError("CurseForge rejected the API key (HTTP 403). Check CF_API_KEY."))
    try:
        kept = modlist.fetch_mod_info("https://www.curseforge.com/minecraft/mc-mods/jei")
    finally:
        providers.PROVIDERS["curseforge"] = original
    assert "CF_API_KEY" in kept["error"], "curated provider copy was swallowed"

    # json.JSONDecodeError subclasses ValueError. Catching ValueError to mean
    # "copy written for the user" leaked raw parser text from a truncated cache
    # file, which is the most likely internal fault this code has.
    assert issubclass(json.JSONDecodeError, ValueError)
    for blow_up in (lambda url: json.loads("{trunc"),
                    lambda url: (_ for _ in ()).throw(ValueError("Expecting value")),
                    lambda url: (_ for _ in ()).throw(KeyError("id"))):
        providers.PROVIDERS["curseforge"] = blow_up
        try:
            r = modlist.fetch_mod_info("https://www.curseforge.com/minecraft/mc-mods/jei")
        finally:
            providers.PROVIDERS["curseforge"] = original
        assert r["error"] == "This mod could not be checked right now", r["error"]

    modlist.log.removeHandler(handler)
    modlist.log.propagate = True

    print("error copy: internal detail logged not returned, provider copy preserved")


def check_optional_api_key():
    """CF_API_KEY is only needed to check a CurseForge mod. Without it the app
    still imports, a Modrinth-only list still works, and a CurseForge URL comes
    back as a row saying why rather than taking the whole app down."""
    import subprocess
    import sys
    # Empty, not absent: python-dotenv never overrides a variable that is already
    # set, so a developer's .env cannot slip a real key into the child.
    env = dict(os.environ, CF_API_KEY="",
               PYTHONPATH=os.path.dirname(os.path.abspath(__file__)))
    started = subprocess.run([sys.executable, "-c", "import web"],
                             env=env, cwd=tempfile.gettempdir(), capture_output=True, text=True)
    assert started.returncode == 0, f"app did not start without a key:\n{started.stderr}"

    saved = os.environ.pop("CF_API_KEY", None)
    try:
        row = modlist.fetch_mod_info("https://www.curseforge.com/minecraft/mc-mods/jei")
    finally:
        if saved is not None:
            os.environ["CF_API_KEY"] = saved
    # _no_network would surface as the generic sentence; this proves the
    # missing key was caught before any request was attempted.
    assert "no CurseForge API key" in row["error"], row
    print("api key: optional at startup, required only for a CurseForge mod")


def check_slug_validation():
    """A slug that is not a slug never reaches the URL builder."""
    from providers.modrinth import slug_from_url

    # Not slugs: traversal, and anything below Modrinth's 3-character minimum.
    for url in ("https://modrinth.com/mod/..%2f..%2fadmin",
                "https://modrinth.com/mod/a%2Fb",
                "https://modrinth.com/mod/ab"):
        assert slug_from_url(url) is None, f"{url!r} -> {slug_from_url(url)!r}"

    # A decoration on a shared link is discarded, not treated as part of the
    # slug — it must neither reach the API URL nor break a legitimate check.
    for url in ("https://modrinth.com/mod/sodium",
                "https://modrinth.com/mod/sodium?utm_source=x",
                "https://modrinth.com/mod/sodium#gallery",
                "https://modrinth.com/mod/sodium/"):
        assert slug_from_url(url) == "sodium", f"{url!r} -> {slug_from_url(url)!r}"
    assert slug_from_url("https://modrinth.com/project/jei") == "jei"
    print("slug validation: traversal refused, decorated links still resolve")


def check_routes_and_headers():
    """The destructive endpoint is gone; the page carries its headers."""
    assert client.post("/clear_cache").status_code == 404, "/clear_cache still answers"
    assert "/clear_cache" not in {str(r) for r in web.app.url_map.iter_rules()}

    page = client.get("/")
    assert page.status_code == 200
    csp = page.headers.get("Content-Security-Policy", "")
    assert "frame-ancestors 'none'" in csp
    assert "script-src 'self'" in csp
    assert page.headers.get("X-Content-Type-Options") == "nosniff"
    assert page.headers.get("Referrer-Policy") == "no-referrer"

    # No CORS layer at all: the page and the API are the same origin.
    assert "Access-Control-Allow-Origin" not in client.options(
        "/analyze", headers={"Origin": "https://evil.example",
                             "Access-Control-Request-Method": "POST"}).headers
    assert "Access-Control-Allow-Origin" not in post(
        {"urls": []}).headers

    print("routes: /clear_cache removed, security headers set, no CORS reflection")


def check_deadline():
    """A slow provider cannot hold the request open indefinitely."""
    original = providers.PROVIDERS["modrinth"]

    def slow(url):
        time.sleep(2)   # far past the deadline; the result is never used
        return {"name": "late", "provider": "modrinth", "id": "1", "slug": "x",
                "versions": [("1.20.1", "Fabric")], "url": url}

    providers.PROVIDERS["modrinth"] = slow
    urls = ["https://modrinth.com/mod/sodium",
            "https://modrinth.com/mod/lithium",
            "nonsense"]
    try:
        start = time.monotonic()
        results = modlist.check_urls(urls, deadline=0.3)
        elapsed = time.monotonic() - start
    finally:
        providers.PROVIDERS["modrinth"] = original

    assert elapsed < 1.5, f"deadline did not bound the call ({elapsed:.2f}s)"
    # Invariant 1: a mod that could not be checked is never dropped.
    assert len(results) == len(urls), f"{len(results)} rows for {len(urls)} URLs"
    reasons = {r["url"]: r["error"] for r in results}
    assert reasons["https://modrinth.com/mod/sodium"] == modlist.TOOK_TOO_LONG
    assert reasons["nonsense"] == modlist.NOT_A_MOD_LINK
    print(f"deadline: bounded at {elapsed:.2f}s, all {len(urls)} URLs still reported")


def check_cache_containment_and_budget():
    """The cache lives in one place, and it has a ceiling."""
    from providers import cache_path, enforce_cache_budget

    real_root = providers.CACHE_ROOT
    tmp_root = tempfile.mkdtemp(prefix="whaaaam-cache-")
    providers.CACHE_ROOT = tmp_root
    try:
        # Resolved against the module, not the working directory: starting the
        # app from elsewhere used to write one cache and clear a different one.
        here = cache_path("modrinth", "sodium", "AAA")
        cwd = os.getcwd()
        os.chdir(tempfile.gettempdir())
        try:
            assert cache_path("modrinth", "sodium", "AAA") == here
        finally:
            os.chdir(cwd)
        assert here.startswith(tmp_root)

        # safe_name permits ".", so assert the containment intention directly.
        assert cache_path("modrinth", "..", "..").startswith(tmp_root)

        paths = []
        for i in range(5):
            path = cache_path("modrinth", f"mod{i}", str(i), 0)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("x" * 100_000)
            stamp = time.time() - 1000 + i          # mod0 oldest, mod4 newest
            os.utime(path, (stamp, stamp))
            paths.append(path)

        removed = enforce_cache_budget(max_bytes=250_000)
        alive = [p for p in paths if os.path.exists(p)]
        assert removed == 3, f"evicted {removed}, expected 3"
        assert paths[0] not in alive and paths[4] in alive, "eviction was not oldest-first"
        assert sum(os.path.getsize(p) for p in alive) <= 250_000
        assert enforce_cache_budget(max_bytes=250_000) == 0, "evicted when under budget"
        print(f"cache: one root regardless of CWD, oldest-first eviction ({removed} removed)")
    finally:
        providers.CACHE_ROOT = real_root
        shutil.rmtree(tmp_root, ignore_errors=True)


def check_curseforge_is_cached():
    """A CurseForge check is one search request, so that search is what gets
    cached. It used to be uncached, and a re-check went back to the network."""
    from providers import curseforge

    class Reply:
        def json(self):
            return {"data": [{"id": 238222, "name": "JEI",
                              "latestFilesIndexes": [{"gameVersion": "1.20.1", "modLoader": 1}]}]}

    calls = []
    real_request, real_root = curseforge.safe_request, providers.CACHE_ROOT
    saved_key = os.environ.get("CF_API_KEY")
    tmp_root = tempfile.mkdtemp(prefix="whaaaam-cache-")
    providers.CACHE_ROOT = tmp_root
    curseforge.safe_request = lambda *a, **k: calls.append(a) or Reply()
    os.environ["CF_API_KEY"] = "test"
    url = "https://www.curseforge.com/minecraft/mc-mods/jei"
    try:
        first, second = curseforge.get_mod_data(url), curseforge.get_mod_data(url)
        assert len(calls) == 1, f"re-check made {len(calls)} requests, expected 1"
        assert first == second and first["versions"] == [("1.20.1", "Forge")]
        # Named by the mod's id like every other cache folder, not "{slug}_search".
        folder = os.path.join(tmp_root, "curseforge")
        assert os.listdir(folder) == ["jei_238222"], os.listdir(folder)
        assert os.path.exists(os.path.join(folder, "jei_238222", "search.json"))

        # The cache is warm, but a keyless server still says it has no key.
        os.environ["CF_API_KEY"] = ""
        try:
            curseforge.get_mod_data(url)
            raise AssertionError("keyless check answered from the cache")
        except providers.http.ProviderError as exc:
            assert "no CurseForge API key" in str(exc)
        print("curseforge: search cached, key still required")
    finally:
        curseforge.safe_request, providers.CACHE_ROOT = real_request, real_root
        if saved_key is None:
            os.environ.pop("CF_API_KEY", None)
        else:
            os.environ["CF_API_KEY"] = saved_key
        shutil.rmtree(tmp_root, ignore_errors=True)


if __name__ == "__main__":
    check_input_limits()
    check_host_allowlist()
    check_canonical_url()
    check_error_copy()
    check_optional_api_key()
    check_slug_validation()
    check_routes_and_headers()
    check_deadline()
    check_cache_containment_and_budget()
    check_curseforge_is_cached()
    print("ok")
