## 2024-06-23 - Switch Component State Context
**Learning:** For state switch components (like a theme toggle using `role="switch"`), the `aria-label` should name the setting itself (e.g., "Dark mode") rather than the action (e.g., "Switch to dark mode"). This allows screen readers to naturally announce the state correctly (e.g., "Dark mode, switch, checked/unchecked") instead of a confusing action-based label.
**Action:** Always verify `aria-label` wording on toggle switches to ensure it describes the noun/setting rather than the verb/action.
