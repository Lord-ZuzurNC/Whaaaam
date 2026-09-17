# Security Review — Whaaaam (second pass, post-remediation)

**Date:** 2026-09-17

**Scope:** Full adversarial re-review of the working tree *after* the same-day
remediation recorded in `secure-review-2026-09-17.md`. Static review of every
Python and JavaScript file, plus dynamic probing: Flask `test_client()`, live
`curl` against both the development server and the **documented gunicorn
deployment command**, and direct exercise of `canonical_url`, `detect_provider`,
`slug_from_url` and `fetch_mod_info` with hostile inputs. One real network call
was made to Modrinth to measure cache cost. Reviewed `requirements.txt`,
`requirements-dev.txt`, the installed virtualenv, `.env`, `.gitignore`, git
state, `test_compat.py` and `test_web.py`. Excluded: `.venv/` internals.

**Explicit goal of this pass: find holes in the fixes themselves.** The previous
review and the code under review were produced in the same session, so treating
the remediation as trustworthy would defeat the exercise. Three of the findings
below are defects *in the remediation*.

**Branch reviewed:** `main` (HEAD `5b06064`, plus uncommitted remediation in the
working tree — the fixes are **not committed**)

**Note on filename:** the first pass already wrote `secure-review-2026-09-17.md`
today, and that file is **untracked in git**. Overwriting it would have destroyed
the only copy of the prior report and its remediation record, so this second pass
is written alongside it rather than over it.

---

## A. Executive Summary

**Verdict: NEEDS HUMAN SECURITY REVIEW.**

Confidence: **High** on the application code — it is ~750 LOC, read in full, and
every finding below was reproduced against running code. Confidence **Medium** on
deployment: the operator has stated the target is public internet, the gunicorn
command in `README.md` is now verified to work, but **no CI, no Dockerfile and no
infrastructure-as-code exist in the repository**, so the nginx rate-limiting that
the whole availability story depends on cannot be confirmed to exist anywhere.

The posture is much improved. The previous pass's twelve findings are genuinely
closed: `/clear_cache` is gone (404 verified), the CORS layer is gone, hosts are
matched exactly, input shape and size are validated, security headers ship on
every response, the server binds loopback, and the dependency tree matches its
pins. Those were verified independently here, not taken on trust.

What this pass found is a different and narrower class. **Two of the fixes are
incomplete in ways that reintroduce the exact problem they were written to
solve**, and both were confirmed by execution, not inspection:
`except (ProviderError, ValueError)` was meant to let curated copy through and
suppress internal detail — but `json.JSONDecodeError` **is a subclass of
`ValueError`**, so a truncated cache file leaks raw parser text to the browser;
and `canonical_url()` calls `parsed.port` outside its own `try`, so an
out-of-range port raises a `ValueError` that the same handler then prints to the
user. Beyond that, the application's remaining exposure is availability, not
confidentiality: there is **no server-side deadline on a check at all**, so a
single request can legitimately occupy a worker for ~14 minutes, and with
gunicorn's sync workers four such requests take the entire service down.

No confidentiality or integrity issue was found. There is still no
authentication, no user data, no database and no tenancy, so IDOR/BOLA,
multi-tenant isolation and privilege escalation remain **structurally
inapplicable** — recorded as N/A with reasoning, not padded into findings.

### Top 3 risks

1. **No server-side deadline; four requests deny service to everyone (HIGH)** —
   `modlist.check_urls` has no time budget and `web.py` imposes none; 200 URLs ×
   33s worst case ÷ 8 workers = **13.8 minutes** of one gunicorn sync worker
   (`modlist.py:79-91`, `providers/http.py:21-62`, `web.py:55-73`).
2. **Error-suppression fix is bypassed by `JSONDecodeError` (MEDIUM)** —
   `except (ProviderError, ValueError)` returns `str(exc)` verbatim, and
   `JSONDecodeError` subclasses `ValueError`, so internal parser text reaches the
   response (`modlist.py:44-52`). Confirmed: `Expecting property name enclosed in
   double quotes: line 1 column 2 (char 1)`.
3. **`canonical_url()` raises on an out-of-range port, and the message is shown
   to the user (MEDIUM)** — `parsed.port` sits outside the function's `try`
   (`providers/__init__.py:82-84`). Confirmed: a check of
   `https://modrinth.com:99999/mod/sodium` returns `Port out of range 0-65535`.

### What is done well (so remediation can stay surgical)

Independently re-verified this pass, not carried over on trust:

- **`/clear_cache` is genuinely gone.** `POST /clear_cache` → **404** against both
  the dev server and gunicorn. No route in `app.url_map`. The destructive
  operation survives only as `main.py --clear-cache`, which is the right place.
- **No CORS layer at all.** `flask_cors` is uninstalled and absent from
  `requirements.txt`; no `Access-Control-Allow-Origin` on any response, including
  a hostile-origin preflight.
- **Exact host matching holds.** All eight spoofing forms tested —
  userinfo (`curseforge.com@169.254.169.254`), suffix
  (`curseforge.com.attacker.example`), path and query decoys — are refused by
  both `detect_provider` and `is_valid_mod_url`, which now share one
  `ALLOWED_HOSTS` table so they cannot diverge.
- **Security headers ship on every response**, verified under **gunicorn** as
  well as the dev server: CSP with `frame-ancestors 'none'` and `base-uri 'none'`,
  `nosniff`, `no-referrer`.
- **The CSP does not break the page.** Checked specifically: the template has no
  inline `style=` attributes, no `<style>` block and no inline event handlers; the
  one JS style write (`static/app.js:116`) is a CSSOM property assignment, which
  `style-src` does not govern; the single `innerHTML` (`static/app.js:487`) is a
  static header literal.
- **The documented deployment command actually works.**
  `gunicorn -w 2 -b 127.0.0.1:5051 --timeout 60 web:app` boots and serves with
  headers intact — worth stating, because a README that recommends an untested
  command is its own failure mode.
- **Input ceilings are enforced before any provider is reached.** Body > 256 KB →
  413; list > 200 → 413; six malformed body shapes → 400, none reaching
  `check_urls`.
- **Dependencies match their pins.** Flask 3.1.3, requests 2.33.0,
  python-dotenv 1.2.2; `pip check` clean; dev tooling separated into
  `requirements-dev.txt`; the orphaned npm tree is gone.
- **The XSS and CSV-injection properties still hold** — `textContent`,
  `createElement`, `new Option()`, and `csvCell()`/`csv_cell()` on both interfaces.
- **Cache keys cannot collide across mods.** `safe_name()` does map `a!b` and
  `a@b` to the same string, but the directory is `{slug}_{id}` and project ids are
  distinct, so one mod's cache cannot poison another's. Verified, not assumed.
- **The secret is still out of git** — `.env` untracked, gitignored, absent from
  history.

---

## A.1 Remediation Status

**Remediated 2026-09-17**, same day, in the working tree (**still uncommitted** —
see the last INFO item in section C).

| ID               | Severity | Title                                                        | Status                                              |
| ---------------- | -------- | ------------------------------------------------------------ | --------------------------------------------------- |
| F-2026-09-17-2-1 | HIGH     | No server-side deadline; four requests deny service          | ✅ Fixed                                             |
| F-2026-09-17-2-2 | MEDIUM   | `JSONDecodeError` bypasses the error-suppression fix         | ✅ Fixed                                             |
| F-2026-09-17-2-3 | MEDIUM   | `canonical_url()` raises on out-of-range port, message shown | ✅ Fixed                                             |
| F-2026-09-17-2-4 | MEDIUM   | Cache grows without bound or eviction                        | ✅ Fixed                                             |
| F-2026-09-17-2-5 | MEDIUM   | Per-caller rate limiting exists only as documentation        | ⚙️ Artifact committed; **deployment still required** |
| F-2026-09-17-2-6 | MEDIUM   | Cache path relative to CWD                                   | ✅ Fixed                                             |
| F-2026-09-17-2-7 | LOW      | `CF_API_KEY` still unrotated                                 | ⏭️ Operator action — cannot be fixed in code         |
| F-2026-09-17-2-8 | LOW      | No CI, no hash-pinned dependencies                           | ⚙️ CI added; hash pinning outstanding                |
| F-2026-09-17-2-9 | LOW      | `safe_name()` still permits `.`                              | ✅ Fixed (containment assertion)                     |

Legend: ✅ fixed · ⚙️ in progress · ⏭️ not started

**What landed**

- **F-1 — `modlist.check_urls()` is bounded in time.** `CHECK_DEADLINE = 45`s,
  implemented with `concurrent.futures.wait(timeout=...)` and
  `pool.shutdown(wait=False, cancel_futures=True)` — the previous `with` block
  would have joined every running thread and defeated the deadline entirely.
  Invariant 1 is preserved: an abandoned lookup returns a row reading *"This mod
  took too long to check"* and stays in the verdict's denominator. `retries` in
  `providers/http.py` dropped 3 → 2, halving the window a single slow URL can
  hold (33s → 21s).
- **F-2 — the error taxonomy no longer catches a builtin.** Both providers now
  raise `ProviderError` where they raised `ValueError`
  (`providers/curseforge.py`, `providers/modrinth.py`), and `fetch_mod_info`
  catches `ProviderError` alone. Recorded as **Invariant 10** in `CLAUDE.md` so
  the catch is not widened again.
- **F-3 — `canonical_url()` is total.** `parsed.port` moved inside the guarding
  `try`; `detect_provider()` also reads `.port` so an unusable port is refused at
  the gate rather than after an upstream request has been spent.
- **F-4 — the cache has a ceiling.** `CACHE_MAX_BYTES` (256 MB) with
  `enforce_cache_budget()` evicting oldest-first after each write.
- **F-5 — the rate limit is now an artifact**, `deploy/nginx.conf`, with
  `limit_req`, `limit_conn`, `client_max_body_size` mirroring the app, and
  `proxy_read_timeout` deliberately above `CHECK_DEADLINE`. **It still has to be
  deployed; a committed file that nothing applies is no better than the README
  it replaced.**
- **F-6 / F-9 — one `CACHE_ROOT`.** Defined once in `providers/__init__.py` and
  imported by `modlist`; `cache_path()` asserts `realpath` containment, which
  retires the `safe_name`-permits-`.` concern.
- **F-8 — CI exists.** `.github/workflows/ci.yml` runs both suites on push and PR
  across Python 3.10/3.12/3.13 (with node, for the JS parity half), plus a
  `pip check` and `pip-audit` job. Hash pinning is **not** done — it needs
  `pip-compile --generate-hashes` and a deliberate lockfile.
- **D.1 — worker class corrected.** `README.md` now documents
  `gunicorn -w 4 --threads 8` (gthread, verified booting) rather than the sync
  default, so one slow request no longer consumes an entire worker.
- **D.2 — cache writes are atomic.** New `write_cache()` writes to a
  process/thread-unique temp file and `os.replace()`s it, which removes the
  truncated-file condition that produced F-2's leak in the first place.
- **Dead imports removed** (`requests` from both providers, `time` from
  modrinth), and two new invariants documented in `CLAUDE.md`.

**Verification.** `test_compat.py` (4 checks) and `test_web.py` (now **8**
checks, up from 6) both pass. New regression tests cover: the deadline (bounded
at 0.30s against providers sleeping 2s, with all three URLs still reported),
`JSONDecodeError`/`ValueError`/`KeyError` all reduced to the generic sentence
while `ProviderError` passes through, `canonical_url` totality over five hostile
inputs, and cache containment under `os.chdir` plus oldest-first eviction. Live:
`gunicorn -w 2 --threads 8` boots as gthread and serves with headers intact,
`/clear_cache` → 404, an out-of-range port returns *"Not a CurseForge or Modrinth
link"* rather than *"Port out of range"*, and a real Modrinth check still
resolves with valid cache JSON and no leftover `.tmp` files.

**Still outstanding**

- **F-5 deployment.** The nginx config exists in the repository; nothing in the
  repository can make it run. Until it is applied, `/analyze` remains unmetered
  per caller, and the deadline is the only thing standing between an attacker and
  worker saturation.
- **F-7 key rotation** and `chmod 600 .env` — operator actions.
- **F-8 hash pinning** — `pip-compile --generate-hashes`, then install with
  `--require-hashes`.
- **The work is uncommitted.** Both remediation passes — twenty-one findings —
  live only as working-tree changes.
- **D.3, D.4, D.5, D.6 remain open** as recorded.

---

## B. Endpoint Inventory

**Auth model: there is none, by design.** No login, session, cookie, token,
middleware or guard. Grepping for `requireAuth`, `requireAdmin`, `authorize`,
`hasPermission`, `checkPermission`, `policy`, `guard`, `Forbidden`,
`AccessDenied`, `@PreAuthorize`, `isAdmin`, `login_required`, `current_user`
returns **zero matches**. There is no admin, billing, user, organization,
project, file, export, webhook or settings endpoint. The API is three routes wide
— one fewer than the previous pass, because `/clear_cache` was removed.

"WS-scoped?" is **N/A** throughout: there are no persistent user-owned objects,
no database, and no object ids accepted from any path, query, body or header. The
only server-side state is a global, non-user-attributed response cache on disk.

| Method   | Path                      | Handler                        | Auth                        | Authz    | WS-scoped?           | Risk     | Tests                                                |
| -------- | ------------------------- | ------------------------------ | --------------------------- | -------- | -------------------- | -------- | ---------------------------------------------------- |
| GET      | `/`                       | `index` — `web.py:50-52`       | None (public page)          | None     | N/A                  | LOW      | ✅ `test_web.py` (headers)                            |
| **POST** | **`/analyze`**            | **`analyze` — `web.py:55-73`** | **None (public by design)** | **None** | **N/A (no objects)** | **HIGH** | **⚙️ limits + shapes covered; no timeout/abuse test** |
| GET      | `/static/<path:filename>` | Flask built-in static          | None                        | None     | N/A                  | LOW      | ❌ none                                               |
| ~~POST~~ | ~~`/clear_cache`~~        | **removed**                    | —                           | —        | —                    | —        | ✅ asserts 404                                        |

`/analyze` remains HIGH not because it is public — it is the product, and
correctly public — but because it is **unmetered in time**: the size ceilings cap
one request, and nothing caps how long that request runs or how many a caller may
make. See F-2026-09-17-2-1 and -5.

Verified dynamically this pass (dev server **and** gunicorn, no auth supplied):

```
GET  /               -> 200  CSP + nosniff + Referrer-Policy present (both servers)
POST /clear_cache    -> 404  (both servers)
POST /analyze [1,2,3]-> 400  {"error":"Send a JSON object with a list of URLs."}
POST /analyze x201   -> 413  {"error":"Check at most 200 mods at a time."}
POST /analyze spoof  -> 200  [{"error":"Not a CurseForge or Modrinth link", ...}]  (no lookup)
OPTIONS /analyze     -> no Access-Control-Allow-Origin
socket               -> 127.0.0.1:5000 only
```

---

## C. Critical Findings

### F-2026-09-17-2-1 — HIGH — No server-side deadline on a check; four requests deny service to every user

**File:** `modlist.py:79-91`, `web.py:55-73`, `providers/http.py:21-62`

```python
# modlist.py:79 — no time budget anywhere in this function
def check_urls(urls, max_workers=MAX_WORKERS):
    results = [None] * len(urls)
    jobs = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for i, url in enumerate(urls):
            if is_valid_mod_url(url):
                jobs[pool.submit(fetch_mod_info, url)] = i
        for future, i in jobs.items():
            results[i] = future.result()      # blocks indefinitely
    return dedupe(results)
```

```python
# providers/http.py:21 — each URL may burn 33s before giving up
def request(service, url, *, headers=None, params=None,
            retries=3, delay=1, timeout=10):
```

**Why dangerous:** The remediation capped *size* (256 KB, 200 URLs) but not
*time*, and those are different resources. Measured from the shipped constants:

- One URL against an unresponsive upstream: `3 × 10s` timeout + `1s + 2s` backoff
  = **33 seconds**.
- 200 URLs ÷ 8 pool workers = **25 sequential batches**.
- Worst case for one accepted, perfectly legal request: **825 seconds ≈ 13.8
  minutes.**

`gunicorn -w 4` — the command this project's own `README.md` recommends — uses
**sync workers**, which serve exactly one request each. **Four concurrent
requests therefore occupy the entire service.** `--timeout 60` does not rescue
this: it kills the worker rather than the request, so the attacker converts a
long occupation into continuous worker churn, and every legitimate request in
flight on that worker dies too.

The client-side abort is cosmetic for this purpose. `static/app.js:593-626` aborts
the *fetch* after 60s; the server never learns, and `check_urls` runs to
completion regardless.

The attacker does not need slow upstreams to exist naturally — 200 URLs pointing
at real mods still costs real time, and `providers/curseforge.py:130` adds a
deliberate `0.2s` sleep per uncached page on top.

**Exploit:** Anonymous, four requests, no special conditions:

```bash
# 200 legal URLs, well under both ceilings; repeat x4 concurrently.
python - <<'PY' > payload.json
import json
print(json.dumps({"urls": [f"https://modrinth.com/mod/mod-{i}" for i in range(200)]}))
PY

for i in 1 2 3 4; do
  curl -s -X POST http://target/analyze \
       -H 'Content-Type: application/json' --data-binary @payload.json &
done
```

Every subsequent request queues behind a sync worker that will not free for
minutes. Sustained with a `while true` loop, the service is permanently
unavailable at a cost of four connections.

**Fix:** Bound the work, not just the input. Three layers, cheapest first:

1. **A deadline on the batch**, so one request cannot outlive its usefulness:
   ```python
   # modlist.py
   CHECK_DEADLINE = 45  # seconds; the browser gives up at 60

   def check_urls(urls, max_workers=MAX_WORKERS, deadline=CHECK_DEADLINE):
       results = [None] * len(urls)
       with ThreadPoolExecutor(max_workers=max_workers) as pool:
           jobs = {pool.submit(fetch_mod_info, u): i
                   for i, u in enumerate(urls) if is_valid_mod_url(u)}
           for i, url in enumerate(urls):
               if results[i] is None and not is_valid_mod_url(url):
                   results[i] = {"url": url, "error": NOT_A_MOD_LINK}
           done, pending = concurrent.futures.wait(jobs, timeout=deadline)
           for future in pending:
               future.cancel()
           for future, i in jobs.items():
               results[i] = (future.result() if future in done
                             else {"url": urls[i],
                                   "error": "This mod took too long to check"})
       return dedupe(results)
   ```
   This preserves Invariant 1 — a mod that could not be checked still occupies its
   row and the verdict's denominator, it simply has a timeout as its reason.
2. **Cut the per-URL worst case.** `retries=3, timeout=10` is generous for a
   batch operation; `retries=2, timeout=5` caps a URL at ~11s.
3. **Use gunicorn's threaded worker** (`-w 4 --threads 8`) or `gevent`, so one
   slow request does not consume a whole worker, and pair it with the proxy rate
   limit in F-2026-09-17-2-5.

**Regression test:** In `test_web.py`, monkeypatch `providers.PROVIDERS` with a
function that sleeps past the deadline; assert `check_urls` returns within
`deadline + slack`, that every submitted URL is still present in the result, and
that the slow ones carry the timeout reason rather than being dropped.

---

### F-2026-09-17-2-2 — MEDIUM — `JSONDecodeError` subclasses `ValueError`, bypassing the error-suppression fix

**File:** `modlist.py:44-52`

```python
    try:
        mod_info = get_mod_data(url)
    except (ProviderError, ValueError) as exc:
        # Both already carry a sentence written for the person who pasted the URL.
        return {"url": url, "error": str(exc)}
    except Exception:
        log.exception("check failed for %s", url)
        return {"url": url, "error": "This mod could not be checked right now"}
```

**Why dangerous:** The intent was that `ValueError` means the providers' own
curated copy — `ValueError("No mod called 'x' on CurseForge")` and
`ValueError("Not a Modrinth mod link")`. But `ValueError` is a builtin with a
large family, and the most likely member here is
**`json.JSONDecodeError`, which is a subclass of `ValueError`**:

```
issubclass(json.JSONDecodeError, ValueError) = True
```

Both cache readers call `json.load()` on a file that may be truncated —
`providers/curseforge.py:34-35` and `providers/modrinth.py:44-45` — and
`cached_fetch` writes non-atomically to the final path with eight threads and no
lock, which is precisely the condition that produces a partial file (see D.2).
The upstream `r.json()` calls have the same exposure.

Confirmed by execution:

```
{'url': 'https://modrinth.com/mod/sodium',
 'error': 'Expecting property name enclosed in double quotes: line 1 column 2 (char 1)'}
```

That string is rendered verbatim in the results table (`static/app.js:572`) and
carried into both exports. It is not catastrophic disclosure — no path, no
credential — but it is exactly the class of internal text the fix was written to
suppress, it violates the project's own error-copy contract in `CLAUDE.md`, and
it does so on the most probable internal failure the system has. The previous
review's regression test passed because it used `OSError`, which the fix does
handle.

**Exploit:** Requires an internal fault rather than attacker input, so this is
disclosure-on-error, not a direct attack: corrupt or truncate any file under
`cache/`, then check that mod. Reachable in normal operation via a crash or a
disk-full during a cache write, and concurrently reachable via D.2.

**Fix:** Catch the curated errors precisely instead of by base class. The
cleanest version makes intent explicit rather than relying on inheritance:

```python
# providers/http.py — one exception type meaning "copy written for the user"
class ProviderError(RuntimeError):
    """A provider failure with a message meant for the person who pasted the URL."""
```

Then have the providers raise `ProviderError` where they currently raise
`ValueError` (`providers/curseforge.py:154`, `providers/modrinth.py:59`) and
reduce the handler to:

```python
    except ProviderError as exc:
        return {"url": url, "error": str(exc)}
    except Exception:
        log.exception("check failed for %s", url)
        return {"url": url, "error": "This mod could not be checked right now"}
```

If the `ValueError` arm must stay for compatibility, it must at minimum exclude
the JSON family: `except ValueError as exc:` preceded by
`except json.JSONDecodeError:` routed to the generic branch.

**Regression test:** Assert that a provider raising
`json.JSONDecodeError`/`ValueError("Expecting value")` yields the generic
sentence, while `ProviderError("… Check CF_API_KEY.")` still passes through
verbatim. The existing `check_error_copy()` covers only `OSError` and must be
extended.

---

### F-2026-09-17-2-3 — MEDIUM — `canonical_url()` raises on an out-of-range port, and the exception text is shown to the user

**File:** `providers/__init__.py:70-88`

```python
def canonical_url(url: str) -> str:
    try:
        parsed = urlparse(url)
    except ValueError:
        return url
    host = (parsed.hostname or "").lower()
    if not host:
        return url
    if parsed.port:                      # <-- outside the try; .port parses lazily
        host = f"{host}:{parsed.port}"
    return urlunparse((parsed.scheme.lower(), host, parsed.path, "", "", ""))
```

**Why dangerous:** `urlparse()` is lazy. It does not validate the port; the
`.port` property does, raising `ValueError("Port out of range 0-65535")` on
access. That access is **outside** the `try` that was written to make this
function total, so `canonical_url` raises for a URL that `detect_provider` has
already accepted — `.hostname` parses fine for the same input.

The failure then lands in F-2026-09-17-2-2's `except (ProviderError, ValueError)`
arm and is printed to the user. Confirmed end to end:

```
detect_provider('https://modrinth.com:99999/mod/sodium') -> 'modrinth'
fetch_mod_info(...) -> {'url': ..., 'error': 'Port out of range 0-65535'}
```

Two distinct defects compound here, which is why both are listed: the raise
itself, and the fact that the error taxonomy then treats an internal `ValueError`
as user-facing copy. Note the ordering — the request to the provider API has
*already been made* by the time `canonical_url` runs, so the work is wasted as
well as mis-reported.

Severity is MEDIUM rather than LOW because it is attacker-reachable with a single
crafted URL and produces a confusing, internal-sounding message on an input the
system claimed was valid — not because the disclosure itself is serious.

**Exploit:** Paste `https://modrinth.com:99999/mod/sodium`. The URL passes the
host allowlist, a real upstream request is spent, and the row comes back reading
`Port out of range 0-65535`.

**Fix:** Move the port access inside the guarded region, and reject an invalid
port at the gate so it never reaches a provider:

```python
def canonical_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if not host:
            return url
        port = parsed.port                      # validates here, inside the try
    except ValueError:
        return url
    if port:
        host = f"{host}:{port}"
    return urlunparse((parsed.scheme.lower(), host, parsed.path, "", "", ""))
```

Better still, reject it in `detect_provider()` so an unreachable port is refused
before a request is spent — wrap its `parsed.hostname` access and a `parsed.port`
access in the same `try`, returning `None` on `ValueError`. Whaaaam only ever
talks to the providers' standard ports, so a non-default port could reasonably be
refused outright.

**Regression test:** `canonical_url('https://modrinth.com:99999/mod/x')` returns
without raising; `detect_provider` on the same URL returns `None`; and a
`fetch_mod_info` for it never produces an error string containing `Port out of
range`.

---

### F-2026-09-17-2-4 — MEDIUM — The cache grows without bound and is never evicted

**File:** `providers/__init__.py:12-27`, `providers/modrinth.py:41-49`, `providers/curseforge.py:30-41`

```python
def is_cache_expired(path: str, ttl_hours: int = 24) -> bool:
    if not os.path.exists(path):
        return True
    return (time.time() - os.path.getmtime(path)) > (ttl_hours * 3600)
```

**Why dangerous:** The 24-hour TTL governs *freshness*, not *lifetime*. An
expired entry is only ever overwritten when that same mod is checked again; a mod
checked once and never again occupies disk forever. Nothing enumerates, sizes,
caps or evicts the cache. The only deletion path in the codebase is the
all-or-nothing `shutil.rmtree` in `modlist.clear_cache()` — which, since the
previous pass removed the HTTP route, is now reachable **only** by an operator
running `main.py --clear-cache` on the box.

Measured, not estimated — one real check of `sodium`:

```
2 file(s), 470,235 bytes  ->  ~459 KB for a single mod
```

At 200 mods per accepted request, one request can write **~92 MB**. Modrinth
hosts tens of thousands of public projects and its API needs no key, so an
attacker enumerating real slugs writes tens of gigabytes with ordinary,
individually-legal requests. Filling the volume takes the application down and,
depending on what shares the disk, more than the application.

Two honest qualifications. The attacker needs *real* slugs: a miss 404s at
`providers/modrinth.py:62` and raises before any cache write, so junk costs
nothing on disk. And CurseForge mostly avoids writes because `index_pairs`
answers from the search response — the paged fallback is the only CF writer. The
disk vector is therefore predominantly Modrinth, which is also the one needing no
credential.

**Exploit:** Iterate Modrinth's public project list 200 slugs at a time. Each
request is under both ceilings and entirely well-formed; the disk fills at
roughly 92 MB per request.

**Fix:** Give the cache a ceiling and an eviction policy.

1. Cheapest immediate mitigation — cap the volume from outside: put `cache/` on
   its own filesystem or a size-limited tmpfs, so exhaustion cannot take the host
   down with it.
2. In-process: before a write, check total cache size and evict the oldest
   entries past a budget (`CACHE_MAX_BYTES`), e.g. with a periodic sweep over
   `os.scandir` sorted by `st_mtime`.
3. Delete on expiry rather than on next use: a sweep at startup and hourly that
   unlinks anything past TTL bounds growth to one TTL window of traffic.
4. Reconsider what is stored. 459 KB per mod is the *raw* API response; the
   product needs only `(version, loader)` pairs, which for Sodium is a few hundred
   bytes. Caching the distilled pairs instead of the payload removes about three
   orders of magnitude and most of this finding with it.

**Regression test:** Not a unit test — a harness that checks N distinct real mods
and asserts `du -s cache` stays under `CACHE_MAX_BYTES`, plus a unit test that
`cached_fetch` evicts the oldest entry once the budget is exceeded.

---

### F-2026-09-17-2-5 — MEDIUM — Per-caller rate limiting exists only as documentation

**File:** `README.md` (deployment section); no corresponding code or config in the repository

**Why dangerous:** The previous pass deliberately placed rate limiting at the
reverse proxy rather than in the application, and the reasoning was sound — under
`gunicorn -w 4`, `flask-limiter`'s in-memory storage is per-worker, so a
"10/minute" rule is really 40/minute. But the consequence is that **the control
lives in a README, and a README enforces nothing.** The repository contains no
nginx configuration, no Dockerfile, no compose file, no systemd unit and no
infrastructure-as-code — confirmed absent — so there is no artifact anywhere in
version control that applies the limit, and no way to verify from the repository
that the deployed system has one.

This is what makes F-2026-09-17-2-1 exploitable in practice: the in-app ceilings
bound a single request, and *nothing in the repository* bounds how many requests
a caller makes. The operator has stated the deployment target is the public
internet.

**Exploit:** See F-2026-09-17-2-1 — the absence of this control is what turns a
slow request into a sustained outage.

**Fix:** Put the control somewhere it can be reviewed and deployed.

1. Commit the nginx snippet as `deploy/nginx.conf` rather than leaving it in
   prose, so it is version-controlled, diffable and reviewable.
2. If no proxy is guaranteed, add `flask-limiter` **backed by a shared store**
   (`storage_uri="redis://…"`), which is correct across workers, and treat the
   in-memory default as unacceptable rather than as a fallback.
3. Either way, fix F-2026-09-17-2-1's deadline in the application, because that
   one does not depend on infrastructure existing.

**Regression test:** A staging smoke test issuing N+1 requests in the window and
asserting the last is rejected. This cannot be a unit test; it belongs to
deployment verification, which is precisely why the config must be an artifact.

---

### F-2026-09-17-2-6 — MEDIUM — Cache path is relative to the working directory; clearing can silently miss the real cache

**File:** `providers/__init__.py:17` vs `modlist.py:19`

```python
# providers/__init__.py:17 — resolved against the CURRENT WORKING DIRECTORY
folder = os.path.join("cache", safe_provider, f"{safe_slug}_{safe_mod_id}")
```

```python
# modlist.py:19 — resolved against the MODULE'S OWN LOCATION
CACHE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
```

**Why dangerous:** Carried over unfixed from the first pass (item D.1) and now
more likely to bite, because `README.md` newly recommends running under gunicorn
— a context where the working directory is set by a service manager rather than
by a developer standing in the repository.

The two definitions coincide **only** when the process is started from the
repository root. Under a systemd unit without `WorkingDirectory=`, a container
with a different `WORKDIR`, or any `cd`-elsewhere invocation, providers write to
`$CWD/cache` while `clear_cache()` deletes `<repo>/cache`. The operator's only
remaining cache-clearing tool then reports success — `main.py:169-172` prints a
count — while the actual cache is untouched, grows unchecked (F-2026-09-17-2-4),
and keeps serving data past its TTL.

There is a second consequence worth stating: the cache is written wherever the
process happens to be standing, which may be a directory with different
permissions or one that is world-readable, and `os.makedirs` is called with
default mode.

**Exploit:** Not attacker-triggered; it is a reliability and remediation-integrity
failure. Its security weight is that the operator cannot tell whether a
corrective action took effect — which matters directly for F-2026-09-17-2-4.

**Fix:** One definition, exported from one place. Move the constant into
`providers/__init__.py` and have `modlist` import it:

```python
# providers/__init__.py
CACHE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, "cache")

def cache_path(provider, slug, mod_id, page=None):
    folder = os.path.join(CACHE_ROOT, safe_name(provider),
                          f"{safe_name(slug)}_{safe_name(mod_id)}")
```

and in `modlist.py`, `from providers import CACHE_ROOT`. Then assert containment
before every open — `os.path.realpath(path).startswith(os.path.realpath(CACHE_ROOT))`
— which also retires F-2026-09-17-2-9.

**Regression test:** `os.chdir(tmpdir)`, call `cache_path(...)`, and assert the
returned path is under `modlist.CACHE_ROOT` regardless of the working directory.

---

### Lower-severity (verified)

- **F-2026-09-17-2-7 — LOW — `CF_API_KEY` is still unrotated and world-readable.**
  `.env` remains untracked, gitignored and absent from history — correct, and
  re-verified. But the value is unchanged from the first pass (same `$2a$10$Ea42…`
  prefix), so the rotation recommended then has not happened, and the file still
  carries default permissions. It is the only credential in the system and the one
  whose loss takes the product offline, since `providers/curseforge.py:19-20`
  raises at import without it. **Fix:** rotate in the CurseForge developer console;
  `chmod 600 .env`. Its value is deliberately not reproduced in this report.
- **F-2026-09-17-2-8 — LOW — No CI, and no hash-pinned dependencies.** Confirmed:
  no `.github/` directory exists, so nothing runs `test_compat.py` or the new
  `test_web.py` on a pull request — including Dependabot's, which is demonstrably
  active (three bump commits on `main`). `requirements.txt` uses exact `==` pins
  but carries no hashes (`grep -c sha256` → 0), so installs are not reproducible
  and are vulnerable to registry-side substitution. This is what allowed the
  previous pass's F-5 (runtime behind the manifest) to go unnoticed in the first
  place; that state was corrected, but the detection gap that hid it was not.
  **Fix:** a GitHub Actions workflow running both suites plus `pip-audit`, and
  `pip-compile --generate-hashes` with `--require-hashes` at install.
- **F-2026-09-17-2-9 — LOW — `safe_name()` still permits `.`.**
  `providers/__init__.py:8-9` allows `[A-Za-z0-9._-]`, so `..` survives
  sanitisation. Traversal remains **unreachable**, for the same reason as before:
  the directory component is always `f"{slug}_{id}"`, whose trailing `_{id}`
  guarantees it can never be exactly `..`, and `page` is an internally generated
  integer. This is still a correct-by-accident defence resting on string
  concatenation rather than intent. **Fix:** fold into F-2026-09-17-2-6's
  `realpath` containment assertion.
- **INFO — Two unused imports remain.** `import requests` in
  `providers/curseforge.py:4` and `providers/modrinth.py:5` — zero uses of
  `requests.` in either file since both route through `providers/http.py`. Also
  `import time` in `providers/modrinth.py:2` (unused). Harmless, but dead imports
  in a network module invite someone to reach for the unwrapped client and bypass
  the retry/error policy. **Fix:** delete them.
- **INFO — Dummy credential string in the test suite.**
  `test_web.py:17` sets `CF_API_KEY` to `"test-key-not-used"` so `web` can be
  imported without a real key. Correct and deliberate — noted only because
  repository secret scanners flag `CF_API_KEY=` assignments, and a reviewer should
  recognise this one as a false positive rather than suppress the rule globally.
- **INFO — Non-standard ports survive canonicalisation.** `canonical_url` keeps a
  valid port, so `https://modrinth.com:8443/mod/x` is allowlisted (hostname
  matches) and rendered as a link to that port. Harmless — the host is genuinely
  Modrinth and the API request goes to the hardcoded `API_BASE` regardless — but
  refusing non-default ports at `detect_provider` would be strictly tidier and
  folds into F-2026-09-17-2-3's fix.
- **INFO — The remediation is uncommitted.** `git status` shows eleven modified
  files, one deletion (`package.json`) and three untracked additions. All twelve
  fixes from the first pass live only in the working tree. A stray
  `git checkout .` restores every original vulnerability. **Fix:** commit.

---

## D. Suspicious Areas Requiring Manual Review

1. **`gunicorn` worker class versus the checking model — the deployment
   recommendation may be the wrong shape.** `README.md` documents
   `gunicorn -w 4 --timeout 60`, which uses **sync** workers: one request per
   worker, and `--timeout` kills the worker rather than the request. Whaaaam's
   requests are long and I/O-bound, which is the case sync workers suit worst.
   **Confirm:** whether `--threads` or a `gevent` worker is appropriate, and what
   `--timeout` should be relative to the deadline proposed in F-2026-09-17-2-1
   (the app deadline must be shorter, or gunicorn kills the worker first and the
   deadline never runs). This was written in the previous pass and verified only
   to *boot*, not to behave correctly under load.
2. **Non-atomic cache writes under eight threads.**
   `providers/curseforge.py:39-41` and `providers/modrinth.py:46-48` `open(...,"w")`
   then `json.dump()` straight to the final path, with no lock and no temp-file
   swap. `dedupe()` runs *after* fetching (`modlist.py:91`), so two threads in one
   request genuinely can write the same file concurrently. The resulting truncated
   file is the most likely trigger for F-2026-09-17-2-2. **Confirm** the
   interleaving is reachable in practice, then fix with
   `os.replace(tmp, final)` — an atomic rename within the same directory.
3. **Whether the browser's 60s abort should propagate.** `static/app.js:626`
   aborts the fetch; the server continues to completion. A user who cancels, or
   whose tab closes, still costs the full server-side run. **Confirm** whether
   Flask/gunicorn can observe the disconnect in this configuration, or whether the
   deadline in F-2026-09-17-2-1 is the only practical control.
4. **`MAX_URLS = 200` versus the product's actual use.** `PRODUCT.md` describes
   modpack-sized lists; 200 may be comfortably above or uncomfortably below a real
   pack. **Confirm** with the operator — set too low it breaks the product, too
   high it widens F-2026-09-17-2-1 linearly (the 13.8-minute figure scales
   directly with this constant).
5. **Deployment topology, still unrepresented in the repository.** The operator
   has answered *where* (public internet). Unanswered and unverifiable from the
   repo: what fronts it, whether TLS terminates upstream, whether the nginx
   `limit_req` block exists anywhere, whether `cache/` has a bounded volume, and
   which user the process runs as. Every one of these is load-bearing for a
   finding above. **Confirm with a human before treating this verdict as final.**
6. **`request.get_json(silent=True)` still parses regardless of `Content-Type`.**
   `web.py:59`. With CORS removed this is much less interesting than it was, but a
   `text/plain` body still reaches the JSON parser without a preflight.
   **Confirm:** whether to require `application/json` explicitly.

---

## E. Missing Security Tests (negative authz)

**What is now well covered.** `test_web.py` is new since the last pass and is
real coverage, not decoration: six checks over input ceilings (400/413 for six
malformed shapes, oversized body, oversized list), exact-host matching (eight
spoofing forms refused, four legitimate forms accepted, plus an assertion that
`is_valid_mod_url` and `detect_provider` can never disagree), URL
canonicalisation, error copy, slug validation, and routes/headers including
`/clear_cache` → 404 and the absence of CORS reflection. It patches
`providers.http.requests.get` to raise, so the suite fails loudly if anything
starts making real network calls — a good property most suites lack.
`test_compat.py` continues to enforce CLI/web verdict parity by executing the
shipped `static/app.js` under Node.

**The standard negative-authz matrix remains N/A** — anonymous → 401, other user
→ 403/404, wrong role → 403, wrong tenant → 403/404 cannot be written against an
application with no auth, no roles and no tenants. Their absence is not a gap.

**The gaps that are real**, each tied to a finding above:

- **Time budget (F-1):** a provider stub that sleeps past the deadline; assert
  `check_urls` returns within `deadline + slack`, that *every* submitted URL is
  still present (Invariant 1), and that slow entries carry a timeout reason.
- **Error taxonomy, completed (F-2):** the existing `check_error_copy()` tests
  only `OSError`. Add `json.JSONDecodeError` and a bare
  `ValueError("Expecting value")` → generic sentence; keep `ProviderError` →
  verbatim. This is the test whose absence let F-2 ship.
- **Total URL helpers (F-3):** `canonical_url` must not raise for *any* string —
  property-style coverage over out-of-range ports, empty input, missing scheme,
  IPv6 literals, and `urlparse`-hostile values.
- **Cache budget (F-4):** `cached_fetch` evicts the oldest entry once
  `CACHE_MAX_BYTES` is exceeded.
- **Path containment (F-6, F-9):** `os.chdir(tmpdir)` then assert `cache_path`
  still resolves under `CACHE_ROOT`, and that a `..`-bearing slug cannot escape it.
- **Concurrency (D.2):** two threads caching the same slug concurrently leave a
  file that `json.load` can read.
- **Static route:** no test asserts `/static/` cannot serve outside its folder.
  Flask handles this correctly, but nothing pins the behaviour.
- **Import-time contract:** `providers/curseforge.py:19-20` raising
  `EnvironmentError` without `CF_API_KEY` is a documented contract in `CLAUDE.md`
  with no test.

---

## F. Suggested Automated Checks

| Check                               | Tooling                                                                                                         | Catches                                                                                                        |
| ----------------------------------- | --------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| **CI gate on both suites**          | GitHub Actions running `test_compat.py` + `test_web.py` on every PR                                             | F-2026-09-17-2-8 — nothing runs today, including on Dependabot PRs. Highest-leverage single addition.          |
| **Exception-hierarchy lint**        | Custom Semgrep: `except (...)` tuples containing `ValueError` in a handler that returns `str(exc)` to a caller  | F-2026-09-17-2-2 exactly — catching a broad builtin and treating it as user-facing copy                        |
| **Lazy-property-outside-try lint**  | Custom Semgrep: `urlparse(...)` result whose `.port` is accessed outside the guarding `try`                     | F-2026-09-17-2-3 — and the same class for `.hostname` on hostile input                                         |
| **Python SAST**                     | `bandit -r . -x .venv`                                                                                          | Broad `except Exception`, `shutil.rmtree`, non-atomic writes (D.2)                                             |
| **Semgrep Flask/Python packs**      | `semgrep --config p/flask --config p/python --config p/secrets`                                                 | Regressions of the first pass's fixes: reintroduced `CORS(app)`, `debug=True`, dropped `MAX_CONTENT_LENGTH`    |
| **Custom Semgrep: host validation** | URL host compared with `in` against `urlparse(...).netloc` instead of equality on `.hostname`                   | Regression of the substring-allowlist class (prior F-4)                                                        |
| **Dependency drift + audit**        | `pip install -r requirements.txt && pip check`, plus `pip-audit`                                                | Recurrence of the prior F-5 (runtime behind manifest); known CVEs                                              |
| **Hash-pinned installs**            | `pip-compile --generate-hashes` → `--require-hashes`                                                            | F-2026-09-17-2-8 — registry substitution; makes `SECURITY.md`'s install rule enforceable                       |
| **Secret scanning**                 | `gitleaks`/`trufflehog`, pre-commit **and** CI history mode, with `test_web.py`'s dummy key allowlisted by path | Keeps `.env` out of git; avoids a blanket suppression that would hide a real key                               |
| **Disk budget monitor**             | Alert on `cache/` size crossing a threshold; harness checking N mods and asserting the cap                      | F-2026-09-17-2-4                                                                                               |
| **Load/abuse harness**              | Four concurrent 200-URL requests against staging; assert the service still answers a fifth                      | F-2026-09-17-2-1 and -5 together — the finding a unit test cannot express                                      |
| **CodeQL**                          | Python + JavaScript packs on PR                                                                                 | Taint from `request.get_json` to filesystem/network sinks; XSS sinks in `static/app.js` if `innerHTML` returns |
| **Container scanning**              | `trivy image` — *only once a Dockerfile exists*                                                                 | Not applicable today; no Dockerfile in the repository                                                          |

---

## Closing note

**What held.** The first pass's twelve fixes are real, and this pass tried to
break them rather than assume them. `/clear_cache` returns 404 under two
different servers; the CORS layer is genuinely absent, not merely reconfigured;
eight host-spoofing forms are refused; the ceilings reject before any credential
is spent; the headers ship under gunicorn as well as the dev server; and the CSP
was checked against the actual page rather than asserted — no inline styles, no
inline handlers, and the one JS style write is CSSOM, which `style-src` does not
govern. The long-standing properties survived too: no XSS sink, CSV injection
neutralised on both interfaces, cache keys that cannot collide across mods, and
the secret still out of git.

**Where the findings cluster, and it is somewhere new.** The previous pass found
everything at one boundary — anonymous internet against a credentialed backend.
That boundary is now defended. This pass's findings sit in two different places.
Three are **defects in the remediation itself** (F-2, F-3, and F-5's
documentation-as-control), which is the expected failure mode when fixes are
written quickly and their tests are written by the same hand: `check_error_copy()`
passed because it tested `OSError`, the one exception the fix actually handled.
The rest are **resource exhaustion** — time (F-1) and disk (F-4) — a class the
first pass under-weighted because it was focused on the credential. Size limits
were added; time and storage limits were not, and those are separate resources.

**What to fix first, and why in this order.**

1. **The deadline (F-1).** It is the only finding an anonymous attacker can use
   to take the service down today, it needs no infrastructure to fix, and four
   requests is a very low bar. Everything else can wait behind it.
2. **The exception taxonomy (F-2) and `canonical_url`'s port (F-3).** Both are
   small, both are in code touched hours ago, and both reintroduce the problem
   their own fix claimed to close. Fixing F-2 properly — one exception type
   meaning "copy written for the user" — also removes the mechanism that makes F-3
   user-visible, so the two fixes compound.
3. **Commit the remediation.** Twelve fixes exist only as uncommitted working-tree
   changes. This costs nothing and currently one careless command reverts all of
   it.
4. **Make the rate limit an artifact (F-5), and bound the disk (F-4).** Both are
   deployment-shaped. Committing `deploy/nginx.conf` turns prose into something
   reviewable; putting `cache/` on a bounded volume is a one-line mitigation that
   does not wait on the code changes in F-4.
5. **Add CI (F-8).** Last in urgency, first in leverage over time: it is what
   would have caught the prior F-5, and what will catch the next regression of any
   fix listed here.

**A note on method and its limits.** This is static review plus local dynamic
probing. Every claim above was reproduced against running code — the two
remediation defects by executing them and capturing the exact leaked strings, the
timing figures by computing from the shipped constants, the 459 KB cache cost by
measuring a real check. No claim rests on grep alone. But no CVE databases were
consulted, only one external network call was made, and **the production
deployment remains uninspectable because the repository does not describe it**.
The verdict is **NEEDS HUMAN SECURITY REVIEW** rather than UNSAFE because nothing
found here compromises confidentiality or integrity — the exposure is
availability plus minor error-text disclosure — and rather than SAFE because the
principal availability control (F-5) exists only as a sentence in a README, and
item D.5 remains unanswered. Confirm D.5, fix F-1, and this becomes a defensible
SAFE for its threat model.
