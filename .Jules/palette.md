## 2024-05-18 - Theme Toggle switch semantics
**Learning:** For state switch components like theme toggles, adding `role="switch"` and `aria-checked` provides the exact state cleanly. Most importantly, the `aria-label` must name the setting itself (e.g., "Dark mode") rather than the action (e.g., "Switch to dark mode") so screen readers announce "Dark mode, switch, checked/unchecked" instead of redundant action descriptions.
**Action:** Always name the object/setting itself on `role="switch"` controls instead of action verbs.
