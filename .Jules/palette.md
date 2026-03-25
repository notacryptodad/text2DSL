## 2024-03-14 - Missing aria-pressed in Selectable Cards
**Learning:** Across the app, selectable cards/buttons functioning as toggles (like `ProviderSelect`) often lack `aria-pressed`. This leaves screen reader users without feedback on which option is currently selected.
**Action:** When implementing or modifying lists of selectable options that function like toggle buttons, ensure the active state is explicitly conveyed using `aria-pressed={selected === item.id}`.
