## 2024-03-22 - Avoid Nested Interactive Elements in Lists

**Learning:** When building clickable list items that also contain secondary actions (like delete buttons), using a wrapper `<div onClick={...}>` containing a `<button>` creates an accessibility anti-pattern (nested interactive elements). This breaks keyboard navigation and causes confusion for screen readers.

**Action:** Refactor these structures to use a layout container (like a flex div) with sibling `<button>` elements—one primary button for selecting the item taking up the main space, and secondary buttons alongside it. Ensure each button has its own `aria-label` and `focus-visible` styles for clear, distinct keyboard navigation.
