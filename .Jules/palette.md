
## 2024-05-15 - AnnotationEditor Input Accessibility
**Learning:** Tables containing inputs for inline editing (like in AnnotationEditor) often lack surrounding labels or visual indicators that screen readers can parse natively, making it a critical accessibility gap in data-heavy forms.
**Action:** When auditing data grids or inline table editing, always verify that `input` and `select` elements have explicit `aria-label` attributes describing their specific row and column context.
