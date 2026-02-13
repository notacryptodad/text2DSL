# Palette's Journal

## 2026-02-13 - Keyboard Shortcut Consistency
**Learning:** Users rely on modifier keys like Ctrl/Cmd+Enter for form submission in textareas, even when helper text explicitly promises it. Implementations often miss checking for `metaKey` or `ctrlKey`.
**Action:** Always verify keyboard event handlers account for platform-specific modifier keys when implementing shortcuts.
