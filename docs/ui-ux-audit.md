# PLEXUDO PHASE 5: UI/UX AUDIT & DESIGN SYSTEM SPECIFICATION

**Date:** 2026-08-30  
**Phase:** Phase 5 — Premium Light UI/UX Redesign & Frontend Polish  
**Status:** In Progress (Audit Complete)

---

## 1. Executive Summary & Audit Findings
A comprehensive UI/UX audit was conducted on the current Plexudo web application across desktop (1920px, 1440px, 1024px) and mobile viewports (375px, 390px, 412px).

### A. Current Design & Visual Problems
1. **Dark & Inconsistent UI Elements:** Legacy dashboard sections retained dark-theme containers (e.g. AI Title suggestions box, dark gradients in SEO Studio header, dark sidebar contrast) which clashed with the clean Light UI SaaS direction.
2. **Scattered Brand Styling:** Some components used legacy emerald greens while others used navy or cyan without a unified primary Indigo/Purple design language.
3. **Visual Hierarchy:** Tool cards on certain pages lacked prominent status indicators, structured input groups, and consistent action button hierarchy.

### B. UX & Interaction Inconsistencies
1. **Empty State Polish:** When no video was selected or history was empty, certain panels showed basic text instead of structured creator-friendly empty state cards with helpful action prompts.
2. **Credit Cost Visibility:** Tool execution triggers needed explicit, transparent cost chips (e.g. `⚡ 1 Credit`) before user action.
3. **Profile & Settings Experience:** Profile options were embedded inside sidebar footer dropdowns rather than having a dedicated, polished Account & Settings modal with password change forms and connection status indicators.

---

## 2. Plexudo Premium Light Design System Specifications

### A. Color Tokens
- **Backgrounds:**
  - Page Canvas: `#F8FAFC` (Slate-50)
  - Surface Panels / Cards: `#FFFFFF` (Pure White)
  - Subtle Contrast Fill: `#F1F5F9` (Slate-100)
- **Primary Brand Accents:**
  - Primary Indigo: `#4F46E5` (Indigo-600)
  - Primary Hover / Dark: `#4338CA` (Indigo-700)
  - Primary Soft Tint: `#EEF2FF` (Indigo-50)
  - Primary Border: `#C7D2FE` (Indigo-200)
- **Functional Semantics:**
  - Success: `#059669` (Emerald-600) / Tint: `#ECFDF5`
  - Warning: `#D97706` (Amber-600) / Tint: `#FFFBEB`
  - Danger / Error: `#DC2626` (Red-600) / Tint: `#FEE2E2`
  - Info / Secondary: `#0284C7` (Sky-600) / Tint: `#E0F2FE`
- **Text & Neutral Contrast:**
  - Heading & Primary Text: `#0F172A` (Slate-900)
  - Body & Muted Text: `#475569` (Slate-600)
  - Subtle / Placeholder: `#94A3B8` (Slate-400)
  - Border Lines: `#E2E8F0` (Slate-200)

### B. Typography & Scale
- **Font Family:** `'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif`
- **Hierarchy:**
  - Page Titles: `font-size: 1.65rem; font-weight: 800; letter-spacing: -0.025em;`
  - Section Headings: `font-size: 1.25rem; font-weight: 700;`
  - Card Titles: `font-size: 1.05rem; font-weight: 700;`
  - Body Text: `font-size: 0.92rem; line-height: 1.6;`
  - Badges & Microcopy: `font-size: 0.78rem; font-weight: 700; text-transform: uppercase;`

### C. Component Architecture
- **Buttons:**
  - `.btn-primary`: Solid Indigo (`#4F46E5`), white text, subtle elevation, 10px radius.
  - `.btn-secondary`: White background, `#E2E8F0` border, `#0F172A` text.
  - `.btn-danger`: Red tone for disconnect / delete actions.
- **Card Containers:** Pure white, 16px radius, 1px solid `#E2E8F0`, soft shadow (`0 4px 16px rgba(15, 23, 42, 0.04)`).
- **50/50 SEO Meter:** High-contrast radial / progress bar layout with crisp emerald/indigo fills.
