/**
 * YouTube Keyword Tool Client JS
 */
const keywordInput = document.getElementById("keywordInput");
const searchKeywordBtn = document.getElementById("searchKeywordBtn");
const suggestionsDropdown = document.getElementById("suggestionsDropdown");
const statusLine = document.getElementById("statusLine");
const loadingArea = document.getElementById("loadingArea");
const resultsArea = document.getElementById("resultsArea");
const keywordsList = document.getElementById("keywordsList");
const comparisonTableBody = document.getElementById("comparisonTableBody");

let debounceTimer = null;

// Autocomplete
if (keywordInput) {
  keywordInput.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    const query = keywordInput.value.trim();
    if (query.length < 2) {
      if (suggestionsDropdown) suggestionsDropdown.style.display = "none";
      return;
    }
    debounceTimer = setTimeout(async () => {
      try {
        const res = await fetchWithTimeout(`/api/suggest?q=${encodeURIComponent(query)}`, {}, 5000);
        if (res.ok) {
          const data = await res.json();
          renderDropdown(data.suggestions || []);
        }
      } catch (e) {}
    }, 250);
  });

  keywordInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      if (suggestionsDropdown) suggestionsDropdown.style.display = "none";
      exploreKeywords();
    }
  });
}

function renderDropdown(suggs) {
  if (!suggestionsDropdown) return;
  if (!suggs || suggs.length === 0) {
    suggestionsDropdown.style.display = "none";
    return;
  }
  suggestionsDropdown.innerHTML = suggs.slice(0, 7).map(s => `
    <div class="suggestion-item" style="padding:10px 14px; cursor:pointer; font-size:14px; border-bottom:1px solid #f1f5f9;">
      🔍 ${escapeHtml(s)}
    </div>
  `).join("");
  suggestionsDropdown.style.display = "block";

  suggestionsDropdown.querySelectorAll(".suggestion-item").forEach((el, idx) => {
    el.addEventListener("click", () => {
      keywordInput.value = suggs[idx];
      suggestionsDropdown.style.display = "none";
      exploreKeywords();
    });
  });
}

if (searchKeywordBtn) {
  searchKeywordBtn.addEventListener("click", exploreKeywords);
}

async function exploreKeywords() {
  const kw = keywordInput ? keywordInput.value.trim() : "";
  if (!kw) {
    showStatusBar(statusLine, "Please enter a keyword to explore", true);
    return;
  }

  hideStatusBar(statusLine);
  if (loadingArea) loadingArea.style.display = "block";
  if (resultsArea) resultsArea.style.display = "none";
  if (searchKeywordBtn) searchKeywordBtn.disabled = true;

  try {
    const [suggestRes, compareRes] = await Promise.all([
      fetchWithTimeout(`/api/suggest?q=${encodeURIComponent(kw)}`, {}, 8000).catch(() => null),
      fetchWithTimeout(`/api/compare-keywords`, {}, 8000).catch(() => null)
    ]);

    let suggestions = [];
    if (suggestRes && suggestRes.ok) {
      const sData = await suggestRes.json();
      suggestions = sData.suggestions || [];
    }

    let comparisons = [];
    if (compareRes && compareRes.ok) {
      const cData = await compareRes.json();
      comparisons = cData.comparison || [];
    }

    renderKeywords(suggestions, comparisons);
  } catch (err) {
    showStatusBar(statusLine, err.message || "Failed to load keywords", true);
  } finally {
    if (loadingArea) loadingArea.style.display = "none";
    if (searchKeywordBtn) searchKeywordBtn.disabled = false;
  }
}

function renderKeywords(suggs, comps) {
  if (keywordsList) {
    if (suggs.length === 0) {
      keywordsList.innerHTML = `<span style="font-size:13px; color:#94a3b8;">No direct suggestions found.</span>`;
    } else {
      keywordsList.innerHTML = suggs.map(s => `
        <span class="panel-badge" style="background:#eef2ff; color:#4f46e5; padding:8px 14px; border-radius:10px; font-size:13px; cursor:pointer;" title="Click to copy" onclick="copyToClipboard('${escapeAttr(s)}', this)">
          🔍 ${escapeHtml(s)}
        </span>
      `).join("");
    }
  }

  if (comparisonTableBody) {
    if (comps.length === 0) {
      comparisonTableBody.innerHTML = `<tr><td colspan="5" style="padding:16px; text-align:center; color:#94a3b8;">No recent keyword comparisons available.</td></tr>`;
    } else {
      comparisonTableBody.innerHTML = comps.map(c => `
        <tr style="border-bottom:1px solid #f1f5f9;">
          <td style="padding:12px; font-weight:700; color:#0f172a;">${escapeHtml(c.keyword)}</td>
          <td style="padding:12px; color:#475569;">${Number(c.total_views || 0).toLocaleString()}</td>
          <td style="padding:12px; color:${c.growth_rate >= 0 ? '#16a34a' : '#dc2626'}; font-weight:700;">${c.growth_rate > 0 ? '+' : ''}${c.growth_rate}%</td>
          <td style="padding:12px; font-weight:700; color:#4f46e5;">${c.virality_score}/100</td>
          <td style="padding:12px; text-transform:capitalize; color:#64748b;">${escapeHtml(c.dominant_sentiment || 'n/a')}</td>
        </tr>
      `).join("");
    }
  }

  if (resultsArea) resultsArea.style.display = "block";
}
