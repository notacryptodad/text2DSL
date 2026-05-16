## 2026-05-16 - Theme Toggle Accessibility
**Learning:** When implementing state switches like a Theme toggle, setting `role="switch"` is not enough. The `aria-label` needs to describe the setting being toggled (e.g. "Dark mode") rather than the action (e.g. "Switch to dark mode"), so screen readers announce it properly as 'Dark mode, switch, checked/unchecked'.
**Action:** Audit all state toggles and ensure the label describes the state, not the action.
