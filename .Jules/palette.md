## 2026-03-08 - ARIA labels on dynamic icon buttons
**Learning:** In dynamic lists (like tags or relationships) in this app, generic 'Remove' ARIA labels aren't helpful enough for screen readers.
**Action:** When adding ARIA labels to repeating elements, always include the dynamic target name (e.g., `Remove relationship with ${rel.target_table}`) for context.
