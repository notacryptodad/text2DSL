## 2024-06-10 - ThemeToggle Switch Accessibility
**Learning:** For state switch components like theme toggles, adding `role="switch"` and `aria-checked` provides the correct semantic feedback. Crucially, the `aria-label` should describe the setting itself (e.g., "Dark mode") rather than the action (e.g., "Switch to dark mode") so that screen readers announce the state correctly as "Dark mode, switch, checked/unchecked".
**Action:** Always verify that interactive switch elements are labeled with their setting name, not the action they perform, and use `role="switch"`.
