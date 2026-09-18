// The rendered theme is whatever [data-theme] says. Nothing else tracks it.
function isDarkTheme() {
  return document.documentElement.getAttribute("data-theme") !== "latte";
}

// ---- Theme Management Module ----
const ThemeManager = (() => {
  const VALID_THEMES = ["latte", "frappe", "macchiato", "mocha"];
  const DEFAULT_THEME = "mocha";
  const STORAGE_KEY = "theme";

  let currentThemeIndex = 0;
  let themeSwitcher = null;
  let themeOptions = null;
  let themeIndicator = null;

  // Check if localStorage is available
  function isLocalStorageAvailable() {
    try {
      const test = "__localStorage_test__";
      localStorage.setItem(test, test);
      localStorage.removeItem(test);
      return true;
    } catch (e) {
      return false;
    }
  }

  // Validate theme name
  function isValidTheme(themeName) {
    return VALID_THEMES.includes(themeName);
  }

  // Get theme from URL parameter
  function getThemeFromURL() {
    const params = new URLSearchParams(window.location.search);
    const urlTheme = params.get("theme");
    return isValidTheme(urlTheme) ? urlTheme : null;
  }

  // Update URL parameter without page reload
  function updateURLParameter(themeName) {
    const url = new URL(window.location);
    url.searchParams.set("theme", themeName);
    window.history.replaceState({}, "", url);
  }

  // Get current theme from URL > localStorage > default
  function getTheme() {
    // URL parameter takes precedence
    const urlTheme = getThemeFromURL();
    if (urlTheme) {
      return urlTheme;
    }

    // Fall back to localStorage
    if (!isLocalStorageAvailable()) {
      return DEFAULT_THEME;
    }
    const saved = localStorage.getItem(STORAGE_KEY);
    return isValidTheme(saved) ? saved : DEFAULT_THEME;
  }

  // Set theme and update UI
  function setTheme(themeName) {
    // Validate theme name
    if (!isValidTheme(themeName)) {
      console.warn(`Invalid theme "${themeName}". Falling back to "${DEFAULT_THEME}".`);
      themeName = DEFAULT_THEME;
    }

    // Update DOM
    document.documentElement.setAttribute("data-theme", themeName);

    // Persist to localStorage if available
    if (isLocalStorageAvailable()) {
      localStorage.setItem(STORAGE_KEY, themeName);
    }

    // Update URL parameter without page reload
    updateURLParameter(themeName);

    // Update UI elements if initialized
    if (themeOptions && themeIndicator) {
      updateUIState(themeName);
    }

    // Update dynamic elements
    updateThemedImages();
  }

  // Update UI state (active states and indicator position)
  function updateUIState(themeName) {
    themeOptions.forEach((option, index) => {
      const isActive = option.dataset.theme === themeName;
      option.setAttribute("aria-checked", isActive);
      // Roving tabindex: only the checked radio is tabbable, which is what lets
      // the focus ring land on a swatch instead of on the group.
      option.tabIndex = isActive ? 0 : -1;
      if (isActive) {
        currentThemeIndex = index;
      }
    });
    updateIndicatorPosition();
  }

  // Move the sliding indicator
  function updateIndicatorPosition() {
    if (!themeSwitcher || !themeIndicator || !themeOptions[currentThemeIndex]) {
      return;
    }
    const activeOption = themeOptions[currentThemeIndex];
    const containerRect = themeSwitcher.getBoundingClientRect();
    const optionRect = activeOption.getBoundingClientRect();
    const offsetX = optionRect.left - containerRect.left;
    themeIndicator.style.transform = `translateX(${offsetX}px)`;
  }

  // Swap the marks that ship as two files. Done here rather than with the CSS
  // `content:` trick, which Firefox does not apply to <img>.
  function updateThemedImages() {
    const dark = isDarkTheme();
    document.querySelectorAll(".provider-logo").forEach((img) => {
      if (img.alt === "CurseForge") {
        img.src = dark ? "/static/cf_dark.svg" : "/static/cf.svg";
      } else if (img.alt === "Modrinth") {
        img.src = dark ? "/static/mr_dark.svg" : "/static/mr.svg";
      }
    });
    document.querySelectorAll(".github-icon").forEach((img) => {
      img.src = dark ? "/static/github_dark.svg" : "/static/github.svg";
    });
  }

  // Initialize theme system and event listeners
  function initTheme() {
    // Get DOM elements
    themeSwitcher = document.querySelector(".theme-switcher");
    themeOptions = document.querySelectorAll(".theme-option");
    themeIndicator = document.querySelector(".theme-indicator");

    // Apply saved or default theme
    const savedTheme = getTheme();
    setTheme(savedTheme);

    // Setup event listeners only if elements exist
    if (!themeSwitcher || !themeOptions.length || !themeIndicator) {
      console.warn("Theme switcher elements not found. Theme switching disabled.");
      return;
    }

    // Click handlers
    themeOptions.forEach((option) => {
      option.addEventListener("click", () => {
        const theme = option.dataset.theme;
        if (theme) {
          setTheme(theme);
        }
      });
    });

    // Keyboard navigation
    themeSwitcher.addEventListener("keydown", (e) => {
      let next = null;
      if (e.key === "ArrowRight" || e.key === "ArrowDown") {
        next = (currentThemeIndex + 1) % VALID_THEMES.length;
      } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
        next = (currentThemeIndex - 1 + VALID_THEMES.length) % VALID_THEMES.length;
      } else if (e.key === "Home") {
        next = 0;
      } else if (e.key === "End") {
        next = VALID_THEMES.length - 1;
      }
      if (next === null) return;
      e.preventDefault();
      currentThemeIndex = next;
      setTheme(VALID_THEMES[currentThemeIndex]);
      themeOptions[currentThemeIndex].focus();
    });

    // Update indicator on window resize. Coalesced into one frame so a drag
    // resize does not read layout on every event.
    let resizeFrame = null;
    window.addEventListener("resize", () => {
      if (resizeFrame) return;
      resizeFrame = requestAnimationFrame(() => {
        resizeFrame = null;
        updateIndicatorPosition();
      });
    });
  }

  // Public API
  return {
    setTheme,
    getTheme,
    initTheme,
  };
})();

// Initialize theme on DOM load
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", ThemeManager.initTheme);
} else {
  // DOM already loaded
  ThemeManager.initTheme();
}

// ---- Helpers ----
function normalizeLoader(l) {
  if (!l) return l;
  l = l.toLowerCase();
  if (l.includes("neo")) return "NeoForge";
  if (l.includes("forge")) return "Forge";
  if (l.includes("fabric")) return "Fabric";
  if (l.includes("quilt")) return "Quilt";
  return l.charAt(0).toUpperCase() + l.slice(1);
}

function postJSON(url, data, signal) {
  return fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
    signal,
  }).then(async (res) => {
    // The body carries the reason for a refusal; fall back to the status only
    // when it does not (Werkzeug's own 413 page, for one).
    const parsed = await res.json().catch(() => null);
    if (!res.ok) throw new Error((parsed && parsed.error) || httpProblem(res.status));
    return parsed;
  });
}

// A status code is a cause, not a message. Name what it means for the user.
function httpProblem(status) {
  // A 429 on /analyze is this server's own per-connection limit (deploy/
  // nginx.conf). An upstream limit never surfaces here: it arrives as a
  // per-mod row, "CurseForge is rate-limiting requests".
  if (status === 429) return "Too many checks from your connection. Wait a moment, then check again.";
  if (status === 404) return "That address is not available on this server.";
  if (status === 413) return "That list is too long to check in one go.";
  if (status >= 500) return "The server ran into a problem.";
  return `The server refused the request (${status}).`;
}

// Browser network errors arrive unpunctuated ("Failed to fetch"), which makes a
// mess of any sentence built around them.
function requestProblem(err) {
  if (typeof navigator !== "undefined" && navigator.onLine === false) {
    return "You appear to be offline.";
  }
  const message = err && err.message ? String(err.message).trim() : "";
  if (!message) return "The request did not complete.";
  return /[.!?]$/.test(message) ? message : `${message}.`;
}

// ---- Status line (validation + request failures) ----
const statusEl = document.getElementById("form-status");
const announceEl = document.getElementById("sr-announce");

// The only thing that speaks. Callers send one finished sentence; nothing here
// is on a timer, so nothing interrupts itself.
function announce(message) {
  announceEl.textContent = message;
}

function setStatus(message, tone) {
  statusEl.textContent = message || "";
  statusEl.hidden = !message;
  statusEl.dataset.tone = tone || "";
}

// ---- Compatibility ----
// `mods` are the ones we successfully fetched versions for; `uncheckedCount` is
// how many were submitted but could not be resolved. Mods we could not check are
// never dropped from the denominator — an unchecked mod is an unanswered question,
// not a compatible one.
// Mirror of compat.py. Change one, change the other, and run test_compat.py,
// which executes THIS function against the same cases as the Python.
function computeCompatibility(mods, uncheckedCount, timedOut = 0) {
  // Declared inside the function on purpose: test_compat.py extracts this
  // function by brace-matching, so anything it depends on must live within it.
  const CACHE_REMEDY =
    "Everything fetched is cached, so checking again will be quick.";
  // Declared inside for the same reason as CACHE_REMEDY: test_compat.py extracts
  // this function by brace-matching and nothing outside it comes along.
  const outstanding = () =>
    timedOut === uncheckedCount
      ? `the check ran out of time before ${timedOut} could be fetched`
      : `${uncheckedCount} could not be checked, ${timedOut} of them because the check ran out of time`;
  const total = mods.length + uncheckedCount;
  if (!total) return { type: "bad", headline: "", keys: [], text: "No mods to check" };
  if (!mods.length) {
    // A run that ran out of time is an incomplete answer, never a negative one.
    if (timedOut) {
      return {
        type: "warning",
        headline: "",
        keys: [],
        text: `None of your ${total} mods were fetched — ${outstanding()}. ${CACHE_REMEDY}`,
      };
    }
    return {
      type: "bad",
      headline: "",
      keys: [],
      text: `None of your ${total} mods could be checked — see the reasons below`,
    };
  }

  const perModSets = mods.map(
    (m) =>
      new Set((m.versions || []).map(([v, l]) => `${v}|${normalizeLoader(l)}`))
  );

  const intersection = [...perModSets[0]].filter((x) =>
    perModSets.every((s) => s.has(x))
  );

  if (intersection.length > 0) {
    const byLoader = {};
    intersection.forEach((k) => {
      const [v, l] = k.split("|");
      if (!byLoader[l]) byLoader[l] = new Set();
      byLoader[l].add(v);
    });
    // Sorted so the sentence is stable regardless of provider ordering.
    const results = Object.entries(byLoader)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([loader, versions]) => {
      const best = [...versions].sort((a, b) =>
        b.localeCompare(a, undefined, { numeric: true })
      )[0];
      return `${loader} ${best}`;
    });

    if (!uncheckedCount) {
      return {
        type: "good",
        headline: results.join(" & "),
        keys: intersection,
        text: `All your mods are compatible with ${results.join(" & ")}`,
      };
    }
    if (timedOut) {
      return {
        type: "warning",
        headline: results.join(" & "),
        keys: intersection,
        text: `${mods.length} of your ${total} mods share: ${results.join(
          " & "
        )} — ${outstanding()}. ${CACHE_REMEDY}`,
      };
    }
    return {
      type: "warning",
      headline: results.join(" & "),
      keys: intersection,
      text: `${mods.length} of your ${total} mods share: ${results.join(
        " & "
      )} — ${uncheckedCount} could not be checked`,
    };
  }

  // Before naming a "closest" match: if the run was cut short, the absence of a
  // consensus is not evidence of one.
  if (timedOut) {
    return {
      type: "warning",
      headline: "",
      keys: [],
      text: `Only ${mods.length} of your ${total} mods were fetched — ${outstanding()}. This is not a full answer yet. ${CACHE_REMEDY}`,
    };
  }

  // Partial agreement: report the largest consensus and its size.
  const countMap = {};
  perModSets.forEach((s) => {
    s.forEach((k) => {
      countMap[k] = (countMap[k] || 0) + 1;
    });
  });
  const sorted = Object.entries(countMap).sort((a, b) => b[1] - a[1]);
  if (!sorted.length)
    return { type: "bad", headline: "", keys: [], text: "No version information for these mods" };

  const [topKey, topCount] = sorted[0];
  const [version, loader] = topKey.split("|");
  if (topCount / total >= 0.5) {
    return {
      type: "warning",
      headline: `${loader} ${version}`,
      keys: [topKey],
      text: `Most of your mods share: ${loader} ${version} (${topCount}/${total})`,
    };
  }
  return {
    type: "bad",
    headline: `${loader} ${version}`,
    keys: [topKey],
    text: `No version works for all your mods. The closest is ${loader} ${version} (${topCount}/${total}).`,
  };
}

// ---- Verdict banner ----
function renderCompatibilityBanner(container, compatibility) {
  const div = document.createElement("div");
  div.className = `compatibility-summary ${compatibility.type}`;
  // Focusable so a finished check can send focus here: that scrolls the answer
  // into view and reads it out in one move, with no live region to duplicate it.
  div.tabIndex = -1;

  // The version+loader is set at display scale inside the sentence rather than
  // repeated above it, so the wording PRODUCT.md records stays exactly as shipped.
  // Built from text nodes — never innerHTML; these strings come from provider APIs.
  const figure = compatibility.headline;
  const at = figure ? compatibility.text.indexOf(figure) : -1;
  if (at === -1) {
    div.textContent = compatibility.text;
  } else {
    const strong = document.createElement("strong");
    strong.className = "verdict-figure";
    strong.textContent = figure;
    div.append(
      document.createTextNode(compatibility.text.slice(0, at)),
      strong,
      document.createTextNode(compatibility.text.slice(at + figure.length))
    );
  }
  container.appendChild(div);
  return div;
}

// ---- Loading overlay ----
const loadingOverlay = document.getElementById("loading-overlay");
const cancelBtn = document.getElementById("cancel-check");
const resultsEl = document.getElementById("results");
const filterBlock = document.getElementById("filter-block");
const outsideToggle = document.getElementById("filter-outside");
const outsideField = document.getElementById("outside-field");
const outsideLabel = document.querySelector('label[for="filter-outside"]');

// How many URLs the user actually submitted, so a silent dedupe can be explained.
let submittedCount = 0;
const analyzeBtn = document.getElementById("analyze-btn");
let loadingInterval;

let heartbeat = null;

function showLoading(count) {
  // showModal() supplies the focus trap, the Escape handling and the top layer
  // that a hand-rolled scrim never had: Tab used to walk into the footer links
  // behind an opaque overlay, and filters stayed operable against stale results.
  loadingOverlay.showModal();
  analyzeBtn.disabled = true;
  const noun = count === 1 ? "mod" : "mods";
  announce(`Checking ${count} ${noun}…`);

  // How many is the one reassuring fact during the wait, so it is on screen and
  // not only in the live region.
  const loadingText = loadingOverlay.querySelector(".loading-text");
  const base = `Checking ${count} ${noun}`;
  loadingText.textContent = base;
  let dots = 0;
  loadingInterval = setInterval(() => {
    dots = (dots + 1) % 4;
    loadingText.textContent = base + ".".repeat(dots);
  }, 500);

  // The dots are aria-hidden because their text is on a timer, which left a
  // screen reader with silence for the whole check. One heartbeat, not a stream.
  heartbeat = setInterval(() => announce(`Still checking your ${noun}…`), 20000);
}

function hideLoading(focusTarget) {
  if (loadingOverlay.open) loadingOverlay.close();
  analyzeBtn.disabled = false;
  // The answer earns focus, not the button that asked for it: focusing the
  // verdict scrolls it into view and reads it out, which is what a user who
  // just waited actually wants. Falls back to the button when there is no answer.
  (focusTarget || analyzeBtn).focus();
  clearInterval(loadingInterval);
  clearInterval(heartbeat);
  loadingInterval = null;
  heartbeat = null;
}

// Deduplicate mods by provider + slug. Failed lookups have neither, so they key
// on their URL — otherwise every failure would collapse into a single row.
function dedupeMods(results) {
  const seen = new Set();
  const deduped = [];
  results.forEach((mod) => {
    const key =
      mod.provider && (mod.slug || mod.id)
        ? `${mod.provider}|${mod.slug || mod.id}`
        : `url|${mod.url}`;
    if (!seen.has(key)) {
      seen.add(key);
      deduped.push(mod);
    }
  });
  return deduped;
}

function fillSelect(select, values, selected) {
  select.replaceChildren(new Option("All", ""));
  values.forEach((v) => select.add(new Option(v, v, false, v === selected)));
}

function wasChecked(mod) {
  return Array.isArray(mod.versions) && mod.versions.length > 0;
}

// The mark on a row that could not be checked: a drawn alert, in the row's
// status colour via currentColor. Decorative — the visually-hidden sentence
// beside it is what a screen reader hears.
function uncheckedMark() {
  const NS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("class", "unchecked-mark");
  svg.setAttribute("viewBox", "0 0 20 20");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  const shapes = [
    ["circle", { cx: 10, cy: 10, r: 8.25, fill: "none", stroke: "currentColor", "stroke-width": 1.75 }],
    ["line", { x1: 10, y1: 5.75, x2: 10, y2: 11, stroke: "currentColor", "stroke-width": 2, "stroke-linecap": "round" }],
    ["circle", { cx: 10, cy: 14.25, r: 1.15, fill: "currentColor" }],
  ];
  shapes.forEach(([tag, attrs]) => {
    const el = document.createElementNS(NS, tag);
    Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
    svg.appendChild(el);
  });
  return svg;
}

// A URL with a line-break opportunity after each "/" and ".", built from text
// nodes and <wbr> — the string is user input and never goes through innerHTML.
// Breaking after "." too keeps the longest piece ("https://") near the width of
// an ordinary word, so the URL cannot widen the column past the versions cell.
function appendBreakableURL(cell, url) {
  url.split(/(?<=[/.])/).forEach((part, i) => {
    if (i) cell.appendChild(document.createElement("wbr"));
    cell.appendChild(document.createTextNode(part));
  });
}

// ---- Rendering ----
function renderTable(results) {
  // renderTable rebuilds the table from scratch, which silently collapsed every
  // open version list on any filter change. Remember what was open first.
  const wasOpen = new Set(
    [...resultsEl.querySelectorAll("details[open]")].map((d) => d.dataset.mod)
  );
  resultsEl.replaceChildren();

  const versionSelect = document.getElementById("filter-version");
  const loaderSelect = document.getElementById("filter-loader");
  const selectedVersion = versionSelect.value;
  const selectedLoader = loaderSelect.value;

  const checked = results.filter(wasChecked);
  const unchecked = results.filter((mod) => !wasChecked(mod));

  // The verdict answers for the whole submitted list, so it is computed before
  // any filtering. Filters narrow the table below it, never the answer above it.
  const timedOut = unchecked.filter((mod) => mod.timed_out).length;
  const verdict = computeCompatibility(checked, unchecked.length, timedOut);
  const banner = renderCompatibilityBanner(resultsEl, verdict);

  // The mods that break the consensus are the answer's fine print, and the
  // product promises they are visible rather than implied. `verdict.keys` is
  // the same intersection the sentence names, so the marks cannot disagree
  // with the verdict above them.
  const consensus = new Set(verdict.keys || []);
  const isOutside = (mod) =>
    consensus.size > 0 &&
    !(mod.versions || []).some(([v, l]) =>
      consensus.has(`${v}|${normalizeLoader(l)}`)
    );
  const outsideMods = checked.filter(isOutside);

  // The toggle only exists when it would do something.
  outsideField.hidden = outsideMods.length === 0;
  if (outsideMods.length === 0) {
    outsideToggle.checked = false;
  } else {
    outsideLabel.textContent = `Only the ${outsideMods.length} outside ${verdict.headline}`;
  }

  // Nothing to filter or export until there is a result. Four dead controls on
  // the first screen are four decisions the user cannot make yet.
  filterBlock.hidden = !results.length;

  // Filter options come from every checked mod, not from the current selection,
  // so narrowing one filter can never strand the other.
  const allVersions = new Set();
  const allLoaders = new Set();
  checked.forEach((mod) =>
    mod.versions.forEach(([v, l]) => {
      allVersions.add(v);
      allLoaders.add(normalizeLoader(l));
    })
  );
  fillSelect(
    versionSelect,
    [...allVersions].sort((a, b) => a.localeCompare(b, undefined, { numeric: true })),
    selectedVersion
  );
  fillSelect(loaderSelect, [...allLoaders].sort(), selectedLoader);

  const pool = outsideToggle.checked ? outsideMods : checked;
  const rows = pool
    .map((mod) => ({
      ...mod,
      outside: isOutside(mod),
      versions: mod.versions.filter(
        ([v, l]) =>
          (!selectedVersion || v === selectedVersion) &&
          (!selectedLoader || normalizeLoader(l) === selectedLoader)
      ),
    }))
    .filter((mod) => mod.versions.length > 0);

  const isFiltered = Boolean(selectedVersion || selectedLoader || outsideToggle.checked);
  const merged = results.length ? Math.max(0, submittedCount - results.length) : 0;
  const notes = [];
  if (isFiltered && rows.length !== checked.length) {
    // "checked mods" is the honest denominator: mods that could not be checked
    // are appended below regardless of the filter, so counting them here made
    // the number above the table disagree with the rows in it.
    notes.push(`Showing ${rows.length} of ${checked.length} checked mods.`);
    if (unchecked.length) {
      notes.push(
        `${unchecked.length} that could not be checked ${
          unchecked.length === 1 ? "is" : "are"
        } always listed.`
      );
    }
  }
  if (merged > 0) {
    // A 60-line paste that renders 57 rows used to explain nothing.
    notes.push(
      `${merged} duplicate ${merged === 1 ? "URL was" : "URLs were"} merged.`
    );
  }
  if (notes.length) {
    const caption = document.createElement("p");
    caption.className = "filter-note";
    caption.textContent = notes.join(" ");
    resultsEl.appendChild(caption);
  }

  if (!rows.length && !unchecked.length) {
    const empty = document.createElement("p");
    empty.className = "table-empty";
    empty.textContent = isFiltered
      ? 'No mods match this filter. Set it back to "All" to see every mod.'
      : "No mods to show.";
    resultsEl.appendChild(empty);
    return { verdict, banner, shown: 0, checked: checked.length };
  }

  const scroller = document.createElement("div");
  scroller.className = "table-scroll";
  scroller.tabIndex = 0;
  scroller.setAttribute("role", "region");
  scroller.setAttribute("aria-label", "Mod compatibility results");

  const table = document.createElement("table");
  const thead = document.createElement("thead");
  thead.innerHTML =
    '<tr><th scope="col" class="col-source">Source</th>' +
    '<th scope="col" class="col-name">Mod Name</th>' +
    '<th scope="col">Versions / Loaders</th></tr>';
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  const isDark = isDarkTheme();

  rows.forEach((mod) => {
    const row = document.createElement("tr");

    const providerCell = document.createElement("td");
    providerCell.className = "col-source";
    if (mod.provider === "curseforge" || mod.provider === "modrinth") {
      const img = document.createElement("img");
      img.className = "provider-logo";
      img.width = 20;
      img.height = 20;
      const cf = mod.provider === "curseforge";
      img.src = `/static/${cf ? "cf" : "mr"}${isDark ? "_dark" : ""}.svg`;
      img.alt = cf ? "CurseForge" : "Modrinth";
      providerCell.appendChild(img);
    } else {
      providerCell.textContent = "?";
    }

    const nameCell = document.createElement("td");
    nameCell.className = "col-name";
    if (mod.url) {
      const a = document.createElement("a");
      a.href = mod.url;
      a.textContent = mod.name || "Unknown";
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      nameCell.appendChild(a);
    } else {
      nameCell.textContent = mod.name || "Unknown";
    }
    if (mod.outside) {
      const note = document.createElement("span");
      note.className = "outside-note";
      // Words first, colour second — and it names what is missing, not just that
      // something is.
      note.textContent = `Not on ${verdict.headline}`;
      nameCell.appendChild(note);
    }

    // <details> carries its own expanded state, keyboard handling and
    // aria-expanded, so none of that is reimplemented here.
    const versionsCell = document.createElement("td");
    const details = document.createElement("details");
    details.dataset.mod = `${mod.provider || "?"}|${mod.slug || mod.id || mod.url}`;
    details.open = wasOpen.has(details.dataset.mod);
    const summary = document.createElement("summary");
    const list = document.createElement("ul");
    list.className = "version-list";

    const seen = new Set();
    mod.versions.forEach(([v, l]) => {
      const loader = normalizeLoader(l);
      const key = `${v}-${loader}`;
      if (seen.has(key)) return;
      seen.add(key);
      const li = document.createElement("li");
      li.textContent = `${v} → ${loader}`;
      list.appendChild(li);
    });

    const count = seen.size;
    summary.textContent = `${count} ${count === 1 ? "version" : "versions"}`;
    details.append(summary, list);
    versionsCell.appendChild(details);

    row.append(providerCell, nameCell, versionsCell);
    tbody.appendChild(row);
  });

  // Mods we could not resolve stay in the table, named and explained.
  unchecked.forEach((mod) => {
    const row = document.createElement("tr");
    row.className = "row-unchecked";

    const providerCell = document.createElement("td");
    providerCell.className = "col-source";
    const spoken = document.createElement("span");
    spoken.className = "visually-hidden";
    spoken.textContent = "Could not be checked";
    providerCell.append(uncheckedMark(), spoken);

    const nameCell = document.createElement("td");
    nameCell.className = "col-name";
    if (mod.name) {
      nameCell.textContent = mod.name;
    } else if (mod.url) {
      nameCell.classList.add("cell-url");
      appendBreakableURL(nameCell, mod.url);
    } else {
      nameCell.textContent = "Unknown mod";
    }

    const reasonCell = document.createElement("td");
    reasonCell.className = "cell-reason";
    reasonCell.textContent = mod.error || "No versions listed for this mod";

    row.append(providerCell, nameCell, reasonCell);
    tbody.appendChild(row);
  });

  table.appendChild(tbody);
  scroller.appendChild(table);
  resultsEl.appendChild(scroller);

  return { verdict, banner, shown: rows.length, checked: checked.length };
}

// ---- Main ----
let lastResults = [];
let inFlight = null;

const CHECK_TIMEOUT_MS = 60000;

function cancelCheck() {
  if (inFlight) inFlight.abort();
}

cancelBtn.onclick = cancelCheck;

// Escape fires the dialog's own cancel event. Abort the request rather than
// letting the dialog close out from under an in-flight check; the finally
// branch closes it once the abort lands.
loadingOverlay.addEventListener("cancel", (event) => {
  event.preventDefault();
  cancelCheck();
});

const urlsField = document.getElementById("mod-urls");

// Paste, then submit without leaving the keyboard.
urlsField.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.metaKey || event.ctrlKey) && !analyzeBtn.disabled) {
    event.preventDefault();
    analyzeBtn.click();
  }
});

analyzeBtn.onclick = async () => {
  const urls = document
    .getElementById("mod-urls")
    .value.split("\n")
    .map((u) => u.trim())
    .filter((u) => u);

  if (!urls.length) {
    setStatus("Paste at least one CurseForge or Modrinth URL to check.", "error");
    document.getElementById("mod-urls").focus();
    return;
  }

  setStatus("");
  showLoading(urls.length);
  const controller = new AbortController();
  inFlight = controller;
  // Pass a reason so the two abort paths can be told apart in the message.
  const deadline = setTimeout(() => controller.abort("timeout"), CHECK_TIMEOUT_MS);
  let focusAfter = null;
  try {
    const results = await postJSON("/analyze", { urls }, controller.signal);
    if (results && results.error) throw new Error(results.error);
    submittedCount = urls.length;
    lastResults = dedupeMods(Array.isArray(results) ? results : []);
    // No announce() here: focus moves to the banner, which reads it out once.
    // Doing both spoke every verdict twice.
    focusAfter = renderTable(lastResults).banner;
  } catch (err) {
    // The previous run's verdict, table and exports must not survive a failed
    // re-check: they are the answer to a different question, and the loudest
    // thing on the page would otherwise be stale data presented as current.
    lastResults = [];
    resultsEl.replaceChildren();
    filterBlock.hidden = true;

    if (err && err.name === "AbortError") {
      const message = controller.signal.reason === "timeout"
        ? "Check cancelled — it took longer than a minute. Try a shorter list."
        : "Check cancelled. Nothing was changed.";
      setStatus(message, "error");
      announce(message);
    } else {
      const reason = requestProblem(err);
      setStatus(`Could not check your mods. ${reason} Try again in a moment.`, "error");
      announce(`Could not check your mods. ${reason}`);
    }
  } finally {
    clearTimeout(deadline);
    inFlight = null;
    hideLoading(focusAfter);
  }
};

function applyFilters() {
  const { shown, checked } = renderTable(lastResults);
  announce(`Showing ${shown} of ${checked} checked mods.`);
}

document.getElementById("filter-version").onchange = applyFilters;
document.getElementById("filter-loader").onchange = applyFilters;
outsideToggle.onchange = applyFilters;

document.getElementById("export-md").onclick = () => exportMD(lastResults);
document.getElementById("export-csv").onclick = () => exportCSV(lastResults);

// ---- Export helpers ----
// A readable local timestamp: four exports in a row used to produce four epoch
// filenames that sorted correctly and meant nothing.
function stamp() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}-${pad(
    d.getHours()
  )}${pad(d.getMinutes())}`;
}

function download(text, type, extension) {
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `mods-${stamp()}.${extension}`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

function exportMD(results) {
  if (!results.length) {
    setStatus("Nothing to export yet — check a list of mods first.", "error");
    return;
  }
  let md = "# Whaaaam\n\n";
  results.forEach((mod) => {
    md += `- **${mod.name || mod.url || "Unknown"}** (${mod.provider || "?"})\n`;
    if (wasChecked(mod)) {
      mod.versions.forEach(([v, l]) => {
        md += `  - ${v} → ${normalizeLoader(l)}\n`;
      });
    } else {
      md += `  - Could not be checked: ${mod.error || "no versions returned"}\n`;
    }
  });
  download(md, "text/markdown", "md");
}

function csvCell(value) {
  let v = String(value ?? "");
  // Mod names come from third parties. A leading =, +, - or @ makes the cell a
  // formula when the export is opened in Excel or Sheets.
  if (/^[=+\-@\t\r]/.test(v)) v = "'" + v;
  return `"${v.replace(/"/g, '""')}"`;
}

function exportCSV(results) {
  if (!results.length) {
    setStatus("Nothing to export yet — check a list of mods first.", "error");
    return;
  }
  let csv = "Mod Name,Provider,Version,Loader,URL,Status\n";
  results.forEach((mod) => {
    const name = mod.name || mod.url || "Unknown";
    if (wasChecked(mod)) {
      mod.versions.forEach(([v, l]) => {
        csv +=
          [name, mod.provider || "?", v, normalizeLoader(l), mod.url || "", "ok"]
            .map(csvCell)
            .join(",") + "\n";
      });
    } else {
      csv +=
        [name, mod.provider || "?", "", "", mod.url || "", mod.error || "unchecked"]
          .map(csvCell)
          .join(",") + "\n";
    }
  });
  download(csv, "text/csv", "csv");
}
