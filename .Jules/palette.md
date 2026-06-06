## 2024-06-06 - Accessible Theme Toggle
**Learning:** State switch components (like a theme toggle using `role="switch"`) need their `aria-label` to name the setting itself (e.g., "Dark mode") rather than the action (e.g., "Switch to dark mode") so screen readers announce the state correctly (e.g., "Dark mode, switch, checked/unchecked").
**Action:** When converting buttons to switches, ensure the aria-label is a noun phrase representing the setting, not an action phrase.
