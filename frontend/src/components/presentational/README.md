# Presentational Components

This folder contains **presentational** (or "dumb") components that focus purely on UI rendering.

## Characteristics

- **Props in, JSX out** — No internal state management or side effects
- **No hooks** — Avoid `useState`, `useEffect`, or custom hooks
- **No data fetching** — Receive all data via props
- **Highly reusable** — Can be used anywhere with the same props
- **Easy to test** — Pure functions of their props

## Examples

```jsx
// Good: Pure presentational component
function UserCard({ name, avatar, role }) {
  return (
    <div className="flex items-center space-x-3">
      <img src={avatar} alt={name} className="w-10 h-10 rounded-full" />
      <div>
        <h3 className="font-semibold">{name}</h3>
        <p className="text-sm text-gray-500">{role}</p>
      </div>
    </div>
  )
}

// Bad: Has internal state/effects
function UserCard({ userId }) {
  const [user, setUser] = useState(null)
  useEffect(() => { fetchUser(userId).then(setUser) }, [userId])
  // ... render
}
```

## When to Use

Use presentational components for:
- Reusable UI elements (buttons, cards, badges)
- Layout components (grids, containers)
- Display-only data views
- Anything that can be a "pure function of props"

## See Also

- `../containers/README.md` — For stateful container components
