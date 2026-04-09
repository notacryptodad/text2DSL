## 2024-04-09 - Provider Select Accessibility
**Learning:** The `<button>` elements used for selectable cards (like in `ProviderSelect`) should use `aria-pressed` to correctly announce their selected state to screen readers. They also lacked clear visual focus states for keyboard navigation.
**Action:** When using buttons as toggleable items or selectable cards, always ensure `aria-pressed` reflects the current selection state, and apply `focus-visible` ring utility classes (e.g. `focus-visible:ring-primary-500`) to improve keyboard navigation accessibility.
