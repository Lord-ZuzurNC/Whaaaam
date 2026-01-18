# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Structure

This Lab directory contains multiple projects:
- **Whaaaam/** - Minecraft mod compatibility checker (main project)
- **Docker/** - Docker/infrastructure notes
- **JdR/** - Personal notes/assets

## Whaaaam Project

### Build and Run Commands

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies
npm install

# Build CSS (required before first run)
npm run build:css

# Watch mode for CSS development
npm run watch:css

# Run web interface (recommended)
python web.py
# Opens at http://localhost:5000

# Run CLI interface
python main.py
```

### Environment Variables

- `CF_API_KEY` - **Required** for CurseForge API access. Must be set in environment or `.env` file.

### Architecture

**Entry Points:**
- `web.py` - Flask web server with `/analyze` and `/clear_cache` endpoints
- `main.py` - CLI interface for terminal usage

**Provider System (`providers/`):**
- `__init__.py` - Provider registry, URL detection (`detect_provider`), caching utilities (`cache_path`, `is_cache_expired`)
- `curseforge.py` - CurseForge API integration (requires API key)
- `modrinth.py` - Modrinth API integration (no key needed)

Each provider's `get_mod_data(url)` returns:
```python
{
    "name": str,
    "provider": str,
    "id": str,
    "slug": str,
    "versions": [(mc_version, loader), ...],  # e.g., [("1.20.1", "Fabric")]
    "url": str
}
```

**Frontend (`static/`, `templates/`):**
- `app.js` - Client-side compatibility analysis, filtering, export (MD/CSV), ThemeManager module
- `index.html` - Single-page web UI with theme switcher component
- `styles.css` - Legacy custom CSS (being gradually migrated to Tailwind)
- `css/tailwind.css` - Generated TailwindCSS output (minified, optimized)

**Caching:**
- Located in `cache/` directory (auto-generated)
- 24-hour TTL per mod/version data
- Clear via `/clear_cache` endpoint

### Frontend Build System

**Technology Stack:**
- **TailwindCSS v3** - Utility-first CSS framework with JIT compilation
- **PostCSS** - CSS processing with autoprefixer for browser compatibility
- **npm scripts** - Build automation

**Build Process:**
1. Source CSS: `src/input.css` (contains Tailwind directives: `@tailwind base/components/utilities`)
2. PostCSS processes with TailwindCSS plugin
3. TailwindCSS scans content paths: `templates/**/*.html` and `static/**/*.js`
4. Tree-shaking removes unused CSS classes
5. Output: `static/css/tailwind.css` (minified, ~5-20KB depending on usage)

**Build Commands:**
```bash
npm run build:css    # Production build with minification
npm run watch:css    # Development mode with auto-rebuild
```

**Configuration Files:**
- `package.json` - npm dependencies and build scripts
- `postcss.config.js` - PostCSS plugins (TailwindCSS, autoprefixer)
- `tailwind.config.js` - Tailwind configuration (content paths, theme colors)

### Theme System Architecture

**Overview:**
The theme system provides 4 Catppuccin color themes with smooth transitions, localStorage persistence, and URL sharing support.

**Catppuccin Color Palettes:**

All 4 palettes are defined in `tailwind.config.js`:

1. **Latte** (light theme) - Warm, cozy light colors
2. **Frappé** (dark theme) - Cool dark with subtle purple tones
3. **Macchiato** (dark theme) - Rich, saturated dark colors
4. **Mocha** (dark theme, default) - Deep dark for late-night sessions

Each palette contains 17 colors:
- **Base colors** (5): `base`, `surface`, `overlay`, `text`, `subtext`
- **Accent colors** (12): `rosewater`, `flamingo`, `pink`, `mauve`, `red`, `maroon`, `peach`, `yellow`, `green`, `teal`, `sky`, `sapphire`, `blue`, `lavender`

**Usage in HTML/CSS:**
```html
<!-- Use as Tailwind utilities -->
<div class="bg-mocha-base text-mocha-text">
  <button class="bg-latte-mauve hover:bg-latte-blue">
    Click me
  </button>
</div>
```

**JavaScript ThemeManager API:**

Located in `static/app.js` using IIFE module pattern:

```javascript
// Public API
ThemeManager.setTheme('latte')    // Set theme (updates DOM, localStorage, URL)
ThemeManager.getTheme()           // Get current theme name
ThemeManager.initTheme()          // Initialize theme system (call on page load)

// Private implementation (not accessible)
// - isValidTheme(name)
// - isLocalStorageAvailable()
// - updateUIState(theme)
// - getThemeFromURL()
```

**Theme Priority Cascade:**
1. URL parameter (`?theme=latte`) - highest priority (for sharing)
2. localStorage (`theme` key) - user's saved preference
3. Default value (`mocha`) - fallback if neither is available

**Theme Switching Mechanism:**
- `<html data-theme="mocha">` attribute controls active theme
- Backward compatible `body.dark` class maintained for legacy CSS
- Smooth 0.5s CSS transitions on background and text colors
- URL updates without page reload using `window.history.replaceState()`

**UI Component:**
- Circular theme switcher with 4 indicators
- Sliding pill animation highlighting active theme
- Full ARIA support: `role="radiogroup"`, `role="radio"`, `aria-checked`
- Keyboard navigation with arrow keys
- Hover interactions with scale transform
- Responsive resize handling

### CSS Migration Strategy

**Current Status: Phase 1 Complete, Phase 2 In Progress**

The project uses a **dual-loading pattern** for safe, incremental migration from custom CSS to TailwindCSS:

**Phase 1: Dual Loading** ✅ Complete
- Both stylesheets loaded in `index.html`:
  1. `styles.css` (legacy) - loaded first
  2. `css/tailwind.css` (new) - loaded second (override priority)
- No breaking changes to existing functionality
- New Tailwind classes can progressively replace legacy CSS

**Phase 2: Component-by-Component Migration** 🚧 In Progress
- Legacy CSS marked with `/* LEGACY: ... */` comments
- Components migrated one at a time
- Test thoroughly before moving to next component
- Migration tracking in `.ralph-tui/MIGRATION_CHECKLIST.md`

**Phase 3: Cleanup & Removal** 📋 Planned
- Remove legacy CSS once all components migrated
- Remove dual-loading, keep only Tailwind CSS
- Remove `styles.css` file entirely
- Update build process documentation

**Migration Guidelines:**
- Check for CSS namespace conflicts (`--custom-*` vs `--tw-*`)
- Verify Tailwind Preflight doesn't break existing layouts
- Document rollback strategy before major changes
- Test both light and dark themes after each component migration
- Use git for easy rollback if needed

**Rollback Plan:**
```bash
# Restore legacy CSS if needed
git restore templates/index.html static/styles.css

# Rebuild Tailwind CSS
npm run build:css
```

### UI Development Guidelines

When building or modifying the UI, follow these patterns:

**CSS Framework:**
- Use TailwindCSS utility classes for all new components
- Use `cn` utility (clsx + tailwind-merge) for conditional class logic
- Prefer Tailwind utilities over custom CSS

**Layout:**
- Use `h-dvh` instead of `h-screen` (better mobile support)
- Use `text-balance` for headings
- Use `text-pretty` for body text
- Use `tabular-nums` for numeric data (tables, version numbers)

**Theming:**
- Use Catppuccin color utilities: `bg-mocha-base`, `text-latte-text`, etc.
- Test all 4 themes (Latte, Frappé, Macchiato, Mocha)
- Use smooth transitions for theme changes (0.5s ease)

**Animations:**
- **Never add animation unless explicitly requested**
- Prefer simple transitions over complex animations
- Use `cubic-bezier(0.4, 0, 0.2, 1)` for natural motion

**Visual Style:**
- **Never use gradients** unless explicitly requested
- **Never use glow effects** unless explicitly requested
- **Never use purple colors** unless part of Catppuccin theme
- Keep design clean and functional

**Accessibility:**
- Use semantic HTML (`<button>`, `<nav>`, `<main>`, etc.)
- Add ARIA roles for custom components (`role="radiogroup"`, `role="radio"`)
- Support keyboard navigation (arrow keys, tab, enter)
- Ensure sufficient color contrast in all themes

**JavaScript Patterns:**
- Use IIFE module pattern for encapsulation
- Expose minimal public API via return object
- Validate all user input (URL params, localStorage, form data)
- Feature detection for localStorage (handle private browsing)
- Check `document.readyState` for proper initialization timing

### Adding a New Provider

To add support for a new mod hosting platform:

1. **Create provider file**: `providers/newplatform.py`
   ```python
   def get_mod_data(url: str) -> dict:
       """
       Fetch mod data from new platform.

       Returns:
           {
               "name": str,
               "provider": str,
               "id": str,
               "slug": str,
               "versions": [(mc_version, loader), ...],
               "url": str
           }
       """
       pass
   ```

2. **Register provider**: Add to `providers/__init__.py`
   ```python
   from .newplatform import get_mod_data as get_newplatform_data

   PROVIDERS = {
       # ...existing providers
       "newplatform": get_newplatform_data,
   }
   ```

3. **Update URL detection**: Modify `detect_provider()` in `providers/__init__.py`
   ```python
   def detect_provider(url: str) -> str:
       if "newplatform.com" in url:
           return "newplatform"
       # ...existing checks
   ```

4. **Update validation**: Modify `is_valid_mod_url()` in `web.py`
   ```python
   def is_valid_mod_url(url):
       valid_domains = [
           "curseforge.com",
           "modrinth.com",
           "newplatform.com",  # Add new domain
       ]
   ```

### Code Style and Patterns

**Python:**
- Follow PEP 8 style guide
- Use type hints where helpful
- Keep functions focused and single-purpose
- Handle errors gracefully with try/except

**JavaScript:**
- Use modern ES6+ syntax
- Prefer `const` over `let`, avoid `var`
- Use template literals for string interpolation
- Keep functions pure when possible
- Document public APIs with JSDoc comments

**CSS:**
- Prefer Tailwind utilities over custom CSS
- Use CSS custom properties for theme-specific values
- Group related styles together
- Comment complex or non-obvious styling decisions

### Testing

Before committing changes:

1. **Test both interfaces:**
   - Run `python web.py` and test web UI
   - Run `python main.py` and test CLI

2. **Test all themes:**
   - Switch between all 4 Catppuccin themes
   - Verify colors and transitions
   - Check both light (Latte) and dark themes

3. **Test responsiveness:**
   - Test on different screen sizes
   - Verify mobile layout

4. **Rebuild CSS:**
   ```bash
   npm run build:css
   ```

5. **Clear cache if needed:**
   - Visit `http://localhost:5000/clear_cache`
   - Or delete `cache/` directory

### Deployment Notes

**Production Checklist:**
1. Run `npm run build:css` to generate optimized CSS
2. Ensure `static/css/tailwind.css` is committed
3. Set `CF_API_KEY` environment variable
4. Clear cache before deployment if needed

**Future Deprecations:**
- `styles.css` will be removed once migration to Tailwind is complete
- `body.dark` class will be removed (use `data-theme` attribute only)
- Dual-loading pattern will be replaced with single Tailwind CSS file
