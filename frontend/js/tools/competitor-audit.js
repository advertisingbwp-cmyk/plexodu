/**
 * YouTube Competitor Channel Audit Client JS
 */
const channelInput = document.getElementById("channelInput");
const auditBtn = document.getElementById("auditBtn");
const statusLine = document.getElementById("statusLine");
const loadingArea = document.getElementById("loadingArea");
const resultsArea = document.getElementById("resultsArea");

const channelAvatar = document.getElementById("channelAvatar");
const channelName = document.getElementById("channelName");
const channelHandle = document.getElementById("channelHandle");
const channelAge = document.getElementById("channelAge");

const subCountVal = document.getElementById("subCountVal");
const viewsCountVal = document.getElementById("viewsCountVal");
const videoCountVal = document.getElementById("videoCountVal");
const earningsVal = document.getElementById("earningsVal");
const topVideosBody = document.getElementById("topVideosBody");

if (auditBtn) {
  auditBtn.addEventListener("click", runChannelAudit);
}

if (channelInput) {
  channelInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") runChannelAudit();
  });
}

async function runChannelAudit() {
  const identifier = channelInput ? channelInput.value.trim() : "";
  if (!identifier) {
    showStatusBar(statusLine, "Please enter a channel handle or URL", true);
    return;
  }

  hideStatusBar(statusLine);
  if (loadingArea) loadingArea.style.display = "block";
  if (resultsArea) resultsArea.style.display = "none";
  if (auditBtn) auditBtn.disabled = true;

  try {
    const res = await fetchWithTimeout("/api/audit-channel", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier })
    }, 25000);

    const data = await res.json();
    if (!res.ok || data.error) {
      showStatusBar(statusLine, data.error || data.message || "Channel audit failed. Please check the handle.", true);
      return;
    }

    renderAuditResults(data);
  } catch (err) {
    showStatusBar(statusLine, err.message || "Network error. Please try again.", true);
  } finally {
    if (loadingArea) loadingArea.style.display = "none";
    if (auditBtn) auditBtn.disabled = false;
  }
}

function renderAuditResults(data) {
  if (channelAvatar) channelAvatar.src = sanitizeUrl(data.avatar_url || data.thumbnail || "");
  if (channelName) channelName.textContent = data.title || data.channel_name || "Channel";
  if (channelHandle) channelHandle.textContent = data.custom_url || data.handle || data.channel_name || "—";
  if (channelAge) channelAge.textContent = `${data.channel_age_years ?? data.age_years ?? 0} years`;

  if (subCountVal) subCountVal.textContent = Number(data.subscribers || data.subscriber_count || 0).toLocaleString();
  if (viewsCountVal) viewsCountVal.textContent = Number(data.total_views || 0).toLocaleString();
  if (videoCountVal) videoCountVal.textContent = Number(data.video_count || 0).toLocaleString();
  if (earningsVal) {
    const minE = data.est_monthly_earnings_min ?? data.earn_min_monthly ?? 0;
    const maxE = data.est_monthly_earnings_max ?? data.earn_max_monthly ?? 0;
    earningsVal.textContent = `$${Number(minE).toLocaleString()} – $${Number(maxE).toLocaleString()}`;
  }

  if (topVideosBody) {
    const vids = data.top_videos || [];
    if (vids.length === 0) {
      topVideosBody.innerHTML = `<tr><td colspan="4" style="padding:16px; text-align:center; color:#94a3b8;">No recent upload data found.</td></tr>`;
    } else {
      topVideosBody.innerHTML = vids.map(v => `
        <tr style="border-bottom:1px solid #f1f5f9;">
          <td style="padding:12px; font-weight:700; color:#0f172a; max-width:320px;">${escapeHtml(v.title)}</td>
          <td style="padding:12px; color:#475569;">${Number(v.views || 0).toLocaleString()}</td>
          <td style="padding:12px; color:#475569;">${Number(v.likes || 0).toLocaleString()}</td>
          <td style="padding:12px; color:#94a3b8;">${(v.published_at || v.upload_date || '—').slice(0, 10)}</td>
        </tr>
      `).join("");
    }
  }

  if (resultsArea) resultsArea.style.display = "block";
}
