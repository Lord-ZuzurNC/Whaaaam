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


# (mods, unchecked_count, expected_type, expected_text)
CASES = [
    ([], 0, "bad", "No mods to check"),
    ([], 3, "bad", "None of your 3 mods could be checked — see the reasons below"),

    # The two strings PRODUCT.md records as real shipped output. If either of
    # these assertions fails, shipped product copy has been reworded.
    ([mod(("1.20.1", "fabric"), ("1.20.1", "forge")),
      mod(("1.20.1", "fabric"), ("1.20.1", "forge"))], 0,
     "good", "All your mods are compatible with Fabric 1.20.1 & Forge 1.20.1"),
    ([mod(("1.20.1", "fabric"))] * 8 + [mod(("1.19.2", "forge"))] * 2, 0,
     "warning", "Most of your mods share: Fabric 1.20.1 (8/10)"),

    # Invariant 3: a single unchecked mod blocks "all compatible".
    ([mod(("1.20.1", "fabric"))], 1,
     "warning", "1 of your 2 mods share: Fabric 1.20.1 — 1 could not be checked"),

    # Invariant 1: unchecked mods stay in the denominator (3, not 2).
    ([mod(("1.20.1", "fabric")), mod(("1.20.1", "fabric"))], 1,
     "warning", "2 of your 3 mods share: Fabric 1.20.1 — 1 could not be checked"),

    # No consensus at all: name the closest so the user knows what to drop.
    ([mod(("1.20.1", "fabric")), mod(("1.7.10", "forge")), mod(("1.21.4", "neoforge"))], 0,
     "bad", "No version works for all your mods. The closest is Fabric 1.20.1 (1/3)."),

    # Numeric-aware version choice: 1.21.11 must beat 1.9 and 1.20.1.
    ([mod(("1.9", "fabric"), ("1.20.1", "fabric"), ("1.21.11", "fabric")),
      mod(("1.9", "fabric"), ("1.20.1", "fabric"), ("1.21.11", "fabric"))], 0,
     "good", "All your mods are compatible with Fabric 1.21.11"),

    # Loader casing is normalised from whatever the providers return.
    ([mod(("1.20.1", "NEOFORGE")), mod(("1.20.1", "neoForge"))], 0,
     "good", "All your mods are compatible with NeoForge 1.20.1"),
]


def check_python():
    for mods, unchecked, want_type, want_text in CASES:
        got = compute_compatibility(mods, unchecked)
        assert got["type"] == want_type, f"{want_text!r}: type {got['type']!r} != {want_type!r}"
        assert got["text"] == want_text, f"expected {want_text!r}\n     got {got['text']!r}"
    assert normalize_loader("neoforge") == "NeoForge"
    assert normalize_loader("") == ""
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
        "console.log(JSON.stringify(cases.map(c => computeCompatibility(c[0], c[1]))));",
    ])
    payload = json.dumps([[m, u] for m, u, _, _ in CASES])
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
        fh.write(harness)
        path = fh.name
    try:
        out = subprocess.run([node, path, payload], capture_output=True, text=True, check=True)
    finally:
        Path(path).unlink(missing_ok=True)
    js = json.loads(out.stdout)
    for (mods, unchecked, _, want_text), got in zip(CASES, js):
        py = compute_compatibility(mods, unchecked)
        assert got["text"] == py["text"], (
            f"CLI and web disagree.\n  python: {py['text']!r}\n  js    : {got['text']!r}")
        assert got["type"] == py["type"], f"type mismatch for {want_text!r}"
    print(f"js parity: {len(CASES)} cases identical to python")


def check_vocabulary():
    """The rules that keep a fake loader or a snapshot out of the verdict."""
    for good in ("1.20.1", "1.21.11", "1.7.10", "1.12.2"):
        assert is_release_version(good), good
    for bad in ("1.20.5-Snapshot", "1.14-Snapshot", "23w13a", "Forge", "", "Fabric 1.20"):
        assert not is_release_version(bad), bad
    assert normalize_loader("neoforge") == normalize_loader("NeoForge") == "NeoForge"
    print("vocabulary: release-version and loader rules hold")


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
    check_curseforge_pairs()
    check_js_agrees()
    print("ok")
