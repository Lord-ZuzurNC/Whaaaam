# Whaaaam

**Whaaaam** tells you what Minecraft version and mod loader all your mods have in common.

Paste your CurseForge and Modrinth mod URLs, and instantly see which Minecraft versions and loaders (Forge, Fabric, NeoForge, Quilt) are compatible across your entire mod list.


## Features

- **Multi-Source Support** - Works with both CurseForge and Modrinth URLs
- **Compatibility Analysis** - Instantly finds common versions/loaders across all mods
- **Dual Interface** - Use via CLI or web browser
- **Smart Filtering** - Filter results by Minecraft version or mod loader
- **Export Options** - Download your mod list as Markdown or CSV
- **Beautiful Themes** - 4 Catppuccin themes (Latte, Frappé, Macchiato, Mocha) with smooth transitions
- **Caching** - Fast repeated lookups with local cache

## Quick Start

### Prerequisites

- Curl and Git

```bash
apt install -y git curl
```

- Python 3.8+
- pip

```bash
apt install -y python3 python3-venv python3-pip build-essential
```

### Installation

```bash
# Clone the repository
git clone https://github.com/Lord-ZuzurNC/Whaaaam.git
cd Whaaaam

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

There is no frontend build step — `static/styles.css` is served as authored.

### Usage

#### Web Interface (Recommended)

```bash
python web.py
```

Open your browser to `http://localhost:5000`, paste your mod URLs (one per line), and click **Check compatibility**.

`web.py` binds `127.0.0.1` and starts Flask's development server. Set `HOST` and
`PORT` to move it, but do not expose that server directly — it has no
request-size or slow-client protection of its own.

#### Deployment

Every check spends your `CF_API_KEY`, so a reachable instance needs a limit in
front of it. Run under a real WSGI server:

```bash
gunicorn -w 4 --threads 8 -b 127.0.0.1:5000 --timeout 60 web:app
```

`--threads` matters: a check is long and I/O-bound, and with the default sync
worker one slow request occupies a whole worker. With four sync workers, four
requests were enough to make the service unavailable to everyone else.

Rate-limiting belongs at the reverse proxy, which is the only place that sees
every worker's traffic. A working configuration is committed at
[`deploy/nginx.conf`](deploy/nginx.conf) — it is a file rather than a snippet in
this README because a limit described in prose enforces nothing.

The app bounds a single request on its own: 256 KB of body, 200 URLs, and a 45
second deadline after which unfinished mods come back as rows saying so. Those
are per-request; only the proxy can cap requests per caller. Keep the proxy's
`proxy_read_timeout` above the app's deadline so the app returns its own partial
answer instead of the proxy cutting the connection.

The response cache is capped at 256 MB (`CACHE_MAX_BYTES`) and evicts
oldest-first, but give `cache/` a bounded volume anyway so a full disk cannot
take the host down with it.

#### Command Line

The CLI gives the same answer as the web UI — same checking, same verdict, same wording.

```bash
# URLs as arguments
python main.py https://modrinth.com/mod/sodium https://www.curseforge.com/minecraft/mc-mods/jei

# from a file, or piped in
python main.py --file mods.txt
cat mods.txt | python main.py

# or paste interactively: run with no arguments, blank line to finish
python main.py
```

| Option             | What it does                                       |
| ------------------ | -------------------------------------------------- |
| `--version 1.20.1` | only show table rows for that Minecraft version    |
| `--loader fabric`  | only show table rows for that loader               |
| `--show-versions`  | list every version instead of a count              |
| `--export md\|csv` | write the results to a file (`--out -` for stdout) |
| `--clear-cache`    | delete the cached version data and exit            |

Filters narrow the table; they never change the verdict above it. Exit status is
`0` when a shared version exists, `2` when none does, `1` when no URLs were given
— so it composes into scripts.

## How It Works

1. **Paste URLs** - Add CurseForge or Modrinth mod page URLs
2. **Check** - Whaaaam fetches version data from each platform's API in parallel
3. **Compare** - All mod versions are cross-referenced to find common compatibility
4. **Results** - See which Minecraft versions and loaders work with ALL your mods.
   Mods that could not be fetched are listed with the reason and still counted, so
   a green verdict always means the whole list was checked.

### Example Output

```text
All your mods are compatible with Fabric 1.20.1 & Forge 1.20.1
```

Or if there's partial compatibility:

```text
Most of your mods share: Fabric 1.20.1 (8/10)
```

## Supported Platforms

| Platform   | URL Format                                              |
| ---------- | ------------------------------------------------------- |
| CurseForge | `https://www.curseforge.com/minecraft/mc-mods/mod-name` |
| Modrinth   | `https://modrinth.com/mod/mod-name`                     |

## Theme System

Whaaaam features 4 beautiful Catppuccin color themes that you can switch between seamlessly:

- **Latte** - Light theme with warm, cozy colors
- **Frappé** - Cool dark theme with subtle purple tones
- **Macchiato** - Darker theme with rich, saturated colors
- **Mocha** - Deep dark theme, perfect for late-night sessions (default)

![Theme Switcher](docs/screenshot_themes.png)

Themes are automatically saved to your browser and can be shared via URL (e.g., `?theme=latte`).

### For Developers

The theme system is built with:
- **CSS custom properties** - one `[data-theme]` block per palette in `static/styles.css`
- **Catppuccin Colors** - all 4 palettes, mapped to semantic roles rather than raw swatches
- **ThemeManager API** - JavaScript module for programmatic theme control
- **URL Parameters** - Share themes via `?theme=<name>` in the URL

To customize or extend themes, see the [Development](#development) section below.

## Configuration

### Environment Variables

| Variable     | Description                   | Default |
| ------------ | ----------------------------- | ------- |
| `CF_API_KEY` | CurseForge API key (required) | None    |

`CF_API_KEY` is checked when `providers/curseforge.py` is imported, so the app
will not start without it — including for a Modrinth-only mod list. Set it in your
environment or in a `.env` file.

## Development

### Frontend

`static/styles.css` is authored by hand and served as-is. There is no build step,
no bundler and no CSS framework — edit the file and reload.

The design system it implements (tokens, type scale, components, named rules) is
documented in [DESIGN.md](DESIGN.md).

### Theme System Architecture

**Tokens** (`static/styles.css`, section 1):
- One `[data-theme="..."]` block per palette: latte, frappe, macchiato, mocha
- Each defines the same 18 semantic properties — `--bg`, `--surface`, `--line`,
  `--border`, `--text`, `--subtext`, `--accent`, `--on-accent`, the verdict
  statuses, and so on
- Components read tokens; they never hard-code a colour
- A Mocha-valued `:root` fallback sits **above** the theme blocks, because
  `:root` and `[data-theme="x"]` share specificity and source order decides

**JavaScript** (`static/app.js`):
- `ThemeManager` module with IIFE pattern for encapsulation
- Public API: `setTheme(name)`, `getTheme()`, `initTheme()`
- Handles localStorage persistence and URL parameter sync
- Priority: URL param > localStorage > default ("mocha")

**HTML** (`templates/index.html`):
- Theme attribute on `<html data-theme="mocha">` — the only theme signal
- Circular theme switcher as an ARIA `radiogroup` with roving tabindex
- Keyboard navigation: arrow keys, Home and End

### Accessibility

Every foreground/background pair is verified against WCAG AA in all four palettes.
Latte is the strict one — its accents are mid-lightness, so a colour that passes on
Mocha can fail there. The page has a single live region (`#sr-announce`), a
`prefers-reduced-motion` path, and a `forced-colors` path.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Security

For security vulnerabilities, please see [SECURITY.md](SECURITY.md).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Thanks to the [CurseForge](https://www.curseforge.com/) and [Modrinth](https://modrinth.com/) teams for their APIs.
- Built with [Flask](https://flask.palletsprojects.com/) and love.

---

Made with love by [Lord_ZuzurNC](https://github.com/Lord-ZuzurNC)
