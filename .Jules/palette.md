## 2024-05-22 - Icon-Only Button Accessibility
**Learning:** The application heavily uses `lucide-react` icons for action buttons (e.g., delete, close) without accompanying text or `aria-label` attributes, making them inaccessible to screen readers.
**Action:** When encountering icon-only buttons, always ensure an `aria-label` is present describing the specific action and context (e.g., "Remove relationship to [Table Name]").
