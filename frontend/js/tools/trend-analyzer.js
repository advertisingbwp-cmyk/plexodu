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
