"""Verdict logic, and proof the two interfaces still agree.

Run: python test_compat.py
"""

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from compat import compute_compatibility, is_release_version, normalize_loader

APP_JS = Path(__file__).parent / "static" / "app.js"


def mod(*versions):
    return {"versions": [list(v) for v in versions]}


# (mods, unchecked_count, timed_out, expected_type, expected_text)
CASES = [
    ([], 0, 0, "bad", "No mods to check"),
    ([], 3, 0, "bad", "None of your 3 mods could be checked — see the reasons below"),

    # The two strings PRODUCT.md records as real shipped output. If either of
    # these assertions fails, shipped product copy has been reworded.
    ([mod(("1.20.1", "fabric"), ("1.20.1", "forge")),
      mod(("1.20.1", "fabric"), ("1.20.1", "forge"))], 0, 0,
     "good", "All your mods are compatible with Fabric 1.20.1 & Forge 1.20.1"),
    ([mod(("1.20.1", "fabric"))] * 8 + [mod(("1.19.2", "forge"))] * 2, 0, 0,
     "warning", "Most of your mods share: Fabric 1.20.1 (8/10)"),

    # Invariant 3: a single unchecked mod blocks "all compatible".
    ([mod(("1.20.1", "fabric"))], 1, 0,
     "warning", "1 of your 2 mods share: Fabric 1.20.1 — 1 could not be checked"),

    # Invariant 1: unchecked mods stay in the denominator (3, not 2).
    ([mod(("1.20.1", "fabric")), mod(("1.20.1", "fabric"))], 1, 0,
     "warning", "2 of your 3 mods share: Fabric 1.20.1 — 1 could not be checked"),

    # No consensus at all: name the closest so the user knows what to drop.
    ([mod(("1.20.1", "fabric")), mod(("1.7.10", "forge")), mod(("1.21.4", "neoforge"))], 0, 0,
     "bad", "No version works for all your mods. The closest is Fabric 1.20.1 (1/3)."),

    # Numeric-aware version choice: 1.21.11 must beat 1.9 and 1.20.1.
    ([mod(("1.9", "fabric"), ("1.20.1", "fabric"), ("1.21.11", "fabric")),
      mod(("1.9", "fabric"), ("1.20.1", "fabric"), ("1.21.11", "fabric"))], 0, 0,
     "good", "All your mods are compatible with Fabric 1.21.11"),

    # Loader casing is normalised from whatever the providers return.
    ([mod(("1.20.1", "NEOFORGE")), mod(("1.20.1", "neoForge"))], 0, 0,
     "good", "All your mods are compatible with NeoForge 1.20.1"),

    # A run that ran out of time is an incomplete answer, never a negative one.
    # Without these three, an 80-mod list that is perfectly compatible reported
    # "No version works for all your mods. The closest is Fabric 1.20.1 (12/80)."
    ([mod(("1.20.1", "fabric"))] * 12, 68, 68, "warning",
     "12 of your 80 mods share: Fabric 1.20.1 — the check ran out of time before 68 "
     "could be fetched. Everything fetched is cached, so checking again will be quick."),

    # No consensus among what was fetched — still not "bad" while a timeout is in play.
    ([mod(("1.20.1", "fabric")), mod(("1.7.10", "forge"))], 8, 8, "warning",
     "Only 2 of your 10 mods were fetched — the check ran out of time before 8 could "
     "be fetched. This is not a full answer yet. Everything fetched is cached, so "
     "checking again will be quick."),

    ([], 5, 5, "warning",
     "None of your 5 mods were fetched — the check ran out of time before 5 could "
     "be fetched. Everything fetched is cached, so checking again will be quick."),

    # Mixed: some mods ran out of time, others will never resolve. Telling a user
    # to "check again" about a typo'd URL is the same class of wrong answer as
    # calling a slow run incompatible, so each gap names its own cause.
    ([mod(("1.20.1", "fabric"))] * 6, 4, 2, "warning",
     "6 of your 10 mods share: Fabric 1.20.1 — 4 could not be checked, 2 of them "
     "because the check ran out of time. Everything fetched is cached, so checking "
     "again will be quick."),

    ([], 4, 1, "warning",
     "None of your 4 mods were fetched — 4 could not be checked, 1 of them because "
     "the check ran out of time. Everything fetched is cached, so checking again "
     "will be quick."),

    ([mod(("1.20.1", "fabric")), mod(("1.7.10", "forge"))], 8, 3, "warning",
     "Only 2 of your 10 mods were fetched — 8 could not be checked, 3 of them "
     "because the check ran out of time. This is not a full answer yet. "
     "Everything fetched is cached, so checking again will be quick."),
]


def check_python():
    for mods, unchecked, timed_out, want_type, want_text in CASES:
        got = compute_compatibility(mods, unchecked, timed_out)
        assert got["type"] == want_type, f"{want_text!r}: type {got['type']!r} != {want_type!r}"
        assert got["text"] == want_text, f"expected {want_text!r}\n     got {got['text']!r}"
    assert normalize_loader("neoforge") == "NeoForge"
    assert normalize_loader("") == ""

    # keys must name the same answer the sentence does, or the table would mark
    # the wrong rows as outside the consensus.
    full = compute_compatibility([mod(("1.20.1", "fabric"))] * 2, 0)
    assert full["keys"] == ["1.20.1|Fabric"], full["keys"]
    assert full["headline"] == "Fabric 1.20.1"
    most = compute_compatibility([mod(("1.20.1", "fabric"))] * 8
                                 + [mod(("1.19.2", "forge"))] * 2, 0)
    assert most["keys"] == ["1.20.1|Fabric"], most["keys"]
    assert compute_compatibility([], 3)["keys"] == []
    print(f"python: {len(CASES)} cases pass")


def _extract(source, signature):
    """Pull one top-level function out of app.js by brace matching."""
    start = source.index(signature)
    depth, i = 0, source.index("{", start)
    while True:
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
        i += 1


def check_js_agrees():
    """Run the shipped browser implementation on the same cases."""
    node = shutil.which("node")
    if not node:
        print("node not found - skipped the JS parity half")
        return
    src = APP_JS.read_text(encoding="utf-8")
    harness = "\n".join([
        _extract(src, "function normalizeLoader("),
        _extract(src, "function computeCompatibility("),
        "const cases = JSON.parse(process.argv[2]);",
        "console.log(JSON.stringify(cases.map(c => computeCompatibility(c[0], c[1], c[2]))));",
    ])
    payload = json.dumps([[m, u, t] for m, u, t, _, _ in CASES])
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
        fh.write(harness)
        path = fh.name
    try:
        out = subprocess.run([node, path, payload], capture_output=True, text=True, check=True)
    finally:
        Path(path).unlink(missing_ok=True)
    js = json.loads(out.stdout)
    for (mods, unchecked, timed_out, _, want_text), got in zip(CASES, js):
        py = compute_compatibility(mods, unchecked, timed_out)
        assert got["text"] == py["text"], (
            f"CLI and web disagree.\n  python: {py['text']!r}\n  js    : {got['text']!r}")
        # The whole verdict, not just its sentence: `headline` drives the display
        # figure and `keys` decides which rows are marked outside the consensus,
        # so a drift in either would show different answers in the two interfaces.
        for field in ("type", "headline", "keys"):
            assert got[field] == py[field], (
                f"{field} mismatch for {want_text!r}\n"
                f"  python: {py[field]!r}\n  js    : {got[field]!r}")
    print(f"js parity: {len(CASES)} cases identical to python")


def check_vocabulary():
    """The rules that keep a fake loader or a snapshot out of the verdict."""
    for good in ("1.20.1", "1.21.11", "1.7.10", "1.12.2"):
        assert is_release_version(good), good
    for bad in ("1.20.5-Snapshot", "1.14-Snapshot", "23w13a", "Forge", "", "Fabric 1.20"):
        assert not is_release_version(bad), bad
    assert normalize_loader("neoforge") == normalize_loader("NeoForge") == "NeoForge"
    print("vocabulary: release-version and loader rules hold")


def _relative_luminance(hex_colour):
    channels = [int(hex_colour.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    channels = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
                for c in channels]
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(a, b):
    light, dark = sorted((_relative_luminance(a), _relative_luminance(b)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


# (foreground, background, floor, why)
CONTRAST_PAIRS = [
    ("text", "bg", 4.5, "body copy on the canvas"),
    ("text", "surface", 4.5, "body copy on a raised surface"),
    ("subtext", "bg", 4.5, "secondary copy on the canvas"),
    ("subtext", "surface", 4.5, "secondary copy on a raised surface"),
    ("text", "good-tint", 4.5, "verdict copy, agreeing list"),
    ("text", "warn-tint", 4.5, "verdict copy, partial list"),
    ("text", "bad-tint", 4.5, "verdict copy, disagreeing list"),
    ("on-accent", "accent", 4.5, "primary button label"),
    ("border", "bg", 3.0, "control edge on the canvas"),
    ("border", "surface", 3.0, "control edge on a raised surface"),
    # 3:1 because the wordmark is WCAG large text — which is only true while
    # --step-3's floor stays at 24px. The assertion below enforces that, so
    # shrinking the wordmark fails here rather than silently dropping below AA.
    ("accent", "surface", 3.0, "wordmark on the header (large text)"),
]


def check_contrast():
    """Every palette against the accessibility floor CLAUDE.md commits to.

    This exists because the rule was previously verified by hand, against the
    wrong background: the header is --surface, not --bg, and measuring the
    wordmark against the canvas hid a real AA failure behind a palette
    deviation that bought 0.2 and still failed. "Verify, don't assume" only
    works if something does the verifying.
    """
    css = (Path(__file__).parent / "static" / "styles.css").read_text(encoding="utf-8")

    floor = re.search(r"--step-3:\s*clamp\(\s*([\d.]+)rem", css)
    assert floor, "could not read the --step-3 clamp floor"
    assert float(floor.group(1)) >= 1.5, (
        f"--step-3 floor is {floor.group(1)}rem; below 1.5rem the wordmark stops "
        "being WCAG large text and the accent needs 4.5:1, which no light "
        "palette's blue reaches on --surface")

    palettes = {m.group(1): dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", m.group(2)))
                for m in re.finditer(r'\[data-theme="(\w+)"\]\s*\{([^}]*)\}', css)}
    assert len(palettes) == 4, f"expected 4 Catppuccin palettes, found {sorted(palettes)}"

    # The :root fallback mirrors Mocha and is what renders before theme-init
    # runs, or at all if scripting is off, so it is a real rendered palette and
    # is held to the same floor.
    for block in re.findall(r":root\s*\{([^}]*)\}", css):
        tokens = dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})", block))
        if "bg" in tokens and "text" in tokens:
            palettes[":root fallback"] = tokens
            break
    assert ":root fallback" in palettes, "no :root colour fallback found"

    for name, tokens in sorted(palettes.items()):
        for fg, bg, minimum, why in CONTRAST_PAIRS:
            assert fg in tokens and bg in tokens, f"{name}: missing --{fg} or --{bg}"
            ratio = contrast(tokens[fg], tokens[bg])
            assert ratio >= minimum, (
                f"{name}: --{fg} on --{bg} is {ratio:.2f}:1, below {minimum} ({why})")

    print(f"contrast: {len(CONTRAST_PAIRS)} pairs clear the floor in "
          f"{len(palettes)} palettes (4 themes + the :root fallback)")


def check_curseforge_pairs():
    """A file we cannot attribute contributes nothing — it must never become
    a loader called "Unknown", which once shipped in the verdict."""
    try:
        from providers.curseforge import index_pairs, loaders_for_file
    except Exception as exc:  # needs CF_API_KEY at import time
        print(f"curseforge helpers: skipped ({type(exc).__name__})")
        return

    assert loaders_for_file({"gameVersions": ["1.20.1", "Fabric"]}) == {"Fabric"}
    assert loaders_for_file({"gameVersions": ["1.20.1", "NeoForge"]}) == {"NeoForge"}
    assert loaders_for_file({"gameVersions": ["1.20.1", "Forge"]}) == {"Forge"}
    # An ancient jar with no loader signal anywhere.
    assert loaders_for_file({"gameVersions": ["1.12.2"], "fileName": "jei-1.12.2.jar"}) == set()
    # Filename fallback when the tags say nothing.
    assert loaders_for_file({"gameVersions": ["1.20.1"],
                             "fileName": "sodium-fabric-0.5.jar"}) == {"Fabric"}

    mod = {"latestFilesIndexes": [
        {"gameVersion": "1.20.1", "modLoader": 4},           # Fabric
        {"gameVersion": "1.20.1", "modLoader": 6},           # NeoForge
        {"gameVersion": "1.20.5-Snapshot", "modLoader": 4},  # snapshot, dropped
        {"gameVersion": "1.20.1", "modLoader": 3},           # LiteLoader, dropped
        {"gameVersion": "1.20.1", "modLoader": 0},           # Any, dropped
    ]}
    assert index_pairs(mod) == {("1.20.1", "Fabric"), ("1.20.1", "NeoForge")}
    print("curseforge: no fabricated loaders, no snapshots")


if __name__ == "__main__":
    check_python()
    check_vocabulary()
    check_contrast()
    check_curseforge_pairs()
    check_js_agrees()
    print("ok")
