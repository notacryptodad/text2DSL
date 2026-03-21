## 2024-03-21 - Icon-only buttons accessibility pattern
**Learning:** Icon-only buttons without visible text must have an `aria-label` attribute on the button itself and an `aria-hidden="true"` attribute on the inner icon to be properly accessible to screen readers, especially when the icon changes dynamically (e.g., Eye vs EyeOff for password visibility toggles). Setting `aria-pressed` on toggle buttons provides extra context for state.
**Action:** Use this standard accessible pattern for any future icon-only toggle buttons in the application.
