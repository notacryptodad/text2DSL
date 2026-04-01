## 2024-05-24 - [Provider Select ARIA State]
**Learning:** Selectable cards masquerading as buttons (like those in ProviderSelect) need `aria-pressed` attributes so screen readers know whether they are currently active/selected.
**Action:** When using buttons as selectable list items, always apply `aria-pressed={isSelected}`.