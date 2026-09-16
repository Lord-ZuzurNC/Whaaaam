"""Compatibility verdict for a list of mods.

This is the product: the one answer about the whole pasted list. `static/app.js`
carries a mirror of this logic for the web UI, so the two must stay identical —
`test_compat.py` runs both against the same cases and fails if they disagree.

The invariants (also in CLAUDE.md):
  1. A mod that could not be checked is never dropped from the denominator.
  2. The verdict is computed before any filtering.
  3. "All your mods are compatible" requires zero unchecked mods.
"""

import re

LOADERS = {"neoforge": "NeoForge", "forge": "Forge",
           "fabric": "Fabric", "quilt": "Quilt"}


def normalize_loader(loader):
    """Providers return loader names in whatever case they please."""
    if not loader:
        return loader
    low = loader.lower()
    for known, proper in LOADERS.items():
        if known in low:
            return proper
    return loader[:1].upper() + loader[1:]


# A snapshot is a development channel, not something anyone pins a server to,
# and it can win the max() that picks the recommended version for a loader.
def is_release_version(version):
    text = str(version)
    return text.startswith("1.") and "snapshot" not in text.lower()


def _version_key(version):
    """Numeric-aware ordering, matching JS localeCompare(numeric: true).

    Without it "1.9" sorts above "1.20.1" and the verdict recommends a version
    three years out of date.
    """
    return [(1, int(tok)) if tok.isdigit() else (0, tok)
            for tok in re.findall(r"\d+|\D+", version)]


def was_checked(mod):
    return bool(mod.get("versions"))


def compute_compatibility(mods, unchecked_count):
    """`mods` are those we got versions for; `unchecked_count` is the rest.

    Returns {"type": "good"|"warning"|"bad", "text": str}.
    """
    total = len(mods) + unchecked_count
    if not total:
        return {"type": "bad", "text": "No mods to check"}
    if not mods:
        return {"type": "bad",
                "text": f"None of your {total} mods could be checked — see the reasons below"}

    # dict.fromkeys preserves first-seen order the way a JS Set does; a Python
    # set would reorder and change which loader is named first.
    per_mod = [list(dict.fromkeys(
        f"{v}|{normalize_loader(l)}" for v, l in (m.get("versions") or [])
    )) for m in mods]

    first = per_mod[0]
    rest = [set(s) for s in per_mod[1:]]
    intersection = [k for k in first if all(k in s for s in rest)]

    if intersection:
        by_loader = {}
        for key in intersection:
            version, loader = key.split("|")
            by_loader.setdefault(loader, []).append(version)
        # Sorted so the sentence is stable regardless of provider ordering.
        results = [f"{loader} {max(versions, key=_version_key)}"
                   for loader, versions in sorted(by_loader.items())]
        joined = " & ".join(results)

        if not unchecked_count:
            return {"type": "good",
                    "text": f"All your mods are compatible with {joined}"}
        return {"type": "warning",
                "text": (f"{len(mods)} of your {total} mods share: {joined}"
                         f" — {unchecked_count} could not be checked")}

    counts = {}
    for keys in per_mod:
        for key in keys:
            counts[key] = counts.get(key, 0) + 1
    if not counts:
        return {"type": "bad", "text": "No version information for these mods"}

    top_key, top_count = max(counts.items(), key=lambda kv: kv[1])
    version, loader = top_key.split("|")
    if top_count / total >= 0.5:
        return {"type": "warning",
                "text": f"Most of your mods share: {loader} {version} ({top_count}/{total})"}
    return {"type": "bad",
            "text": (f"No version works for all your mods. "
                     f"The closest is {loader} {version} ({top_count}/{total}).")}
