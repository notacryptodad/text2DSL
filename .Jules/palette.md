## 2025-04-13 - [Results Table Accessibility]
**Learning:** React Table (TanStack Table) components are frequently missing keyboard accessibility on column headers when using custom sorting implementations. Interactive `th` elements need `tabIndex`, `onKeyDown` handlers for Enter/Space, and `aria-sort` attributes to correctly communicate the sorting state to screen readers.
**Action:** Always add keyboard handlers (`onKeyDown`), focus states (`focus-visible:ring-2`), and semantic ARIA states (`aria-sort` for headers, `aria-label` for pagination controls) to custom table implementations.
