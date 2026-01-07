# Contributing to Whaaaam

First off, thank you for considering contributing to Whaaaam! It's people like you that make this tool better for everyone in the Minecraft modding community.

## Code of Conduct

This project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## How Can I Contribute?

### Reporting Bugs

Before creating a bug report, please check existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Describe the behavior you observed and what you expected**
- **Include your Python version and operating system**
- **If applicable, include the mod URLs you were analyzing**

Use our [bug report template](https://github.com/Lord-ZuzurNC/Whaaaam/issues/new?template=bug_report.yml) to get started.

### Suggesting Features

Feature requests are welcome! Please use our [feature request template](https://github.com/Lord-ZuzurNC/Whaaaam/issues/new?template=feature_request.yml) and include:

- **A clear description of the feature**
- **Why this feature would be useful**
- **Any implementation ideas you might have**

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Make your changes** following the coding style below
3. **Test your changes** thoroughly
4. **Commit with clear messages** (see commit guidelines below)
5. **Push to your fork** and submit a pull request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/Whaaaam.git
cd Whaaaam

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the web interface
python web.py

# Or run the CLI
python main.py
```

## Coding Style

### Python

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and reasonably sized

### JavaScript

- Use `const` and `let` instead of `var`
- Use meaningful function and variable names
- Keep functions focused and reasonably sized

### HTML/CSS

- Use semantic HTML elements
- Keep CSS organized and consistent with existing styles
- Test in both light and dark modes

## Commit Guidelines

- Use clear, descriptive commit messages
- Start with a verb in present tense (e.g., "Add", "Fix", "Update")
- Keep the first line under 72 characters
- Reference issues when relevant (e.g., "Fix #123")

**Examples:**
```
Add support for modpacks in CurseForge
Fix version parsing for NeoForge mods
Update README with new installation steps
```

## Project Structure

```
Whaaaam/
├── main.py              # CLI entry point
├── web.py               # Flask web server
├── providers/           # Mod platform providers
│   ├── __init__.py
│   ├── curseforge.py    # CurseForge API integration
│   └── modrinth.py      # Modrinth API integration
├── static/              # Static assets (JS, CSS, images)
│   └── app.js           # Frontend JavaScript
├── templates/           # HTML templates
│   └── index.html       # Main web page
└── cache/               # Local cache (auto-generated)
```

## Adding a New Provider

Want to add support for another mod platform? Here's how:

1. Create a new file in `providers/` (e.g., `providers/newplatform.py`)
2. Implement a function that takes a URL and returns mod data in this format:
   ```python
   {
       "name": "Mod Name",
       "provider": "newplatform",
       "id": "unique-id",
       "slug": "mod-slug",
       "versions": [
           ["1.20.1", "Fabric"],
           ["1.19.4", "Forge"],
       ],
       "url": "https://..."
   }
   ```
3. Register your provider in `providers/__init__.py`
4. Update the URL validation in `web.py` if needed
5. Submit a pull request!

## Questions?

Feel free to open an issue for any questions about contributing. We're happy to help!

---

Thank you for contributing!
