// ---- Theme ----
function applyTheme(theme) {
  document.body.classList.toggle("dark", theme === "dark");
  localStorage.setItem("theme", theme);
}

// Initialize theme
const savedTheme = localStorage.getItem("theme") || "light";
applyTheme(savedTheme);

document.getElementById("theme-toggle").onclick = () => {
  const newTheme = document.body.classList.contains("dark") ? "light" : "dark";
  applyTheme(newTheme);
};

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

function postJSON(url, data) {
  return fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  }).then((res) => res.json());
}

// ---- Filters ----
function applyFilters(results) {
  const version = document.getElementById("filter-version").value;
  const loader = document.getElementById("filter-loader").value;

  return results.map((mod) => {
    if (!mod.versions) return mod;
    const filtered = mod.versions.filter(([v, l]) => {
      const lv = normalizeLoader(l);
      return (!version || v === version) && (!loader || lv === loader);
    });
    return { ...mod, versions: filtered };
  });
}

function populateFilters(results) {
  const versionSelect = document.getElementById("filter-version");
  const loaderSelect = document.getElementById("filter-loader");
  const versions = new Set();
  const loaders = new Set();

  results.forEach((mod) => {
    if (!mod.versions) return;
    mod.versions.forEach(([v, l]) => {
      versions.add(v);
      loaders.add(normalizeLoader(l));
    });
  });

  versionSelect.innerHTML =
    '<option value="">All</option>' +
    [...versions]
      .sort()
      .map((v) => `<option value="${v}">${v}</option>`)
      .join("");

  loaderSelect.innerHTML =
    '<option value="">All</option>' +
    [...loaders]
      .sort()
      .map((l) => `<option value="${l}">${l}</option>`)
      .join("");
}

// ---- Compatibility ----
function computeCompatibility(mods) {
  if (!mods.length) return { type: "bad", text: "No mods provided" };
  const perModSets = mods.map(
    (m) =>
      new Set((m.versions || []).map(([v, l]) => `${v}|${normalizeLoader(l)}`))
  );
  if (!perModSets.length) return { type: "bad", text: "No versions found" };

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
    const results = Object.entries(byLoader).map(([loader, versions]) => {
      const best = [...versions].sort((a, b) =>
        b.localeCompare(a, undefined, { numeric: true })
      )[0];
      return `${loader} ${best}`;
    });
    return {
      type: "good",
      text: `All your mods are compatible with ${results.join(" & ")}`,
    };
  }

  // partial intersection
  const countMap = {};
  perModSets.forEach((s) => {
    s.forEach((k) => {
      countMap[k] = (countMap[k] || 0) + 1;
    });
  });
  const sorted = Object.entries(countMap).sort((a, b) => b[1] - a[1]);
  if (!sorted.length)
    return { type: "bad", text: "No common denominator found" };

  const [topKey, topCount] = sorted[0];
  if (topCount / mods.length >= 0.5) {
    const [loader, version] = topKey.split("|");
    return {
      type: "warning",
      text: `Most of your mods share: ${loader} ${version} (${topCount}/${mods.length})`,
    };
  }
  return { type: "bad", text: "No common denominator found" };
}

// ---- Compatibility banner ----
function renderCompatibilityBanner(container, compatibility) {
  const div = document.createElement("div");
  div.className = "compatibility-summary";
  div.textContent = compatibility.text;

  // Add colored ribbon
  div.classList.remove("good", "warning", "bad");
  div.classList.add(compatibility.type);

  container.appendChild(div);
}

// Example usage inside renderTable:
function renderTable(results) {
  const container = document.getElementById("results");
  container.innerHTML = "";

  const filteredResults = applyFilters(results);

  // Top compatibility
  const compTop = computeCompatibility(filteredResults);
  renderCompatibilityBanner(container, compTop);

  const table = document.createElement("table");
  const header = document.createElement("tr");
  header.innerHTML =
    '<th class="col-source">Source</th><th class="col-name">Mod Name</th><th>Versions / Loaders</th>';
  table.appendChild(header);

  filteredResults.forEach((mod) => {
    const row = document.createElement("tr");

    // Source
    const providerCell = document.createElement("td");
    providerCell.className = "col-source";
    if (mod.provider === "curseforge") {
      const img = document.createElement("img");
      img.src = "/static/cf.svg";
      img.alt = "CurseForge";
      img.title = "CurseForge";
      img.className = "provider-logo";
      providerCell.appendChild(img);
    } else if (mod.provider === "modrinth") {
      const img = document.createElement("img");
      img.src = "/static/mr.svg";
      img.alt = "Modrinth";
      img.title = "Modrinth";
      img.className = "provider-logo";
      providerCell.appendChild(img);
    } else {
      providerCell.textContent = "?";
    }

    // Mod name
    const nameCell = document.createElement("td");
    nameCell.className = "col-name";
    if (mod.url) {
      const a = document.createElement("a");
      a.href = mod.url;
      a.textContent = mod.name || "Unknown";
      a.target = "_blank";
      nameCell.appendChild(a);
    } else {
      nameCell.textContent = mod.name || "Unknown";
    }

    // Versions / Loaders
    const versionsCell = document.createElement("td");
    if (mod.error) {
      versionsCell.textContent = mod.error;
    } else {
      const toggleBtn = document.createElement("button");
      toggleBtn.textContent = "Show/Hide";
      const list = document.createElement("ul");
      list.style.display = "none";
      const seen = new Set();
      (mod.versions || []).forEach(([v, l]) => {
        const key = `${v}-${normalizeLoader(l)}`;
        if (seen.has(key)) return;
        seen.add(key);
        const li = document.createElement("li");
        li.textContent = `${v} → ${normalizeLoader(l)}`;
        list.appendChild(li);
      });
      toggleBtn.onclick = () =>
        (list.style.display = list.style.display === "none" ? "block" : "none");
      versionsCell.append(toggleBtn, list);
    }

    row.append(providerCell, nameCell, versionsCell);
    table.appendChild(row);
  });

  container.appendChild(table);

  // Bottom compatibility
  const compBottom = computeCompatibility(filteredResults);
  renderCompatibilityBanner(container, compBottom);

  // Populate filter dropdowns
  populateFilters(results);
}

// ---- Main ----
let lastResults = [];

document.getElementById("analyze-btn").onclick = async () => {
  const urls = document
    .getElementById("mod-urls")
    .value.split("\n")
    .map((u) => u.trim())
    .filter((u) => u);
  if (!urls.length) return alert("Please enter at least one URL");

  lastResults = await postJSON("/analyze", { urls });
  renderTable(lastResults);
};

// Clear cache (silent)
document.getElementById("clear-cache").onclick = () =>
  fetch("/clear_cache", { method: "POST" });

// Filter auto-apply
document.getElementById("filter-version").onchange = () =>
  renderTable(lastResults);
document.getElementById("filter-loader").onchange = () =>
  renderTable(lastResults);

// Export buttons
document.getElementById("export-md").onclick = () => exportMD(lastResults);
document.getElementById("export-csv").onclick = () => exportCSV(lastResults);

// ---- Export helpers ----
function exportMD(results) {
  if (!results.length) return;
  let md = "# Minecraft Mod Matrix\n\n";
  results.forEach((mod) => {
    md += `- **${mod.name || "Unknown"}** (${mod.provider || "?"})\n`;
    (mod.versions || []).forEach(([v, l]) => {
      md += `  - ${v} → ${normalizeLoader(l)}\n`;
    });
  });
  const blob = new Blob([md], { type: "text/markdown" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `mods-${Date.now()}.md`;
  a.click();
}

function exportCSV(results) {
  if (!results.length) return;
  let csv = "Mod Name,Provider,Version,Loader,URL\n";
  results.forEach((mod) => {
    (mod.versions || []).forEach(([v, l]) => {
      csv += `"${mod.name || "Unknown"}","${
        mod.provider || "?"
      }","${v}","${normalizeLoader(l)}","${mod.url || ""}"\n`;
    });
  });
  const blob = new Blob([csv], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `mods-${Date.now()}.csv`;
  a.click();
}
