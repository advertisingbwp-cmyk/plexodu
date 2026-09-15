/**
 * YouTube Trend Analyzer Client JS (Phase 8 Rebuild)
 */
let currentTrendId = null;
let currentKeyword = "";
let viewsChartInstance = null;
let debounceTimer = null;
let currentTimelineData = [];
let activeTimeframe = "all";

const keywordInput = document.getElementById("keywordInput");
const analyzeBtn = document.getElementById("analyzeBtn");
const suggestionsDropdown = document.getElementById("suggestionsDropdown");
const statusLine = document.getElementById("statusLine");
const loadingArea = document.getElementById("loadingArea");
const resultsArea = document.getElementById("resultsArea");

// Educational Banner
const trendBanner = document.getElementById("trendBanner");
const trendBannerText = document.getElementById("trendBannerText");

// 4 Top KPI Elements
const kpiTrendScoreVal = document.getElementById("kpiTrendScoreVal");
const kpiTrendScoreBadge = document.getElementById("kpiTrendScoreBadge");
const kpiVelocityVal = document.getElementById("kpiVelocityVal");
const kpiDirectionBadge = document.getElementById("kpiDirectionBadge");
const kpiViewsVal = document.getElementById("kpiViewsVal");
const kpiConfidenceVal = document.getElementById("kpiConfidenceVal");
const kpiScanCountSub = document.getElementById("kpiScanCountSub");

// Trend Summary Box
const summaryDirection = document.getElementById("summaryDirection");
const summaryVelocity = document.getElementById("summaryVelocity");
const summaryAcceleration = document.getElementById("summaryAcceleration");
const summaryEngagement = document.getElementById("summaryEngagement");
const summaryVirality = document.getElementById("summaryVirality");

// Audience Sentiment Elements
const dominantSentimentBadge = document.getElementById("dominantSentimentBadge");
const sentimentBreakdown = document.getElementById("sentimentBreakdown");
const sampleCommentText = document.getElementById("sampleCommentText");

// Derived Events & Historical Windows
const trendEventsList = document.getElementById("trendEventsList");
const historyTableBody = document.getElementById("historyTableBody");

// Forecast Elements
const forecastFallback = document.getElementById("forecastFallback");
const forecastGrid = document.getElementById("forecastGrid");

// Tags & Context Titles
const tagsList = document.getElementById("tagsList");
const hashtagsList = document.getElementById("hashtagsList");
const aiTitlesList = document.getElementById("aiTitlesList");

// Actions & Exports
const ctaStrategistBtn = document.getElementById("ctaStrategistBtn");
const ctaCompetitorBtn = document.getElementById("ctaCompetitorBtn");
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
          const raw = await res.text();
          try {
            const data = JSON.parse(raw);
            renderSuggestions(data.suggestions || []);
          } catch (e) {}
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

// ── Timeframe Tabs ──────────────────────────────────────────────────────────
document.querySelectorAll(".trend-tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".trend-tab-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    activeTimeframe = btn.getAttribute("data-range") || "all";
    applyTimeframeFilter();
  });
});

function applyTimeframeFilter() {
  if (!currentTimelineData || currentTimelineData.length === 0) return;
  
  if (activeTimeframe === "all") {
    renderChart(currentTimelineData);
    return;
  }

  const now = new Date();
  let cutoffDays = 30;
  if (activeTimeframe === "1d") cutoffDays = 1;
  else if (activeTimeframe === "7d") cutoffDays = 7;
  else if (activeTimeframe === "30d") cutoffDays = 30;
  else if (activeTimeframe === "90d") cutoffDays = 90;

  const cutoffDate = new Date(now.getTime() - (cutoffDays * 24 * 60 * 60 * 1000));
  const filtered = currentTimelineData.filter(d => {
    const itemDate = new Date(d.date.replace(" ", "T"));
    return isNaN(itemDate.getTime()) || itemDate >= cutoffDate;
  });

  renderChart(filtered.length > 0 ? filtered : currentTimelineData);
}

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

  currentKeyword = kw;
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

    const rawText = await res.text();
    let data;
    try {
      data = JSON.parse(rawText);
    } catch (parseErr) {
      throw new Error("Server returned an invalid response. Please try again.");
    }

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
  const intel = res.trend_intelligence || {};

  // 1. Educational Banner for Baseline Scans
  if (intel.status === "baseline" && intel.educational_banner) {
    if (trendBanner) trendBanner.style.display = "flex";
    if (trendBannerText) trendBannerText.textContent = intel.educational_banner;
  } else {
    if (trendBanner) trendBanner.style.display = "none";
  }

  // 2. 4 Top KPI Cards
  // KPI 1: Trend Score
  if (kpiTrendScoreVal) {
    kpiTrendScoreVal.textContent = intel.current_trend_score_display || "Pending";
  }
  if (kpiTrendScoreBadge) {
    if (intel.status === "baseline") {
      kpiTrendScoreBadge.className = "panel-badge badge-baseline";
      kpiTrendScoreBadge.textContent = "Baseline";
    } else {
      kpiTrendScoreBadge.className = "panel-badge badge-rising";
      kpiTrendScoreBadge.textContent = "Live Index";
    }
  }

  // KPI 2: Velocity & Direction
  if (kpiVelocityVal) {
    kpiVelocityVal.textContent = intel.velocity_display || "Pending";
  }
  if (kpiDirectionBadge) {
    const dir = intel.current_direction || "BASELINE";
    if (dir === "RISING") {
      kpiDirectionBadge.className = "panel-badge badge-rising";
      kpiDirectionBadge.textContent = "Rising ↗";
    } else if (dir === "FALLING") {
      kpiDirectionBadge.className = "panel-badge badge-falling";
      kpiDirectionBadge.textContent = "Falling ↘";
    } else if (dir === "STABLE") {
      kpiDirectionBadge.className = "panel-badge badge-stable";
      kpiDirectionBadge.textContent = "Stable →";
    } else {
      kpiDirectionBadge.className = "panel-badge badge-baseline";
      kpiDirectionBadge.textContent = "Baseline";
    }
  }

  // KPI 3: Total Views
  if (kpiViewsVal) {
    kpiViewsVal.textContent = Number(res.total_views || 0).toLocaleString();
  }

  // KPI 4: Confidence & Scans
  if (kpiConfidenceVal) {
    kpiConfidenceVal.textContent = intel.current_confidence || "Low";
  }
  if (kpiScanCountSub) {
    const sc = intel.scan_count || 1;
    kpiScanCountSub.textContent = `${sc} scan${sc === 1 ? "" : "s"} recorded`;
  }

  // 3. Trend Summary Box
  const isFirstScan = intel.status === "baseline" || !intel.velocity;
  if (kpiVelocitySub) {
    kpiVelocitySub.textContent = isFirstScan ? "First Scan — baseline tracking" : "Day-over-day tracking";
  }
  if (summaryDirection) summaryDirection.textContent = intel.current_direction_display || res.stage || "Stable";
  if (summaryVelocity) summaryVelocity.textContent = intel.velocity_display || (isFirstScan ? "First Scan" : "Pending");
  if (summaryAcceleration) summaryAcceleration.textContent = intel.acceleration_display || "Pending";
  if (summaryEngagement) summaryEngagement.textContent = `${res.engagement_rate || 0}%`;
  if (summaryVirality) summaryVirality.textContent = `${res.virality_score || 0}/100`;

  // 4. Sentiment
  const s = res.sentiment || {};
  const domSent = (s.dominant_sentiment || "Neutral").toLowerCase();
  if (dominantSentimentBadge) {
    dominantSentimentBadge.textContent = domSent.toUpperCase();
    dominantSentimentBadge.className = `panel-badge badge-${domSent === "positive" ? "rising" : (domSent === "negative" ? "falling" : "stable")}`;
  }
  if (sentimentBreakdown) {
    sentimentBreakdown.textContent = `Positive: ${s.positive_score || 0}% • Neutral: ${s.neutral_score || 0}% • Negative: ${s.negative_score || 0}%`;
  }
  if (sampleCommentText) {
    const rawComment = s.sample_comment || "";
    const isFakeComment = !rawComment || rawComment.toLowerCase().includes("no comments available") || rawComment.toLowerCase().includes("for this video");
    sampleCommentText.textContent = isFakeComment ? "No recent audience comments available for this topic." : `"${rawComment}"`;
  }

  // 5. Chart Time-Series Data
  if (intel.timeline && intel.timeline.length > 1) {
    currentTimelineData = intel.timeline;
  } else if (res.daily_metrics && res.daily_metrics.length > 0) {
    currentTimelineData = res.daily_metrics.map(d => ({
      date: d.date,
      views: d.views,
      smoothed_views: d.views,
      engagement_rate: res.engagement_rate || 0
    }));
  } else {
    currentTimelineData = [];
  }
  applyTimeframeFilter();

  // 6. Trend Milestones & Events
  if (trendEventsList) {
    const events = intel.events || [];
    if (events.length === 0) {
      trendEventsList.innerHTML = `
        <div class="trend-event-item">
          <div class="trend-event-icon">📍</div>
          <div class="trend-event-content">
            <div class="trend-event-title">Baseline Recorded</div>
            <div class="trend-event-desc">Initial snapshot captured.</div>
          </div>
          <div class="trend-event-date">Today</div>
        </div>
      `;
    } else {
      trendEventsList.innerHTML = events.map(ev => {
        let icon = "📍";
        if (ev.type === "spike") icon = "⚡";
        else if (ev.type === "drop") icon = "📉";
        else if (ev.type === "shift") icon = "🔄";
        else if (ev.type === "engagement") icon = "❤️";
        else if (ev.type === "scan") icon = "🔍";

        return `
          <div class="trend-event-item">
            <div class="trend-event-icon">${icon}</div>
            <div class="trend-event-content">
              <div class="trend-event-title">${escapeHtml(ev.title)}</div>
              <div class="trend-event-desc">${escapeHtml(ev.description)}</div>
            </div>
            <div class="trend-event-date">${escapeHtml(ev.date || "Today")}</div>
          </div>
        `;
      }).join("");
    }
  }

  // 7. Historical Windows Table
  if (historyTableBody) {
    const hw = intel.historical_context || {};
    const windows = [
      { key: "1d", label: "1 Day" },
      { key: "7d", label: "7 Days" },
      { key: "30d", label: "30 Days" },
      { key: "90d", label: "90 Days" }
    ];

    historyTableBody.innerHTML = windows.map(w => {
      const entry = hw[w.key] || { status: "insufficient_history", display: "Insufficient history" };
      const isAvail = entry.status === "available" && entry.change_pct !== null;
      const badgeClass = isAvail ? (entry.change_pct >= 0 ? "badge-rising" : "badge-falling") : "badge-stable";
      const growthDisplay = isAvail ? `${entry.change_pct > 0 ? "+" : ""}${entry.change_pct}%` : "—";
      const statusText = isAvail ? "Audited" : "Insufficient history";

      return `
        <tr>
          <td><strong>${w.label}</strong></td>
          <td><span class="panel-badge ${badgeClass}">${growthDisplay}</span></td>
          <td><span class="panel-badge badge-stable">${statusText}</span></td>
        </tr>
      `;
    }).join("");
  }

  // 8. Conservative 7-Day Forecast
  const fc = intel.forecast || {};
  if (fc.available && fc.projection_days && fc.projection_days.length > 0) {
    if (forecastFallback) forecastFallback.style.display = "none";
    if (forecastGrid) {
      forecastGrid.style.display = "grid";
      forecastGrid.innerHTML = fc.projection_days.map(d => `
        <div class="trend-forecast-card">
          <div class="trend-forecast-day">${escapeHtml(d.day)}</div>
          <div class="trend-forecast-val">${Number(d.expected_views).toLocaleString()}</div>
          <div class="trend-forecast-range">±${Number(d.upper_bound - d.expected_views).toLocaleString()}</div>
        </div>
      `).join("");
    }
  } else {
    if (forecastGrid) forecastGrid.style.display = "none";
    if (forecastFallback) forecastFallback.style.display = "block";
  }

  // 9. Tags
  if (tagsList) {
    const tags = res.youtube_tags || [];
    tagsList.innerHTML = tags.map(t => `
      <span class="tag-item-default" data-copy="${escapeAttr(t)}" title="Click to copy">
        🏷️ ${escapeHtml(t)}
      </span>
    `).join("");
  }

  // 10. Hashtags
  if (hashtagsList) {
    const htags = res.youtube_hashtags || [];
    hashtagsList.innerHTML = htags.map(h => `
      <span class="tag-item-accent" data-copy="${escapeAttr(h)}" title="Click to copy">
        ${escapeHtml(h)}
      </span>
    `).join("");
  }

  // 11. AI Titles
  if (aiTitlesList) {
    const titles = res.seo_title_ideas || [];
    aiTitlesList.innerHTML = titles.map(title => `
      <div class="flex-between-center p-12 bg-slate-50 border-slate-200 radius-10">
        <span class="font-600 font-0-9 text-slate-900">${escapeHtml(title)}</span>
        <button class="tool-copy-action-btn" data-copy="${escapeAttr(title)}">Copy</button>
      </div>
    `).join("");
  }

  if (resultsArea) resultsArea.style.display = "block";
}

function renderChart(dataPoints) {
  const ctx = document.getElementById("viewsChart");
  if (!ctx || !window.Chart) return;

  if (viewsChartInstance) {
    viewsChartInstance.destroy();
  }

  const isBaseline = dataPoints.length <= 1;
  const chartBaselineNote = document.getElementById("chartBaselineNote");
  if (chartBaselineNote) {
    chartBaselineNote.style.display = isBaseline ? "block" : "none";
  }

  const labels = dataPoints.map(d => d.date);
  const rawViews = dataPoints.map(d => d.views);
  const smoothedViews = dataPoints.map(d => d.smoothed_views !== undefined ? d.smoothed_views : d.views);

  const datasets = [
    {
      label: "Smoothed Trajectory",
      data: smoothedViews,
      borderColor: "#4f46e5",
      backgroundColor: "rgba(79, 70, 229, 0.08)",
      fill: true,
      tension: 0.35,
      pointRadius: isBaseline ? 6 : 3,
      pointHoverRadius: isBaseline ? 8 : 6,
      order: 1
    }
  ];

  // Show raw observation points if we have multiple observations and raw differs
  const hasSmoothedVariance = rawViews.some((v, idx) => v !== smoothedViews[idx]);
  if (hasSmoothedVariance) {
    datasets.push({
      label: "Raw Observations",
      data: rawViews,
      borderColor: "#94a3b8",
      backgroundColor: "rgba(148, 163, 184, 0.4)",
      fill: false,
      showLine: false,
      pointRadius: 5,
      pointHoverRadius: 7,
      order: 2
    });
  }

  viewsChartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "index",
        intersect: false
      },
      plugins: {
        legend: {
          display: datasets.length > 1,
          position: "top",
          labels: { boxWidth: 12, font: { size: 11 } }
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              return `${context.dataset.label}: ${Number(context.raw).toLocaleString()} views`;
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: "#f1f5f9" },
          ticks: {
            callback: function(val) {
              if (val >= 1000000) return (val / 1000000).toFixed(1) + "M";
              if (val >= 1000) return (val / 1000).toFixed(0) + "K";
              return val;
            }
          }
        },
        x: {
          grid: { display: false },
          offset: isBaseline,
          ticks: { maxRotation: 45, minRotation: 0 }
        }
      }
    }
  });
}

// ── Connected Actions ───────────────────────────────────────────────────────
if (ctaStrategistBtn) {
  ctaStrategistBtn.addEventListener("click", () => {
    const topic = currentKeyword || (keywordInput ? keywordInput.value.trim() : "");
    window.location.href = `/tools/ai-strategist${topic ? "?topic=" + encodeURIComponent(topic) : ""}`;
  });
}

if (ctaCompetitorBtn) {
  ctaCompetitorBtn.addEventListener("click", () => {
    const topic = currentKeyword || (keywordInput ? keywordInput.value.trim() : "");
    window.location.href = `/tools/competitor-audit${topic ? "?channel=" + encodeURIComponent(topic) : ""}`;
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

// Delegated click listener for tags and titles (no inline onclick handlers)
document.addEventListener("click", (e) => {
  const copyTarget = e.target.closest("[data-copy]");
  if (copyTarget) {
    const textToCopy = copyTarget.getAttribute("data-copy");
    if (typeof copyToClipboard === "function") {
      copyToClipboard(textToCopy, copyTarget);
    }
  }
});
