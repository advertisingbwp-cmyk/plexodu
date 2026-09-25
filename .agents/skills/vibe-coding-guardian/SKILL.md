---
name: vibe-coding-guardian
description: Enforces Plexudo's Bento-box design system, strict mobile responsive layouts (320px to 1920px), typography standards, cache-busting versioning, and zero-regression safeguards during web development and UI generation.
---

# Vibe Coding Guardian & Web Crafting Standards

When the user asks to build, modify, or redesign any UI, component, or web page in Plexudo, follow this 5-step checklist to ensure 100% aesthetic match, responsive perfection, and zero bugs.

---

## 1. Context & Design System Alignment
Before writing any HTML or CSS:
1. **Reuse Existing Design Tokens:** Reference `:root` variables in `frontend/css/style.css`:
   - Surface colors: `var(--bg-panel)`, `var(--bg-panel-2)`, `var(--bg)`
   - Borders: `var(--border)`, `var(--border-hover)`
   - Brand accents: `var(--primary)`, `var(--cyan)`, `var(--pink)`, `var(--purple)`, `var(--green)`
   - Typography: `var(--text)`, `var(--text-muted)`
2. **Reuse Existing Bento Card Classes:** Look at how existing tools (e.g. Trend Analyzer, AI Strategist, Dashboard) construct cards:
   - Card base: `.tool-card`, `.dashboard-card`, `.bento-card`
   - Header: `.tool-card-header`, `.card-title`, `.card-badge`
   - Buttons: `.tool-primary-btn`, `.btn-secondary`, `.btn-icon`

---

## 2. Strict Responsive & Mobile Checks (320px – 1920px)
Always test mental rendering across 4 core viewports:
- **Small Mobile (320px – 375px):**
  - Font sizes must not overflow container boxes.
  - Multi-column grids must collapse to `1fr` (`grid-template-columns: 1fr`).
  - Action bars / Search bars: Input gets `flex: 1 1 auto; min-width: 0;` and button gets `flex-shrink: 0; width: auto;`.
- **Standard Mobile (375px – 480px):**
  - Inputs must have `font-size: 16px` to prevent iOS Safari auto-zoom.
  - Interactive click/tap targets must be at least `44px` in height.
- **Tablet (768px – 1024px):**
  - Balanced 2-column or 3-column layouts without empty dead space.
- **Desktop (1200px+):**
  - Bento grid layout with proper aspect ratios and aligned card heights.

---

## 3. Inline Styles Ban
- **NEVER** write inline layout styles such as `style="display: flex; width: 300px; grid-template-columns: 1fr 1fr;"`.
- Always declare named CSS classes in `frontend/css/style.css` and use `@media (max-width: 768px)` or `@media (max-width: 480px)` for mobile overrides.

---

## 4. Cache-Busting Version Bump
- Whenever any change is made to `frontend/css/style.css` or frontend JavaScript files:
  - Check the referencing HTML file (e.g., `frontend/tools/*.html` or `frontend/index.html`).
  - Increment the query version string:
    - Example: `<link rel="stylesheet" href="/css/style.css?v=26.0">` ➔ `<link rel="stylesheet" href="/css/style.css?v=27.0">`
  - This guarantees the user's browser renders the changes instantly on reload without stale cache.

---

## 5. Pre-Completion Quality Verification
Before reporting completion to the user:
- [ ] Are all opened HTML tags properly closed?
- [ ] Are JavaScript element IDs preserved without breakages?
- [ ] Is horizontal scroll (`overflow-x`) completely eliminated?
- [ ] Did you bump the asset cache version in the HTML file?
