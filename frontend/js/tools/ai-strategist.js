/**
 * AI Creator Strategist Client JS (Multi-turn Memory + Roman Urdu + Groq Backend)
 */
let conversationHistory = [];

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
            Conversation cleared. How can I assist you with your YouTube growth today? 🚀
          </div>
          <div class="chat-timestamp">Just now</div>
        </div>
      </div>
    `;
  }
}

async function handleSendMessage() {
  const text = chatInput ? chatInput.value.trim() : "";
  if (!text) return;

  // Append user bubble
  appendBubble("user", text);
  if (chatInput) chatInput.value = "";
  if (chatSendBtn) chatSendBtn.disabled = true;

  // Typing indicator
  const typingId = appendTypingBubble();

  try {
    const res = await fetchWithTimeout("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        history: conversationHistory
      })
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

  const formattedContent = escapeHtml(content).replace(/\n/g, "<br>");

  bubbleDiv.innerHTML = `
    ${isAi ? `
      <div class="chat-avatar">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/><path d="M5 3v4M3 5h4M19 17v4M17 19h4"/></svg>
      </div>
    ` : ""}
    <div>
      <div class="chat-bubble">
        ${formattedContent}
        ${isAi ? `<div style="margin-top:8px;"><button class="tool-secondary-btn" style="padding:4px 8px; font-size:11px;" onclick="copyToClipboard('${escapeAttr(content)}', this)">Copy Text</button></div>` : ""}
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
    <div class="chat-bubble" style="font-style:italic; color:#64748b;">
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
