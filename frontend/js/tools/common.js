/**
 * Plexudo Standalone Tools — Shared Utilities (Zero Authentication)
 */

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  const d = document.createElement("div");
  d.textContent = String(str);
  return d.innerHTML;
}

function escapeAttr(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function sanitizeUrl(url) {
  if (!url || typeof url !== "string") return "";
  const trimmed = url.trim();
  if (/^(?:javascript|data|vbscript):/i.test(trimmed)) {
    return "";
  }
  return trimmed;
}

async function fetchWithTimeout(resource, options = {}, timeoutMs = 20000) {
  const { timeout: _, ...fetchOptions } = options;
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(resource, {
      ...fetchOptions,
      signal: controller.signal
    });
    return response;
  } catch (err) {
    if (err.name === "AbortError") {
      throw new Error(`Request timed out after ${timeoutMs / 1000}s`);
    }
    throw err;
  } finally {
    clearTimeout(id);
  }
}

function showStatusBar(statusEl, message, isError = false) {
  if (!statusEl) return;
  statusEl.textContent = message;
  statusEl.className = `tool-status-bar ${isError ? "error" : "success"}`;
  statusEl.style.display = "block";
}

function hideStatusBar(statusEl) {
  if (!statusEl) return;
  statusEl.style.display = "none";
  statusEl.textContent = "";
}

function copyToClipboard(text, btn) {
  const onSuccess = () => {
    if (btn) {
      const orig = btn.innerHTML;
      btn.innerHTML = "Copied! ✓";
      setTimeout(() => { btn.innerHTML = orig; }, 2000);
    }
  };

  if (!navigator.clipboard) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.select();
    try {
      document.execCommand("copy");
      onSuccess();
    } catch (e) {
      console.error("Copy failed", e);
    }
    document.body.removeChild(textArea);
    return;
  }

  navigator.clipboard.writeText(text).then(onSuccess).catch((err) => {
    console.error("Copy failed", err);
  });
}

function toggleMobileMenu() {
  const drawer = document.getElementById("mobileDrawer");
  if (drawer) drawer.classList.toggle("active");
}
