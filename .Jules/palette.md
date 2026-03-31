## 2024-03-14 - Interactive Cards Need explicit aria-pressed state
**Learning:** When using buttons as selectable cards or toggle lists (like the provider selection), screen readers don't inherently know which option is currently selected just from the visual styles (e.g., border color or a check icon).
**Action:** Always add `aria-pressed={isSelected}` to interactive elements functioning as selectable cards/toggles to explicitly communicate their state to assistive technologies.
