## 2024-03-27 - Provider Selection Accessibility
**Learning:** Provider select lists and modals used `<button>` elements for selection cards but lacked proper `aria-pressed` state to inform screen readers of their selection status, and lacked clear `focus-visible` styles for keyboard navigation.
**Action:** Always add `aria-pressed={isSelected}` and Tailwind `focus-visible` utility rings/backgrounds to custom interactive list items built from generic elements like buttons or divs to ensure they behave like native radio buttons or checkboxes for a11y users.
