const API = "/api";

const loginForm    = document.getElementById("loginForm");
const registerForm = document.getElementById("registerForm");
const errorBox     = document.getElementById("errorBox");
const tabLogin     = document.getElementById("tabLogin");
const tabRegister  = document.getElementById("tabRegister");

function showError(msg) {
  errorBox.textContent = msg;
  errorBox.style.display = "block";
  // re-trigger shake animation
  errorBox.style.animation = "none";
  errorBox.offsetHeight;
  errorBox.style.animation = "";
}

function clearError() { errorBox.style.display = "none"; }

// ─── Tab switching ────────────────────────────────────────────────────────────
tabLogin.addEventListener("click", () => switchTab("login"));
tabRegister.addEventListener("click", () => switchTab("register"));

function switchTab(tab) {
  clearError();
  if (tab === "login") {
    loginForm.style.display    = "block";
    registerForm.style.display = "none";
    tabLogin.classList.add("active");
    tabRegister.classList.remove("active");
  } else {
    loginForm.style.display    = "none";
    registerForm.style.display = "block";
    tabLogin.classList.remove("active");
    tabRegister.classList.add("active");
  }
}

// ─── Login ────────────────────────────────────────────────────────────────────
loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  clearError();
  const btn      = document.getElementById("loginBtn");
  const email    = document.getElementById("loginEmail").value;
  const password = document.getElementById("loginPassword").value;

  btn.textContent = "Signing in…";
  btn.disabled    = true;

  try {
    const res  = await fetch(`${API}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) { showError(data.error || "Login failed"); return; }
    window.location.href = "dashboard.html";
  } catch (err) {
    showError("Cannot reach the server. Is the Flask backend running on port 5000?");
  } finally {
    btn.textContent = "Sign In";
    btn.disabled    = false;
  }
});

// ─── Register ─────────────────────────────────────────────────────────────────
registerForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  clearError();
  const btn      = document.getElementById("registerBtn");
  const name     = document.getElementById("regName").value;
  const email    = document.getElementById("regEmail").value;
  const password = document.getElementById("regPassword").value;
  const role     = document.getElementById("regRole").value;

  if (password.length < 6) { showError("Password must be at least 6 characters."); return; }

  btn.textContent = "Creating account…";
  btn.disabled    = true;

  try {
    const res  = await fetch(`${API}/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ name, email, password, role }),
    });
    const data = await res.json();
    if (!res.ok) { showError(data.error || "Registration failed"); return; }
    switchTab("login");
    clearError();
    showSuccess("Account created! Please check your email inbox to verify your account before signing in.");
  } catch (err) {
    showError("Cannot reach the server. Is the Flask backend running on port 5000?");
  } finally {
    btn.textContent = "Create Account";
    btn.disabled    = false;
  }
});

function showSuccess(msg) {
  errorBox.textContent = "✓ " + msg;
  errorBox.style.display = "block";
  errorBox.style.background = "rgba(6,214,160,0.1)";
  errorBox.style.borderColor = "rgba(6,214,160,0.35)";
  errorBox.style.color = "#06d6a0";
}

// ==============================================================================
// ─── USER'S EXACT 3D REALISTIC BABY PANDA MASCOT CONTROLS ─────────────────────
// ==============================================================================
const pandaIdle  = document.getElementById("pandaIdle");
const pandaCover = document.getElementById("pandaCover");
const pandaPeek  = document.getElementById("pandaPeek");

const loginEmail    = document.getElementById("loginEmail");
const loginPassword = document.getElementById("loginPassword");
const regEmail      = document.getElementById("regEmail");
const regPassword   = document.getElementById("regPassword");
const showLoginPass = document.getElementById("showLoginPassword");
const showRegPass   = document.getElementById("showRegPassword");

function setPandaPose(pose) {
  if (!pandaIdle || !pandaCover || !pandaPeek) return;
  if (pose === "idle") {
    pandaIdle.style.opacity  = "1";
    pandaCover.style.opacity = "0";
    pandaPeek.style.opacity  = "0";
  } else if (pose === "cover") {
    pandaIdle.style.opacity  = "0";
    pandaCover.style.opacity = "1";
    pandaPeek.style.opacity  = "0";
  } else if (pose === "peek") {
    pandaIdle.style.opacity  = "0";
    pandaCover.style.opacity = "0";
    pandaPeek.style.opacity  = "1";
  }
}

// 1. Subtle Smooth Internal Pan when typing in Email (Frame stays 100% stationary)
function trackInput(inputEl) {
  if (!inputEl) return;
  setPandaPose("idle");
  const len = Math.min(inputEl.value.length, 30);
  const progress = len / 30; // 0 to 1
  const transX = progress * 6 - 3; // -3px to +3px
  if (pandaIdle) {
    pandaIdle.style.transform = `scale(1.15) translate(${transX}px, -2px)`;
  }
}

function resetPanda() {
  if (pandaIdle) {
    pandaIdle.style.transform = "scale(1.15) translate(0px, -2px)";
  }
  setPandaPose("idle");
}

if (loginEmail) {
  loginEmail.addEventListener("input", () => trackInput(loginEmail));
  loginEmail.addEventListener("focus", () => trackInput(loginEmail));
  loginEmail.addEventListener("blur", resetPanda);
}

if (regEmail) {
  regEmail.addEventListener("input", () => trackInput(regEmail));
  regEmail.addEventListener("focus", () => trackInput(regEmail));
  regEmail.addEventListener("blur", resetPanda);
}

// 2. Cover Eyes with its OWN 3D Paws on Password Focus
if (loginPassword) {
  loginPassword.addEventListener("focus", () => {
    if (showLoginPass && showLoginPass.checked) {
      setPandaPose("peek");
    } else {
      setPandaPose("cover");
    }
  });
  loginPassword.addEventListener("blur", resetPanda);
}

if (regPassword) {
  regPassword.addEventListener("focus", () => {
    if (showRegPass && showRegPass.checked) {
      setPandaPose("peek");
    } else {
      setPandaPose("cover");
    }
  });
  regPassword.addEventListener("blur", resetPanda);
}

// 3. Show / Hide password toggles with peek-a-boo
if (showLoginPass) {
  showLoginPass.addEventListener("change", () => {
    if (showLoginPass.checked) {
      loginPassword.type = "text";
      setPandaPose("peek");
    } else {
      loginPassword.type = "password";
      setPandaPose("cover");
    }
  });
}

if (showRegPass) {
  showRegPass.addEventListener("change", () => {
    if (showRegPass.checked) {
      regPassword.type = "text";
      setPandaPose("peek");
    } else {
      regPassword.type = "password";
      setPandaPose("cover");
    }
  });
}

// ==============================================================================
// ─── LANDING PAGE FAQ ACCORDION & MODAL SYSTEM ────────────────────────────────
// ==============================================================================
function toggleFaq(itemEl) {
  const isActive = itemEl.classList.contains("active");
  document.querySelectorAll(".lp-faq-item").forEach(el => el.classList.remove("active"));
  if (!isActive) itemEl.classList.add("active");
}

function openAuthModal(tab = "login") {
  if (tab === "register") {
    switchTab("register");
  } else {
    switchTab("login");
  }
  openModal("authModal");
}

function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.style.display = "flex";
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.style.display = "none";
}

// Close on overlay click
document.addEventListener("click", (e) => {
  if (e.target.classList && e.target.classList.contains("lp-modal-overlay")) {
    e.target.style.display = "none";
  }
});

// Blog Articles Database for Instant Modal Reading & SEO
const BLOG_ARTICLES = {
  views100k: {
    tag: "🔥 VIRAL STRATEGY",
    date: "August 2026 • 6 min read",
    title: "How to Get 100,000 Views on YouTube Fast with AI SEO (2026 Algorithmic Guide)",
    content: `
      <h2>The New YouTube Algorithm Reality in 2026</h2>
      <p>YouTube's recommendation system no longer relies solely on keyword stuffing. Today, the algorithm analyzes <strong>Click-Through Rate (CTR)</strong> in the first 2 hours, <strong>Audience Retention</strong>, and <strong>Semantic Relevance</strong> across Title, Tags, and Description.</p>
      
      <h3>Step 1: Exploit Real-Time View Velocity</h3>
      <p>Before recording a video, analyze keyword velocity on SMTAS. High velocity keywords with a <strong>Virality Index (VI) &gt; 70</strong> have unmet viewer demand. Target topics where established creators have not published in the last 48 hours.</p>

      <h3>Step 2: Achieve a 50/50 SEO Score</h3>
      <p>Using our AI YouTube SEO Studio, align your top keyword in 3 places:
      <ul>
        <li><strong>Title:</strong> Place the primary keyword within the first 45 characters.</li>
        <li><strong>Description:</strong> Include the primary keyword in the first 2 lines (before the 'Show More' fold).</li>
        <li><strong>Tags:</strong> Ensure your top 3 tags match the exact phrases used in your title and description (Triple Keyword Overlap).</li>
      </ul>
      </p>

      <h3>Step 3: High-CTR AI Viral Titles</h3>
      <p>Our Groq Llama 3.3 70B engine recommends titles using psychological curiosity gaps, emotional triggers, and power brackets (e.g. <em>"[NEW ALGORITHM SECRETS]"</em>). High CTR signals YouTube to push your video to Suggested Videos.</p>
    `
  },
  seo5050: {
    tag: "⚡ 50/50 ALGORITHM",
    date: "August 2026 • 5 min read",
    title: "The 50/50 YouTube SEO Formula: How to Rank #1 on YouTube Search in 24 Hours",
    content: `
      <h2>What is the 50/50 SEO Score?</h2>
      <p>The 50/50 SEO score is an enterprise VidIQ-grade multi-factor algorithmic standard designed to maximize YouTube search indexing and suggested video impressions.</p>

      <h3>The 5 Core Scoring Factors (10 Points Each):</h3>
      <ol style="padding-left:20px; margin-bottom:18px; line-height:1.8;">
        <li><strong>Tag Count (10/10):</strong> Use between 15 to 25 relevant tags to maximize semantic reach without trigger spam penalties.</li>
        <li><strong>Tag Volume (10/10):</strong> Total tag volume across high-search keywords should exceed 400 characters of high-relevance terms.</li>
        <li><strong>Keywords in Title (10/10):</strong> High-intent keyword phrases placed in prominent positions.</li>
        <li><strong>Keywords in Description (10/10):</strong> Rich 200+ word contextual description naturally weaving tags.</li>
        <li><strong>Triple Keyword Overlap (10/10):</strong> Exact match of primary keyword across Title, Description, and Tags.</li>
      </ol>
      <p>Videos scoring 45+/50 consistently rank in top 3 search results for niche keywords within 24 to 48 hours of publishing.</p>
    `
  },
  sentiment: {
    tag: "🧠 NLP EMOTION",
    date: "August 2026 • 4 min read",
    title: "Sentiment Analysis for YouTubers: How Audience Emotion Drives the Recommendation Algorithm",
    content: `
      <h2>Why Comment Sentiment Matters for Video Reach</h2>
      <p>YouTube's AI monitors user engagement beyond simple likes and views. Videos with highly engaging, opinionated comment sections trigger algorithmic signals that indicate high viewer resonance.</p>

      <h3>How SMTAS Sentiment Engine Works</h3>
      <p>Our NLP engine scrapes top YouTube comments, runs natural language processing (TextBlob tokenization and polarity scoring), and categorizes viewer reactions into <strong>Positive</strong>, <strong>Neutral</strong>, and <strong>Negative</strong> percentages.</p>

      <h3>Actionable Creator Takeaways:</h3>
      <ul>
        <li><strong>High Positive Sentiment (70%+):</strong> Excellent for sponsor brand deals, merchandise, and affiliate conversions.</li>
        <li><strong>Controversial / Mixed Sentiment:</strong> Generates rapid comment velocity, driving higher impressions in Home Feed recommendations.</li>
        <li><strong>Dominant Negative Sentiment:</strong> Indicates mismatched thumbnail expectations or audience dissatisfaction that needs immediate title/thumbnail iteration.</li>
      </ul>
    `
  },
  virality: {
    tag: "📈 VIRALITY INDEX",
    date: "August 2026 • 5 min read",
    title: "Decoding the YouTube Virality Index: What Makes a Video Go Viral in 2026?",
    content: `
      <h2>The Virality Index (VI) Formula</h2>
      <p>The Virality Index is calculated via a proprietary formula that measures the ratio of recent view growth relative to channel size, engagement density (Likes + Comments per View), and sentiment velocity.</p>

      <h3>The 4 Trend Stages:</h3>
      <ul>
        <li><strong>Emerging (VI 80–100):</strong> Rapidly gaining views in under 24 hours. The highest ROI topic to jump on immediately.</li>
        <li><strong>Explosive / Peaking (VI 60–79):</strong> Peak search volume and maximum current audience interest.</li>
        <li><strong>Sustained (VI 40–59):</strong> Steady evergreen search interest (e.g. tutorials, setups, software reviews).</li>
        <li><strong>Declining (VI &lt; 40):</strong> Market saturation. Avoid creating content in this phase unless presenting a completely contrarian angle.</li>
      </ul>
    `
  }
};

function openBlogModal(key) {
  const article = BLOG_ARTICLES[key];
  if (!article) return;

  const tagEl     = document.getElementById("blogModalTag");
  const metaEl    = document.getElementById("blogModalMeta");
  const titleEl   = document.getElementById("blogModalTitle");
  const contentEl = document.getElementById("blogModalBody");

  if (tagEl)     tagEl.textContent     = article.tag;
  if (metaEl)    metaEl.textContent    = article.date;
  if (titleEl)   titleEl.textContent   = article.title;
  if (contentEl) contentEl.innerHTML   = article.content;

  openModal("blogReaderModal");
}

function openLegalModal(type) {
  const titleEl   = document.getElementById("legalModalTitle");
  const contentEl = document.getElementById("legalModalBody");

  if (type === "terms") {
    if (titleEl) titleEl.textContent = "Terms & Conditions — SMTAS";
    if (contentEl) contentEl.innerHTML = `
      <h2>1. Acceptance of Terms</h2>
      <p>By accessing or using SMTAS (Social Media Trend Analysis System / Plexudo), you agree to be bound by these Terms and Conditions and all applicable laws and regulations.</p>

      <h2>2. 100% Free &amp; Ad-Supported Service</h2>
      <p>SMTAS provides enterprise-grade YouTube analytics, SEO scoring, and AI utilities free of charge. In exchange, the platform is supported by third-party advertising networks (including Adsterra and sponsor reward gateways). By using the service, you consent to the display of advertisements and reward unlock mechanisms.</p>

      <h2>3. YouTube API Services Compliance</h2>
      <p>SMTAS utilizes the YouTube Data API v3 to retrieve public metadata, view counts, and engagement metrics. By using this service, you also agree to be bound by YouTube's Terms of Service (<a href="https://www.youtube.com/t/terms" target="_blank" rel="noopener">https://www.youtube.com/t/terms</a>) and Google's Privacy Policy.</p>

      <h2>4. User Accounts &amp; Security</h2>
      <p>You are responsible for maintaining the confidentiality of your account credentials and password. SMTAS reserves the right to terminate accounts that engage in automated scraping, abuse, or unauthorized reverse engineering.</p>

      <h2>5. Disclaimer of Warranties</h2>
      <p>The analytics, Virality Index scores, and AI recommendations are provided on an "as-is" and "as-available" basis for educational and optimization purposes. SMTAS does not guarantee specific view counts or revenue results on YouTube.</p>
    `;
  } else if (type === "privacy") {
    if (titleEl) titleEl.textContent = "Privacy Policy — SMTAS";
    if (contentEl) contentEl.innerHTML = `
      <h2>1. Information We Collect</h2>
      <p>We collect information you provide directly to us when creating an account (such as name, email address, and role), as well as automated analytics data (browser type, IP address, and search query history).</p>

      <h2>2. How We Use Information</h2>
      <p>We use your information to operate, personalize, and improve our trend analysis algorithms, authenticate your session, and provide contextual AI chat suggestions.</p>

      <h2>3. Third-Party Advertising &amp; Cookies</h2>
      <p>We work with trusted third-party advertising partners (such as Adsterra) that may use cookies, web beacons, and similar tracking technologies to deliver relevant advertisements. You may configure your browser settings to reject cookies if preferred.</p>

      <h2>4. Data Retention &amp; Security</h2>
      <p>We implement industry-standard 256-bit encryption and hashing algorithms (Werkzeug PBKDF2) to protect your stored passwords and personal data.</p>

      <h2>5. GDPR &amp; CCPA Rights</h2>
      <p>Users have the right to access, rectify, or request the deletion of their personal account data at any time by contacting support.</p>
    `;
  } else if (type === "disclaimer") {
    if (titleEl) titleEl.textContent = "Disclaimer & Attribution";
    if (contentEl) contentEl.innerHTML = `
      <h2>Attribution &amp; Trademarks</h2>
      <p>YouTube™ is a registered trademark of Google LLC. SMTAS is an independent research and analytics platform designed for creators and digital marketers, and is not officially affiliated with, endorsed by, or sponsored by YouTube or Google LLC.</p>
      <h2>Algorithm Scoring Disclaimer</h2>
      <p>All SEO scores, virality ratings, and title suggestions are calculated using algorithmic analysis and heuristic modeling. Individual video success depends on viewer retention, content quality, and external factors.</p>
    `;
  }
  openModal("legalModal");
}








