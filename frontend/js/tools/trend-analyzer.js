/**
 * YouTube Trend Analyzer — Claude Pulsecheck Dark Theme Controller
 * Connected to Live YouTube Data API v3 (/api/trending-feed)
 * Retains 'First Scan' baseline tracking for single-point queries.
 */

// Global State
let activeRegion = "United States";
let activeTimeframe = "7d";
let activeCategory = "All";
let activeQuery = "";
let currentVideos = [];
let viewsChart = null;
let catChart = null;
let lowerViewsChart = null;
let currentTrendId = null;
let currentKeyword = "";
let searchDebounce = null;

const CATEGORIES = [
  { name: "Music", hue: "#FF6B4A" },
  { name: "Gaming", hue: "#8B5CF6" },
  { name: "Comedy", hue: "#FBBF24" },
  { name: "Tech", hue: "#38BDF8" },
  { name: "Education", hue: "#4ADE80" },
  { name: "Sports", hue: "#F472B6" },
  { name: "News", hue: "#94A3B8" },
  { name: "Lifestyle", hue: "#FB923C" },
];

function formatCompact(n) {
  if (n == null || isNaN(n)) return "0";
  const num = Number(n);
  if (num >= 1_000_000_000) return (num / 1_000_000_000).toFixed(1).replace(/\.0$/, "") + "B";
  if (num >= 1_000_000) return (num / 1_000_000).toFixed(1).replace(/\.0$/, "") + "M";
  if (num >= 1_000) return (num / 1_000).toFixed(1).replace(/\.0$/, "") + "K";
  return String(Math.round(num));
}

function escapeHtml(str) {
  if (!str) return "";
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function escapeAttr(str) {
  if (!str) return "";
  return String(str).replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

// ── DOM Initialization ───────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  initCategories();
  initTimeframePills();
  initRegionSelect();
  initSearchInput();
  fetchTrendingFeed();
});

// ── Category Scroller ────────────────────────────────────────────────────────
function initCategories() {
  const container = document.getElementById("pulseCatScroller");
  if (!container) return;

  container.innerHTML = "";

  const allBtn = document.createElement("button");
  allBtn.className = "pulsecheck-cat-chip" + (activeCategory === "All" ? " active" : "");
  allBtn.textContent = "All";
  allBtn.addEventListener("click", () => {
    setActiveCategory("All");
  });
  container.appendChild(allBtn);

  CATEGORIES.forEach((cat) => {
    const btn = document.createElement("button");
    btn.className = "pulsecheck-cat-chip";
    btn.textContent = cat.name;
    btn.setAttribute("data-category", cat.name);
    btn.addEventListener("click", () => {
      setActiveCategory(cat.name);
    });
    container.appendChild(btn);
  });
}

function setActiveCategory(catName) {
  activeCategory = catName;
  const container = document.getElementById("pulseCatScroller");
  if (container) {
    const chips = container.querySelectorAll(".pulsecheck-cat-chip");
    chips.forEach((chip) => {
      const chipCat = chip.getAttribute("data-category") || "All";
      if (chipCat === catName) {
        chip.classList.add("active");
        const found = CATEGORIES.find((c) => c.name === catName);
        if (found) {
          chip.style.backgroundColor = found.hue;
          chip.style.borderColor = found.hue;
          chip.style.color = "#ffffff";
        } else {
          chip.style.backgroundColor = "#4f46e5";
          chip.style.borderColor = "#4f46e5";
          chip.style.color = "#ffffff";
        }
      } else {
        chip.classList.remove("active");
        chip.style.backgroundColor = "#ffffff";
        chip.style.borderColor = "#e2e8f0";
        chip.style.color = "#64748b";
      }
    });
  }

  fetchTrendingFeed();
}

// ── Timeframe Pills ──────────────────────────────────────────────────────────
function initTimeframePills() {
  const pills = document.querySelectorAll(".pulsecheck-pill");
  pills.forEach((pill) => {
    pill.addEventListener("click", () => {
      pills.forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      activeTimeframe = pill.getAttribute("data-timeframe") || "7d";
      fetchTrendingFeed();
    });
  });
}

// ── Region Dropdown ──────────────────────────────────────────────────────────
function initRegionSelect() {
  const sel = document.getElementById("pulseRegionSelect");
  if (sel) {
    sel.addEventListener("change", (e) => {
      activeRegion = e.target.value;
      fetchTrendingFeed();
    });
  }
}

// ── Search Input ─────────────────────────────────────────────────────────────
function initSearchInput() {
  const inp = document.getElementById("pulseSearchInput");
  if (!inp) return;

  const btn = document.getElementById("analyzeBtn");
  if (btn) {
    btn.addEventListener("click", () => {
      clearTimeout(searchDebounce);
      activeQuery = inp.value.trim();
      fetchTrendingFeed();
    });
  }

  inp.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      clearTimeout(searchDebounce);
      activeQuery = inp.value.trim();
      fetchTrendingFeed();
    }
  });

  inp.addEventListener("input", (e) => {
    const val = e.target.value.trim();
    activeQuery = val;

    // Instant local filtering of current videos
    filterCurrentVideos(val);

    // Debounced full YouTube API search
    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(() => {
      fetchTrendingFeed();
    }, 450);
  });
}

function filterCurrentVideos(q) {
  if (!currentVideos || currentVideos.length === 0) return;
  const filtered = currentVideos.filter(
    (v) =>
      v.title.toLowerCase().includes(q.toLowerCase()) ||
      v.channel.toLowerCase().includes(q.toLowerCase())
  );
  renderTrendingList(filtered, q);
}

// ── Fetch Trending Feed from Live YouTube API ────────────────────────────────
async function fetchTrendingFeed() {
  const loadingEl = document.getElementById("pulseLoading");
  if (loadingEl) loadingEl.style.display = "flex";

  try {
    const params = new URLSearchParams({
      region: activeRegion,
      category: activeCategory,
      timeframe: activeTimeframe,
      q: activeQuery,
    });

    const res = await fetch(`/api/trending-feed?${params.toString()}`);
    if (!res.ok) {
      throw new Error(`API returned HTTP ${res.status}`);
    }

    const data = await res.json();
    currentVideos = data.videos || [];

    renderKpis(data.kpis || {});
    renderViewsChart(data.timeSeries || [], activeCategory);
    renderCategoryChart(data.catBreakdown || []);
    renderTrendingList(currentVideos, activeQuery);

    const ytData = data.results && data.results.YouTube ? data.results.YouTube : null;
    if (ytData) {
      renderDeepIntelligence(ytData);
    }
  } catch (err) {
    console.error("Failed to load trending feed:", err);
    // Display graceful state
    const listEl = document.getElementById("pulseList");
    if (listEl && currentVideos.length === 0) {
      listEl.innerHTML = `
        <div class="pulsecheck-empty-state">
          Unable to connect to live YouTube feed right now. Please verify your connection or try again.
        </div>
      `;
    }
  } finally {
    if (loadingEl) loadingEl.style.display = "none";
  }
}

// ── Render KPIs ──────────────────────────────────────────────────────────────
function renderKpis(kpis) {
  const totalViewsVal = document.getElementById("kpiTotalViewsVal");
  const avgEngVal = document.getElementById("kpiAvgEngVal");
  const topCatVal = document.getElementById("kpiTopCatVal");
  const topCatDeltaText = document.getElementById("kpiTopCatDeltaText");
  const risingCountVal = document.getElementById("kpiRisingCountVal");
  const risingCountDeltaText = document.getElementById("kpiRisingCountDeltaText");

  if (totalViewsVal) {
    totalViewsVal.textContent = formatCompact(kpis.totalViews || 0);
  }

  if (avgEngVal) {
    const eng = Number(kpis.avgEngagement || 0);
    avgEngVal.textContent = `${eng.toFixed(1)}%`;
  }

  if (topCatVal) {
    topCatVal.textContent = kpis.fastestCategory || "—";
  }
  if (topCatDeltaText) {
    const catViews = kpis.topCategoryViews ? formatCompact(kpis.topCategoryViews) : "—";
    topCatDeltaText.textContent = `${catViews} views`;
  }

  if (risingCountVal) {
    risingCountVal.textContent = String(kpis.risingCount || 0);
  }
  if (risingCountDeltaText) {
    const tracked = kpis.trackedCount || currentVideos.length || 18;
    risingCountDeltaText.textContent = `of ${tracked} tracked`;
  }
}

// ── Render Views Trajectory Chart ────────────────────────────────────────────
function renderViewsChart(timeSeries, categoryName) {
  const titleEl = document.getElementById("viewsTrendTitle");
  if (titleEl) {
    titleEl.textContent = `Views trend — ${categoryName === "All" ? "all categories" : categoryName.toLowerCase()}`;
  }

  const canvas = document.getElementById("pulseViewsChart");
  if (!canvas) return;

  const labels = timeSeries.map((p) => p.label);
  const dataPoints = timeSeries.map((p) => p.views);

  if (viewsChart) {
    viewsChart.destroy();
  }

  const ctx = canvas.getContext("2d");
  const gradient = ctx.createLinearGradient(0, 0, 0, 200);
  gradient.addColorStop(0, "rgba(79, 70, 229, 0.16)");
  gradient.addColorStop(1, "rgba(79, 70, 229, 0)");

  // Baseline observation / First Scan tracking status
  // Used when single-point queries are evaluated
  const isFirstScan = timeSeries.length <= 1;

  viewsChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Volume",
          data: dataPoints,
          borderColor: "#4F46E5",
          borderWidth: 2.5,
          backgroundColor: gradient,
          fill: true,
          tension: 0.35,
          pointRadius: isFirstScan ? 4 : 0,
          pointHoverRadius: 5,
          pointHoverBackgroundColor: "#4F46E5",
          pointHoverBorderColor: "#FFFFFF",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        intersect: false,
        mode: "index",
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#0F172A",
          titleColor: "#94A3B8",
          bodyColor: "#FFFFFF",
          borderColor: "#1E293B",
          borderWidth: 1,
          padding: 10,
          cornerRadius: 8,
          titleFont: { size: 11, family: "Plus Jakarta Sans, Inter, sans-serif" },
          bodyFont: { size: 13, weight: "700", family: "Plus Jakarta Sans, Inter, sans-serif" },
          callbacks: {
            label: (context) => `${formatCompact(context.parsed.y)} views`,
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          border: { color: "#E2E8F0" },
          ticks: { color: "#64748B", font: { size: 11 } },
        },
        y: {
          grid: { color: "#F1F5F9" },
          border: { display: false },
          ticks: {
            color: "#64748B",
            font: { size: 11 },
            callback: (val) => formatCompact(val),
          },
        },
      },
    },
  });
}

// ── Render Category Bar Chart ────────────────────────────────────────────────
function renderCategoryChart(catBreakdown) {
  const canvas = document.getElementById("pulseCatChart");
  if (!canvas) return;

  if (catChart) {
    catChart.destroy();
  }

  const labels = catBreakdown.map((c) => c.name);
  const values = catBreakdown.map((c) => c.value);
  const hues = catBreakdown.map((c) => c.hue);

  const ctx = canvas.getContext("2d");
  catChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          data: values,
          backgroundColor: hues,
          borderRadius: 6,
          borderSkipped: false,
          barThickness: 12,
        },
      ],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#0F172A",
          titleColor: "#94A3B8",
          bodyColor: "#FFFFFF",
          borderColor: "#1E293B",
          borderWidth: 1,
          padding: 10,
          cornerRadius: 8,
          callbacks: {
            label: (context) => `${formatCompact(context.parsed.x)} views`,
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          border: { display: false },
          ticks: {
            color: "#64748B",
            font: { size: 10 },
            callback: (val) => formatCompact(val),
          },
        },
        y: {
          grid: { display: false },
          border: { display: false },
          ticks: {
            color: "#0F172A",
            font: { size: 12, weight: "600" },
          },
        },
      },
    },
  });
}

// ── Render Trending List ─────────────────────────────────────────────────────
function renderTrendingList(videos, query) {
  const titleEl = document.getElementById("trendingListTitle");
  if (titleEl) {
    titleEl.textContent = `Trending now (${videos.length})`;
  }

  const listEl = document.getElementById("pulseList");
  const emptyEl = document.getElementById("pulseEmptyState");
  const emptyQueryEl = document.getElementById("pulseEmptyQuery");

  if (!listEl) return;

  if (videos.length === 0) {
    listEl.innerHTML = "";
    if (emptyEl) {
      if (emptyQueryEl) emptyQueryEl.textContent = query || "this filter";
      emptyEl.style.display = "block";
    }
    return;
  }

  if (emptyEl) emptyEl.style.display = "none";

  listEl.innerHTML = videos
    .map((v) => {
      const isPos = v.growthPct >= 0;
      const absGrowth = Math.abs(v.growthPct);
      const deltaColor = isPos ? "#16A34A" : "#DC2626";
      const hue = v.hue || "#4F46E5";

      return `
      <div class="pulsecheck-row">
        <div class="pulsecheck-rank">${v.rank}</div>

        <div class="pulsecheck-thumb" style="background: ${hue}18; border: 1px solid ${hue}35;">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="${hue}" stroke="${hue}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="5 3 19 12 5 21 5 3"/>
          </svg>
        </div>

        <div class="pulsecheck-row-main">
          <div class="pulsecheck-row-title" title="${escapeHtml(v.title)}">${escapeHtml(v.title)}</div>
          <div class="pulsecheck-row-meta">
            <span>${escapeHtml(v.channel)}</span>
            <span class="pulsecheck-dot">&bull;</span>
            <span style="color: ${hue}; font-weight: 600;">${escapeHtml(v.category)}</span>
            <span class="pulsecheck-dot">&bull;</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-1px;">
              <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
            </svg>
            <span>${v.hoursAgo}h ago</span>
          </div>
        </div>

        <div class="pulsecheck-row-stat" title="Total Views">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>
          </svg>
          <span>${formatCompact(v.views)}</span>
        </div>

        <div class="pulsecheck-row-stat" title="Audience Comments">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>
          </svg>
          <span>${formatCompact(v.comments)}</span>
        </div>

        <div class="pulsecheck-row-stat" title="Engagement Rate">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M7 10v12"/><path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2h0a3.13 3.13 0 0 1 3 3.88Z"/>
          </svg>
          <span>${v.engagement.toFixed(1)}%</span>
        </div>

        <div class="pulsecheck-growth ${isPos ? "pos" : "neg"}" title="Velocity Growth">
          ${
            isPos
              ? `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="${deltaColor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>`
              : `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="${deltaColor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/></svg>`
          }
          <span>${isPos ? "+" : "-"}${absGrowth}%</span>
        </div>
      </div>
    `;
    })
    .join("");
}

function renderTrajectory(container, response) {
  const snapshot_count = response.snapshot_count ?? response.scan_count ?? 1;
  const history = response.timeline || response.daily_metrics || [];

  if (!container) return;

  if (snapshot_count < 2) {
    container.innerHTML = `
      <div class="trajectory-empty">
        <div class="baseline-dot"></div>
        <p>First observation recorded. This becomes a trend line once the next scan lands.</p>
      </div>`;
    return;
  }

  container.innerHTML = `<div class="chart-container-box"><canvas id="viewsChart"></canvas></div>`;
  renderLowerChart(history);
}

function renderGrowthWindow(el, value, label) {
  if (!el) return;
  if (value === null || value === undefined) {
    el.innerHTML = `<span class="window-label">${escapeHtml(label)}</span><span class="window-empty">—</span>`;
    return;
  }
  const cls = value >= 0 ? 'growth-up' : 'growth-down';
  const sign = value >= 0 ? '+' : '';
  el.innerHTML = `<span class="window-label">${escapeHtml(label)}</span><span class="${cls}">${sign}${value}%</span>`;
}

// ── Render Deep Intelligence (Velocity, Virality, Sentiment, Tags) ──────────
function renderDeepIntelligence(ytData) {
  const resultsArea = document.getElementById("resultsArea");
  if (!resultsArea) return;

  currentTrendId = ytData.trend_id || null;
  currentKeyword = ytData.keyword || activeQuery || "";

  const snapshotCount = ytData.snapshot_count ?? ytData.scan_count ?? 1;
  const intel = ytData.trend_intelligence || {};

  // 1. Compact baseline / status line
  const statusLine = document.getElementById("statusLine");
  if (statusLine) {
    if (intel.educational_banner || snapshotCount === 1) {
      statusLine.textContent = intel.educational_banner || "Baseline observation established. Scan again in 24–48 hours to measure real-world growth velocity.";
      statusLine.className = "tool-status-bar success";
      statusLine.style.display = "block";
    } else {
      statusLine.style.display = "none";
    }
  }

  // 2. Virality Score Hero
  const viralityScoreEl = document.getElementById("viralityScore");
  if (viralityScoreEl) {
    viralityScoreEl.textContent = ytData.virality_score != null ? ytData.virality_score : "0";
  }

  const summaryVirality = document.getElementById("summaryVirality");
  if (summaryVirality) {
    summaryVirality.textContent = `${ytData.virality_score || 0}/100`;
  }

  // 3. Trajectory rendering
  const trajectoryContainer = document.getElementById("trajectoryContainer");
  const timelineData = (intel.timeline && intel.timeline.length > 0) ? intel.timeline : (ytData.daily_metrics || []);
  if (trajectoryContainer) {
    renderTrajectory(trajectoryContainer, { snapshot_count: snapshotCount, scan_count: snapshotCount, timeline: timelineData });
  } else {
    renderLowerChart(timelineData);
  }

  // 4. Velocity & Summary breakdown
  const summaryDirection = document.getElementById("summaryDirection");
  if (summaryDirection) {
    summaryDirection.textContent = intel.current_direction_display || ytData.stage || "Emerging";
  }

  const summaryVelocity = document.getElementById("summaryVelocity");
  if (summaryVelocity) {
    summaryVelocity.textContent = intel.velocity_display || (ytData.growth_rate !== undefined ? `${ytData.growth_rate > 0 ? "+" : ""}${ytData.growth_rate}% / day` : "—");
  }

  const summaryAcceleration = document.getElementById("summaryAcceleration");
  if (summaryAcceleration) {
    summaryAcceleration.textContent = intel.acceleration_display || "Normal";
  }

  const summaryEngagement = document.getElementById("summaryEngagement");
  if (summaryEngagement) {
    summaryEngagement.textContent = `${ytData.engagement_rate || 0}%`;
  }

  // 5. Audience Sentiment
  const sentiment = ytData.sentiment || {};
  const dominantBadge = document.getElementById("dominantSentimentBadge");
  if (dominantBadge) {
    const dom = sentiment.dominant_sentiment || "Neutral";
    dominantBadge.textContent = dom.charAt(0).toUpperCase() + dom.slice(1);
    dominantBadge.className = "panel-badge " + (dom.toLowerCase() === "positive" ? "badge-rising" : dom.toLowerCase() === "negative" ? "badge-falling" : "badge-stable");
  }

  const sentimentBreakdown = document.getElementById("sentimentBreakdown");
  if (sentimentBreakdown) {
    sentimentBreakdown.innerHTML = `Positive: ${sentiment.positive_score || 0}% &bull; Neutral: ${sentiment.neutral_score || 0}% &bull; Negative: ${sentiment.negative_score || 0}%`;
  }

  const sampleCommentText = document.getElementById("sampleCommentText");
  if (sampleCommentText) {
    sampleCommentText.textContent = sentiment.sample_comment || (ytData.comments && ytData.comments[0]) || "Audience discussion reflects healthy creator momentum.";
  }

  // 6. Milestones & Events
  const eventsList = document.getElementById("trendEventsList");
  if (eventsList) {
    const events = intel.events || [];
    if (events.length === 0) {
      eventsList.innerHTML = `
        <div class="trend-event-item">
          <div class="trend-event-icon"><i data-lucide="map-pin"></i></div>
          <div class="trend-event-content">
            <div class="trend-event-title">Baseline Observation</div>
            <div class="trend-event-desc">Initial observation recorded. Velocity calculated after future scans.</div>
          </div>
          <div class="trend-event-date">Today</div>
        </div>
      `;
    } else {
      eventsList.innerHTML = events.map(ev => {
        let lucideName = "map-pin";
        if (ev.type === "spike") lucideName = "zap";
        else if (ev.type === "drop") lucideName = "trending-down";
        else if (ev.type === "shift") lucideName = "repeat";
        else if (ev.type === "engagement") lucideName = "heart";
        else if (ev.type === "scan") lucideName = "search";

        return `
          <div class="trend-event-item">
            <div class="trend-event-icon"><i data-lucide="${lucideName}"></i></div>
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

  // 7. Compact Growth Windows
  const historyContainer = document.getElementById("historyWindowsContainer");
  if (historyContainer) {
    const hw = intel.historical_context || {};
    const windows = [
      { key: "1d", label: "1 Day" },
      { key: "7d", label: "7 Days" },
      { key: "30d", label: "30 Days" },
      { key: "90d", label: "90 Days" }
    ];

    historyContainer.innerHTML = windows.map(w => {
      const entry = hw[w.key] || {};
      const val = (entry.status === "available" && entry.change_pct !== null) ? entry.change_pct : null;
      const cls = val !== null ? (val >= 0 ? 'growth-up' : 'growth-down') : 'window-empty';
      const sign = (val !== null && val >= 0) ? '+' : '';
      const valText = val !== null ? `${sign}${val}%` : '—';

      return `
        <div class="window-row">
          <span class="window-label">${w.label}</span>
          <span class="${cls}">${valText}</span>
        </div>
      `;
    }).join("");
  }

  // 8. Projection Box — strictly rendered only when snapshot_count >= 3
  const projectionEl = document.getElementById("projectionBox");
  if (projectionEl) {
    if (snapshotCount >= 3 && intel.forecast && intel.forecast.available) {
      projectionEl.classList.remove("hidden");
      const forecastVal = (intel.forecast.projection_days && intel.forecast.projection_days[0])
        ? formatCompact(intel.forecast.projection_days[0].expected_views)
        : formatCompact(ytData.total_views);
      const projValueEl = projectionEl.querySelector(".projection-value");
      if (projValueEl) {
        projValueEl.textContent = `≈ ${forecastVal} views`;
      }
    } else {
      projectionEl.classList.add("hidden");
    }
  }

  // 9. High-CTR Tag Combinations
  const tagsList = document.getElementById("tagsList");
  if (tagsList) {
    const tags = ytData.youtube_tags || [];
    if (tags.length === 0) {
      tagsList.innerHTML = `<span class="text-slate-400 font-0-85">No specific tags extracted.</span>`;
    } else {
      tagsList.innerHTML = tags.map(t => `
        <span class="tag-item-default" data-copy="${escapeAttr(t)}" title="Click to copy">
          <i data-lucide="tag"></i> ${escapeHtml(t)}
        </span>
      `).join("");
    }
  }

  // 10. High-CTR Hashtags
  const hashtagsList = document.getElementById("hashtagsList");
  if (hashtagsList) {
    const htags = ytData.youtube_hashtags || [];
    if (htags.length > 0) {
      hashtagsList.innerHTML = htags.map(h => `
        <span class="tag-item-accent" data-copy="${escapeAttr(h)}" title="Click to copy">
          ${escapeHtml(h)}
        </span>
      `).join("");
    } else {
      hashtagsList.innerHTML = "";
    }
  }

  // 11. Context-Aware High-CTR Titles
  const aiTitlesList = document.getElementById("aiTitlesList");
  if (aiTitlesList) {
    const titles = ytData.seo_title_ideas || [];
    if (titles.length === 0) {
      aiTitlesList.innerHTML = `<span class="text-slate-400 font-0-85">No titles generated yet.</span>`;
    } else {
      aiTitlesList.innerHTML = titles.map(title => `
        <div class="flex-between-center p-12 bg-slate-50 border-slate-200 radius-10">
          <span class="font-600 font-0-9 text-slate-900">${escapeHtml(title)}</span>
          <button class="tool-copy-action-btn" data-copy="${escapeAttr(title)}" type="button">Copy</button>
        </div>
      `).join("");
    }
  }

  resultsArea.style.display = "block";

  if (typeof lucide !== "undefined" && lucide.createIcons) {
    lucide.createIcons();
  }
}

// ── Render Lower Time-Series Chart ──────────────────────────────────────────
function renderLowerChart(dataPoints) {
  const ctx = document.getElementById("viewsChart");
  if (!ctx || !window.Chart) return;

  if (lowerViewsChart) {
    lowerViewsChart.destroy();
  }

  const isBaseline = dataPoints.length <= 1;
  const chartBaselineNote = document.getElementById("chartBaselineNote");
  if (chartBaselineNote) {
    chartBaselineNote.style.display = isBaseline ? "block" : "none";
  }

  const labels = dataPoints.map(d => d.date || d.label || "Obs 1");
  const rawViews = dataPoints.map(d => d.views || 0);
  const smoothedViews = dataPoints.map(d => d.smoothed_views !== undefined ? d.smoothed_views : d.views || 0);

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

  lowerViewsChart = new Chart(ctx, {
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
          backgroundColor: "#0f172a",
          titleColor: "#94a3b8",
          bodyColor: "#ffffff",
          padding: 10,
          cornerRadius: 8,
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
            color: "#64748b",
            font: { size: 11 },
            callback: function(val) {
              if (val >= 1000000) return (val / 1000000).toFixed(1) + "M";
              if (val >= 1000) return (val / 1000).toFixed(0) + "K";
              return val;
            }
          }
        },
        x: {
          grid: { display: false },
          border: { color: "#e2e8f0" },
          offset: isBaseline,
          ticks: { color: "#64748b", font: { size: 11 }, maxRotation: 45, minRotation: 0 }
        }
      }
    }
  });
}

// ── Connected Actions & Exports ─────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const ctaStrat = document.getElementById("ctaStrategistBtn");
  if (ctaStrat) {
    ctaStrat.addEventListener("click", () => {
      const topic = currentKeyword || (document.getElementById("pulseSearchInput")?.value.trim() || "");
      window.location.href = `/tools/ai-strategist${topic ? "?topic=" + encodeURIComponent(topic) : ""}`;
    });
  }

  const ctaComp = document.getElementById("ctaCompetitorBtn");
  if (ctaComp) {
    ctaComp.addEventListener("click", () => {
      const topic = currentKeyword || (document.getElementById("pulseSearchInput")?.value.trim() || "");
      window.location.href = `/tools/competitor-audit${topic ? "?channel=" + encodeURIComponent(topic) : ""}`;
    });
  }

  const expPdf = document.getElementById("exportPdfBtn");
  if (expPdf) {
    expPdf.addEventListener("click", () => {
      if (!currentTrendId) return;
      window.location.href = `/api/report/${currentTrendId}`;
    });
  }

  const expCsv = document.getElementById("exportCsvBtn");
  if (expCsv) {
    expCsv.addEventListener("click", () => {
      if (!currentTrendId) return;
      window.location.href = `/api/export-csv/${currentTrendId}`;
    });
  }
});

// Delegated click listener for tags and titles clipboard copying
document.addEventListener("click", (e) => {
  const copyTarget = e.target.closest("[data-copy]");
  if (copyTarget) {
    const textToCopy = copyTarget.getAttribute("data-copy");
    if (typeof copyToClipboard === "function") {
      copyToClipboard(textToCopy, copyTarget);
    } else if (navigator.clipboard) {
      navigator.clipboard.writeText(textToCopy).then(() => {
        const prev = copyTarget.textContent;
        copyTarget.textContent = "Copied!";
        setTimeout(() => { copyTarget.textContent = prev; }, 1500);
      });
    }
  }
});
