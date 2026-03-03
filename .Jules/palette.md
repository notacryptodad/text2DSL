## 2024-03-24 - Dynamic Pagination Indicators
**Learning:** In data tables with client-side pagination, simply adding `aria-label`s to the Previous and Next buttons isn't enough for screen reader users to understand the current state after a click. The focus remains on the button, but the content changes below.
**Action:** Always add `aria-live="polite"` to the current page text indicator (e.g., `Page 1 of 5`) when implementing pagination, so screen reader users hear the updated page number automatically after clicking Next/Previous.
