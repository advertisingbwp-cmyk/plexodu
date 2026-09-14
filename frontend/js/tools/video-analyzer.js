/**
 * YouTube Video Virality Analyzer Client JS
 */
const videoUrlInput = document.getElementById("videoUrlInput");
const analyzeVideoBtn = document.getElementById("analyzeVideoBtn");
const statusLine = document.getElementById("statusLine");
const loadingArea = document.getElementById("loadingArea");
const resultsArea = document.getElementById("resultsArea");

const videoThumb = document.getElementById("videoThumb");
const videoTitle = document.getElementById("videoTitle");
const videoChannel = document.getElementById("videoChannel");
const videoDate = document.getElementById("videoDate");
const videoDescription = document.getElementById("videoDescription");

const videoViralityVal = document.getElementById("videoViralityVal");
const videoViewsVal = document.getElementById("videoViewsVal");
const videoEngagementVal = document.getElementById("videoEngagementVal");

const copyTitleBtn = document.getElementById("copyTitleBtn");
const copyDescBtn = document.getElementById("copyDescBtn");
const copyTagsBtn = document.getElementById("copyTagsBtn");

let currentVideoTitle = "";
let currentVideoDescription = "";
let currentVideoTags = [];

const sentimentStats = document.getElementById("sentimentStats");
const sampleCommentText = document.getElementById("sampleCommentText");
const tagsContainer = document.getElementById("tagsContainer");
const commentsList = document.getElementById("commentsList");

if (analyzeVideoBtn) {
  analyzeVideoBtn.addEventListener("click", runVideoAnalysis);
}

if (videoUrlInput) {
  videoUrlInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") runVideoAnalysis();
  });
}

// Copy Action Handlers
if (copyTitleBtn) {
  copyTitleBtn.addEventListener("click", () => {
    safeCopyToClipboard(currentVideoTitle, copyTitleBtn);
  });
}

if (copyDescBtn) {
  copyDescBtn.addEventListener("click", () => {
    safeCopyToClipboard(currentVideoDescription, copyDescBtn);
  });
}

if (copyTagsBtn) {
  copyTagsBtn.addEventListener("click", () => {
    const tagsText = (currentVideoTags && currentVideoTags.length > 0)
      ? currentVideoTags.join(", ")
      : "";
    safeCopyToClipboard(tagsText, copyTagsBtn);
  });
}

async function safeCopyToClipboard(text, btnElement) {
  if (!text) return false;
  let copied = false;
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      copied = true;
    } else {
      throw new Error("Clipboard API unavailable");
    }
  } catch (err) {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    textarea.style.top = "0";
    textarea.setAttribute("readonly", "");
    document.body.appendChild(textarea);
    textarea.select();
    try {
      copied = document.execCommand("copy");
    } catch (e) {
      copied = false;
    }
    document.body.removeChild(textarea);
  }

  if (copied && btnElement) {
    const originalText = btnElement.textContent;
    btnElement.textContent = "Copied!";
    btnElement.classList.add("copied");
    setTimeout(() => {
      btnElement.textContent = originalText;
      btnElement.classList.remove("copied");
    }, 2000);
  }
  return copied;
}

function decodeHtmlEntities(str) {
  if (!str) return "";
  const txt = document.createElement("textarea");
  txt.innerHTML = str;
  return txt.value;
}

async function runVideoAnalysis() {
  const url = videoUrlInput ? videoUrlInput.value.trim() : "";
  if (!url) {
    showStatusBar(statusLine, "Please enter a valid YouTube video URL or ID", true);
    return;
  }

  hideStatusBar(statusLine);
  if (loadingArea) loadingArea.style.display = "block";
  if (resultsArea) resultsArea.style.display = "none";
  if (analyzeVideoBtn) analyzeVideoBtn.disabled = true;

  try {
    const res = await fetchWithTimeout("/api/video-analysis", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url })
    }, 25000);

    const data = await res.json();
    if (!res.ok || data.error) {
      showStatusBar(statusLine, data.error || data.message || "Could not analyze video. Please verify the link.", true);
      return;
    }

    renderVideoResults(data);
  } catch (err) {
    showStatusBar(statusLine, err.message || "Network error. Please try again.", true);
  } finally {
    if (loadingArea) loadingArea.style.display = "none";
    if (analyzeVideoBtn) analyzeVideoBtn.disabled = false;
  }
}

function renderVideoResults(data) {
  currentVideoTitle = (data.title || "Unknown Video").trim();
  currentVideoTags = Array.isArray(data.tags) ? data.tags : [];

  if (videoThumb) videoThumb.src = sanitizeUrl(data.thumbnail || "");
  if (videoTitle) videoTitle.textContent = currentVideoTitle;
  if (videoChannel) videoChannel.textContent = data.channel_title || data.channel_name || "Unknown Channel";
  if (videoDate) {
    const pubDate = data.published_at || data.upload_date;
    videoDate.textContent = pubDate ? pubDate.slice(0, 10) : "—";
  }

  // Full Description Handling with Strict XSS Protection
  const rawDesc = (data.description != null && String(data.description).trim() !== "")
    ? String(data.description).trim()
    : "";

  if (rawDesc) {
    // Decode HTML entities if any were passed from legacy API, and normalize any raw <br> tags
    const decoded = decodeHtmlEntities(rawDesc).replace(/<br\s*\/?>/gi, "\n");
    currentVideoDescription = decoded;
    if (videoDescription) {
      videoDescription.textContent = decoded; // textContent guarantees safe rendering with zero XSS!
      videoDescription.classList.remove("is-empty");
      videoDescription.style.display = "block";
    }
    if (copyDescBtn) copyDescBtn.disabled = false;
  } else {
    currentVideoDescription = "";
    if (videoDescription) {
      videoDescription.textContent = "No description available.";
      videoDescription.classList.add("is-empty");
      videoDescription.style.display = "block";
    }
    if (copyDescBtn) copyDescBtn.disabled = true;
  }

  if (copyTagsBtn) {
    copyTagsBtn.disabled = currentVideoTags.length === 0;
  }

  if (videoViralityVal) videoViralityVal.textContent = `${data.virality_score || 0}/100`;
  if (videoViewsVal) videoViewsVal.textContent = Number(data.views || data.view_count || 0).toLocaleString();
  if (videoEngagementVal) videoEngagementVal.textContent = `${data.engagement_rate || 0}%`;

  const s = data.sentiment || {};
  if (sentimentStats) {
    sentimentStats.textContent = `Positive: ${s.positive_score || 0}% • Neutral: ${s.neutral_score || 0}% • Negative: ${s.negative_score || 0}%`;
  }
  if (sampleCommentText) {
    sampleCommentText.textContent = s.sample_comment ? `"${s.sample_comment}"` : "No sample comment recorded.";
  }

  // Tags
  if (tagsContainer) {
    const tags = data.tags || [];
    if (tags.length === 0) {
      tagsContainer.innerHTML = `<span style="font-size:13px; color:#94a3b8;">No tags provided for this upload</span>`;
    } else {
      tagsContainer.innerHTML = tags.map(t => `
        <span class="panel-badge" style="background:#f1f5f9; color:#0f172a; padding:6px 12px; border-radius:8px; font-size:13px; cursor:pointer;" title="Click to copy" onclick="copyToClipboard('${escapeAttr(t)}', this)">
          🏷️ ${escapeHtml(t)}
        </span>
      `).join("");
    }
  }

  // Comments
  if (commentsList) {
    const comments = data.comments || [];
    if (comments.length === 0) {
      commentsList.innerHTML = `<div style="font-size:13px; color:#94a3b8;">No public comments available.</div>`;
    } else {
      commentsList.innerHTML = comments.slice(0, 10).map(c => `
        <div style="padding:12px 14px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; font-size:13px; color:#334155; line-height:1.5;">
          ${escapeHtml(c.text || c)}
        </div>
      `).join("");
    }
  }

  if (resultsArea) resultsArea.style.display = "block";
}
