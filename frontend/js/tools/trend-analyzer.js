/**
 * YouTube Trend Analyzer Client JS
 */
let currentTrendId = null;
let viewsChartInstance = null;
let debounceTimer = null;

const keywordInput = document.getElementById("keywordInput");
const analyzeBtn = document.getElementById("analyzeBtn");
const suggestionsDropdown = document.getElementById("suggestionsDropdown");
const statusLine = document.getElementById("statusLine");
const loadingArea = document.getElementById("loadingArea");
const resultsArea = document.getElementById("resultsArea");

const totalViewsVal = document.getElementById("totalViewsVal");
const growthRateVal = document.getElementById("growthRateVal");
const viralityScoreVal = document.getElementById("viralityScoreVal");

const dominantSentimentBadge = document.getElementById("dominantSentimentBadge");
const sentimentBreakdown = document.getElementById("sentimentBreakdown");
const sampleCommentText = document.getElementById("sampleCommentText");

const tagsList = document.getElementById("tagsList");
const hashtagsList = document.getElementById("hashtagsList");
const aiTitlesList = document.getElementById("aiTitlesList");

const exportPdfBtn = document.getElementById("exportPdfBtn");
const exportCsvBtn = document.getElementById("exportCsvBtn");

// ── Autocomplete Suggestions ────────────────────────────────────────────────
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
          renderSuggestions(data.suggestions || []);
        }
      } catch (err) {
        // silent fail on suggestions
      }
    }, 250);
  });

  keywordInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      if (suggestionsDropdown) suggestionsDropdown.style.display = "none";
      runTrendAnalysis();
    }
  });
}

function renderSuggestions(suggs) {
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
      runTrendAnalysis();
    });
  });
}

document.addEventListener("click", (e) => {
  if (suggestionsDropdown && !suggestionsDropdown.contains(e.target) && e.target !== keywordInput) {
    suggestionsDropdown.style.display = "none";
  }
});

// ── Trend Analysis Action ───────────────────────────────────────────────────
if (analyzeBtn) {
  analyzeBtn.addEventListener("click", runTrendAnalysis);
}

async function runTrendAnalysis() {
  const kw = keywordInput ? keywordInput.value.trim() : "";
  if (!kw) {
    showStatusBar(statusLine, "Please enter a search topic or keyword", true);
    return;
  }

  hideStatusBar(statusLine);
  if (loadingArea) loadingArea.style.display = "block";
  if (resultsArea) resultsArea.style.display = "none";
  if (analyzeBtn) analyzeBtn.disabled = true;

  try {
    const res = await fetchWithTimeout("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keyword: kw })
    }, 25000);

    const data = await res.json();
    if (!res.ok || data.error) {
      const errMsg = data.error || (data.results && data.results.YouTube && data.results.YouTube.message) || "Analysis failed. Please try again.";
      showStatusBar(statusLine, errMsg, true);
      return;
    }

    const ytData = data.results ? data.results.YouTube : data;
    if (!ytData || ytData.error) {
      showStatusBar(statusLine, (ytData && ytData.message) || "Could not retrieve YouTube data for this topic.", true);
      return;
    }

    renderResults(ytData);
  } catch (err) {
    showStatusBar(statusLine, err.message || "Network error. Please try again.", true);
  } finally {
    if (loadingArea) loadingArea.style.display = "none";
    if (analyzeBtn) analyzeBtn.disabled = false;
  }
}

function renderResults(res) {
  currentTrendId = res.trend_id || null;

  if (totalViewsVal) totalViewsVal.textContent = Number(res.total_views || 0).toLocaleString();
  if (growthRateVal) {
    const daily = res.daily_metrics || [];
    if (daily.length < 2 || (res.growth_rate === 0 && daily.length <= 1)) {
      growthRateVal.textContent = "First Scan";
      growthRateVal.title = "Initial snapshot — recurring tracking calculates day-over-day velocity.";
    } else {
      growthRateVal.textContent = `${res.growth_rate > 0 ? "+" : ""}${res.growth_rate}%`;
      growthRateVal.removeAttribute("title");
    }
  }
  if (viralityScoreVal) viralityScoreVal.textContent = `${res.virality_score}/100`;

  // Sentiment
  const s = res.sentiment || {};
  if (dominantSentimentBadge) {
    dominantSentimentBadge.textContent = (s.dominant_sentiment || "Neutral").toUpperCase();
  }
  if (sentimentBreakdown) {
    sentimentBreakdown.textContent = `Positive: ${s.positive_score || 0}% • Neutral: ${s.neutral_score || 0}% • Negative: ${s.negative_score || 0}%`;
  }
  if (sampleCommentText) {
    sampleCommentText.textContent = s.sample_comment ? `"${s.sample_comment}"` : "No sample comment recorded.";
  }

  // Chart
  renderChart(res.daily_metrics || []);

  // Tags
  if (tagsList) {
    const tags = res.youtube_tags || [];
    tagsList.innerHTML = tags.map(t => `
      <span class="panel-badge" style="background:#f1f5f9; color:#0f172a; padding:6px 12px; border-radius:8px; font-size:13px; cursor:pointer;" title="Click to copy" onclick="copyToClipboard('${escapeAttr(t)}', this)">
        🏷️ ${escapeHtml(t)}
      </span>
    `).join("");
  }

  // Hashtags
  if (hashtagsList) {
    const htags = res.youtube_hashtags || [];
    hashtagsList.innerHTML = htags.map(h => `
      <span class="panel-badge" style="background:#eef2ff; color:#4f46e5; padding:6px 12px; border-radius:8px; font-size:13px; cursor:pointer;" title="Click to copy" onclick="copyToClipboard('${escapeAttr(h)}', this)">
        ${escapeHtml(h)}
      </span>
    `).join("");
  }

  // AI Titles
  if (aiTitlesList) {
    const titles = res.seo_title_ideas || [];
    aiTitlesList.innerHTML = titles.map(title => `
      <div style="display:flex; align-items:center; justify-content:space-between; gap:12px; padding:12px 16px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px;">
        <span style="font-weight:600; font-size:14px; color:#0f172a;">${escapeHtml(title)}</span>
        <button class="tool-secondary-btn" style="padding:6px 12px; font-size:12px;" onclick="copyToClipboard('${escapeAttr(title)}', this)">Copy</button>
      </div>
    `).join("");
  }

  if (resultsArea) resultsArea.style.display = "block";
}

function renderChart(daily) {
  const ctx = document.getElementById("viewsChart");
  if (!ctx) return;

  if (viewsChartInstance) {
    viewsChartInstance.destroy();
  }

  const labels = daily.map(d => d.date);
  const data = daily.map(d => d.views);

  viewsChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: "Views Trajectory",
        data: data,
        borderColor: "#4f46e5",
        backgroundColor: "rgba(79, 70, 229, 0.08)",
        fill: true,
        tension: 0.35,
        pointRadius: 4,
        pointHoverRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: "#f1f5f9" }
        },
        x: {
          grid: { display: false }
        }
      }
    }
  });
}

// ── Exports ─────────────────────────────────────────────────────────────────
if (exportPdfBtn) {
  exportPdfBtn.addEventListener("click", () => {
    if (!currentTrendId) return;
    window.location.href = `/api/report/${currentTrendId}`;
  });
}

if (exportCsvBtn) {
  exportCsvBtn.addEventListener("click", () => {
    if (!currentTrendId) return;
    window.location.href = `/api/export-csv/${currentTrendId}`;
  });
}
