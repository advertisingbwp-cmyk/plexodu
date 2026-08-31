/**
 * SMTAS YouTube Trend Dashboard — Full JS v5.0
 * Features: YouTube-Only API, Groq AI Chat, Keyword Comparison,
 *           Channel Audit (7D/28D/3M), CSV & PDF Exports,
 *           Keyword Autocomplete, Neutral=Blue Sentiment
 */

const API = "/api";

// ─── State ──────────────────────────────────────────────────────────────────
let activeCharts          = [];
let viralityCompareChartInst = null;
let channelGrowthChart    = null;
let chatContext           = null;
let suggestDebounceTimer  = null;
let highlightedSuggestion = -1;
let currentAuditData      = null;   // store latest channel audit for timeframe switching

// ─── DOM Refs ────────────────────────────────────────────────────────────────
const keywordInput        = document.getElementById("keywordInput");
const analyzeBtn          = document.getElementById("analyzeBtn");
const statusLine          = document.getElementById("statusLine");
const emptyState          = document.getElementById("emptyState");
const resultsArea         = document.getElementById("resultsArea");
const platformCards       = document.getElementById("platformCards");
const historyBody         = document.getElementById("historyBody");
const suggestionsDropdown  = document.getElementById("suggestionsDropdown");
const chatMessages        = document.getElementById("chatMessages");
const chatInput           = document.getElementById("chatInput");
const chatSendBtn         = document.getElementById("chatSendBtn");
const chatContextBadge    = document.getElementById("chatContextBadge");
const chatContextLabel    = document.getElementById("chatContextLabel");
const auditTimeline       = document.getElementById("auditTimeline");

// ─── Init ────────────────────────────────────────────────────────────────────
checkSession();
loadHistory();

// Check if returning from YouTube OAuth redirect
if (window.location.search.includes("seo_auth=success")) {
  setTimeout(() => {
    switchSection("channelSeo");
    alert("🎉 YouTube Channel Successfully Connected!");
    window.history.replaceState({}, '', '/dashboard.html');
  }, 300);
}

// ─── Session ─────────────────────────────────────────────────────────────────
async function checkSession(retry = 1) {
  const nameEl   = document.getElementById("userName");
  const roleEl   = document.getElementById("userRole");
  const avatarEl = document.getElementById("userAvatar");
  const kpiCreds = document.getElementById("kpiCreditsCount");

  // Load from local storage for instant visual rendering without waiting
  const cachedUserStr = localStorage.getItem("plexudo_user");
  if (cachedUserStr) {
    try {
      const u = JSON.parse(cachedUserStr);
      if (nameEl)   nameEl.textContent   = u.name || "Creator";
      if (roleEl)   roleEl.textContent   = u.role || "Creator";
      if (avatarEl) avatarEl.textContent = (u.name || "C").charAt(0).toUpperCase();
      if (kpiCreds && u.credits !== undefined) kpiCreds.textContent = u.credits;
    } catch (e) {}
  }

  try {
    const res = await fetch(`${API}/session`, { credentials: "include" });
    if (!res.ok) {
      if (retry > 0) {
        // Retry once after 600ms in case serverless container is warming up
        setTimeout(() => checkSession(retry - 1), 600);
        return;
      }
      localStorage.removeItem("plexudo_user");
      window.location.href = "/";
      return;
    }
    const data = await res.json();
    if (!data || !data.user) {
      localStorage.removeItem("plexudo_user");
      window.location.href = "/";
      return;
    }
    const u = data.user;
    localStorage.setItem("plexudo_user", JSON.stringify(u));
    if (nameEl)   nameEl.textContent   = u.name || "Creator";
    if (roleEl)   roleEl.textContent   = u.role || "Creator";
    if (avatarEl) avatarEl.textContent = (u.name || "C").charAt(0).toUpperCase();
    if (kpiCreds && u.credits !== undefined) kpiCreds.textContent = u.credits;
  } catch (e) {
    console.warn("Session check retry/network note:", e);
    if (retry > 0) {
      setTimeout(() => checkSession(retry - 1), 800);
    }
  }
}

async function handleLogout() {
  try {
    await fetch(`${API}/logout`, { method: "POST", credentials: "include" });
  } catch (e) {}
  localStorage.removeItem("plexudo_user");
  localStorage.removeItem("smtas_is_pro");
  window.location.href = "/";
}

document.getElementById("logoutBtn").addEventListener("click", handleLogout);

const userCard = document.getElementById("userInfoCard");
if (userCard) {
  userCard.addEventListener("click", () => {
    openProfileModal();
  });
}

// ─── Mobile Sidebar Drawer ───────────────────────────────────────────────────
function toggleMobileSidebar(forceState) {
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.getElementById("sidebarBackdrop");
  if (!sidebar || !backdrop) return;
  const isOpen = forceState !== undefined ? forceState : !sidebar.classList.contains("open");
  if (isOpen) {
    sidebar.classList.add("open");
    backdrop.classList.add("active");
    document.body.style.overflow = "hidden";
  } else {
    sidebar.classList.remove("open");
    backdrop.classList.remove("active");
    document.body.style.overflow = "";
  }
}

// ─── Sidebar Navigation ───────────────────────────────────────────────────────
const sections = ["dashboard", "comparison", "chat", "videoAnalysis", "auditUrl", "channelSeo", "history", "audit"];

document.querySelectorAll(".nav-item").forEach((item) => {
  item.addEventListener("click", () => {
    switchSection(item.dataset.section);
    if (window.innerWidth <= 900) {
      toggleMobileSidebar(false);
    }
  });
});

function switchSection(sec) {
  sections.forEach((s) => {
    const secEl = document.getElementById(`section${capitalize(s)}`);
    if (secEl) secEl.classList.remove("active");
    const nav = document.getElementById(`nav${capitalize(s)}`);
    if (nav) nav.classList.remove("active");
  });
  const targetSec = document.getElementById(`section${capitalize(sec)}`);
  if (targetSec) targetSec.classList.add("active");
  const targetNav = document.getElementById(`nav${capitalize(sec)}`);
  if (targetNav) targetNav.classList.add("active");

  // Keep topbar & hamburger button ALWAYS visible in all sections!
  const searchWrap = document.querySelector(".topbar-container .search-wrapper");
  const rightActions = document.querySelector(".topbar-actions-right");
  const sectionTitle = document.getElementById("topbarSectionTitle");
  const sectionIcon = document.getElementById("topbarSectionIcon");
  const sectionName = document.getElementById("topbarSectionName");

  const sectionMeta = {
    dashboard: { icon: "⚡", name: "Dashboard" },
    comparison: { icon: "📊", name: "Keyword Comparison" },
    chat: { icon: "✨", name: "AI Assistant" },
    auditUrl: { icon: "🔗", name: "Competitor Analysis" },
    videoAnalysis: { icon: "🎬", name: "Video Analysis" },
    channelSeo: { icon: "🎬", name: "YouTube SEO Studio" },
    history: { icon: "🕑", name: "Search History" },
    audit: { icon: "🔍", name: "Audit Trail" }
  };

  if (sec === "dashboard") {
    if (searchWrap) searchWrap.style.display = "";
    if (rightActions) rightActions.style.display = "";
    if (sectionTitle) sectionTitle.style.display = "none";
  } else {
    if (searchWrap) searchWrap.style.display = "none";
    if (rightActions) rightActions.style.display = "none";
    if (sectionTitle) {
      sectionTitle.style.display = "flex";
      const meta = sectionMeta[sec] || { icon: "📁", name: capitalize(sec) };
      if (sectionIcon) sectionIcon.textContent = meta.icon;
      if (sectionName) sectionName.textContent = meta.name;
    }
  }

  if (sec === "audit")      loadAuditLog();
  if (sec === "history")    loadHistory();
  if (sec === "comparison") loadKeywordComparison();
  if (sec === "channelSeo") loadChannelSeoVideos();
}

function capitalize(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

// ─── Status Bar ──────────────────────────────────────────────────────────────
function showStatus(msg, isError = false) {
  statusLine.textContent = msg;
  statusLine.className   = "status-bar" + (isError ? " error" : "");
}
function hideStatus() { statusLine.className = "status-bar hidden"; }

// ─── Keyword Suggestions ─────────────────────────────────────────────────────
keywordInput.addEventListener("input", () => {
  clearTimeout(suggestDebounceTimer);
  const q = keywordInput.value.trim();
  if (q.length < 2) { closeSuggestions(); return; }
  suggestDebounceTimer = setTimeout(() => fetchSuggestions(q), 300);
});

keywordInput.addEventListener("keydown", (e) => {
  const items = suggestionsDropdown.querySelectorAll(".suggestion-item");
  if (e.key === "ArrowDown") {
    e.preventDefault();
    highlightedSuggestion = Math.min(highlightedSuggestion + 1, items.length - 1);
    updateHighlight(items);
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    highlightedSuggestion = Math.max(highlightedSuggestion - 1, -1);
    updateHighlight(items);
  } else if (e.key === "Enter") {
    e.preventDefault();
    if (highlightedSuggestion >= 0 && items[highlightedSuggestion]) {
      keywordInput.value = items[highlightedSuggestion].dataset.value;
    }
    closeSuggestions();
    const keyword = keywordInput.value.trim();
    if (!keyword) { showStatus("Please enter a YouTube keyword or hashtag first.", true); return; }
    triggerAdReward("YouTube Trend Analysis", () => runAnalysis());
  } else if (e.key === "Escape") {
    closeSuggestions();
  }
});

// ─── Enter Key Event Listeners for inputs ─────────────────────────────────────
const auditUrlInput = document.getElementById("auditUrlInput");
if (auditUrlInput) {
  auditUrlInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      runChannelAudit();
    }
  });
}

const videoAnalysisInput = document.getElementById("videoAnalysisInput");
if (videoAnalysisInput) {
  videoAnalysisInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      runVideoAnalysis();
    }
  });
}

keywordInput.addEventListener("blur", () => {
  setTimeout(() => closeSuggestions(), 150);
});

function updateHighlight(items) {
  items.forEach((el, i) => el.classList.toggle("highlighted", i === highlightedSuggestion));
}

async function fetchSuggestions(q) {
  try {
    const res  = await fetch(`${API}/suggest?q=${encodeURIComponent(q)}`, { credentials: "include" });
    const data = await res.json();
    renderSuggestions(data.suggestions || []);
  } catch { closeSuggestions(); }
}

function renderSuggestions(list) {
  if (!list.length) { closeSuggestions(); return; }
  highlightedSuggestion = -1;
  suggestionsDropdown.innerHTML = list.map((s, i) => `
    <div class="suggestion-item" data-value="${escapeHtml(s)}" data-index="${i}">
      <span class="sugg-icon">🔥</span>
      <span class="sugg-text">${escapeHtml(s)}</span>
      <span class="sugg-trending">TRENDING</span>
    </div>
  `).join("");
  suggestionsDropdown.style.display = "block";
  suggestionsDropdown.classList.add("open");
  suggestionsDropdown.querySelectorAll(".suggestion-item").forEach((el) => {
    el.addEventListener("mousedown", (e) => {
      e.preventDefault();
      e.stopPropagation();
      keywordInput.value = el.dataset.value;
      closeSuggestions();
      runAnalysis();
    });
  });
}

function closeSuggestions() {
  clearTimeout(suggestDebounceTimer);
  suggestionsDropdown.classList.remove("open");
  suggestionsDropdown.style.display = "none";
  suggestionsDropdown.innerHTML = "";
  highlightedSuggestion = -1;
}

document.addEventListener("click", (e) => {
  if (!e.target.closest(".search-wrapper")) closeSuggestions();
});

// ─── Analyze Trend ───────────────────────────────────────────────────────────
analyzeBtn.addEventListener("click", (e) => {
  e.preventDefault();
  closeSuggestions();
  const keyword = keywordInput.value.trim();
  if (!keyword) { showStatus("Please enter a YouTube keyword or hashtag first.", true); return; }
  triggerAdReward("YouTube Trend Analysis", () => runAnalysis());
});


async function runAnalysis() {
  const keyword = keywordInput.value.trim();
  closeSuggestions();
  if (!keyword) { showStatus("Please enter a YouTube keyword or hashtag first.", true); return; }

  analyzeBtn.classList.add("loading");
  analyzeBtn.innerHTML = '<span class="spinner"></span> Analyzing YouTube…';
  showStatus(`Fetching live YouTube Data API v3 for "${keyword}"…`);

  try {
    const res  = await fetch(`${API}/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ keyword }),
    });
    const data = await res.json();
    if (!res.ok) { showStatus(data.error || "Something went wrong.", true); return; }

    showStatus(`✓ Analysis complete for YouTube keyword "${keyword}" — ${new Date().toLocaleTimeString()}`);
    buildChatContext(keyword, data.results);
    renderResults(data.results);
    loadHistory();
  } catch (err) {
    showStatus("Network error while contacting the backend.", true);
  } finally {
    analyzeBtn.classList.remove("loading");
    analyzeBtn.textContent = "Analyze Trend";
  }
}

// ─── Build Chat Context ───────────────────────────────────────────────────────
function buildChatContext(keyword, results) {
  const yt = results["YouTube"];
  if (yt && !yt.error) {
    chatContext = {
      keyword, platform: "YouTube",
      total_views: yt.total_views, growth_rate: yt.growth_rate,
      virality_score: yt.virality_score, stage: yt.stage, sentiment: yt.sentiment,
    };
    chatContextBadge.style.display = "flex";
    chatContextLabel.textContent   = `Context: "${keyword}" YouTube data loaded`;
  }
}

function clearChatContext() {
  chatContext = null;
  chatContextBadge.style.display = "none";
}

// ─── Render YouTube Card ──────────────────────────────────────────────────────
function destroyCharts() { activeCharts.forEach((c) => c.destroy()); activeCharts = []; }

function renderResults(results) {
  const chartOk = typeof Chart !== "undefined";
  destroyCharts();
  platformCards.innerHTML = "";
  emptyState.style.display  = "none";
  resultsArea.style.display = "block";

  const yt = results["YouTube"];
  if (!yt) return;

  if (yt.error) {
    const div = document.createElement("div");
    div.className = "panel";
    div.innerHTML = `
      <div class="panel-header"><h3>YouTube API Error</h3></div>
      <p style="color:var(--red); font-size:13.5px;">⚠ ${yt.message}</p>`;
    platformCards.appendChild(div);
    return;
  }

  const pieId      = `pie_YouTube`;
  const lineId     = `line_YouTube`;
  const stageClass = `stage-${yt.stage.toLowerCase()}`;

  const card = document.createElement("div");
  card.className = "panel";
  card.innerHTML = `
    <div class="panel-header" style="flex-wrap:wrap; gap:12px;">
      <div>
        <h3 style="font-size:18px; color:var(--text); margin:0;">YouTube Analysis: "${escapeHtml(yt.keyword)}"</h3>
        <div style="font-size:12px; color:var(--text-muted); margin-top:4px;">
          Video: <strong>${escapeHtml(yt.title || yt.keyword)}</strong>
        </div>
      </div>
      <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
        <div class="export-btn-group">
          <button class="export-btn pdf" onclick="exportReport(${yt.trend_id})">📄 Export PDF</button>
          <button class="export-btn csv" onclick="exportCSV(${yt.trend_id})">📊 Export CSV</button>
        </div>
        <span class="panel-badge youtube">▶ LIVE YOUTUBE DATA</span>
      </div>
    </div>

    <!-- 1. Top Metrics Summary Row (Modern Floating Cards) -->
    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:16px; margin-top:20px;">
      <!-- Card 1: Total Views -->
      <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:20px; padding:20px; box-shadow:0 8px 24px rgba(67,73,191,0.04); display:flex; flex-direction:column; justify-content:space-between;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size:11.5px; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:0.04em;">Total Views</span>
          <span style="font-size:12px; color:#6366f1; font-weight:800; background:#eef2ff; padding:3px 8px; border-radius:8px;">↑ ${yt.growth_rate}%</span>
        </div>
        <div style="font-size:30px; font-weight:800; color:#0f172a; margin-top:10px; line-height:1;">${formatNum(yt.total_views)}</div>
        <div style="font-size:11.5px; color:#94a3b8; margin-top:6px; font-weight:500;">Live Search Traffic</div>
      </div>

      <!-- Card 2: Growth Velocity -->
      <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:20px; padding:20px; box-shadow:0 8px 24px rgba(67,73,191,0.04); display:flex; flex-direction:column; justify-content:space-between;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size:11.5px; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:0.04em;">Growth Velocity</span>
          <span style="font-size:12px; color:#f97316; font-weight:800; background:#fff7ed; padding:3px 8px; border-radius:8px;">⚡ Velocity</span>
        </div>
        <div style="font-size:30px; font-weight:800; color:#f97316; margin-top:10px; line-height:1;">${yt.growth_rate}%</div>
        <div style="font-size:11.5px; color:#94a3b8; margin-top:6px; font-weight:500;">28-Day View Acceleration</div>
      </div>

      <!-- Card 3: Virality Index -->
      <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:20px; padding:20px; box-shadow:0 8px 24px rgba(67,73,191,0.04); display:flex; flex-direction:column; justify-content:space-between;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size:11.5px; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:0.04em;">Virality Index</span>
          <span style="font-size:12px; color:#0284c7; font-weight:800; background:#e0f2fe; padding:3px 8px; border-radius:8px;">★ Viral</span>
        </div>
        <div style="font-size:30px; font-weight:800; color:#0284c7; margin-top:10px; line-height:1;">${yt.virality_score}<span style="font-size:18px; color:#94a3b8; font-weight:600;">/100</span></div>
        <div style="font-size:11.5px; color:#94a3b8; margin-top:6px; font-weight:500;">Share & Retention Potential</div>
      </div>

      <!-- Card 4: Engagement Rate -->
      <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:20px; padding:20px; box-shadow:0 8px 24px rgba(67,73,191,0.04); display:flex; flex-direction:column; justify-content:space-between;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size:11.5px; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:0.04em;">Engagement Rate</span>
          <span style="font-size:12px; color:#10b981; font-weight:800; background:#ecfdf5; padding:3px 8px; border-radius:8px;">♥ Audience</span>
        </div>
        <div style="font-size:30px; font-weight:800; color:#10b981; margin-top:10px; line-height:1;">${yt.engagement_rate || 0}%</div>
        <div style="font-size:11.5px; color:#94a3b8; margin-top:6px; font-weight:500;">Likes & Comments / Views</div>
      </div>

      <!-- Card 5: Trend Lifecycle -->
      <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:20px; padding:20px; box-shadow:0 8px 24px rgba(67,73,191,0.04); display:flex; flex-direction:column; justify-content:space-between;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size:11.5px; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:0.04em;">Trend Stage</span>
          <span style="font-size:12px; color:#6366f1; font-weight:800; background:#f5f3ff; padding:3px 8px; border-radius:8px;">📊 Status</span>
        </div>
        <div style="margin-top:10px;">
          <span class="badge ${stageClass}" style="font-size:15px; font-weight:800; padding:6px 14px; border-radius:10px;">${yt.stage}</span>
        </div>
        <div style="font-size:11.5px; color:#94a3b8; margin-top:6px; font-weight:500;">Lifecycle Trajectory</div>
      </div>
    </div>

    <!-- 2. SEO Opportunity Score & AI Content Strategy -->
    <div style="display:grid; grid-template-columns: 1fr 1.3fr; gap:20px; margin-top:24px;">
      <!-- SEO Opportunity Meter -->
      <div style="padding:24px; background:#ffffff; border:1px solid #e2e8f0; border-radius:22px; box-shadow:0 10px 30px rgba(67,73,191,0.05); display:flex; flex-direction:column; justify-content:space-between;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size:12px; text-transform:uppercase; color:#6366f1; font-weight:800; letter-spacing:0.04em;">🎯 YouTube SEO Opportunity Score</span>
          <span class="badge" style="background:#eef2ff; color:#6366f1; border:1px solid #c7d2fe;">SEO METRIC</span>
        </div>
        <div style="margin:20px 0; display:flex; align-items:center; gap:16px;">
          <div style="width:74px; height:74px; border-radius:50%; background:conic-gradient(#6366f1 ${(yt.seo_analysis ? yt.seo_analysis.score : 75)}%, #e2e8f0 0); display:flex; align-items:center; justify-content:center; flex-shrink:0; box-shadow:0 4px 14px rgba(99,102,241,0.15);">
            <div style="width:60px; height:60px; border-radius:50%; background:#ffffff; display:flex; align-items:center; justify-content:center; font-size:16px; font-weight:900; color:#0f172a;">
              ${yt.seo_analysis ? yt.seo_analysis.score : 75}%
            </div>
          </div>
          <div>
            <div style="font-size:18px; font-weight:800; color:#0f172a;">${yt.seo_analysis ? yt.seo_analysis.rating : 'HIGH OPPORTUNITY'}</div>
            <div style="font-size:12.5px; color:#64748b; margin-top:4px;">Competition Level: <strong style="color:#6366f1;">${yt.seo_analysis ? yt.seo_analysis.competition : 'Medium'}</strong></div>
          </div>
        </div>
        <div style="font-size:12.5px; color:#64748b; line-height:1.5; background:#f8fafc; padding:12px 14px; border-radius:12px; border:1px solid #e2e8f0;">
          💡 High search demand relative to creator competition. Strongly recommended for video targeting.
        </div>
      </div>

      <!-- AI High-CTR Video Title Ideas -->
      <div style="padding:24px; background:#ffffff; border:1px solid #e2e8f0; border-radius:22px; box-shadow:0 10px 30px rgba(67,73,191,0.05);">
        <div style="font-size:12px; text-transform:uppercase; color:#64748b; font-weight:800; letter-spacing:0.04em; margin-bottom:14px; display:flex; justify-content:space-between; align-items:center;">
          <span>💡 Trending AI Creator Titles</span>
          <span style="font-size:11px; background:#eef2ff; color:#6366f1; border:1px solid #c7d2fe; font-weight:700; padding:3px 8px; border-radius:6px;">High CTR</span>
        </div>
        <div style="display:flex; flex-direction:column; gap:10px;">
          ${(yt.seo_title_ideas || []).map(title => `
            <div style="display:flex; justify-content:space-between; align-items:center; padding:10px 14px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; font-size:13px; color:#0f172a; font-weight:600; transition:all 0.15s ease;">
              <span style="flex:1; margin-right:10px; line-height:1.4;">${escapeHtml(title)}</span>
              <button onclick="copyToClipboard('${escapeHtml(title)}')" style="background:#ffffff; border:1px solid #cbd5e1; color:#6366f1; cursor:pointer; font-size:11.5px; font-weight:700; padding:4px 10px; border-radius:8px; box-shadow:0 1px 3px rgba(0,0,0,0.04); white-space:nowrap;">Copy</button>
            </div>
          `).join("")}
        </div>
      </div>
    </div>

    <!-- 3. Full-Width View Growth Velocity Line Chart (Matches Reference UI) -->
    <div style="margin-top:24px; background:#ffffff; border:1px solid #e2e8f0; border-radius:24px; padding:24px; box-shadow:0 10px 30px rgba(67,73,191,0.05);">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
        <div>
          <h4 style="font-size:14px; font-weight:800; color:#0f172a; margin:0; text-transform:uppercase; letter-spacing:0.04em;">📈 View Growth Velocity Over Time</h4>
          <div style="font-size:12px; color:#64748b; margin-top:3px;">Historical viewer acquisition and momentum curve</div>
        </div>
        <span style="background:#f8fafc; border:1px solid #e2e8f0; font-size:12px; font-weight:700; color:#475569; padding:5px 12px; border-radius:10px;">Daily Trend Series</span>
      </div>
      <div style="position:relative; width:100%; height:260px;">
        <canvas id="${lineId}"></canvas>
      </div>
    </div>

    <!-- 4. Sentiment & Audience Feedback Row (Matches Reference UI) -->
    <div style="display:grid; grid-template-columns: 280px 1fr; gap:24px; margin-top:24px; align-items:stretch;">
      <!-- Comment Sentiment Donut -->
      <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:24px; padding:24px; box-shadow:0 10px 30px rgba(67,73,191,0.05); display:flex; flex-direction:column; justify-content:space-between; text-align:center;">
        <div>
          <h4 style="font-size:13px; font-weight:800; color:#0f172a; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:4px;">Comment Sentiment</h4>
          <div style="font-size:12px; color:#64748b;">Audience sentiment breakdown</div>
        </div>
        <div style="position:relative; width:100%; height:190px; margin:10px 0;">
          <canvas id="${pieId}"></canvas>
        </div>
        <div style="font-size:12px; font-weight:700; color:#6366f1; background:#eef2ff; padding:6px 12px; border-radius:10px;">
          Dominant: <strong style="text-transform:capitalize;">${yt.sentiment.dominant_sentiment}</strong>
        </div>
      </div>

      <!-- Top Audience Comments & Reactions (Clean Light Card) -->
      <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:24px; padding:24px; box-shadow:0 10px 30px rgba(67,73,191,0.05); display:flex; flex-direction:column; justify-content:space-between;">
        <div>
          <div style="font-size:12px; text-transform:uppercase; color:#64748b; font-weight:800; letter-spacing:0.04em; margin-bottom:14px; display:flex; justify-content:space-between; align-items:center;">
            <span>💬 Top Audience Comments &amp; Reactions</span>
            <span style="font-size:12px; color:#059669; font-weight:700; background:#ecfdf5; border:1px solid #a7f3d0; padding:3px 8px; border-radius:6px;">NLP Verified</span>
          </div>
          <div style="display:flex; flex-direction:column; gap:10px;">
            ${(yt.sentiment.sample_comments || []).map(sc => `
              <div style="display:flex; align-items:flex-start; gap:10px; font-size:13px; line-height:1.45; background:#f8fafc; border:1px solid #e2e8f0; border-radius:14px; padding:12px 16px;">
                <span class="badge ${sc.sentiment === 'positive' ? 'positive' : sc.sentiment === 'negative' ? 'negative' : 'neutral'}" style="margin-top:2px; text-transform:capitalize; flex-shrink:0;">
                  ${sc.sentiment}
                </span>
                <span style="color:#1e293b; font-weight:500;">"${escapeHtml(sc.text)}"</span>
              </div>
            `).join("")}
          </div>
        </div>
        <div style="margin-top:16px; display:flex; gap:12px; font-size:12.5px; border-top:1px solid #f1f5f9; padding-top:14px; flex-wrap:wrap;">
          <span style="background:#ecfdf5; color:#047857; font-weight:700; padding:4px 10px; border-radius:8px;">Positive: <strong>${yt.sentiment.positive_score}%</strong></span>
          <span style="background:#fff1f2; color:#e11d48; font-weight:700; padding:4px 10px; border-radius:8px;">Negative: <strong>${yt.sentiment.negative_score}%</strong></span>
          <span style="background:#eff6ff; color:#1d4ed8; font-weight:700; padding:4px 10px; border-radius:8px;">Neutral: <strong>${yt.sentiment.neutral_score}%</strong></span>
        </div>
      </div>
    </div>`;

  platformCards.appendChild(card);

  // 5. Copyable YouTube Tags Card
  const tagsList = yt.youtube_tags || [];
  if (tagsList.length > 0) {
    const tagsCard = document.createElement("div");
    tagsCard.className = "panel";
    tagsCard.style.marginTop = "20px";
    const tagsString = tagsList.join(", ");
    const chipsHtml  = tagsList.map(tag => `
      <span class="toggle-chip" style="background:#f8fafc; border-color:#e2e8f0; color:#334155; font-size:12.5px; padding:6px 14px; cursor:default;">
        🏷️ ${escapeHtml(tag)}
      </span>
    `).join("");
    const hashtagsHtml = (yt.youtube_hashtags || []).map(ht => `
      <span style="color:var(--cyan); font-weight:700; font-size:13px;">${escapeHtml(ht)}</span>
    `).join("  ");

    tagsCard.innerHTML = `
      <div class="panel-header" style="align-items:center;">
        <div>
          <h3 style="font-size:15px; margin:0;">🏷️ Copyable YouTube Upload Tags &amp; Hashtags</h3>
          <div style="font-size:12px; color:var(--text-muted); margin-top:2px;">Formatted for 1-click copy into YouTube Studio tag box</div>
        </div>
        <button class="export-btn default" onclick="copyToClipboard('${escapeHtml(tagsString)}')" style="background:var(--primary); color:#ffffff; border:none; padding:9px 18px;">
          📋 Copy All Tags
        </button>
      </div>
      <div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:14px;">${chipsHtml}</div>
      <div style="margin-top:14px; padding-top:12px; border-top:1px solid #f1f5f9; display:flex; gap:12px; align-items:center; flex-wrap:wrap;">
        <span style="font-size:12px; font-weight:700; color:var(--text-muted); text-transform:uppercase;">Top Hashtags:</span>
        ${hashtagsHtml}
      </div>
    `;
    platformCards.appendChild(tagsCard);
  }

  // 6. Related Trending Keywords Panel
  const relatedList = yt.related_keywords || [];
  if (relatedList.length > 0) {
    const relatedCard = document.createElement("div");
    relatedCard.className = "panel";
    relatedCard.style.marginTop = "20px";
    const relChipsHtml = relatedList.map(kw => `
      <button class="toggle-chip" style="cursor:pointer; background:rgba(2,132,199,0.08); border-color:rgba(2,132,199,0.2); color:var(--cyan); font-size:12.5px; padding:8px 16px;" onclick="searchRelatedKeyword('${escapeHtml(kw)}')">
        🔥 ${escapeHtml(kw)}
      </button>
    `).join("");
    relatedCard.innerHTML = `
      <div class="panel-header">
        <h3 style="font-size:15px; margin:0;">🔥 Suggested Trending Keywords for "${escapeHtml(yt.keyword)}"</h3>
        <span class="panel-badge youtube">Click any tag to analyze instantly</span>
      </div>
      <div style="display:flex; flex-wrap:wrap; gap:10px; margin-top:14px;">${relChipsHtml}</div>
    `;
    platformCards.appendChild(relatedCard);
  }

  if (!chartOk) return;

  // Line Chart — views over time (Smooth Spline Curve with Gradient Fill)
  const lineCanvas = document.getElementById(lineId);
  const lineCtx = lineCanvas.getContext("2d");
  
  // Create beautiful gradient fill matching reference image
  const lineGradient = lineCtx.createLinearGradient(0, 0, 0, 240);
  lineGradient.addColorStop(0, "rgba(99, 102, 241, 0.28)");
  lineGradient.addColorStop(1, "rgba(99, 102, 241, 0.0)");

  activeCharts.push(new Chart(lineCtx, {
    type: "line",
    data: {
      labels: yt.daily_metrics.map((d) => d.date),
      datasets: [{
        label: "Views",
        data: yt.daily_metrics.map((d) => d.views),
        borderColor: "#6366f1",
        backgroundColor: lineGradient,
        fill: true,
        tension: 0.45,
        borderWidth: 3,
        pointRadius: 5,
        pointHoverRadius: 8,
        pointBackgroundColor: "#ffffff",
        pointBorderColor: "#6366f1",
        pointBorderWidth: 3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#1e1b4b",
          titleColor: "#ffffff",
          bodyColor: "#c7d2fe",
          borderColor: "#4338ca",
          borderWidth: 1,
          padding: 12,
          cornerRadius: 10,
          displayColors: false
        }
      },
      scales: {
        x: {
          ticks: { color: "#64748b", font: { size: 11, weight: "600" } },
          grid: { color: "#f1f5f9", drawBorder: false }
        },
        y: {
          ticks: { color: "#64748b", font: { size: 11, weight: "600" }, callback: (v) => formatNum(v) },
          grid: { color: "#f1f5f9", drawBorder: false }
        },
      },
    },
  }));

  // Sentiment Doughnut Chart (Matching Reference Donut UI)
  const pieCtx = document.getElementById(pieId).getContext("2d");
  activeCharts.push(new Chart(pieCtx, {
    type: "doughnut",
    data: {
      labels: ["Positive", "Negative", "Neutral"],
      datasets: [{
        data: [yt.sentiment.positive_score, yt.sentiment.negative_score, yt.sentiment.neutral_score],
        backgroundColor: ["#6366f1", "#f97316", "#38bdf8"],
        borderWidth: 0,
        hoverOffset: 8,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "72%",
      plugins: {
        legend: {
          position: "bottom",
          labels: { color: "#0f172a", font: { size: 11.5, weight: "700" }, padding: 12, usePointStyle: true }
        },
      },
    },
  }));

  // Hide empty placeholder
  emptyState.style.display = "none";
}

// ─── Channel Audit ────────────────────────────────────────────────────────────
function runChannelAudit() {
  const input = document.getElementById("auditUrlInput");
  const identifier = input ? input.value.trim() : "";
  if (!identifier) {
    const statusEl = document.getElementById("auditUrlStatus");
    if (statusEl) {
      statusEl.textContent = "Please enter a channel URL or @handle first.";
      statusEl.className = "status-bar error";
    }
    return;
  }
  triggerAdReward("Competitor Channel Audit", () => executeChannelAudit());
}

const requestChannelAudit = runChannelAudit;

async function executeChannelAudit() {
  const input     = document.getElementById("auditUrlInput");
  const statusEl  = document.getElementById("auditUrlStatus");
  const emptyEl   = document.getElementById("auditUrlEmpty");
  const resultsEl = document.getElementById("auditUrlResults");
  const btn       = document.getElementById("auditUrlBtn");

  const identifier = input.value.trim();
  if (!identifier) return;

  btn.textContent  = "⏳ Auditing…";
  btn.disabled     = true;
  statusEl.textContent = `Fetching live YouTube channel data for "${identifier}"…`;
  statusEl.className   = "status-bar";
  emptyEl.style.display   = "none";
  resultsEl.style.display = "none";

  try {
    const res  = await fetch(`${API}/audit-channel`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ identifier }),
    });
    const data = await res.json();

    if (!res.ok || data.error) {
      statusEl.textContent = `⚠ ${data.message || data.error || "Audit failed."}`;
      statusEl.className   = "status-bar error";
      emptyEl.style.display = "block";
      return;
    }

    statusEl.textContent = `✓ Audit complete for "${data.channel_name}" — ${new Date().toLocaleTimeString()}`;
    statusEl.className   = "status-bar";

    currentAuditData = data;
    renderChannelAudit(data, "28d");

  } catch (err) {
    statusEl.textContent = "Network error while contacting the backend.";
    statusEl.className   = "status-bar error";
  } finally {
    btn.textContent = "🔍 Audit Channel";
    btn.disabled    = false;
  }
}

function renderChannelAudit(data, tf = "28d") {
  const resultsEl = document.getElementById("auditUrlResults");
  resultsEl.style.display = "block";

  // Pick correct growth series
  const growthSeries = tf === "7d" ? data.growth_7d : tf === "3m" ? data.growth_3m : data.growth_28d;

  // Earnings format
  const earnMin = formatNum(data.earn_min_monthly);
  const earnMax = formatNum(data.earn_max_monthly);

  // Avatar HTML
  const avatarHtml = data.avatar_url
    ? `<img src="${data.avatar_url}" alt="${escapeHtml(data.channel_name)}" style="width:72px; height:72px; border-radius:50%; object-fit:cover; border:3px solid #38bdf8;">`
    : `<div style="width:72px; height:72px; border-radius:50%; background:#38bdf8; color:#0f172a; display:flex; align-items:center; justify-content:center; font-size:28px; font-weight:900;">${(data.channel_name || "C").charAt(0)}</div>`;

  // Country flag (basic mapping)
  const flagMap = { US:"🇺🇸", GB:"🇬🇧", PK:"🇵🇰", IN:"🇮🇳", CA:"🇨🇦", AU:"🇦🇺", DE:"🇩🇪", FR:"🇫🇷", BR:"🇧🇷", JP:"🇯🇵", KR:"🇰🇷", MX:"🇲🇽" };
  const flag = flagMap[data.country] || "🌍";

  // Top Videos Table
  const topVideosHtml = (data.top_videos || []).map(v => `
    <tr onclick="window.open('https://youtube.com/watch?v=${v.video_id}', '_blank')" style="cursor:pointer;">
      <td>
        <div style="display:flex; align-items:center; gap:10px;">
          ${v.thumbnail ? `<img src="${v.thumbnail}" alt="" style="width:80px; height:45px; border-radius:6px; object-fit:cover; flex-shrink:0;">` : '<div style="width:80px; height:45px; background:#e2e8f0; border-radius:6px; flex-shrink:0;"></div>'}
          <div>
            <div style="font-weight:600; font-size:13px; line-height:1.4; max-width:240px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(v.title)}</div>
            <div style="font-size:11px; color:var(--text-muted); margin-top:2px;">${v.is_short ? '🩳 Short' : '🎬 Long Video'}</div>
          </div>
        </div>
      </td>
      <td><strong>${formatNum(v.views)}</strong></td>
      <td style="color:var(--green);">${formatNum(v.vph)}/hr</td>
    </tr>
  `).join("");

  // Content ring charts (SVG donut rings)
  const longformUploadPct = data.longform_pct || 0;
  const shortsUploadPct   = data.shorts_pct   || 0;
  const longformViewsPct  = data.longform_views_pct || 0;
  const shortsViewsPct    = data.shorts_views_pct   || 0;

  resultsEl.innerHTML = `
    <!-- Hero Channel Header -->
    <div class="panel" style="margin-bottom:20px;">
      <div style="display:flex; align-items:center; gap:20px; flex-wrap:wrap;">
        ${avatarHtml}
        <div style="flex:1;">
          <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
            <h2 style="font-size:22px; font-weight:900; margin:0; color:var(--text);">${escapeHtml(data.channel_name)}</h2>
            <span style="background:#38bdf8; color:#0f172a; font-size:10px; font-weight:800; padding:3px 8px; border-radius:6px; text-transform:uppercase;">✓ YouTube</span>
          </div>
          <div style="font-size:13px; color:var(--text-muted); margin-top:6px; display:flex; gap:16px; flex-wrap:wrap;">
            <span>${flag} ${data.country || "Global"}</span>
            <span>📅 ${data.age_years} yrs old</span>
            <span>🗓 Since ${data.published_at}</span>
          </div>
          <div style="font-size:12.5px; color:var(--text-muted); margin-top:6px; line-height:1.5; max-width:500px;">${escapeHtml(data.description || "")}</div>
        </div>
        <!-- Rank & Earnings badges -->
        <div style="display:flex; flex-direction:column; gap:10px; align-items:flex-end;">
          <div style="background:#0f172a; color:#ffffff; padding:14px 18px; border-radius:16px; text-align:center; min-width:160px;">
            <div style="font-size:10px; color:#94a3b8; text-transform:uppercase; font-weight:700; letter-spacing:0.06em;">Country Rank</div>
            <div style="font-size:20px; font-weight:900; color:#38bdf8; margin-top:4px;">${data.country_rank}</div>
          </div>
          <div style="background:#0f172a; color:#ffffff; padding:14px 18px; border-radius:16px; text-align:center; min-width:160px;">
            <div style="font-size:10px; color:#94a3b8; text-transform:uppercase; font-weight:700; letter-spacing:0.06em;">Worldwide Rank</div>
            <div style="font-size:20px; font-weight:900; color:#34d399; margin-top:4px;">${data.worldwide_rank}</div>
          </div>
        </div>
      </div>

      <!-- Key Stats Row -->
      <div class="metric-row" style="margin-top:20px; grid-template-columns: repeat(5, 1fr);">
        <div class="metric-box">
          <div class="val">${formatNum(data.subscriber_count)}</div>
          <div class="lbl">Subscribers</div>
        </div>
        <div class="metric-box">
          <div class="val">${formatNum(data.total_views)}</div>
          <div class="lbl">Total Views</div>
        </div>
        <div class="metric-box">
          <div class="val">${formatNum(data.video_count)}</div>
          <div class="lbl">Total Videos</div>
        </div>
        <div class="metric-box">
          <div class="val" style="color:#34d399;">$${earnMin}</div>
          <div class="lbl">Est. Min/Month</div>
        </div>
        <div class="metric-box">
          <div class="val" style="color:#f97316;">$${earnMax}</div>
          <div class="lbl">Est. Max/Month</div>
        </div>
      </div>
    </div>

    <!-- VidIQ Ring Charts: Videos vs Shorts Breakdown -->
    <div class="panel" style="margin-bottom:20px;">
      <div class="panel-header">
        <h3>📊 Content Breakdown — Long Videos vs Shorts</h3>
        <span class="panel-badge youtube">▶ VidIQ Style</span>
      </div>

      <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px; margin-top:20px;">

        <!-- Uploads Ring -->
        <div style="background:#f8fafc; border:1px solid var(--border); border-radius:20px; padding:24px; text-align:center;">
          <div style="font-size:12px; font-weight:700; text-transform:uppercase; color:var(--text-muted); letter-spacing:0.06em; margin-bottom:16px;">Uploads</div>
          <div style="position:relative; width:140px; height:140px; margin:0 auto;">
            <svg viewBox="0 0 140 140" style="width:100%; height:100%; transform:rotate(-90deg);">
              <circle cx="70" cy="70" r="55" fill="none" stroke="#f1f5f9" stroke-width="18"/>
              <circle cx="70" cy="70" r="55" fill="none" stroke="#f97316" stroke-width="18"
                stroke-dasharray="${Math.round(2 * Math.PI * 55 * shortsUploadPct / 100)} ${Math.round(2 * Math.PI * 55)}"
                stroke-linecap="round"/>
              <circle cx="70" cy="70" r="55" fill="none" stroke="#2563eb" stroke-width="18"
                stroke-dasharray="${Math.round(2 * Math.PI * 55 * longformUploadPct / 100)} ${Math.round(2 * Math.PI * 55)}"
                stroke-dashoffset="${-Math.round(2 * Math.PI * 55 * shortsUploadPct / 100)}"
                stroke-linecap="round"/>
            </svg>
            <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); text-align:center;">
              <div style="font-size:22px; font-weight:900; color:#2563eb; line-height:1;">${data.longform_count}</div>
              <div style="font-size:10px; color:var(--text-muted); font-weight:600;">Long Videos</div>
            </div>
          </div>
          <div style="display:flex; justify-content:center; gap:20px; margin-top:16px; font-size:12.5px; font-weight:600;">
            <span><span style="display:inline-block; width:10px; height:10px; background:#2563eb; border-radius:50%; margin-right:4px;"></span>Long: ${longformUploadPct}%</span>
            <span><span style="display:inline-block; width:10px; height:10px; background:#f97316; border-radius:50%; margin-right:4px;"></span>Shorts: ${shortsUploadPct}%</span>
          </div>
        </div>

        <!-- Views Ring -->
        <div style="background:#f8fafc; border:1px solid var(--border); border-radius:20px; padding:24px; text-align:center;">
          <div style="font-size:12px; font-weight:700; text-transform:uppercase; color:var(--text-muted); letter-spacing:0.06em; margin-bottom:16px;">Views</div>
          <div style="position:relative; width:140px; height:140px; margin:0 auto;">
            <svg viewBox="0 0 140 140" style="width:100%; height:100%; transform:rotate(-90deg);">
              <circle cx="70" cy="70" r="55" fill="none" stroke="#f1f5f9" stroke-width="18"/>
              <circle cx="70" cy="70" r="55" fill="none" stroke="#f97316" stroke-width="18"
                stroke-dasharray="${Math.round(2 * Math.PI * 55 * shortsViewsPct / 100)} ${Math.round(2 * Math.PI * 55)}"
                stroke-linecap="round"/>
              <circle cx="70" cy="70" r="55" fill="none" stroke="#2563eb" stroke-width="18"
                stroke-dasharray="${Math.round(2 * Math.PI * 55 * longformViewsPct / 100)} ${Math.round(2 * Math.PI * 55)}"
                stroke-dashoffset="${-Math.round(2 * Math.PI * 55 * shortsViewsPct / 100)}"
                stroke-linecap="round"/>
            </svg>
            <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); text-align:center;">
              <div style="font-size:22px; font-weight:900; color:#2563eb; line-height:1;">${formatNum(data.longform_views)}</div>
              <div style="font-size:10px; color:var(--text-muted); font-weight:600;">Long Views</div>
            </div>
          </div>
          <div style="display:flex; justify-content:center; gap:20px; margin-top:16px; font-size:12.5px; font-weight:600;">
            <span><span style="display:inline-block; width:10px; height:10px; background:#2563eb; border-radius:50%; margin-right:4px;"></span>Long: ${longformViewsPct}%</span>
            <span><span style="display:inline-block; width:10px; height:10px; background:#f97316; border-radius:50%; margin-right:4px;"></span>Shorts: ${shortsViewsPct}%</span>
          </div>
        </div>

      </div>
    </div>

    <!-- 28-Day / 7D / 3M Growth Chart -->
    <div class="panel" style="margin-bottom:20px;">
      <div class="panel-header">
        <h3>📈 Historical View Growth Trend</h3>
        <div style="display:flex; gap:6px;">
          <button id="tf7d" onclick="switchChannelTimeframe('7d')"
            style="padding:6px 14px; border-radius:10px; border:1.5px solid ${tf === '7d' ? '#0284c7' : '#e2e8f0'}; background:${tf === '7d' ? '#e0f2fe' : '#f8fafc'}; color:${tf === '7d' ? '#0284c7' : '#64748b'}; font-size:12px; font-weight:700; cursor:pointer;">7D</button>
          <button id="tf28d" onclick="switchChannelTimeframe('28d')"
            style="padding:6px 14px; border-radius:10px; border:1.5px solid ${tf === '28d' ? '#0284c7' : '#e2e8f0'}; background:${tf === '28d' ? '#e0f2fe' : '#f8fafc'}; color:${tf === '28d' ? '#0284c7' : '#64748b'}; font-size:12px; font-weight:700; cursor:pointer;">28D</button>
          <button id="tf3m" onclick="switchChannelTimeframe('3m')"
            style="padding:6px 14px; border-radius:10px; border:1.5px solid ${tf === '3m' ? '#0284c7' : '#e2e8f0'}; background:${tf === '3m' ? '#e0f2fe' : '#f8fafc'}; color:${tf === '3m' ? '#0284c7' : '#64748b'}; font-size:12px; font-weight:700; cursor:pointer;">3M</button>
        </div>
      </div>
      <div style="position:relative; height:220px; margin-top:16px;">
        <canvas id="channelGrowthChart"></canvas>
      </div>
    </div>

    <!-- Top Videos Table -->
    <div class="panel">
      <div class="panel-header">
        <h3>🎬 Top Popular Videos</h3>
        <span class="panel-badge youtube">Click row to open on YouTube</span>
      </div>
      <div class="history-table-wrap" style="margin-top:12px;">
        <table class="history-table">
          <thead>
            <tr>
              <th>Video</th>
              <th>Views</th>
              <th>VPH Velocity</th>
            </tr>
          </thead>
          <tbody>
            ${topVideosHtml || '<tr><td colspan="3" style="text-align:center; padding:24px; color:var(--text-muted);">No videos found</td></tr>'}
          </tbody>
        </table>
      </div>
    </div>
  `;

  // Render channel growth line chart
  if (typeof Chart !== "undefined" && growthSeries && growthSeries.length) {
    if (channelGrowthChart) { channelGrowthChart.destroy(); channelGrowthChart = null; }
    const ctx = document.getElementById("channelGrowthChart").getContext("2d");
    channelGrowthChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: growthSeries.map(d => d.date),
        datasets: [{
          label: "Daily Views",
          data: growthSeries.map(d => d.views),
          borderColor: "#2563eb",
          backgroundColor: "rgba(37, 99, 235, 0.1)",
          fill: true, tension: 0.4, borderWidth: 2.5,
          pointRadius: growthSeries.length > 30 ? 0 : 3,
          pointBackgroundColor: "#2563eb",
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { backgroundColor: "#1e293b", borderColor: "#e2e8f0", borderWidth: 1 } },
        scales: {
          x: { ticks: { color: "#64748b", font: { size: 10 }, maxTicksLimit: 10 }, grid: { color: "#f1f5f9" } },
          y: { ticks: { color: "#64748b", font: { size: 10 } }, grid: { color: "#f1f5f9" } },
        },
      },
    });
  }
}

// ─── Switch Channel Timeframe ─────────────────────────────────────────────────
function switchChannelTimeframe(tf) {
  if (!currentAuditData) return;
  renderChannelAudit(currentAuditData, tf);
}

// ─── Keyword Trends Comparison ───────────────────────────────────────────────
async function loadKeywordComparison() {
  const emptyEl   = document.getElementById("comparisonEmpty");
  const chartArea = document.getElementById("comparisonChartArea");
  const tableBody = document.getElementById("comparisonTableBody");

  try {
    const res  = await fetch(`${API}/compare-keywords`, { credentials: "include" });
    const data = await res.json();

    if (!data.comparison || data.comparison.length < 2) {
      emptyEl.style.display   = "block";
      chartArea.style.display = "none";
      return;
    }

    emptyEl.style.display   = "none";
    chartArea.style.display = "block";

    const comp = data.comparison;

    if (viralityCompareChartInst) { viralityCompareChartInst.destroy(); }
    const ctx = document.getElementById("viralityCompareChart").getContext("2d");
    viralityCompareChartInst = new Chart(ctx, {
      type: "bar",
      data: {
        labels: comp.map(c => c.keyword),
        datasets: [
          {
            label: "Virality Index",
            data: comp.map(c => c.virality_score),
            backgroundColor: "rgba(2, 132, 199, 0.7)", borderColor: "#0284c7",
            borderWidth: 1.5, borderRadius: 8,
          },
          {
            label: "Growth Velocity (%)",
            data: comp.map(c => c.growth_rate),
            backgroundColor: "rgba(16, 185, 129, 0.75)", borderColor: "#10b981",
            borderWidth: 1.5, borderRadius: 8,
          }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: "#0f172a", font: { size: 12, weight: "600" } } } },
        scales: {
          x: { ticks: { color: "#64748b" }, grid: { color: "#f1f5f9" } },
          y: { ticks: { color: "#64748b" }, grid: { color: "#f1f5f9" } },
        }
      }
    });

    tableBody.innerHTML = comp.map(c => `
      <tr>
        <td><strong>${escapeHtml(c.keyword)}</strong></td>
        <td>${formatNum(c.total_views)}</td>
        <td>${c.growth_rate}%</td>
        <td><strong style="color:var(--cyan);">${c.virality_score}/100</strong></td>
        <td><span class="badge ${c.stage === 'Rising' ? 'positive' : 'neutral'}">${c.stage}</span></td>
        <td><span class="badge ${c.dominant_sentiment === 'positive' ? 'positive' : 'negative'}">${c.dominant_sentiment}</span></td>
      </tr>
    `).join("");

  } catch (e) {
    emptyEl.style.display   = "block";
    chartArea.style.display = "none";
  }
}

// ─── History ─────────────────────────────────────────────────────────────────
async function loadHistory() {
  try {
    const res  = await fetch(`${API}/trends`, { credentials: "include" });
    if (!res.ok) return;
    const data = await res.json();
    historyBody.innerHTML = "";
    if (!data.trends.length) {
      historyBody.innerHTML = `<tr><td colspan="8" class="text-muted" style="padding:24px; text-align:center;">No searches yet</td></tr>`;
      return;
    }
    data.trends.forEach((t) => {
      const row = document.createElement("tr");
      const sentClass = t.dominant_sentiment === "positive" ? "positive" :
                        t.dominant_sentiment === "negative" ? "negative" : "neutral";
      row.innerHTML = `
        <td><strong>${escapeHtml(t.keyword)}</strong></td>
        <td><span class="badge youtube">YouTube</span></td>
        <td>${formatNum(t.total_views)}</td>
        <td>${t.growth_rate}%</td>
        <td><strong style="color:var(--cyan);">${t.virality_score}</strong></td>
        <td><span class="badge ${sentClass}">${t.dominant_sentiment}</span></td>
        <td class="text-muted">${t.timestamp}</td>
        <td>
          <div class="export-btn-group">
            <button class="export-btn pdf" onclick="exportReport(${t.trend_id})" title="Download PDF">PDF</button>
            <button class="export-btn csv" onclick="exportCSV(${t.trend_id})"    title="Download CSV">CSV</button>
          </div>
        </td>`;
      historyBody.appendChild(row);
    });
  } catch (e) { /* silent */ }
}

// ─── Exports ─────────────────────────────────────────────────────────────────
function exportReport(trendId) {
  triggerAdReward("PDF Analytics Report", () => {
    window.open(`${API}/report/${trendId}`, "_blank");
  });
}

function exportCSV(trendId) {
  const link = document.createElement("a");
  link.href  = `${API}/export-csv/${trendId}`;
  link.target = "_blank";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// ─── AI Chat (Groq Llama 3.3 70B) ────────────────────────────────────────────
function handleChatSubmit() {
  const message = chatInput.value.trim();
  if (!message) return;
  triggerAdReward("AI Trend Strategist Consultation", () => sendChatMessage());
}

chatSendBtn.addEventListener("click", handleChatSubmit);
chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    handleChatSubmit();
  }
});
chatInput.addEventListener("input", () => {
  chatInput.style.height = "auto";
  chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + "px";
});

async function sendChatMessage() {
  const message = chatInput.value.trim();
  if (!message) return;
  appendChatMessage("user", message);
  chatInput.value = "";
  chatInput.style.height = "auto";

  const typingId = appendTyping();
  chatSendBtn.disabled = true;

  try {
    const res  = await fetch(`${API}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ message, context: chatContext }),
    });
    const data = await res.json();
    removeTyping(typingId);
    appendChatMessage("ai", data.reply || "⚠ No response received.");
  } catch (err) {
    removeTyping(typingId);
    appendChatMessage("ai", "❌ Could not reach the backend server.");
  } finally {
    chatSendBtn.disabled = false;
  }
}

const AI_AVATAR_SVG   = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/><path d="M5 3v4M3 5h4M19 17v4M17 19h4"/></svg>`;
const USER_AVATAR_SVG = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`;

function appendChatMessage(role, text) {
  const wrap = document.createElement("div");
  wrap.className = `chat-message ${role}`;
  const avatarSvg = role === "ai" ? AI_AVATAR_SVG : USER_AVATAR_SVG;
  const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  wrap.innerHTML = `
    <div class="chat-avatar">${avatarSvg}</div>
    <div>
      <div class="chat-bubble">${formatChatText(text)}</div>
      <div class="chat-timestamp">${time}</div>
    </div>`;
  chatMessages.appendChild(wrap);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return wrap;
}

function appendTyping() {
  const id   = "typing_" + Date.now();
  const wrap = document.createElement("div");
  wrap.className = "chat-message ai";
  wrap.id        = id;
  wrap.innerHTML = `
    <div class="chat-avatar">${AI_AVATAR_SVG}</div>
    <div>
      <div class="chat-bubble">
        <div class="typing-dots"><span></span><span></span><span></span></div>
      </div>
    </div>`;
  chatMessages.appendChild(wrap);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return id;
}

function removeTyping(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function formatChatText(text) {
  return escapeHtml(text)
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/```(.*?)\n([\s\S]*?)```/g, "<pre><code>$2</code></pre>")
    .replace(/\n/g, "<br>");
}

// ─── Audit Log ────────────────────────────────────────────────────────────────
async function loadAuditLog() {
  auditTimeline.innerHTML = `<div class="text-muted" style="padding:20px; text-align:center;">Loading…</div>`;
  try {
    const res  = await fetch(`${API}/audit-log`, { credentials: "include" });
    const data = await res.json();

    if (!data.logs || !data.logs.length) {
      auditTimeline.innerHTML = `<div class="text-muted" style="padding:20px; text-align:center;">No activity recorded yet.</div>`;
      return;
    }

    auditTimeline.innerHTML = data.logs.map((log) => {
      const actionColors = {
        LOGIN: "var(--green)", LOGOUT: "var(--text-muted)", REGISTER: "var(--yellow)",
        SEARCH: "var(--cyan)", EXPORT_PDF: "var(--red)", EXPORT_CSV: "var(--green)",
        CHAT: "var(--purple)", LOGIN_FAILED: "var(--red)", LOGIN_LOCKED: "var(--red)",
        AUDIT_CHANNEL: "#f97316",
      };
      const col = actionColors[log.action] || "var(--text-muted)";
      return `
        <div class="audit-entry">
          <div class="audit-dot ${log.action}" style="background:${col};"></div>
          <div class="audit-body">
            <div class="audit-action ${log.action}">${log.action.replace("_", " ")}</div>
            <div class="audit-details">${escapeHtml(log.details) || "—"}</div>
            <div class="audit-meta">
              <span>🕐 ${log.timestamp}</span>
              <span>🌐 ${log.ip_address}</span>
            </div>
          </div>
        </div>`;
    }).join("");
  } catch (e) {
    auditTimeline.innerHTML = `<div class="text-muted" style="padding:20px; text-align:center;">Failed to load audit log.</div>`;
  }
}

function refreshAuditLog() { loadAuditLog(); }

// ─── Helpers ─────────────────────────────────────────────────────────────────
function searchRelatedKeyword(kw) {
  if (!kw) return;
  keywordInput.value = kw;
  window.scrollTo({ top: 0, behavior: "smooth" });
  runAnalysis();
}

function copyToClipboard(text) {
  if (!text) return;
  navigator.clipboard.writeText(text).then(() => {
    showStatus(`✓ Copied to clipboard: "${text.length > 30 ? text.substring(0, 30) + '...' : text}"`);
    setTimeout(hideStatus, 3000);
  }).catch(() => {
    showStatus("Could not copy text.", true);
  });
}

function formatNum(n) {
  n = Number(n) || 0;
  if (n >= 1_000_000_000) return (n / 1_000_000_000).toFixed(1) + "B";
  if (n >= 1_000_000)     return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000)         return (n / 1_000).toFixed(1) + "K";
  return String(n);
}

function escapeHtml(str) {
  if (typeof str !== "string") return str;
  const d = document.createElement("div");
  d.textContent = str;
  return d.innerHTML;
}

// ─── Video Analysis ───────────────────────────────────────────────────────────
function runVideoAnalysis() {
  const input = document.getElementById("videoAnalysisInput");
  const url = input ? input.value.trim() : "";
  if (!url) {
    const statusEl = document.getElementById("videoAnalysisStatus");
    if (statusEl) {
      statusEl.textContent = "⚠ Please paste a YouTube video URL first.";
      statusEl.className   = "status-bar error";
    }
    return;
  }
  triggerAdReward("YouTube Video SEO & Tags Analysis", () => executeVideoAnalysis());
}

const requestVideoAnalysis = runVideoAnalysis;

async function executeVideoAnalysis() {
  const input   = document.getElementById("videoAnalysisInput");
  const statusEl = document.getElementById("videoAnalysisStatus");
  const emptyEl  = document.getElementById("videoAnalysisEmpty");
  const resultsEl = document.getElementById("videoAnalysisResults");
  const btn      = document.getElementById("videoAnalysisBtn");

  const url = input.value.trim();
  if (!url) return;

  btn.disabled = true;
  btn.textContent = "⏳ Analyzing…";
  statusEl.textContent = `⏳ Fetching video data…`;
  statusEl.className   = "status-bar";
  emptyEl.style.display  = "none";
  resultsEl.style.display = "none";

  try {
    const res  = await fetch(`${API}/video-analysis`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ url }),
    });
    const data = await res.json();

    if (data.error || data.message) {
      statusEl.textContent = `⚠ ${data.message || "Analysis failed."}`;
      statusEl.className   = "status-bar error";
      emptyEl.style.display = "";
      return;
    }

    statusEl.textContent = `✓ Analysis complete for "${data.title}" — ${new Date().toLocaleTimeString()}`;
    statusEl.className   = "status-bar";
    renderVideoAnalysis(data);
    resultsEl.style.display = "";

  } catch (e) {
    statusEl.textContent = `⚠ Network error: ${e.message}`;
    statusEl.className   = "status-bar error";
    emptyEl.style.display = "";
  } finally {
    btn.disabled = false;
    btn.textContent = "🎬 Analyze Video";
  }
}

function renderVideoAnalysis(d) {
  const resultsEl = document.getElementById("videoAnalysisResults");
  const sent = d.sentiment || {};
  const pos  = sent.positive_score || 0;
  const neg  = sent.negative_score || 0;
  const neu  = sent.neutral_score  || 0;
  const dom  = (sent.dominant_sentiment || "neutral");
  const sentColor = dom === "positive" ? "#059669" : dom === "negative" ? "#e11d48" : "#0284c7";
  const sentEmoji = dom === "positive" ? "😊" : dom === "negative" ? "😠" : "😐";

  const viralityScore = Math.round(d.virality_score || 0);
  const viralityColor = viralityScore >= 70 ? "#059669" : viralityScore >= 40 ? "#d97706" : "#e11d48";
  const stageLabel = d.stage || "—";

  const tagsBadges = (d.tags || []).map(t =>
    `<span style="display:inline-block; background:var(--purple-dim); color:var(--purple); padding:4px 10px; border-radius:20px; font-size:12px; font-weight:600; margin:3px;">#${escapeHtml(t)}</span>`
  ).join("") || "<span style='color:var(--text-muted);font-size:13px;'>No tags available</span>";

  const topComments = (d.top_comments || []).slice(0, 6).map(c => `
    <div style="background:var(--bg-panel-2); border-radius:12px; padding:12px 14px; margin-bottom:10px; border:1px solid var(--border);">
      <div style="font-size:12px; font-weight:700; color:var(--cyan); margin-bottom:4px;">👤 ${escapeHtml(c.author || "Anonymous")}</div>
      <div style="font-size:13px; color:var(--text); line-height:1.5;">${escapeHtml((c.text || "").substring(0, 200))}</div>
      ${c.likes > 0 ? `<div style="font-size:11px; color:var(--text-muted); margin-top:6px;">👍 ${c.likes} likes</div>` : ""}
    </div>`).join("") || "<div style='color:var(--text-muted);font-size:13px;padding:12px 0;'>No comments available.</div>";

  const sampleComments = (sent.sample_comments || []).map(sc => {
    const col = sc.sentiment === "positive" ? "#059669" : sc.sentiment === "negative" ? "#e11d48" : "#0284c7";
    const em  = sc.sentiment === "positive" ? "😊" : sc.sentiment === "negative" ? "😠" : "😐";
    return `<div style="background:var(--bg-panel-2); border-radius:12px; padding:12px 14px; margin-bottom:8px; border-left:3px solid ${col};">
      <span style="font-size:11px;font-weight:700;color:${col};text-transform:uppercase;">${em} ${sc.sentiment}</span>
      <div style="font-size:13px;color:var(--text);margin-top:4px;line-height:1.5;">${escapeHtml((sc.text||"").substring(0,200))}</div>
    </div>`;
  }).join("");

  resultsEl.innerHTML = `
    <!-- Video Hero Card -->
    <div class="panel" style="margin-bottom:20px; overflow:hidden;">
      <div style="display:flex; gap:20px; flex-wrap:wrap; align-items:flex-start;">
        ${d.thumbnail ? `<img src="${d.thumbnail}" alt="thumbnail" style="width:280px; height:158px; object-fit:cover; border-radius:14px; flex-shrink:0; box-shadow:0 8px 24px rgba(0,0,0,0.1);">` : ""}
        <div style="flex:1; min-width:200px;">
          <div style="display:flex; gap:8px; align-items:center; margin-bottom:8px;">
            <span style="background:#ff0000; color:#fff; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700;">▶ YouTube</span>
            ${d.is_short ? `<span style="background:#f3e8ff; color:#7c3aed; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700;">📱 Short</span>` : `<span style="background:#e0f2fe; color:#0284c7; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700;">🎥 Long-form</span>`}
          </div>
          <h2 style="font-size:17px; font-weight:700; color:var(--text); margin-bottom:10px; line-height:1.4;">${escapeHtml(d.title)}</h2>
          <a href="https://www.youtube.com/channel/${d.channel_id}" target="_blank"
             style="font-size:13px; color:var(--cyan); font-weight:600; text-decoration:none;">
            📺 ${escapeHtml(d.channel_name)}
          </a>
          <div style="display:flex; gap:16px; flex-wrap:wrap; margin-top:12px; font-size:12px; color:var(--text-muted);">
            <span>📅 ${d.upload_date}</span>
            <span>⏱ ${d.duration}</span>
            <span>👥 ${formatNum(d.subscriber_count)} subscribers</span>
          </div>
          <div style="margin-top:12px;">
            <a href="https://www.youtube.com/watch?v=${d.video_id}" target="_blank"
               style="display:inline-block; padding:8px 18px; background:#ff0000; color:#fff; border-radius:10px; font-size:13px; font-weight:700; text-decoration:none;">
              ▶ Watch on YouTube
            </a>
          </div>
        </div>
      </div>
    </div>

    <!-- Stats Cards Row -->
    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(140px, 1fr)); gap:14px; margin-bottom:20px;">
      <div class="panel" style="text-align:center; padding:20px 12px;">
        <div style="font-size:24px; font-weight:800; color:var(--cyan);">${formatNum(d.view_count)}</div>
        <div style="font-size:11px; color:var(--text-muted); margin-top:4px; font-weight:600;">👁 VIEWS</div>
      </div>
      <div class="panel" style="text-align:center; padding:20px 12px;">
        <div style="font-size:24px; font-weight:800; color:#e11d48;">${formatNum(d.like_count)}</div>
        <div style="font-size:11px; color:var(--text-muted); margin-top:4px; font-weight:600;">❤️ LIKES</div>
      </div>
      <div class="panel" style="text-align:center; padding:20px 12px;">
        <div style="font-size:24px; font-weight:800; color:#059669;">${formatNum(d.comment_count)}</div>
        <div style="font-size:11px; color:var(--text-muted); margin-top:4px; font-weight:600;">💬 COMMENTS</div>
      </div>
      <div class="panel" style="text-align:center; padding:20px 12px;">
        <div style="font-size:24px; font-weight:800; color:var(--purple);">${d.engagement_rate}%</div>
        <div style="font-size:11px; color:var(--text-muted); margin-top:4px; font-weight:600;">📈 ENGAGEMENT</div>
      </div>
      <div class="panel" style="text-align:center; padding:20px 12px;">
        <div style="font-size:24px; font-weight:800; color:${viralityColor};">${viralityScore}</div>
        <div style="font-size:11px; color:var(--text-muted); margin-top:4px; font-weight:600;">🔥 VIRALITY</div>
      </div>
      <div class="panel" style="text-align:center; padding:20px 12px;">
        <div style="font-size:18px; font-weight:800; color:var(--yellow);">${stageLabel}</div>
        <div style="font-size:11px; color:var(--text-muted); margin-top:4px; font-weight:600;">📊 TREND STAGE</div>
      </div>
    </div>

    <!-- Sentiment + Description Row -->
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:20px; flex-wrap:wrap;">
      <!-- Sentiment -->
      <div class="panel">
        <div class="panel-header"><h3>💬 Comment Sentiment</h3></div>
        <div style="display:flex; gap:12px; margin:16px 0; flex-wrap:wrap;">
          <div style="flex:1; background:#d1fae5; border-radius:12px; padding:14px; text-align:center;">
            <div style="font-size:20px; font-weight:800; color:#059669;">${pos.toFixed(1)}%</div>
            <div style="font-size:11px; color:#059669; font-weight:700; margin-top:4px;">😊 Positive</div>
          </div>
          <div style="flex:1; background:#ffe4e6; border-radius:12px; padding:14px; text-align:center;">
            <div style="font-size:20px; font-weight:800; color:#e11d48;">${neg.toFixed(1)}%</div>
            <div style="font-size:11px; color:#e11d48; font-weight:700; margin-top:4px;">😠 Negative</div>
          </div>
          <div style="flex:1; background:#e0f2fe; border-radius:12px; padding:14px; text-align:center;">
            <div style="font-size:20px; font-weight:800; color:#0284c7;">${neu.toFixed(1)}%</div>
            <div style="font-size:11px; color:#0284c7; font-weight:700; margin-top:4px;">😐 Neutral</div>
          </div>
        </div>
        <div style="background:var(--bg-panel-2); border-radius:10px; padding:10px 14px; border-left:3px solid ${sentColor};">
          <span style="font-size:12px; font-weight:700; color:${sentColor};">${sentEmoji} Dominant: ${dom.toUpperCase()}</span>
        </div>
        ${sampleComments ? `<div style="margin-top:14px;">${sampleComments}</div>` : ""}
      </div>

      <!-- Description -->
      <div class="panel">
        <div class="panel-header"><h3>📝 Video Description</h3></div>
        <div style="font-size:13px; color:var(--text); line-height:1.7; margin-top:12px; white-space:pre-wrap;">${escapeHtml(d.description || "No description available.")}</div>
        ${d.tags && d.tags.length ? `
        <div style="margin-top:16px;">
          <div style="font-size:11px; font-weight:700; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.06em; margin-bottom:8px;">🏷 Tags</div>
          <div>${tagsBadges}</div>
        </div>` : ""}
      </div>
    </div>

    <!-- Top Comments -->
    <div class="panel" style="margin-bottom:20px;">
      <div class="panel-header"><h3>💬 Top Comments</h3></div>
      <div style="margin-top:14px;">${topComments}</div>
    </div>

    <!-- Growth Chart -->
    <div class="panel">
      <div class="panel-header">
        <h3>📈 Estimated View Growth</h3>
        <span class="panel-badge youtube">10-Day Trend</span>
      </div>
      <div style="position:relative; height:200px; width:100%; margin-top:16px;">
        <canvas id="videoGrowthChart"></canvas>
      </div>
    </div>
  `;

  // Render growth chart
  const ctx = document.getElementById("videoGrowthChart");
  if (ctx && d.daily_metrics && d.daily_metrics.length) {
    const labels = d.daily_metrics.map(m => m.date);
    const views  = d.daily_metrics.map(m => m.views);
    new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [{
          label: "Views",
          data: views,
          borderColor: "#7c3aed",
          backgroundColor: "rgba(124,58,237,0.08)",
          borderWidth: 2.5,
          pointRadius: 4,
          pointBackgroundColor: "#7c3aed",
          fill: true,
          tension: 0.4,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false }, ticks: { font: { size: 11 }, maxTicksLimit: 7 } },
          y: { grid: { color: "rgba(0,0,0,0.04)" }, ticks: { font: { size: 11 }, callback: v => formatNum(v) } }
        }
      }
    });
  }
}

// ==============================================================================
// 🎯 MY CHANNEL SEO STUDIO (VIDIQ-STYLE SUITE)
// ==============================================================================
let seoState = {
  videoId: "",
  title: "",
  description: "",
  tags: [],
  categoryId: "20",
  thumbnail: "",
  activeTab: "seo"
};

function connectYouTubeChannel() {
  window.location.href = "/api/channel-seo/auth/google";
}

function toggleYouTubeConnection(isConnected) {
  if (isConnected) {
    if (confirm("Do you want to disconnect your YouTube Channel?")) {
      disconnectYouTubeChannel();
    }
  } else {
    connectYouTubeChannel();
  }
}

async function disconnectYouTubeChannel() {
  try {
    await fetch("/api/channel-seo/auth/disconnect", { method: "POST", credentials: "include" });
    alert("✓ YouTube Channel Disconnected");
    loadChannelSeoVideos();
  } catch (e) {
    console.error("Disconnect error:", e);
  }
}

async function loadChannelSeoVideos() {
  const select = document.getElementById("channelVideoSelect");
  const connectCard = document.getElementById("seoConnectCard");
  const selectorPanel = document.getElementById("seoVideoSelectorPanel");
  const studioArea = document.getElementById("seoStudioArea");

  try {
    const res = await fetch("/api/channel-seo/videos", { credentials: "include" });
    const data = await res.json();

    const btn = document.getElementById("btnConnectYouTubeChannel");
    if (btn) {
      btn.innerHTML = data.connected ? "🔌 Disconnect Channel" : "▶ Connect YouTube Channel";
      btn.style.background = data.connected ? "#475569" : "#dc2626";
      btn.onclick = () => toggleYouTubeConnection(data.connected);
    }

    const kpiTitle = document.getElementById("kpiChannelTitle");
    const kpiSub = document.getElementById("kpiChannelSub");
    if (kpiTitle && kpiSub) {
      if (data.connected && data.channel) {
        kpiTitle.textContent = data.channel.title || "Connected Channel";
        kpiSub.textContent = `✓ ${data.videos ? data.videos.length : 0} Videos Loaded`;
      } else if (data.connected) {
        kpiTitle.textContent = "✓ YouTube Connected";
        kpiSub.textContent = `${data.videos ? data.videos.length : 0} Videos Synced`;
      } else {
        kpiTitle.textContent = "Not Connected";
        kpiSub.textContent = "Click to Connect Channel";
      }
    }

    if (connectCard) connectCard.style.display = "none";
    if (selectorPanel) selectorPanel.style.display = "block";
    if (studioArea) studioArea.style.display = "block";

    const cardsContainer = document.getElementById("seoVideoCardsContainer");
    const cardsGrid = document.getElementById("seoVideoCardsGrid");
    const countEl = document.getElementById("seoVideoCount");

    if (data.videos && data.videos.length > 0) {
      if (select) {
        select.innerHTML = `<option value="">-- Choose a video to analyze --</option>` +
          data.videos.map(v => `<option value="${v.videoId}">${v.title}</option>`).join('');
      }
      if (countEl) countEl.textContent = data.videos.length;
      if (cardsContainer) cardsContainer.style.display = "block";
      if (cardsGrid) {
        cardsGrid.innerHTML = data.videos.map(v => `
          <div class="seo-video-card" id="card-${v.videoId}" onclick="loadSelectedVideoSeo('${v.videoId}')"
            style="background:#f8fafc; border:1.5px solid #e2e8f0; border-radius:14px; overflow:hidden; cursor:pointer; transition:all 0.2s ease; display:flex; flex-direction:column; box-shadow:0 2px 8px rgba(0,0,0,0.04);"
            onmouseover="this.style.transform='translateY(-2px)'; this.style.borderColor='#3b82f6';"
            onmouseout="if(seoState.videoId !== '${v.videoId}') { this.style.transform='none'; this.style.borderColor='#e2e8f0'; }">
            <div style="position:relative; width:100%; aspect-ratio:16/9; background:#0f172a; overflow:hidden;">
              <img src="${v.thumbnail || 'https://i.ytimg.com/vi/' + v.videoId + '/hqdefault.jpg'}" alt="" style="width:100%; height:100%; object-fit:cover;">
              <div style="position:absolute; inset:0; background:linear-gradient(to top, rgba(0,0,0,0.6) 0%, transparent 50%);"></div>
              <span style="position:absolute; bottom:6px; right:6px; background:rgba(0,0,0,0.75); color:#ffffff; font-size:10px; font-weight:700; padding:2px 6px; border-radius:4px;">▶ Video</span>
            </div>
            <div style="padding:12px; display:flex; flex-direction:column; justify-content:space-between; flex:1; gap:10px;">
              <div style="font-size:12.5px; font-weight:700; color:#0f172a; line-height:1.35; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;" title="${v.title}">
                ${v.title}
              </div>
              <button style="width:100%; padding:7px 10px; background:#eff6ff; color:#2563eb; border:1px solid #bfdbfe; border-radius:8px; font-size:11.5px; font-weight:700; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:4px;">
                <span>⚡</span> Optimize Video
              </button>
            </div>
          </div>
        `).join('');
      }
    } else {
      if (select) {
        select.innerHTML = `<option value="">-- No uploaded videos (Paste URL above or connect channel) --</option>`;
      }
      if (cardsContainer) cardsContainer.style.display = "none";
    }
  } catch (e) {
    console.error("Error loading videos:", e);
  }
}

function loadCustomSeoVideo() {
  const input = document.getElementById("customSeoVideoInput");
  let val = input ? input.value.trim() : "";
  if (!val) {
    alert("Please enter a YouTube video URL or ID");
    return;
  }
  let videoId = val;
  if (val.includes("v=")) {
    videoId = val.split("v=")[1].split("&")[0];
  } else if (val.includes("youtu.be/")) {
    videoId = val.split("youtu.be/")[1].split("?")[0];
  } else if (val.includes("/shorts/")) {
    videoId = val.split("/shorts/")[1].split("?")[0];
  }
  loadSelectedVideoSeo(videoId);
}

async function loadSelectedVideoSeo(videoId) {
  if (!videoId) return;
  seoState.videoId = videoId;
  const studio = document.getElementById("seoStudioArea");
  if (studio) studio.style.display = "block";

  try {
    const res = await fetch(`/api/channel-seo/videos/${videoId}`, { credentials: "include" });
    const data = await res.json();

    seoState.title = data.title || "";
    seoState.description = data.description || "";
    seoState.tags = (data.tags || []).map(t => typeof t === 'string' ? { name: t, volume: Math.floor(Math.random() * 40) + 40 } : t);
    seoState.categoryId = data.categoryId || "20";
    seoState.thumbnail = data.thumbnail || "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg";

    document.getElementById("inputVideoTitle").value = seoState.title;
    document.getElementById("inputVideoDescription").value = seoState.description;

    document.getElementById("previewTitle").textContent = seoState.title;
    document.getElementById("previewDesc").textContent = seoState.description;
    document.getElementById("previewThumb").src = seoState.thumbnail;

    const select = document.getElementById("channelVideoSelect");
    if (select) select.value = videoId;

    document.querySelectorAll(".seo-video-card").forEach(c => {
      c.style.borderColor = "#e2e8f0";
      c.style.background = "#f8fafc";
    });
    const activeCard = document.getElementById(`card-${videoId}`);
    if (activeCard) {
      activeCard.style.borderColor = "#2563eb";
      activeCard.style.background = "#eff6ff";
    }

    renderCurrentTags();
    recalculateSeoLive();
  } catch (e) {
    console.error("Error loading video details:", e);
  }
}

function switchSeoTab(tabName) {
  seoState.activeTab = tabName;
  ['title', 'seo', 'preview'].forEach(t => {
    const btn = document.getElementById(`tabBtn${capitalize(t)}`);
    const content = document.getElementById(`seoTab${capitalize(t)}`);
    if (btn) btn.style.background = (t === tabName) ? "#1f2937" : "transparent";
    if (btn) btn.style.color = (t === tabName) ? "#ffffff" : "#9ca3af";
    if (content) content.style.display = (t === tabName) ? "block" : "none";
  });
}

function renderCurrentTags() {
  const wrap = document.getElementById("currentTagsWrap");
  const countEl = document.getElementById("currentTagCount");
  if (countEl) countEl.textContent = seoState.tags.length;
  if (!wrap) return;

  wrap.innerHTML = seoState.tags.map((t, idx) => {
    const name = typeof t === 'string' ? t : t.name;
    const vol = typeof t === 'object' && t.volume ? t.volume : Math.floor(Math.random() * 35) + 45;
    const volColor = vol >= 65 ? "#eab308" : vol >= 55 ? "#eab308" : "#ef4444";
    return `
      <div style="display:inline-flex; align-items:center; gap:6px; background:#1e293b; color:#ffffff; padding:6px 10px; border-radius:8px; font-size:13px; border:1px solid #334155;">
        <span style="color:${volColor}; font-weight:800; font-size:12px;">${vol}</span>
        <span>${name}</span>
        <button onclick="removeTagFromSeo(${idx})" style="background:none; border:none; color:#94a3b8; cursor:pointer; font-size:12px;">✕</button>
      </div>
    `;
  }).join('');
}

function addTagToSeo(tagItem) {
  const tagName = (typeof tagItem === 'string' ? tagItem : tagItem.name).trim();
  if (!tagName) return;

  if (seoState.tags.some(t => (typeof t === 'string' ? t : t.name).toLowerCase() === tagName.toLowerCase())) {
    return;
  }

  const tagObj = typeof tagItem === 'object' ? tagItem : { name: tagName, volume: Math.floor(Math.random() * 35) + 50 };
  seoState.tags.push(tagObj);
  renderCurrentTags();
  recalculateSeoLive();
}

function removeTagFromSeo(idx) {
  seoState.tags.splice(idx, 1);
  renderCurrentTags();
  recalculateSeoLive();
}

function promptAddCustomTag() {
  const t = prompt("Enter new tag name:");
  if (t) addTagToSeo(t);
}

async function recalculateSeoLive() {
  seoState.title = document.getElementById("inputVideoTitle").value;
  seoState.description = document.getElementById("inputVideoDescription").value;

  const tagNames = seoState.tags.map(t => typeof t === 'string' ? t : t.name);

  try {
    const res = await fetch("/api/channel-seo/seo/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: seoState.title,
        description: seoState.description,
        tags: tagNames
      })
    });
    const data = await res.json();
    const b = data.actionableItems.breakdown;
    const total = data.actionableItems.total;

    document.getElementById("overallSeoScoreText").textContent = `${total}/50`;
    document.getElementById("scoreTagCount").textContent = `${b.tagCount.score}/10`;
    document.getElementById("barTagCount").style.width = `${(b.tagCount.score/10)*100}%`;

    document.getElementById("scoreTagVolume").textContent = `${b.tagVolume.score}/10`;
    document.getElementById("barTagVolume").style.width = `${(b.tagVolume.score/10)*100}%`;

    document.getElementById("scoreKwTitle").textContent = `${b.keywordsInTitle.score}/10`;
    document.getElementById("barKwTitle").style.width = `${(b.keywordsInTitle.score/10)*100}%`;

    document.getElementById("scoreKwDesc").textContent = `${b.keywordsInDescription.score}/10`;
    document.getElementById("barKwDesc").style.width = `${(b.keywordsInDescription.score/10)*100}%`;

    document.getElementById("scoreOverlap").textContent = `${b.sameKeywordOverlap.score}/10`;
    document.getElementById("barOverlap").style.width = `${(b.sameKeywordOverlap.score/10)*100}%`;
  } catch (e) {
    console.error("Error recalculating SEO:", e);
  }
}

function generateAiTitles() {
  triggerAdReward("AI Viral Titles Generator", () => executeGenerateAiTitles());
}

async function executeGenerateAiTitles() {
  const btn = document.getElementById("btnGenerateAiTitles");
  if (btn) btn.innerHTML = "⌛ Generating 3 AI Titles...";

  const topicInput = document.getElementById("inputVideoTopic");
  const topicVal = topicInput ? topicInput.value.trim() : "";

  try {
    const res = await fetch("/api/channel-seo/ai/suggest-titles", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: seoState.title,
        topic: topicVal || seoState.title,
        description: seoState.description,
        tags: seoState.tags.map(t => typeof t === 'string' ? t : t.name)
      })
    });
    const data = await res.json();
    const box = document.getElementById("aiTitleSuggestionsBox");
    const list = document.getElementById("aiTitlesList");
    if (box && list && data.titles) {
      box.style.display = "block";
      list.innerHTML = data.titles.map(t => {
        const title = t.title || '';
        const strategy = t.strategy || 'Search-Focused';
        const reason = t.reason || 'Aligned with search intent and viewer value.';
        const safeTitle = title.replace(/'/g, "\\'");
        return `
          <div style="background:#ffffff; border:1px solid #e2e8f0; padding:14px; border-radius:12px; box-shadow:0 2px 6px rgba(15,23,42,0.03); display:flex; flex-direction:column; gap:8px;">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:10px;">
              <span style="font-size:14px; font-weight:700; color:#0f172a; flex:1; line-height:1.4;">${title}</span>
              <span style="background:#e0e7ff; color:#4338ca; border:1px solid #c7d2fe; font-weight:700; font-size:11px; padding:3px 8px; border-radius:6px; white-space:nowrap;">${strategy}</span>
            </div>
            <div style="font-size:12px; color:#64748b; line-height:1.4;">
              <strong style="color:#334155;">Why it works:</strong> ${reason}
            </div>
            <button onclick="applyAiTitle('${safeTitle}')"
              style="padding:6px 14px; background:#4f46e5; color:#ffffff; border:none; border-radius:8px; font-weight:700; font-size:12px; cursor:pointer; align-self:flex-start; margin-top:2px;">
              + Apply Title
            </button>
          </div>
        `;
      }).join('');
    }
  } catch (e) {
    console.error("AI Title Error:", e);
  } finally {
    if (btn) btn.innerHTML = "✨ Generate 3 AI Title Suggestions";
  }
}

function applyAiTitle(newTitle) {
  seoState.title = newTitle;
  document.getElementById("inputVideoTitle").value = newTitle;
  document.getElementById("previewTitle").textContent = newTitle;
  recalculateSeoLive();
  alert("✅ Applied AI Title!");
}

function generateAiDescription() {
  triggerAdReward("AI Description Generator", () => executeGenerateAiDescription());
}

async function executeGenerateAiDescription() {
  const btn = document.getElementById("btnGenerateAiDesc");
  if (btn) btn.innerHTML = "⌛ Generating...";

  try {
    const res = await fetch("/api/channel-seo/ai/generate-description", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: seoState.title,
        tags: seoState.tags.map(t => typeof t === 'string' ? t : t.name)
      })
    });
    const data = await res.json();
    if (data.description) {
      document.getElementById("inputVideoDescription").value = data.description;
      document.getElementById("previewDesc").textContent = data.description;
      recalculateSeoLive();
    }
  } catch (e) {
    console.error("AI Description Error:", e);
  } finally {
    if (btn) btn.innerHTML = "✨ AI Generate";
  }
}

function generateAiTags() {
  triggerAdReward("AI YouTube Tags Generator", () => executeGenerateAiTags());
}

async function executeGenerateAiTags() {
  const btn = document.getElementById("btnGenerateAiTags");
  if (btn) btn.innerHTML = "⌛ Generating...";

  try {
    const res = await fetch("/api/channel-seo/ai/suggest-tags", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: seoState.title, description: seoState.description })
    });
    const data = await res.json();
    const wrap = document.getElementById("recommendedTagsWrap");
    if (wrap && data.tags) {
      wrap.innerHTML = data.tags.map(t => {
        const name = typeof t === 'string' ? t : (t.name || '');
        const tier = typeof t === 'object' && t.relevance_tier ? t.relevance_tier : 'Relevant';
        const tierBg = tier === 'YouTube Search' ? '#ecfdf5' : '#f1f5f9';
        const tierColor = tier === 'YouTube Search' ? '#059669' : '#475569';
        const jsonStr = JSON.stringify({ name, relevance_tier: tier }).replace(/"/g, '&quot;');
        return `
          <button onclick="addTagToSeo(${jsonStr})"
            style="display:inline-flex; align-items:center; gap:6px; background:#ffffff; color:#0f172a; padding:6px 12px; border-radius:8px; font-size:13px; border:1px solid #e2e8f0; cursor:pointer; box-shadow:0 1px 3px rgba(0,0,0,0.03); transition:all 0.15s;">
            <span style="background:${tierBg}; color:${tierColor}; font-weight:700; font-size:10px; padding:2px 6px; border-radius:4px; text-transform:uppercase;">${tier}</span>
            <span style="font-weight:600;">${name}</span>
            <span style="color:#4f46e5; font-weight:800; margin-left:4px;">+</span>
          </button>
        `;
      }).join('');
    }
  } catch (e) {
    console.error("AI Tags Error:", e);
  } finally {
    if (btn) btn.innerHTML = "✨ Generate";
  }
}

async function runFindTags() {
  const input = document.getElementById("findTagsInput");
  const keyword = input ? input.value : "";
  if (!keyword) return;

  try {
    const res = await fetch("/api/channel-seo/ai/find-tags", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keyword })
    });
    const data = await res.json();
    const wrap = document.getElementById("findTagsResults");
    if (wrap && data.tags) {
      wrap.innerHTML = data.tags.map(t => {
        const name = typeof t === 'string' ? t : (t.name || '');
        const tier = typeof t === 'object' && t.relevance_tier ? t.relevance_tier : 'Search Term';
        const tierBg = tier === 'YouTube Search' ? '#ecfdf5' : '#f1f5f9';
        const tierColor = tier === 'YouTube Search' ? '#059669' : '#475569';
        const jsonStr = JSON.stringify({ name, relevance_tier: tier }).replace(/"/g, '&quot;');
        return `
          <button onclick="addTagToSeo(${jsonStr})"
            style="display:inline-flex; align-items:center; gap:6px; background:#ffffff; color:#0f172a; padding:6px 12px; border-radius:8px; font-size:13px; border:1px solid #e2e8f0; cursor:pointer; box-shadow:0 1px 3px rgba(0,0,0,0.03); transition:all 0.15s;">
            <span style="background:${tierBg}; color:${tierColor}; font-weight:700; font-size:10px; padding:2px 6px; border-radius:4px; text-transform:uppercase;">${tier}</span>
            <span style="font-weight:600;">${name}</span>
            <span style="color:#4f46e5; font-weight:800; margin-left:4px;">+</span>
          </button>
        `;
      }).join('');
    }
  } catch (e) {
    console.error("Find Tags Error:", e);
  }
}

async function saveChangesToYouTube() {
  if (!seoState.videoId) {
    alert("Please select a video first!");
    return;
  }

  const btn = document.getElementById("btnSaveToYouTube");
  if (btn) btn.innerHTML = "⌛ Syncing Changes to YouTube...";

  try {
    const res = await fetch(`/api/channel-seo/videos/${seoState.videoId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: seoState.title,
        description: seoState.description,
        tags: seoState.tags.map(t => typeof t === 'string' ? t : t.name),
        categoryId: seoState.categoryId
      })
    });
    const data = await res.json();
    if (data.success) {
      alert("✅ Successfully updated live video on YouTube!");
    } else {
      alert("❌ " + (data.error || "Failed to update video"));
    }
  } catch (e) {
    alert("❌ Error updating video on YouTube: " + e.message);
  } finally {
    if (btn) btn.innerHTML = "💾 Save & Sync Changes to YouTube";
  }
}

// ─── Ad Reward & 100% Free Mode ──────────────────────────────────────────────
let adRewardCallback = null;
let adRewardTimer    = null;

function triggerAdReward(featureName, callback) {
  adRewardCallback = callback;
  
  const modal = document.getElementById("adRewardModal");
  const featNameEl = document.getElementById("adRewardFeatureName");
  const timerTextEl = document.getElementById("adTimerText");
  const timerBarEl = document.getElementById("adTimerBar");
  
  if (featNameEl) featNameEl.textContent = `Unlocking ${featureName || "Feature"}…`;
  if (timerTextEl) timerTextEl.textContent = "⏳ Unlocking in 4s...";
  if (timerBarEl) timerBarEl.style.width = "0%";
  if (modal) modal.style.display = "flex";
  
  if (adRewardTimer) clearInterval(adRewardTimer);
  const totalMs = 3500;
  const startTime = Date.now();
  
  adRewardTimer = setInterval(() => {
    const elapsed = Date.now() - startTime;
    const remaining = Math.max(0, Math.ceil((totalMs - elapsed) / 1000));
    const progress = Math.min(100, (elapsed / totalMs) * 100);
    
    if (timerTextEl) timerTextEl.textContent = `⏳ Unlocking in ${remaining}s...`;
    if (timerBarEl) timerBarEl.style.width = `${progress}%`;
    
    if (elapsed >= totalMs) {
      clearInterval(adRewardTimer);
      adRewardTimer = null;
      completeRewardAd();
    }
  }, 100);
}

function completeRewardAd() {
  if (adRewardTimer) {
    clearInterval(adRewardTimer);
    adRewardTimer = null;
  }
  const modal = document.getElementById("adRewardModal");
  if (modal) modal.style.display = "none";
  
  if (typeof adRewardCallback === "function") {
    const cb = adRewardCallback;
    adRewardCallback = null;
    cb();
  }
}

function instantUnlockViaSponsor() {
  window.open("https://bibleearthquake.com/h9fgjabvra?key=afd27586e5e065ccedc5e1e9314adfc7", "_blank");
  completeRewardAd();
}

function getProStatus() {
  return true; // All features are 100% Free!
}

function renderProState() {
  // YouTube SEO Studio
  const paywallEl = document.getElementById("seoProPaywall");
  const studioEl  = document.getElementById("seoProStudio");
  if (paywallEl) paywallEl.style.display = "none";
  if (studioEl)  studioEl.style.display  = "block";

  // AI Assistant Chat
  const aiPaywallEl = document.getElementById("aiChatProPaywall");
  const aiStudioEl  = document.getElementById("aiChatProStudio");
  if (aiPaywallEl) aiPaywallEl.style.display = "none";
  if (aiStudioEl)  aiStudioEl.style.display  = "block";
}

// Initialize Free state on load
renderProState();

let currentProfileUser = null;

async function openProfileModal() {
  const modal = document.getElementById("profileModal");
  if (!modal) return;
  try {
    const res = await fetch(`${API}/session`, { credentials: "include" });
    const data = await res.json();
    if (data && data.user) {
      currentProfileUser = data.user;
      const u = data.user;
      const nameEl = document.getElementById("modalUserName");
      const emailEl = document.getElementById("modalUserEmail");
      const avatarEl = document.getElementById("modalUserAvatar");
      const creditsEl = document.getElementById("modalCreditBalance");
      const verifyBadge = document.getElementById("modalVerifyBadge");
      const unverifiedBox = document.getElementById("modalUnverifiedBox");

      if (nameEl) nameEl.textContent = u.name || "Creator";
      if (emailEl) emailEl.textContent = u.email || "user@example.com";
      if (avatarEl) {
        if (u.avatar_url) {
          avatarEl.innerHTML = `<img src="${u.avatar_url}" style="width:100%; height:100%; border-radius:14px; object-fit:cover;">`;
        } else {
          avatarEl.textContent = (u.name || "U").charAt(0).toUpperCase();
        }
      }
      if (creditsEl) creditsEl.textContent = `${u.credits !== undefined ? u.credits : 3} / 3 Free`;

      if (verifyBadge && unverifiedBox) {
        if (u.email_verified === false) {
          verifyBadge.innerHTML = `<span style="background:#fef3c7; color:#d97706; border:1px solid #fde68a; font-size:11px; font-weight:800; padding:3px 8px; border-radius:6px; white-space:nowrap;">⚠️ Unverified</span>`;
          unverifiedBox.style.display = "flex";
        } else {
          verifyBadge.innerHTML = `<span style="background:#ecfdf5; color:#059669; border:1px solid #a7f3d0; font-size:11px; font-weight:800; padding:3px 8px; border-radius:6px; white-space:nowrap;">✓ Verified</span>`;
          unverifiedBox.style.display = "none";
        }
      }

      // Channel sync info
      const channelTitleEl = document.getElementById("modalChannelTitle");
      const channelStatusEl = document.getElementById("modalChannelStatus");
      const channelActionEl = document.getElementById("modalChannelAction");
      if (channelTitleEl && channelStatusEl && channelActionEl) {
        if (isYouTubeConnected) {
          channelTitleEl.textContent = channelProfile.title || "YouTube Channel Connected";
          channelStatusEl.textContent = `Sync Active (${channelProfile.subscriberCount || 'Live'} subscribers)`;
          channelActionEl.innerHTML = `
            <button onclick="handleDisconnectYouTube()" style="padding:7px 14px; background:#fee2e2; border:1px solid #fca5a5; color:#dc2626; border-radius:8px; font-size:12px; font-weight:700; cursor:pointer; white-space:nowrap; transition:all 0.15s;">
              Disconnect
            </button>
          `;
        } else {
          channelTitleEl.textContent = "YouTube Data API v3";
          channelStatusEl.textContent = "Connect to sync channel videos & tags";
          channelActionEl.innerHTML = `
            <button onclick="connectYouTubeChannel()" style="padding:7px 14px; background:#4f46e5; color:#ffffff; border:none; border-radius:8px; font-size:12px; font-weight:700; cursor:pointer; white-space:nowrap; transition:all 0.15s;">
              Connect YouTube
            </button>
          `;
        }
      }
    }
  } catch (e) {
    console.error("Error loading profile:", e);
  }
  modal.style.display = "flex";
}

function closeProfileModal() {
  const modal = document.getElementById("profileModal");
  if (modal) modal.style.display = "none";
}

function togglePasswordVisibility(inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  if (input.type === "password") {
    input.type = "text";
    btn.textContent = "🔒";
  } else {
    input.type = "password";
    btn.textContent = "👁️";
  }
}

async function handlePasswordChange(e) {
  e.preventDefault();
  const oldPassword = document.getElementById("modalOldPassword").value;
  const newPassword = document.getElementById("modalNewPassword").value;
  const confirmPassword = document.getElementById("modalConfirmPassword").value;
  const feedback = document.getElementById("passwordFeedback");
  if (!feedback) return;

  if (newPassword !== confirmPassword) {
    feedback.style.display = "block";
    feedback.style.background = "#fef2f2";
    feedback.style.color = "#dc2626";
    feedback.textContent = "❌ New passwords do not match.";
    return;
  }

  if (newPassword.length < 8) {
    feedback.style.display = "block";
    feedback.style.background = "#fef2f2";
    feedback.style.color = "#dc2626";
    feedback.textContent = "❌ Password must be at least 8 characters.";
    return;
  }

  feedback.style.display = "block";
  feedback.style.background = "#eef2ff";
  feedback.style.color = "#4f46e5";
  feedback.textContent = "Updating password...";

  try {
    const res = await fetch(`${API}/change-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword })
    });
    const data = await res.json();
    if (res.ok) {
      feedback.style.background = "#ecfdf5";
      feedback.style.color = "#059669";
      feedback.textContent = "✓ Password updated successfully!";
      document.getElementById("modalOldPassword").value = "";
      document.getElementById("modalNewPassword").value = "";
      document.getElementById("modalConfirmPassword").value = "";
      setTimeout(() => { feedback.style.display = "none"; }, 3500);
    } else {
      feedback.style.background = "#fef2f2";
      feedback.style.color = "#dc2626";
      feedback.textContent = data.error || "Failed to update password.";
    }
  } catch (err) {
    feedback.style.background = "#fef2f2";
    feedback.style.color = "#dc2626";
    feedback.textContent = "Network error. Please try again.";
  }
}

async function resendAccountVerification() {
  if (!currentProfileUser || !currentProfileUser.email) return;
  try {
    const res = await fetch(`${API}/v1/auth/resend-verification`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: currentProfileUser.email })
    });
    alert("✉️ If your email is pending verification, a new verification link has been sent.");
  } catch (e) {
    alert("❌ Error sending verification email. Please try again.");
  }
}

function handleDisconnectYouTube() {
  if (confirm("Are you sure you want to disconnect your YouTube channel?")) {
    toggleYouTubeConnection(true);
    openProfileModal();
  }
}

async function promptDeleteAccount() {
  const pwd = prompt("⚠️ WARNING: This will permanently delete your Plexudo account and all associated data.\n\nPlease enter your password to confirm:");
  if (!pwd) return;

  try {
    const res = await fetch(`${API}/delete-account`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ password: pwd })
    });
    const data = await res.json();
    if (res.ok) {
      alert("✅ Your account has been deleted.");
      window.location.href = "/";
    } else {
      alert(`❌ ${data.error || "Failed to delete account."}`);
    }
  } catch (e) {
    alert("❌ Network error deleting account.");
  }
}

