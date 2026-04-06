## 2024-04-06 - Accessible Selectable Cards
**Learning:** When interactive elements function as selectable cards or toggle buttons (e.g., in a list of selectable providers where only one is active), using `aria-pressed="true"` or `aria-pressed="false"` explicitly communicates their selection state to screen readers better than visual cues alone.
**Action:** Always add `aria-pressed={isSelected}` to `<button>` elements that act as mutually exclusive selection toggles or list options within a group.
