"""Whaaaam command line interface.

Mirrors the web UI: the same checking, the same verdict, the same words. The
verdict and the fetching come from `compat.py` and `modlist.py`, which the Flask
app also uses, so the two interfaces cannot answer the same list differently.
"""

import argparse
import csv
import io
import os
import sys
import time

from tabulate import tabulate

import modlist
from compat import compute_compatibility, normalize_loader, was_checked

# The verdict is the only thing allowed to be loud — the same rule the web UI
# follows. Colour is dropped when piped, or when NO_COLOR is set.
TONE = {"good": "\033[32m", "warning": "\033[33m", "bad": "\033[31m"}
BOLD, RESET = "\033[1m", "\033[0m"


def use_colour(stream):
    if os.environ.get("NO_COLOR"):
        return False
    return hasattr(stream, "isatty") and stream.isatty()


def paint(text, tone, stream):
    if not use_colour(stream):
        return text
    return f"{BOLD}{TONE.get(tone, '')}{text}{RESET}"


def read_urls(args):
    """URLs from arguments, a file, a pipe, or an interactive paste."""
    if args.urls:
        return args.urls
    if args.file:
        with open(args.file, encoding="utf-8") as handle:
            return [line.strip() for line in handle if line.strip()]
    if not sys.stdin.isatty():
        return [line.strip() for line in sys.stdin if line.strip()]

    print("Paste your CurseForge and Modrinth mod URLs, one per line.")
    print("Press Enter on an empty line to check them.")
    urls = []
    while True:
        try:
            line = input().strip()
        except EOFError:
            break
        if not line:
            break
        urls.append(line)
    return urls


def filter_versions(mod, want_version, want_loader):
    return [
        (version, loader)
        for version, loader in (mod.get("versions") or [])
        if (not want_version or version == want_version)
        and (not want_loader or normalize_loader(loader) == normalize_loader(want_loader))
    ]


def outside_consensus(mod, keys):
    """True when a mod carries none of the verdict's consensus pairs."""
    if not keys:
        return False
    return not any(f"{version}|{normalize_loader(loader)}" in keys
                   for version, loader in (mod.get("versions") or []))


def render_table(checked, want_version, want_loader, expand, keys=()):
    """The web collapses a mod's versions behind a disclosure showing the count.
    The default here matches that: a 60-mod list should not print 2,000 rows."""
    rows = []
    for mod in checked:
        versions = filter_versions(mod, want_version, want_loader)
        if not versions:
            continue
        seen = list(dict.fromkeys(
            f"{version} → {normalize_loader(loader)}" for version, loader in versions
        ))
        if expand:
            cell = "\n".join(seen)
        else:
            cell = f"{len(seen)} version{'' if len(seen) == 1 else 's'}"
        name = mod.get("name") or mod.get("url") or "Unknown"
        if outside_consensus(mod, keys):
            name = f"{name}  (outside)"
        rows.append([
            (mod.get("provider") or "?").title().replace("Curseforge", "CurseForge"),
            name,
            cell,
        ])
    return rows


def export_rows(results):
    for mod in results:
        name = mod.get("name") or mod.get("url") or "Unknown"
        provider = mod.get("provider") or "?"
        if was_checked(mod):
            for version, loader in mod["versions"]:
                yield [name, provider, version, normalize_loader(loader),
                       mod.get("url") or "", "ok"]
        else:
            yield [name, provider, "", "", mod.get("url") or "",
                   mod.get("error") or "unchecked"]


def csv_cell(value):
    text = "" if value is None else str(value)
    # A leading =, +, - or @ makes the cell a formula in Excel or Sheets.
    # "" in "=+-@" is True in Python, so an empty cell must be excluded first,
    # or every blank version column exports as a stray apostrophe.
    return "'" + text if text and text[0] in "=+-@\t\r" else text


def export(results, fmt, out):
    if fmt == "csv":
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(["Mod Name", "Provider", "Version", "Loader", "URL", "Status"])
        for row in export_rows(results):
            writer.writerow([csv_cell(cell) for cell in row])
        text = buffer.getvalue()
    else:
        lines = ["# Whaaaam", ""]
        for mod in results:
            name = mod.get("name") or mod.get("url") or "Unknown"
            lines.append(f"- **{name}** ({mod.get('provider') or '?'})")
            if was_checked(mod):
                for version, loader in mod["versions"]:
                    lines.append(f"  - {version} → {normalize_loader(loader)}")
            else:
                reason = mod.get("error") or "no versions returned"
                lines.append(f"  - Could not be checked: {reason}")
        text = "\n".join(lines) + "\n"

    if out == "-":
        sys.stdout.write(text)
        return None
    path = out or f"mods-{int(time.time() * 1000)}.{'csv' if fmt == 'csv' else 'md'}"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return path


def build_parser():
    parser = argparse.ArgumentParser(
        prog="python main.py",
        description="Find the Minecraft version and loader your whole mod list has in common.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
input:
  URLs are read from the arguments, else --file, else a pipe. With none of
  those, it asks you to paste them, one per line; an empty line checks.

examples:
  python main.py https://modrinth.com/mod/sodium https://www.curseforge.com/minecraft/mc-mods/jei
  python main.py --file mods.txt --loader fabric
  cat mods.txt | python main.py --export csv --out mods.csv
  python main.py --file mods.txt --export md --out -

exit status:
  0  the list shares a version (fully, or as a majority consensus)
  1  no URLs were given, or some mods were not fetched before the deadline
  2  the list shares no version, or nothing could be checked

environment (also read from a .env file next to the code):
  CF_API_KEY  CurseForge API key; only needed to check CurseForge mods
  NO_COLOR    any value turns off the coloured verdict

Filters narrow the table; they never change the verdict above it.""",
    )
    parser.add_argument("urls", nargs="*", metavar="URL",
                        help="CurseForge or Modrinth mod page URLs")
    parser.add_argument("-f", "--file", metavar="PATH",
                        help="read URLs from a file, one per line")
    parser.add_argument("--version", dest="mc_version", metavar="MC_VERSION",
                        help="only show rows for this Minecraft version, e.g. 1.20.1")
    parser.add_argument("--loader", metavar="LOADER",
                        help="only show rows for this loader: Forge, Fabric, NeoForge or Quilt")
    parser.add_argument("--show-versions", action="store_true",
                        help="list every version instead of a count (implied by a filter)")
    parser.add_argument("--export", choices=["md", "csv"],
                        help="write the results as Markdown or CSV")
    parser.add_argument("--out", metavar="PATH",
                        help="export destination, or - for stdout "
                             "(default: mods-<timestamp>.md or .csv here)")
    parser.add_argument("--clear-cache", action="store_true",
                        help="delete the cached version data and exit")
    return parser


def main():
    args = build_parser().parse_args()

    if args.clear_cache:
        removed = modlist.clear_cache()
        if not removed:
            print("The cache was already empty.")
            return 0
        print(f"Cache cleared ({removed} provider "
              f"{'directory' if removed == 1 else 'directories'}). "
              "The next check fetches every mod again.")
        return 0

    urls = read_urls(args)
    if not urls:
        print("Paste at least one CurseForge or Modrinth URL to check.", file=sys.stderr)
        return 1

    print(f"Checking {len(urls)} {'mod' if len(urls) == 1 else 'mods'}…", file=sys.stderr)
    results = modlist.check_urls(urls)

    checked = [m for m in results if was_checked(m)]
    unchecked = [m for m in results if not was_checked(m)]

    # Invariant: the verdict answers for the whole submitted list. Filters narrow
    # the table below it, never the answer above it.
    timed_out = sum(1 for m in unchecked if m.get("timed_out"))
    verdict = compute_compatibility(checked, len(unchecked), timed_out)
    print()
    print(paint(verdict["text"], verdict["type"], sys.stdout))
    print()

    filtered = bool(args.mc_version or args.loader)
    rows = render_table(checked, args.mc_version, args.loader,
                        args.show_versions or filtered, set(verdict.get("keys") or ()))
    if rows:
        print(tabulate(rows, headers=["Source", "Mod Name", "Versions / Loaders"],
                       tablefmt="grid"))
        if filtered and len(rows) != len(checked):
            print(f"Showing {len(rows)} of {len(checked)} checked mods.")
        if not args.show_versions and not filtered:
            print("Pass --show-versions to list them, "
                  "or --version/--loader to narrow the table.")
    elif checked:
        print('No mods match this filter. Drop --version/--loader to see every mod.')

    if unchecked:
        print()
        print("Could not be checked")
        width = max(len(m.get("name") or m.get("url") or "") for m in unchecked)
        for mod in unchecked:
            label = mod.get("name") or mod.get("url") or "Unknown mod"
            reason = mod.get("error") or "No versions listed for this mod"
            print(f"  {label.ljust(width)}  {reason}")

    if args.export:
        path = export(results, args.export, args.out)
        if path:
            print(f"\nWrote {path}")

    # A timed-out run is a warning, not a pass: before the timeout fix it
    # returned "bad" and exited 2, so leaving it on 0 would tell a script the
    # list is fine when nothing was answered. Genuine partial consensus keeps
    # its existing 0 so the contract for everything else is unchanged.
    if verdict["type"] == "bad":
        return 2
    return 1 if timed_out else 0


if __name__ == "__main__":
    sys.exit(main())
