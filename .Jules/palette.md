## 2024-04-16 - Add aria-pressed to interactive selectable cards
**Learning:** For interactive elements functioning as selectable cards or toggle buttons (e.g., ProviderSelect), standard generic click handlers lack context for screen readers regarding the selection state.
**Action:** Explicitly set the `aria-pressed` attribute based on their selection state (`aria-pressed={selected?.id === provider.id}`) to ensure proper screen reader accessibility.
