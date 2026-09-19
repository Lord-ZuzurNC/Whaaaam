## What this changes

<!-- One or two sentences. Link the issue: "Fixes #123". -->

## How it was checked

- [ ] `python test_compat.py` passes (verdict logic, CLI/web parity)
- [ ] `python test_web.py` passes (HTTP edge, no network)
- [ ] Checked a list mixing a working mod, an unreachable mod and a junk URL: failures show as rows and count in the verdict
- [ ] UI change: checked all four themes (Latte, Frappé, Macchiato, Mocha) and 320px width

## Invariants

- [ ] If the verdict logic changed, `compat.py` and `static/app.js` changed together
- [ ] No third-party string (mod name, version) is put into HTML without escaping
- [ ] User-facing wording keeps the project vocabulary ("check", "URL", "could not be checked")
