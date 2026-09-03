# Plexudo UI & Layout Rules

## Responsive CSS Guidelines
- **NEVER** use inline style="..." attributes for layout-critical CSS properties (e.g., display: grid, display: flex, grid-template-columns, width, min-width, max-width).
- Inline layout styles override @media queries and cause systemic responsive layout bugs.
- **ALWAYS** define layout configurations in proper CSS classes within style.css (e.g., .dashboard-grid-1-1, .flex-row-center) and apply those classes in HTML/JS templates.
- Ensure all fixed widths use responsive fallbacks (like max-width: 100%) to allow components to shrink gracefully on smaller mobile viewports.
