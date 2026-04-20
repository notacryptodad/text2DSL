## 2024-04-20 - Selectable Cards Accessibility
**Learning:** List items functioning as selectable cards/toggles require explicit state indication and keyboard focus visibility to be accessible. A generic 'button' role is not enough.
**Action:** Always add `aria-pressed` based on selection state and use `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500` for clear keyboard navigation focus states on selectable items.
