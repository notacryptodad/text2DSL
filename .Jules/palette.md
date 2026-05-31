## 2024-05-31 - [ThemeToggle Accessibility]
**Learning:** For state switch components like the ThemeToggle, using `aria-label="Dark mode"` with `role="switch"` and `aria-checked` provides better screen reader feedback (e.g., "Dark mode, switch, checked/unchecked") than dynamically swapping the action text ("Switch to dark/light mode").
**Action:** Consistently use `role="switch"` and static, descriptive setting names for toggle buttons instead of dynamic action labels.
