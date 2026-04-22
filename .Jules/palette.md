## 2026-04-22 - Interactive Selection Cards Need aria-pressed
**Learning:** When using `<button>` elements as selectable cards or list items (like in `ProviderSelect`), screen readers need to know which option is currently selected. Adding `aria-pressed` properly announces this state.
**Action:** Always add `aria-pressed={isSelected}` to custom selectable buttons, along with `type="button"` and `focus-visible` utility classes for complete accessibility.
