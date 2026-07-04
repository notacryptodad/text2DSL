## 2026-07-04 - [ThemeToggle Accessibility Fix]
**Learning:** Using `aria-label` with dynamic text representing an action (e.g., "Switch to dark mode") on a toggle element confuses screen readers. It's better to name the setting itself (e.g., "Dark mode") and use `role="switch"` with `aria-checked` to communicate state changes.
**Action:** Always use `role="switch"` and `aria-checked` for state toggles, and keep the `aria-label` static to represent the noun/setting name.
