## 2025-05-24 - Textarea Submission UX
**Learning:** Users expect `Cmd+Enter` (Mac) or `Ctrl+Enter` (Windows) to submit forms when focused on a textarea, especially in chat or feedback interfaces.
**Action:** Always add `onKeyDown` handlers to textareas that support this shortcut, checking for `(e.metaKey || e.ctrlKey) && e.key === 'Enter'`.
