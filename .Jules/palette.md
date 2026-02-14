# Palette's Journal

## 2024-05-22 - Keyboard Shortcuts in Textareas
**Learning:** Textarea inputs in this application are often advertised to support `Ctrl+Enter` submission, but do not implement it by default. The custom `handleKeyDown` logic explicitly excluded modifier keys in some cases.
**Action:** Always verify that advertised keyboard shortcuts (especially `Ctrl+Enter` for submission) are actually implemented in the `onKeyDown` handlers for textareas.
