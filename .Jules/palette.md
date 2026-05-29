## 2024-05-29 - Missing ARIA Labels on Pagination Buttons
**Learning:** Found multiple instances where icon-only pagination/navigation buttons (like those using ChevronLeft/ChevronRight) lack ARIA labels, making them inaccessible to screen readers.
**Action:** Add descriptive aria-labels (e.g., 'Previous change', 'Next change') to all icon-only pagination and navigation buttons.
