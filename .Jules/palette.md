## 2025-05-15 - Icon-only Buttons Missing ARIA Labels
**Learning:** Found several high-value interactive elements (copy, download, trace toggle) that relied solely on `title` or visual cues (icons) without screen reader support.
**Action:** When auditing components, specifically check all icon-only buttons for `aria-label` or `aria-expanded` attributes, as `title` is insufficient for accessibility.
