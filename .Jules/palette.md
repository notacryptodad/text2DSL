## 2026-02-21 - Local vs Global Keyboard Shortcuts
**Learning:** Global keyboard hooks often restrict modifier keys based on OS detection (e.g., only Cmd on Mac, only Ctrl on Windows), which can frustrate power users who expect both to work.
**Action:** For input-specific shortcuts like 'Submit', implement local `onKeyDown` handlers that support both Ctrl+Enter and Meta+Enter universally, and use `e.stopPropagation()` to prevent conflicts with global listeners.
