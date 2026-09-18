# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary: **Minecraft server administrators.** They arrive mid-decision, with a mod list already chosen or newly changed, and one question blocking them — which single Minecraft version and loader does the *entire* list agree on? The check recurs: every time a mod is added, dropped, or updated, the whole list has to be re-validated before the server can move.

Other audiences (solo pack builders, published pack authors) use the same flow but were not confirmed as design targets. Design decisions answer to the server admin's situation.

## Product Purpose

Whaaaam takes a pasted list of CurseForge and Modrinth mod URLs and returns the Minecraft version + loader combinations common to all of them. Success is a confident go/no-go in seconds: either "all your mods are compatible with X", or an explicit account of what the majority shares and how many mods fall outside it.

## Positioning

**Whaaaam answers about the list as a whole, not mod by mod.** Every neighbouring option — CurseForge's version filter, a mod's own file list, checking tabs by hand — answers for one mod at a time and leaves the intersection to the user's head. Whaaaam computes the intersection, and when the list does not fully agree it reports the largest consensus with an explicit count (`Most of your mods share: Fabric 1.20.1 (8/10)`), so the mods breaking consensus are visible rather than merely implied.

## Operating Context

- Input is a paste: one mod URL per line, CurseForge and Modrinth mixed freely.
- Two interfaces ship today: web (`python web.py`, Flask, `localhost:5000`) and CLI (`python main.py`, tabulated output).
- Version data is fetched per mod from each platform's API — 8 in parallel on the web path — and cached on disk for 24h under `cache/{provider}/{slug}_{id}/`. Clearing it is an operator action, `python main.py --clear-cache`; the web UI has no clear action, since it would let any visitor wipe the shared cache.
- Results are filterable by MC version and by loader, and exportable as Markdown or CSV. Export is how a checked list leaves the tool and enters a server's own notes or install process.
- `CF_API_KEY` is **needed only to check CurseForge mods** (decided by the user). Without it the app starts and Modrinth-only lists work; each CurseForge URL is reported as a mod that could not be checked, with the reason, and still counts toward the verdict.

## Capabilities and Constraints

- Supported sources: CurseForge (`curseforge.com/minecraft/mc-mods/<slug>`) and Modrinth (`modrinth.com/mod/<slug>`). Anything else is rejected at validation.
- Loader vocabulary: Forge, Fabric, NeoForge, Quilt.
- Per-URL error handling: an unknown or unreachable mod returns an `error` string carried alongside the successful results rather than failing the whole run.
- No accounts, no persisted user data, no database — all state is the paste plus a local disposable cache. *Observed in code; not confirmed as a permanent product rule.*
- Providers sit behind one registry (`providers/PROVIDERS`) with a uniform `get_mod_data(url)` contract; a new platform is a provider file plus URL detection. *Observed in code; not confirmed as a binding commitment.*
- **CLI/web parity is a rule.** Confirmed by the user. Both interfaces check the same way, compute the same verdict from the same code (`compat.py`, `modlist.py`), filter without changing the verdict, and export the same Markdown and CSV including failed mods. A feature that lands in one interface is expected in the other.

## Brand Commitments

- Name **Whaaaam**. Author Lord_ZuzurNC. MIT licensed.
- **Catppuccin is binding.** The four palettes (Latte, Frappé, Macchiato, Mocha — Mocha default) are the only theme system to implement. Do not introduce a competing palette or a fifth theme identity.
- **Press Start 2P is not fixed.** The current pixel wordmark font is replaceable; it carries no commitment.
- **Undecided — canonical repository.** README clones from `codeberg.org/LordZNC/Whaaaam`; package.json and the in-app footer point at GitHub (`Lord-ZuzurNC/Whaaaam`, `3M-MinecraftModpackMatrix`). Do not present either as canonical in UI copy until this is settled.

## Evidence on Hand

- Screenshots: `docs/screenshot_light.png`, `docs/screenshot_dark.png`, `docs/screenshot_themes.png`.
- Real output strings from shipped code: `All your mods are compatible with Fabric 1.20.1 & Forge 1.20.1` and `Most of your mods share: Fabric 1.20.1 (8/10)`.
- Assets: `static/favico.ico` (16/32/48), `favicon-32.png`, `apple-touch-icon.png`, `logo-48.png`, CurseForge / Modrinth / GitHub marks in light and dark variants.
- **No** testimonials, named users, install counts, uptime figures, benchmarks, or press coverage exist. Do not fabricate any.

## Product Principles

1. **The list is the unit.** Every answer is about the whole paste. Per-mod detail is available on demand, never the headline.
2. **Partial agreement is information, not failure.** When the list doesn't converge, name the largest consensus and the count outside it instead of reporting "incompatible".
3. **A re-check must be cheaper than the first check.** Admins run this repeatedly as their mod list churns; caching, filters, and the persistent paste box exist to make the second run nearly free.
4. **Answer first, substantiate below.** The verdict leads; version tables, filters, and exports support it underneath.
5. **Never decide on a mod's behalf.** A mod that failed to fetch is reported as failed, never silently dropped from the intersection.

## Accessibility & Inclusion

No user-specific accessibility requirement was established. The repository's checked-in instructions commit to semantic HTML, ARIA roles for custom controls, keyboard navigation, and sufficient contrast across all four Catppuccin themes; treat that as the standing floor.
