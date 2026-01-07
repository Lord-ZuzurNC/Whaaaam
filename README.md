# Whaaaam

**Whaaaam** tells you what Minecraft version and mod loader all your mods have in common.

Paste your CurseForge and Modrinth mod URLs, and instantly see which Minecraft versions and loaders (Forge, Fabric, NeoForge, Quilt) are compatible across your entire mod list.

## Features

- **Multi-Source Support** - Works with both CurseForge and Modrinth URLs
- **Compatibility Analysis** - Instantly finds common versions/loaders across all mods
- **Dual Interface** - Use via CLI or web browser
- **Smart Filtering** - Filter results by Minecraft version or mod loader
- **Export Options** - Download your mod list as Markdown or CSV
- **Dark Mode** - Easy on the eyes for late-night modding sessions
- **Caching** - Fast repeated lookups with local cache

## Quick Start

### Prerequisites

- Python 3.8+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/Lord-ZuzurNC/Whaaaam.git
cd Whaaaam

# Install dependencies
pip install -r requirements.txt
```

### Usage

#### Web Interface (Recommended)

```bash
python web.py
```

Open your browser to `http://localhost:5000`, paste your mod URLs (one per line), and click **Analyze**.

#### Command Line

```bash
python main.py
```

Enter your mod URLs one per line, then press Enter on an empty line to analyze.

## How It Works

1. **Paste URLs** - Add CurseForge or Modrinth mod page URLs
2. **Analyze** - Whaaaam fetches version data from each platform's API
3. **Compare** - All mod versions are cross-referenced to find common compatibility
4. **Results** - See which Minecraft versions and loaders work with ALL your mods

### Example Output

```
All your mods are compatible with Fabric 1.20.1 & Forge 1.20.1
```

Or if there's partial compatibility:

```
Most of your mods share: Fabric 1.20.1 (8/10)
```

## Supported Platforms

| Platform | URL Format |
|----------|------------|
| CurseForge | `https://www.curseforge.com/minecraft/mc-mods/mod-name` |
| Modrinth | `https://modrinth.com/mod/mod-name` |

## Configuration

No configuration required! Whaaaam works out of the box.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CF_API_KEY` | CurseForge API key (optional, for higher rate limits) | None |

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Security

For security vulnerabilities, please see [SECURITY.md](SECURITY.md).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Thanks to the [CurseForge](https://www.curseforge.com/) and [Modrinth](https://modrinth.com/) teams for their APIs
- Built with [Flask](https://flask.palletsprojects.com/) and love

---

Made with love by [Lord_ZuzurNC](https://github.com/Lord-ZuzurNC)
