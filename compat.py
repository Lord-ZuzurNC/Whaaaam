"""Compatibility verdict for a list of mods.

This is the product: the one answer about the whole pasted list. `static/app.js`
carries a mirror of this logic for the web UI, so the two must stay identical —
`test_compat.py` runs both against the same cases and fails if they disagree.

The invariants (also in CLAUDE.md):
  1. A mod that could not be checked is never dropped from the denominator.
  2. The verdict is computed before any filtering, unless the user forces it:
     `only_version` / `only_loader` narrow every mod's pairs first, and a mod
     left with none still counts in the denominator.
  3. "All your mods are compatible" requires zero unchecked mods.
"""

import re

LOADERS = {"neoforge": "NeoForge", "forge": "Forge",
           "fabric": "Fabric", "quilt": "Quilt"}

# The remedy, stated at the moment it is true: a run that ran out of time still
# warmed the cache, so the next one is cheap. PRODUCT.md principle 3, made visible.
CACHE_REMEDY = "Everything fetched is cached, so checking again will be quick."


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


def forced_label(only_version=None, only_loader=None):
    """What a forced verdict is limited to, e.g. "Forge 1.21.11"."""
    return " ".join(p for p in (normalize_loader(only_loader), only_version) if p)


def compute_compatibility(mods, unchecked_count, timed_out=0,
                          only_version=None, only_loader=None):
    """`mods` are those we got versions for; `unchecked_count` is the rest.

    `timed_out` is how many of those ran out of time rather than failing. The
    distinction is the whole point: an unfetched mod is an unanswered question,
    not an incompatible one. Reporting "No version works for all your mods" for
    a run that simply did not finish is a confident wrong answer about someone's
    mod list, and the rational response to it is to go and dismantle a working
    list. A timed-out run therefore never returns "bad".

    Returns {"type": ..., "text": str, "headline": str}. `headline` is the
    version+loader figure alone, so the renderer can set the answer at display
    scale inside the sentence without the sentence being reworded or duplicated.
    It is "" when there is no figure to name. `keys` carries the same answer as
    "<version>|<Loader>" strings, so a caller can mark which mods are outside it
    without re-deriving the intersection and drifting from this function.
    """
    total = len(mods) + unchecked_count

    def outstanding():
        """Name what is missing without blaming the wrong cause.

        A run can hold both kinds of gap at once — mods that ran out of time and
        mods that will never resolve — and telling the user to "check again"
        about a typo'd URL is the same class of wrong answer as calling a slow
        run incompatible.
        """
        if timed_out == unchecked_count:
            return f"the check ran out of time before {timed_out} could be fetched"
        return (f"{unchecked_count} could not be checked, {timed_out} of them "
                f"because the check ran out of time")

    if not total:
        return {"type": "bad", "headline": "", "keys": [], "text": "No mods to check"}
    if not mods:
        if timed_out:
            return {"type": "warning", "headline": "", "keys": [],
                    "text": (f"None of your {total} mods were fetched — "
                             f"{outstanding()}. {CACHE_REMEDY}")}
        return {"type": "bad", "headline": "", "keys": [],
                "text": f"None of your {total} mods could be checked — see the reasons below"}

    # dict.fromkeys preserves first-seen order the way a JS Set does; a Python
    # set would reorder and change which loader is named first.
    # Forcing narrows each mod's pairs, never the list: a mod with nothing left
    # stays in per_mod as an empty entry, so it still counts against the total.
    per_mod = [list(dict.fromkeys(
        f"{v}|{normalize_loader(l)}" for v, l in (m.get("versions") or [])
        if (not only_version or v == only_version)
        and (not only_loader or normalize_loader(l) == normalize_loader(only_loader))
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
            return {"type": "good", "headline": joined, "keys": intersection,
                    "text": f"All your mods are compatible with {joined}"}
        if timed_out:
            return {"type": "warning", "headline": joined, "keys": intersection,
                    "text": (f"{len(mods)} of your {total} mods share: {joined} — "
                             f"{outstanding()}. {CACHE_REMEDY}")}
        return {"type": "warning", "headline": joined, "keys": intersection,
                "text": (f"{len(mods)} of your {total} mods share: {joined}"
                         f" — {unchecked_count} could not be checked")}

    # Before naming a "closest" match: if the run was cut short, the absence of a
    # consensus is not evidence of one.
    if timed_out:
        return {"type": "warning", "headline": "", "keys": [],
                "text": (f"Only {len(mods)} of your {total} mods were fetched — "
                         f"{outstanding()}. This is not a full answer yet. "
                         f"{CACHE_REMEDY}")}

    counts = {}
    for keys in per_mod:
        for key in keys:
            counts[key] = counts.get(key, 0) + 1
    if not counts and (only_version or only_loader):
        return {"type": "bad", "headline": "", "keys": [],
                "text": f"None of your mods have {forced_label(only_version, only_loader)} (0/{total})"}
    if not counts:
        return {"type": "bad", "headline": "", "keys": [], "text": "No version information for these mods"}

    top_key, top_count = max(counts.items(), key=lambda kv: kv[1])
    version, loader = top_key.split("|")
    if top_count / total >= 0.5:
        return {"type": "warning", "headline": f"{loader} {version}", "keys": [top_key],
                "text": f"Most of your mods share: {loader} {version} ({top_count}/{total})"}
    return {"type": "bad", "headline": f"{loader} {version}", "keys": [top_key],
            "text": (f"No version works for all your mods. "
                     f"The closest is {loader} {version} ({top_count}/{total}).")}
