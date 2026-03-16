## 2024-03-16 - Accessible Pagination Buttons
**Learning:** Icon-only navigation buttons in custom tables (like ChevronLeft/ChevronRight for pagination) frequently lack `aria-label` attributes and screen reader-friendly text. In `ResultsTable`, they only had a visual chevron icon, making them incomprehensible for screen reader users.
**Action:** Always check custom pagination controls and other small interaction buttons. Ensure icon-only buttons have a descriptive `aria-label` and that their inner SVG/icons have `aria-hidden="true"`.
