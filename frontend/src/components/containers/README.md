# Container Components

This folder contains **container** (or "smart") components that manage state and data flow.

## Characteristics

- **State management** — Use `useState`, `useReducer`, context, etc.
- **Side effects** — Handle data fetching, subscriptions, timers with `useEffect`
- **Business logic** — Coordinate between multiple components
- **Compose presentational components** — Provide data to dumb components via props

## Examples

```jsx
// Good: Container that manages state and composes presentational components
function UserListContainer() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchUsers().then(data => {
      setUsers(data)
      setLoading(false)
    })
  }, [])

  if (loading) return <LoadingSpinner />
  
  return (
    <div>
      {users.map(user => (
        <UserCard key={user.id} {...user} />  {/* presentational */}
      ))}
    </div>
  )
}
```

## When to Use

Use container components for:
- Pages and route components
- Components that fetch data
- Components managing complex state
- Components that need to coordinate multiple child components

## Pattern Benefits

Separating containers from presentational components:
1. **Improves testability** — Test UI separately from logic
2. **Increases reusability** — Presentational components work anywhere
3. **Better separation of concerns** — Clear boundaries
4. **Easier refactoring** — Change data layer without touching UI

## See Also

- `../presentational/README.md` — For stateless presentational components
