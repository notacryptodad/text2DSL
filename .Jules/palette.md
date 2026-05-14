## 2024-05-14 - Accessible Theme Toggle Switch
**Learning:** Using a generic `<button>` with a dynamic `aria-label` that changes text (e.g., "Switch to light mode" / "Switch to dark mode") provides confusing feedback to screen reader users because the name of the control changes underneath them. Standard `role="switch"` is much better.
**Action:** When implementing toggles for binary states (like Theme), always convert the button to `role="switch"`, set `aria-checked` to reflect the state, and use a static `aria-label` (e.g., "Dark mode") that names the setting itself rather than the action.
