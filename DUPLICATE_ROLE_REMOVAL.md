# Duplicate Role Removal - Summary

## Change Made

**Removed workspace-level "expert" role** to eliminate duplication with system-level expert.

## Before (Duplicated)

### System Roles
- super_admin
- **expert** ← System-wide reviewer
- user

### Workspace Roles  
- owner
- admin
- **expert** ← Workspace-specific reviewer (DUPLICATE!)
- member

## After (Clean)

### System Roles
- super_admin
- **expert** ← Only expert role (system-wide)
- user

### Workspace Roles
- owner
- admin
- member

## Rationale

1. **Eliminates confusion**: One "expert" role with clear scope
2. **Simplifies permissions**: Expert = can review queries (system-wide)
3. **Clearer separation**: Workspace roles = management, System roles = capabilities

## Migration

Created migration `81cbfeaef060_remove_workspace_expert_role.py`:
- Converts existing workspace experts to members
- Preserves data (no deletion)

## Code Changes

### 1. Model (`src/text2x/models/admin.py`)
```python
class AdminRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    # EXPERT = "expert"  ← REMOVED
    MEMBER = "member"
```

### 2. Auth (`src/text2x/api/auth.py`)
- `require_expert()`: Now only checks system-level expert
- `check_workspace_expert()`: Simplified to system-level only

## Impact

### ✅ No Breaking Changes
- Existing workspace experts converted to members
- System experts unchanged
- All review functionality still works

### ⚠️ Behavioral Change
- Users who were workspace experts can no longer review queries
- Must be promoted to system expert role to review

## New Permission Model

| Role | Scope | Can Review Queries |
|------|-------|-------------------|
| super_admin | System | ✅ All workspaces |
| expert | System | ✅ All workspaces |
| user + owner | Workspace | ❌ |
| user + admin | Workspace | ❌ |
| user + member | Workspace | ❌ |

**To enable query review**: Promote user to system-level "expert" role.

## Upgrade Path

If you need workspace-specific review permissions:
1. Create system expert users
2. Assign them to specific workspaces as members
3. Implement workspace filtering in review UI (optional)

## Files Changed

1. `src/text2x/models/admin.py` - Removed AdminRole.EXPERT
2. `src/text2x/api/auth.py` - Updated require_expert() and check_workspace_expert()
3. `src/text2x/migrations/versions/81cbfeaef060_remove_workspace_expert_role.py` - Migration

## Testing

```bash
# Verify migration ran
uv run alembic current

# Check no workspace experts remain
psql -d text2dsl -c "SELECT role, COUNT(*) FROM workspace_admins GROUP BY role;"

# Should show: owner, admin, member (no expert)
```

## Status
✅ Migration applied
✅ Backend restarted
✅ No duplicate roles
