
## 2024-05-18 - [ThemeToggle Accessibility]
**Learning:** Toggle switches for theme or options in React/Tailwind applications should include `role="switch"` and `aria-checked` properties. Setting `aria-label` to the state itself (e.g., "Dark mode") provides clearer semantics for screen readers than the action string (e.g., "Switch to dark mode") since screen readers will announce "Dark mode, switch, checked/unchecked".
**Action:** Always implement boolean toggles using `role="switch"` and `aria-checked`. Set the label to the name of the toggle setting instead of an action verb.
