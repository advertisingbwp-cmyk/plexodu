/**
 * AI Creator Strategist Client JS (Multi-turn Memory + Roman Urdu + Groq Backend)
 */
let conversationHistory = [];
let currentTopic = "";

const chatMessages = document.getElementById("chatMessages");
const chatInput = document.getElementById("chatInput");
const chatSendBtn = document.getElementById("chatSendBtn");

if (chatSendBtn) {
  chatSendBtn.addEventListener("click", handleSendMessage);
}

if (chatInput) {
  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  });

  const urlParams = new URLSearchParams(window.location.search);
  const topicParam = urlParams.get("topic");
  if (topicParam) {
    currentTopic = topicParam.trim();
    chatInput.value = `Help me create a content strategy and viral video ideas for the trending topic: "${currentTopic}"`;
    setTimeout(() => handleSendMessage(), 300);
  }
}

function sendChipPrompt(promptText) {
  if (chatInput) {
    chatInput.value = promptText;
    handleSendMessage();
  }
}

function clearChat() {
  conversationHistory = [];
  if (chatMessages) {
    chatMessages.innerHTML = `
      <div class="chat-message ai">
        <div class="chat-avatar">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/><path d="M5 3v4M3 5h4M19 17v4M17 19h4"/></svg>
        </div>
        <div>
          <div class="chat-bubble">
            👋 Conversation cleared! What YouTube niche or video topic would you like to plan next? (Roman Urdu mein bhi pooch saktay hain 🚀)
          </div>
          <div class="chat-timestamp">Just now</div>
        </div>
      </div>
    `;
  }
}

function formatMarkdown(text) {
  if (!text) return "";
  let safe = escapeHtml(text);

  // Markdown Headings
  safe = safe.replace(/^###\s+(.+)$/gm, '<h4 class="chat-md-heading">$1</h4>');
  safe = safe.replace(/^##\s+(.+)$/gm, '<h4 class="chat-md-heading">$1</h4>');
  safe = safe.replace(/^#\s+(.+)$/gm, '<h4 class="chat-md-heading">$1</h4>');

  // Horizontal Dividers
  safe = safe.replace(/^---$/gm, '<hr class="chat-md-divider">');

  // Bold (**text**)
  safe = safe.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

  // Italics (*text*)
  safe = safe.replace(/(^|[^\*])\*([^\*]+)\*([^\*]|$)/g, '$1<em>$2</em>$3');

  // Bullet items (- or *)
  safe = safe.replace(/^[-*]\s+(.+)$/gm, '<div class="chat-md-item"><span class="chat-md-bullet">•</span><span>$1</span></div>');

  // Preserve double and single line breaks
  safe = safe.replace(/\n\n/g, '<br><br>');
  safe = safe.replace(/\n/g, '<br>');

  return safe;
}

async function handleSendMessage() {
  const text = chatInput ? chatInput.value.trim() : "";
  if (!text) return;

  // Track topic if user asks for specific topic
  const topicMatch = text.match(/(?:topic|about|for):\s*["']?([^"'\n,]+)["']?/i);
  if (topicMatch && topicMatch[1]) {
    currentTopic = topicMatch[1].trim();
  }

  // Append user bubble
  appendBubble("user", text);
  if (chatInput) chatInput.value = "";
  if (chatSendBtn) chatSendBtn.disabled = true;

  // Typing indicator
  const typingId = appendTypingBubble();

  try {
    const payload = {
      message: text,
      history: conversationHistory
    };
    if (currentTopic) {
      payload.context = { keyword: currentTopic };
    }

    const res = await fetchWithTimeout("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }, 30000);

    const data = await res.json();
    removeTypingBubble(typingId);

    if (!res.ok || data.error) {
      appendBubble("ai", data.error || "Sorry, could not process your request. Please try again.");
      return;
    }

    const reply = data.reply || data.response || "No response received.";
    appendBubble("ai", reply);

    // Save to multi-turn memory
    conversationHistory.push({ role: "user", content: text });
    conversationHistory.push({ role: "assistant", content: reply });
  } catch (err) {
    removeTypingBubble(typingId);
    appendBubble("ai", "Network error or timeout. Please check your connection.");
  } finally {
    if (chatSendBtn) chatSendBtn.disabled = false;
  }
}

function appendBubble(role, content) {
  if (!chatMessages) return;
  const isAi = role === "ai";
  const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  const bubbleDiv = document.createElement("div");
  bubbleDiv.className = `chat-message ${isAi ? "ai" : "user"}`;

  const formattedContent = isAi ? formatMarkdown(content) : escapeHtml(content).replace(/\n/g, "<br>");

  // Quick Action Buttons for AI responses
  let actionButtonsHtml = "";
  if (isAi) {
    actionButtonsHtml = `
      <div class="chat-bubble-action-wrap">
        <button class="chat-action-btn" onclick="copyToClipboard('${escapeAttr(content)}', this)">📋 Copy Advice</button>
        <button class="chat-action-btn" onclick="sendChipPrompt('Idea #1 ka 60-second viral YouTube Shorts script bana kar dain.')">📱 Shorts Script</button>
        <button class="chat-action-btn" onclick="sendChipPrompt('In ideas ke liye high-CTR YouTube Tags aur SEO Description dain.')">🏷️ Tags &amp; SEO</button>
      </div>
    `;
  }

  bubbleDiv.innerHTML = `
    ${isAi ? `
      <div class="chat-avatar">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/><path d="M5 3v4M3 5h4M19 17v4M17 19h4"/></svg>
      </div>
    ` : ""}
    <div>
      <div class="chat-bubble">
        ${formattedContent}
        ${actionButtonsHtml}
      </div>
      <div class="chat-timestamp">${now}</div>
    </div>
  `;

  chatMessages.appendChild(bubbleDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendTypingBubble() {
  if (!chatMessages) return null;
  const id = `typing-${Date.now()}`;
  const typingDiv = document.createElement("div");
  typingDiv.id = id;
  typingDiv.className = "chat-message ai";
  typingDiv.innerHTML = `
    <div class="chat-avatar">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/><path d="M5 3v4M3 5h4M19 17v4M17 19h4"/></svg>
    </div>
    <div class="chat-bubble chat-thinking-bubble">
      Plexudo AI Strategist is thinking…
    </div>
  `;
  chatMessages.appendChild(typingDiv);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return id;
}

function removeTypingBubble(id) {
  if (!id) return;
  const el = document.getElementById(id);
  if (el) el.remove();
}
