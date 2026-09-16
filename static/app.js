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
  }).then((res) => {
    if (!res.ok) throw new Error(httpProblem(res.status));
    return res.json();
  });
}

// A status code is a cause, not a message. Name what it means for the user.
function httpProblem(status) {
  if (status === 429) return "CurseForge or Modrinth is rate-limiting this check.";
  if (status === 404) return "That address is not available on this server.";
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
function computeCompatibility(mods, uncheckedCount) {
  const total = mods.length + uncheckedCount;
  if (!total) return { type: "bad", text: "No mods to check" };
  if (!mods.length) {
    return {
      type: "bad",
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
        text: `All your mods are compatible with ${results.join(" & ")}`,
      };
    }
    return {
      type: "warning",
      text: `${mods.length} of your ${total} mods share: ${results.join(
        " & "
      )} — ${uncheckedCount} could not be checked`,
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
    return { type: "bad", text: "No version information for these mods" };

  const [topKey, topCount] = sorted[0];
  const [version, loader] = topKey.split("|");
  if (topCount / total >= 0.5) {
    return {
      type: "warning",
      text: `Most of your mods share: ${loader} ${version} (${topCount}/${total})`,
    };
  }
  return {
    type: "bad",
    text: `No version works for all your mods. The closest is ${loader} ${version} (${topCount}/${total}).`,
  };
}

// ---- Verdict banner ----
function renderCompatibilityBanner(container, compatibility) {
  const div = document.createElement("div");
  div.className = `compatibility-summary ${compatibility.type}`;
  div.textContent = compatibility.text;
  container.appendChild(div);
}

// ---- Loading overlay ----
const loadingOverlay = document.getElementById("loading-overlay");
const cancelBtn = document.getElementById("cancel-check");
const resultsEl = document.getElementById("results");
const analyzeBtn = document.getElementById("analyze-btn");
let loadingInterval;

function showLoading(count) {
  loadingOverlay.hidden = false;
  analyzeBtn.disabled = true;
  // The only reachable control while the scrim is up, so focus belongs on it.
  cancelBtn.focus();
  announce(`Checking ${count} ${count === 1 ? "mod" : "mods"}…`);

  const loadingText = loadingOverlay.querySelector(".loading-text");
  let dots = 0;
  loadingInterval = setInterval(() => {
    dots = (dots + 1) % 4;
    loadingText.textContent = "Checking mods" + ".".repeat(dots);
  }, 500);
}

function hideLoading() {
  loadingOverlay.hidden = true;
  analyzeBtn.disabled = false;
  analyzeBtn.focus();
  clearInterval(loadingInterval);
  loadingInterval = null;
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

// ---- Rendering ----
function renderTable(results) {
  resultsEl.replaceChildren();

  const versionSelect = document.getElementById("filter-version");
  const loaderSelect = document.getElementById("filter-loader");
  const selectedVersion = versionSelect.value;
  const selectedLoader = loaderSelect.value;

  const checked = results.filter(wasChecked);
  const unchecked = results.filter((mod) => !wasChecked(mod));

  // The verdict answers for the whole submitted list, so it is computed before
  // any filtering. Filters narrow the table below it, never the answer above it.
  const verdict = computeCompatibility(checked, unchecked.length);
  renderCompatibilityBanner(resultsEl, verdict);

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

  const rows = checked
    .map((mod) => ({
      ...mod,
      versions: mod.versions.filter(
        ([v, l]) =>
          (!selectedVersion || v === selectedVersion) &&
          (!selectedLoader || normalizeLoader(l) === selectedLoader)
      ),
    }))
    .filter((mod) => mod.versions.length > 0);

  const isFiltered = Boolean(selectedVersion || selectedLoader);
  if (isFiltered && rows.length !== checked.length) {
    const caption = document.createElement("p");
    caption.className = "filter-note";
    caption.textContent = `Showing ${rows.length} of ${checked.length} checked mods.`;
    resultsEl.appendChild(caption);
  }

  if (!rows.length && !unchecked.length) {
    const empty = document.createElement("p");
    empty.className = "table-empty";
    empty.textContent = isFiltered
      ? 'No mods match this filter. Set it back to "All" to see every mod.'
      : "No mods to show.";
    resultsEl.appendChild(empty);
    return { verdict, shown: 0, checked: checked.length };
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

    // <details> carries its own expanded state, keyboard handling and
    // aria-expanded, so none of that is reimplemented here.
    const versionsCell = document.createElement("td");
    const details = document.createElement("details");
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
    const mark = document.createElement("span");
    mark.setAttribute("aria-hidden", "true");
    mark.textContent = "—";
    const spoken = document.createElement("span");
    spoken.className = "visually-hidden";
    spoken.textContent = "Could not be checked";
    providerCell.append(mark, spoken);

    const nameCell = document.createElement("td");
    nameCell.className = "col-name";
    nameCell.textContent = mod.name || mod.url || "Unknown mod";

    const reasonCell = document.createElement("td");
    reasonCell.className = "cell-reason";
    reasonCell.textContent = mod.error || "No versions listed for this mod";

    row.append(providerCell, nameCell, reasonCell);
    tbody.appendChild(row);
  });

  table.appendChild(tbody);
  scroller.appendChild(table);
  resultsEl.appendChild(scroller);

  return { verdict, shown: rows.length, checked: checked.length };
}

// ---- Main ----
let lastResults = [];
let inFlight = null;

const CHECK_TIMEOUT_MS = 60000;

function cancelCheck() {
  if (inFlight) inFlight.abort();
}

cancelBtn.onclick = cancelCheck;

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !loadingOverlay.hidden) {
    event.preventDefault();
    cancelCheck();
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
  try {
    const results = await postJSON("/analyze", { urls }, controller.signal);
    if (results && results.error) throw new Error(results.error);
    lastResults = dedupeMods(Array.isArray(results) ? results : []);
    const { verdict } = renderTable(lastResults);
    announce(verdict.text);
  } catch (err) {
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
    hideLoading();
  }
};

document.getElementById("clear-cache").onclick = async (e) => {
  const btn = e.currentTarget;
  btn.disabled = true;
  try {
    await fetch("/clear_cache", { method: "POST" });
    setStatus("Cache cleared. The next check fetches every mod again.", "ok");
  } catch (err) {
    setStatus(`Could not clear the cache. ${requestProblem(err)}`, "error");
  } finally {
    btn.disabled = false;
  }
};

function applyFilters() {
  const { shown, checked } = renderTable(lastResults);
  announce(`Showing ${shown} of ${checked} checked mods.`);
}

document.getElementById("filter-version").onchange = applyFilters;
document.getElementById("filter-loader").onchange = applyFilters;

document.getElementById("export-md").onclick = () => exportMD(lastResults);
document.getElementById("export-csv").onclick = () => exportCSV(lastResults);

// ---- Export helpers ----
function download(text, type, extension) {
  const blob = new Blob([text], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `mods-${Date.now()}.${extension}`;
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
