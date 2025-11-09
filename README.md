# Minecraft Mod Matrix

> _A smarter way to build Minecraft modpacks — find which mods are compatible across versions and loaders in seconds._

---

[![Python](https://img.shields.io/badge/Python-3.10–3.12-blue?logo=python)](https://www.python.org/)  
[![Flask](https://img.shields.io/badge/Backend-Flask-000?logo=flask)](https://flask.palletsprojects.com/)  
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)  
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/Lord_ZuzurNC/3M-MinecraftModpackMatrix/python-app.yml?label=Build%20Status)](https://github.com/Lord-ZuzurNC/3M-MinecraftModpackMatrix/actions)

---

### 💡 Overview

Tired of checking **every single mod page** to see if they all support the same Minecraft version or loader?<br>
**Minecraft Mod Matrix (3M)** automates that for you.

Paste your Modrinth and CurseForge URLs, click **Analyze**, and get a beautiful table showing:

- ✅ Which mods are compatible
- ⚙️ Which versions and loaders they share
- 📊 Compatibility summary ribbons
- 💾 Exportable results in Markdown or CSV

---

### 🧩 Features

| Feature                     | Description                                                                      |
| --------------------------- | -------------------------------------------------------------------------------- |
| 🔍 **Smart Analysis**       | Automatically detects provider (CurseForge / Modrinth) and version-loader pairs. |
| 🧱 **Compatibility Ribbon** | Instantly shows if all mods share a common setup.                                |
| 🌓 **Theme Memory**         | Light/dark theme toggle — remembers your choice.                                 |
| 🧹 **Cache Management**     | Clear cached data with one click if results get stale.                           |
| ⚙️ **Filtering**            | Filter by game version or loader (Forge, Fabric, NeoForge, etc.).                |
| 📦 **Export**               | Save results as `mods-YYYYMMDD-HHMM.csv` or `.md`.                               |

---

### 🧰 Installation & Setup

#### Requirements

- **Python 3.10 → 3.12** (tested)
- **Flask** + **Flask-CORS**
- (OPTIONAL) **CurseForge API key** (if you use cursforge mods)

#### 1️⃣ Clone the Repository

```bash
git clone https://github.com/Lord_ZuzurNC/3M-MinecraftModpackMatrix.git
cd 3M-MinecraftModpackMatrix
```

#### 2️⃣ Configure Environment Variables

Create a .env file in the project root:

```
CF_API_KEY=your_curseforge_api_key_here
```

> You need to get the Cusrforge API from their [Studio](https://console.curseforge.com/) > API keys.<br>
> If you skip the API key, Modrinth mods will still analyze fine.

#### 3️⃣ Install Dependencies

```bash
python -m venv venv
source venv/bin/activate   # (Windows: venv\Scripts\activate)
pip install -r requirements.txt
```

Then visit 👉 http://localhost:5000

---

#### 🖱️ Usage Guide

1. Paste your Modrinth or CurseForge URLs (one per line).
2. Click Analyze to fetch mod info.
3. The table will show each mod’s:
   - Source icon ![Modrinth logo](https://github.com/Lord-ZuzurNC/3M-MinecraftModpackMatrix/blob/main/static/mr.svg) Modrinth / ![Curseforge logo](https://github.com/Lord-ZuzurNC/3M-MinecraftModpackMatrix/blob/main/static/cf.svg) CurseForge
   - Clickable mod name
   - Toggleable version/loader list
4. Filter results using the dropdowns at the top.
5. Click Export MD or Export CSV to save the data.

💡 If you notice incomplete data or errors, click Clear Cache to refresh.

---

#### 📷 Screenshot

![Screenshot of the app](https://github.com/Lord-ZuzurNC/3M-MinecraftModpackMatrix/blob/main/docs/screenshot_themes.png)

---

#### 🧾 Example Use Case

You’re building a modpack for Minecraft 1.20.1 and want to make sure all mods support NeoForge.<br>
Just paste their URLs, click Analyze, and Minecraft Mod Matrix will instantly show which ones align — no manual checking needed.

---

#### ⚙️ Tech Stack

- Backend: Flask + Flask-CORS
- Frontend: Vanilla JS, HTML5, CSS3
- Cache: Local JSON files (auto-refreshed every 24h)
- Supported Providers: CurseForge, Modrinth

---

#### 🧹 Troubleshooting

| Problem             | Solution                                                    |
| ------------------- | ----------------------------------------------------------- |
| ❌ Missing mod info | Click Clear Cache, then Analyze again                       |
| 🌗 Theme resets     | Browser must allow local storage                            |
| 🧩 Invalid URLs     | Only official CurseForge / Modrinth mod pages are supported |

---

#### ❤️ Contributing (WIP)

Pull requests are welcome!<br>
Whether it’s new providers, UI polish, or better filtering logic — open an issue or PR to help improve Minecraft Mod Matrix.

---

#### 📜 License

Released under the [MIT License](https://github.com/Lord-ZuzurNC/3M-MinecraftModpackMatrix/blob/main/LICENSE)<br>
© 2025 – Lord_ZuzurNC
