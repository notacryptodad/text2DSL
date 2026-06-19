## 2026-06-19 - Theme Toggle Switch Pattern
**Learning:** For a state-switch UI element like a theme toggle button, the `aria-label` should noun-ify the setting (e.g., "Dark mode") instead of providing an action string (e.g., "Switch to dark mode"). Action strings combined with the `switch` role make screen readers announce confusing combinations like "Switch to dark mode, switch, off".
**Action:** When converting toggle buttons to `role="switch"`, ensure the label names the setting itself rather than describing the action.
