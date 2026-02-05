# Admin Endpoints Fix - Summary

## Problem
Frontend was calling `/api/v1/admin/providers` and `/api/v1/admin/connections` which returned 404.

## Root Cause
These endpoints didn't exist. Only workspace-scoped endpoints existed:
- `/api/v1/workspaces/{workspace_id}/providers`
- `/api/v1/workspaces/{workspace_id}/providers/{provider_id}/connections`

## Solution
Added flat admin endpoints that list ALL providers/connections across workspaces.

## Changes Made

### 1. Added Admin Endpoints (`src/text2x/api/routes/admin.py`)

```python
@router.get("/admin/providers")
async def list_all_providers(
    current_user: User = Depends(require_any_role(["super_admin", "admin", "expert"])),
) -> list[dict]:
    """List all providers across all workspaces (admin only)."""

@router.get("/admin/connections")
async def list_all_connections(
    current_user: User = Depends(require_any_role(["super_admin", "admin", "expert"])),
) -> list[dict]:
    """List all connections across all providers (admin only)."""
```

### 2. Fixed Role System (`src/text2x/api/auth.py`)

**Added `require_any_role()` helper:**
```python
def require_any_role(allowed_roles: list[str]):
    """Require ANY of the specified roles (OR logic)."""
```

**Fixed `require_role()` to use `role` field instead of `roles`:**
```python
def require_role(required_role: str):
    user_role = current_user.role  # Was: current_user.roles
    if user_role != required_role:
        raise HTTPException(...)
```

**Fixed `require_expert()` similarly.**

## Role System Clarification

### System-Wide Roles (users table)
1. **super_admin** - Full system access, can do everything
2. **expert** - System-wide expert, can review queries in ALL workspaces
3. **user** - Regular user, needs workspace membership

### Workspace-Level Roles (workspace_admins table)
1. **owner** - Full workspace control, can manage admins
2. **admin** - Can manage workspace settings/connections
3. **expert** - Can review queries in THIS workspace only
4. **member** - Read access, can query databases

### Permission Examples
- `/admin/providers` - Requires: super_admin OR expert (system-level)
- `/workspaces/{id}/providers` - Requires: workspace owner OR admin
- Review endpoints - Requires: super_admin OR expert (system) OR workspace expert

## Testing

```bash
# Login as super_admin
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@text2dsl.com","password":"Admin123!"}' | jq -r .access_token)

# List all providers
curl -s http://localhost:8000/api/v1/admin/providers \
  -H "Authorization: Bearer $TOKEN" | jq .

# List all connections
curl -s http://localhost:8000/api/v1/admin/connections \
  -H "Authorization: Bearer $TOKEN" | jq .
```

## Status
✅ Admin endpoints working
✅ Role system fixed
✅ Multi-role support added
✅ Frontend 404 errors resolved
