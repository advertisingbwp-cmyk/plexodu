# Plexudo Design System & Vibe Coding Guardrails

This document establishes the non-negotiable frontend, UI/UX, and architectural rules for Plexudo. Every generated, modified, or refactored component MUST strictly adhere to these standards to eliminate mobile breakage, visual inconsistency, and regression bugs.

---

## 1. Plexudo Bento-Box Design System Consistency
- **Design Tokens First:** ALWAYS use Plexudo's existing CSS variables from `frontend/css/style.css`:
  - Canvas & Cards: `var(--bg)`, `var(--bg-panel)`, `var(--border)`, `var(--shadow-card)`
  - Brand & Accents: `var(--primary)`, `var(--primary-hover)`, `var(--cyan)`, `var(--pink)`, `var(--purple)`, `var(--green)`
  - Typography: `var(--text)`, `var(--text-muted)`, fonts `'Plus Jakarta Sans', 'Inter', sans-serif`
  - Corners: `var(--radius-sm)`, `var(--radius-md)`, `var(--radius-lg)`
- **NEVER Invent Arbitrary Colors:** Do not introduce random hex colors (e.g., `#23a1ff`, `#f03456`) or custom shadow styles when existing design tokens cover the requirement.
- **Card Aesthetics:** Every panel or card must have clean borders (`1px solid var(--border)`), subtle card shadow (`var(--shadow-card)`), and comfortable padding (`16px` to `24px` on desktop, `12px` to `16px` on mobile).

---

## 2. Responsive CSS & Mobile-First Layout Rules
- **NEVER use inline `style="..."` attributes** for layout-critical CSS properties (e.g., `display: grid`, `display: flex`, `grid-template-columns`, `width`, `min-width`, `max-width`, `height`). Inline styles override `@media` queries and cause systemic responsive layout bugs.
- **ALWAYS define layout configurations in CSS classes** inside `frontend/css/style.css` (e.g., `.dashboard-grid-1-1`, `.flex-row-center`) and apply classes in HTML/JS templates.
- **Flexbox Squish Protection (Mandatory):**
  - In any flex row containing an `<input>` and a `<button>` (e.g. search bars, form bars):
    - Input MUST have: `flex: 1 1 auto; min-width: 0; width: auto;`
    - Button MUST have: `flex-shrink: 0; width: auto; white-space: nowrap;`
  - Never allow buttons or badges to squish inputs or cause horizontal overflow.
- **Touch Target Accessibility:** All buttons, interactive icons, and tap targets on mobile (`max-width: 768px`) must have a minimum clickable height of `44px` (or `36px` with adequate padding).
- **iOS Auto-Zoom Prevention:** Form inputs (`<input>`, `<select>`, `<textarea>`) must have at least `font-size: 16px` (or `14px` with `-webkit-text-size-adjust: 100%`) on mobile viewports to prevent iOS Safari from automatically zooming into the page and breaking viewport layout.
- **Zero Horizontal Scrollbar (`overflow-x`):**
  - Containers must NEVER have fixed pixel widths without a responsive fallback (`max-width: 100%`).
  - Use `box-sizing: border-box` universally.
  - Test mental breakpoints: `320px` (small phone), `375px/390px` (standard mobile), `768px` (tablet), `1024px+` (desktop).

---

## 3. Cache-Busting & Immediate Reflection Discipline
- Whenever `frontend/css/style.css` or any frontend script in `frontend/js/` is modified, **ALWAYS bump the cache-busting query parameter** in all referencing HTML files (e.g. `<link rel="stylesheet" href="/css/style.css?v=27.0">`).
- Without this version bump, users and browsers will load cached old styles, resulting in apparent layout bugs and false failure reports.

---

## 4. Zero-Regression & Integrity Rules
- **Preserve IDs and Data Attributes:** Never remove, rename, or alter existing element IDs (e.g., `id="analyzeBtn"`, `id="creatorInput"`) or data attributes that JavaScript or API calls bind to.
- **Preserve Working Features:** When asked to edit or add a feature, never strip away previously working analytics, charts, or state handling.
- **Maintain Clean Code & Comments:** Preserve meaningful comments and documentation while ensuring CSS classes remain clean and reusable.
