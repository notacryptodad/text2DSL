## 2025-02-19 - Accessibility in Dense Editor Interfaces
**Learning:** Complex editors with multiple small interactions (like adding/removing tags or relationships) often rely on icon-only buttons to save space. These are major accessibility traps if ARIA labels are forgotten.
**Action:** When designing "dense" UIs, always audit icon-only buttons first. Adding dynamic ARIA labels (e.g., "Remove relationship to Users") instead of generic ones ("Remove") significantly improves the screen reader experience.
