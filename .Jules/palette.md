
## 2024-05-20 - Selectable Cards and Dynamic Text Updates
**Learning:** Selectable cards without native radio button semantics (e.g. `ProviderSelect`) need `aria-pressed` or `aria-selected` to convey state to screen readers. Dynamic updates in tables like `ResultsTable` pagination changes need `aria-live="polite"` so screen readers announce the new page count or status.
**Action:** When creating or fixing custom selectable cards/buttons or dynamic text indicators (like pagination), explicitly set `aria-pressed` based on selection state, and use `aria-live="polite"` on the text element to ensure changes are announced.
