# Palette's Journal

This journal records critical UX and accessibility learnings.

## 2024-05-22 - [Initial Entry]
**Learning:** Accessibility and intuitive interactions are foundational, not optional. Users rely on keyboard navigation and screen readers more than we think.
**Action:** Always test with keyboard-only navigation and check ARIA labels.

## 2024-05-22 - Keyboard Shortcuts Expectations
**Learning:** Users expect platform-native shortcuts (Cmd+Enter on Mac, Ctrl+Enter on Windows) even if the UI text is ambiguous. Explicit handling is often required.
**Action:** Implement explicit `e.metaKey || e.ctrlKey` checks for submission actions, don't rely on browser defaults for textareas.
