# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

**Visual design decisions live in [DESIGN.md](DESIGN.md), not here.** That file is
normative for colour, type, layout, elevation, shape and components, and carries
the named rules. This file covers how the project is built and run.

## Whaaaam

Paste a list of CurseForge and Modrinth mod URLs; get back the Minecraft version
and loader combinations the whole list has in common. Product context — users,
positioning, principles, brand commitments — is in [PRODUCT.md](PRODUCT.md).

### Build and Run Commands

```bash
# Python dependencies
pip install -r requirements.txt

# Web interface (recommended)
python web.py          # http://localhost:5000

# CLI interface
python main.py
```

There is **no frontend build step**. `static/styles.css` is authored directly and
served as-is. `npm install` is not required to run the project.

### Environment Variables

- `CF_API_KEY` — **required.** `providers/curseforge.py` raises
  `EnvironmentError("Missing CF_API_KEY in environment")` at *import* time, so the
  app will not start without it, even for a Modrinth-only mod list. Set it in the
  environment or in a `.env` file.

### Architecture

**Entry points**
- `web.py` — Flask routing only. `POST /analyze` takes `{"urls": [...]}`; `POST /clear_cache`.
- `main.py` — CLI. Same checking, same verdict, same words as the web UI.

**Shared core — the two interfaces must never answer differently**
- `compat.py` — `compute_compatibility(mods, unchecked_count)`, `normalize_loader()`. The verdict.
  `static/app.js` carries a mirror of this for the browser.
- `modlist.py` — `check_urls()` (parallel fetch, input order preserved, deduped),
  `fetch_mod_info()`, `is_valid_mod_url()`, `clear_cache()`.
- `providers/http.py` — one `request()` with a retry policy that only retries what
  can succeed later. A 401/403 is raised immediately as "rejected the API key"; retrying
  it five times turned an instant diagnosis into a six-second wait blaming the wrong thing.

**CurseForge version data comes from `latestFilesIndexes`**, which ships with the
search response already made — one request per mod. Paging `/mods/{id}/files` is the
fallback for a mod with no index. The old code always paged: JEI cost 74 requests and
20s to produce 66 pairs, 18 of which were the fabricated `Unknown` loader. The index
holds every real release pair (verified against JEI, JourneyMap, Create and AppleSkin;
the only entries it lacks are snapshot channels, which are filtered anyway).

**Provider system (`providers/`)**
- `__init__.py` — registry, `detect_provider()`, cache helpers (`cache_path`, `is_cache_expired`).
- `curseforge.py` — CurseForge API (needs the key).
- `modrinth.py` — Modrinth API (no key).

Each provider's `get_mod_data(url)` returns:

```python
{
    "name": str,
    "provider": str,
    "id": str,
    "slug": str,
    "versions": [(mc_version, loader), ...],  # e.g. [("1.20.1", "Fabric")]
    "url": str
}
```

**The error contract matters.** A mod that cannot be resolved comes back as
`{"url": ..., "error": "<reason>"}` with no `versions` key, alongside the
successful results. The frontend must keep these visible — see Invariants.

**Concurrency** — `/analyze` fetches with a `ThreadPoolExecutor` of 8 workers.

**Frontend (`static/`, `templates/`)**
- `templates/index.html` — the single page.
- `static/app.js` — `ThemeManager` IIFE, compatibility computation, rendering, export.
- `static/styles.css` — the whole design system: theme tokens, components, responsive, reduced motion, forced colours.

**Caching** — `cache/{provider}/{slug}_{mod_id}/page-{page}.json`, 24h TTL,
cleared via `POST /clear_cache`.

### Invariants

These are correctness rules, not preferences. Breaking one produces a wrong answer.

1. **A mod that could not be checked is never dropped.** It stays in the results
   table with its reason, and it stays in the verdict's denominator. `2/10` means
   ten mods were submitted. (PRODUCT.md principle 5.)
2. **The verdict is computed before filtering.** `computeCompatibility()` runs on
   the full result set; the version and loader filters narrow the table only. If
   the verdict were derived from filtered results, selecting a version would make
   it report full compatibility with that version, always.
3. **The "all compatible" state requires zero unchecked mods.** With any failure,
   the verdict downgrades to a counted partial.
4. **Both interfaces answer identically.** The verdict comes from `compat.py`
   (CLI) and its mirror in `static/app.js` (web). Change one, change the other, and
   run `test_compat.py`, which compares them.
5. **Provider output is ordered.** Version pairs are sorted by version *and loader*;
   sorting by version alone over a `set` let same-version loaders fall out in hash
   order, so the same list produced differently-worded verdicts run to run.
6. **A loader is never invented.** A CurseForge file whose loader cannot be read
   from its version tags or its filename contributes nothing. It used to become
   `"Unknown"`, which shipped in the verdict as
   *"compatible with … & Unknown 1.12.2"*. `Unknown` is not in the vocabulary.
7. **Snapshots are not release targets.** `is_release_version()` in `compat.py`
   gates every version pair; `1.20.5-Snapshot` is not something a server pins to,
   and it can win the `max()` that picks the recommended version for a loader.
8. **Throttle the network, never the disk.** `cached_fetch()` returns
   `(data, from_cache)` and the 0.2s politeness sleep only runs on a real request.
   Sleeping after a cache hit made a fully cached re-check of JEI cost 14.5s and
   broke PRODUCT.md principle 3.
9. **Third-party strings are never interpolated into HTML.** Mod names and version
   strings come from provider APIs. Use `textContent` and `new Option()`; CSV cells
   go through `csvCell()`, which also neutralises leading `=`, `+`, `-` and `@`.

### Interface Vocabulary

One word per concept, in both interfaces. Changing one of these means changing it
everywhere, including `main.py`.

| Concept | Word | Not |
|---|---|---|
| The primary operation | **check** ("Check compatibility", "Checking mods", "could not be checked") | analyze, fetch, scan, verify |
| What the user pastes | **URL** | link, address |
| A mod that failed to resolve | **could not be checked** | error, failed, invalid |
| The loaders | **Forge, Fabric, NeoForge, Quilt** — exact casing | Neoforge, fabric |
| The answer | **verdict** (internally); user-facing it is a sentence, never a label | result, status |

Two verdict strings are recorded in PRODUCT.md as real shipped output and are
reproduced exactly — do not reword them:

- `All your mods are compatible with Fabric 1.20.1 & Forge 1.20.1`
- `Most of your mods share: Fabric 1.20.1 (8/10)`

Error copy names what happened and what remains possible. It never exposes an
internal API URL, a provider id, or a bare HTTP status as the message — see
`httpProblem()` and `requestProblem()` in `static/app.js`, and the `error` strings
in `web.py` and `providers/`, which are read verbatim by users.

Button labels are sentence case. Placeholders are examples; every field has a
persistent `<label>`.

### Theme System

Four Catppuccin palettes — Latte, Frappé, Macchiato, Mocha (default). They are a
binding brand commitment: no fifth theme, no competing palette.

**How it works**
- `<html data-theme="...">` selects the palette. That attribute is the *only*
  theme signal; nothing keys off a body class.
- `static/styles.css` section 1 defines one `[data-theme="..."]` block per palette,
  each setting the same 18 custom properties. Components read tokens and never
  hard-code a colour.
- `:root` carries a Mocha-valued fallback and **must stay above** the theme blocks:
  `:root` and `[data-theme="x"]` have identical specificity `(0,1,0)`, so whichever
  comes last wins. Putting the fallback last silently breaks every non-default theme.
- Images that ship in two variants (`cf`/`cf_dark`, `mr`/`mr_dark`, `github`/`github_dark`)
  are swapped in `updateThemedImages()`, not with the CSS `content:` trick, which
  Firefox does not apply to `<img>`.

**ThemeManager API** (`static/app.js`, IIFE)

```javascript
ThemeManager.setTheme('latte')  // set, persist, update URL and UI
ThemeManager.getTheme()         // URL ?theme= > localStorage > 'mocha'
ThemeManager.initTheme()        // wire up on load
```

Priority cascade: URL parameter → `localStorage` → `mocha`.

The switcher is a `radiogroup` with roving tabindex; arrows, Home and End move
between palettes and move focus with them.

### Accessibility Floor

- Every foreground/background pair must clear WCAG AA **in all four palettes**.
  Latte is the one that breaks: its accents are mid-lightness, so a colour that
  passes on Mocha can fail there. Verify, don't assume.
- `#sr-announce` is the page's **only** live region. It receives one finished
  sentence per state change. Do not add `aria-live` to a container that re-renders
  in bulk, and never to an element whose text is on a timer — the loading overlay
  animates its dots, which is why it is `aria-hidden`.
- Controls need a visible `:focus-visible` ring and a 24px minimum target (44px
  under `pointer: coarse`).
- Prefer a native element over a custom one: the version disclosure is `<details>`,
  which supplies `aria-expanded`, keyboard handling and state for free.
- There is a `prefers-reduced-motion` block; it reduces movement rather than
  removing feedback (the spinner steps instead of sweeping).
- There is a `forced-colors` block; the verdict states are distinguished by border
  *style*, because colour is overridden in that mode.

### UI Development Guidelines

- Read DESIGN.md first. Use its tokens; the only hex in `styles.css` belongs to the
  four `[data-theme]` blocks and the four literal palette swatches in the switcher.
- Use `h-dvh` semantics over viewport-height units that ignore mobile chrome.
- Balance headings, use `text-wrap: pretty` for body copy, `tabular-nums` for any
  version number or count.
- **Never add animation unless explicitly requested.**
- **Never use gradients or glow effects unless explicitly requested.**
- Purple is permitted only as a Catppuccin token (mauve is the visited-link role).
- Test all four themes, not just light and dark.

### Adding a New Provider

1. Create `providers/newplatform.py` with `get_mod_data(url) -> dict` matching the
   contract above, raising or returning an `error` entry on failure.
2. Register it in `providers/__init__.py` `PROVIDERS`.
3. Extend `detect_provider()` in `providers/__init__.py`.
4. Extend `is_valid_mod_url()` in `web.py`.
5. Add the logo in light and dark variants and handle it in `updateThemedImages()`.

### Testing

Before committing:

0. `python test_compat.py` — asserts the verdict logic and runs the shipped
   `static/app.js` implementation against the same cases. It fails if the CLI and
   the web would answer the same mod list differently, and if either of the two
   verdict strings PRODUCT.md records has been reworded.
1. `python web.py` and check the web UI; `python main.py <url> <url>` for the CLI.
2. Submit a list that mixes a working mod, an unreachable mod and a junk URL.
   Confirm the failures appear as rows and are counted in the verdict.
3. Apply a version filter and confirm the verdict above the table does not change.
4. Switch all four themes and check contrast, including Latte.
5. Check at 320px and at desktop width; the page must not scroll horizontally.
