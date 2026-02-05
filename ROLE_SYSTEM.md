# Role System Documentation

## Role Hierarchy

### System-Wide Roles (in `users` table)
Defined in `text2x.models.user.UserRole`:

1. **SUPER_ADMIN** (`super_admin`)
   - Full system access
   - Can manage all workspaces, users, and settings
   - Can access all admin endpoints
   - Bypasses all workspace-level permissions
   - Can review queries across all workspaces

2. **EXPERT** (`expert`)
   - System-wide expert role
   - Can review/approve queries across ALL workspaces
   - Can correct SQL and mark examples as good/bad
   - Cannot manage workspaces or users
   - Does NOT need workspace membership to review

3. **USER** (`user`)
   - Default role for regular users
   - **NO system-level permissions**
   - Can only access workspaces they're invited to
   - All permissions come from workspace role

### Workspace-Level Roles (in `workspace_admins` table)
Defined in `text2x.models.admin.AdminRole`:

1. **OWNER** (`owner`)
   - Full control of the workspace
   - Can manage admins/members (add/remove/change roles)
   - Can delete workspace
   - Can transfer ownership
   - Can manage workspace settings
   - Can manage providers and connections
   - **Cannot review queries** (that's expert's job)

2. **ADMIN** (`admin`)
   - Can manage workspace settings
   - Can manage providers and connections
   - **Cannot manage other admins/members**
   - **Cannot delete workspace**
   - **Cannot review queries** (that's expert's job)

3. **MEMBER** (`member`)
   - Read access to workspace
   - Can query databases
   - Can view query results
   - Cannot manage anything

**Note**: Workspace-level "expert" role has been removed to eliminate duplication with system-level expert.

## Clear Permission Matrix

| Action | super_admin | expert (system) | user + owner | user + admin | user + member | user (no workspace) |
|--------|-------------|-----------------|--------------|--------------|---------------|---------------------|
| **System-Level** |
| Manage all workspaces | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Manage all users | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| View all providers/connections | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Review queries (any workspace) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Workspace-Level** |
| Delete workspace | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Manage workspace admins | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Manage workspace settings | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| Manage providers | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| Manage connections | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| Review queries (this workspace) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Approve/reject SQL | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Correct SQL examples | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Query databases | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| View query results | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |

## Key Differences

### OWNER vs ADMIN

| Capability | OWNER | ADMIN |
|------------|-------|-------|
| Manage people (admins/members) | ✅ | ❌ |
| Delete workspace | ✅ | ❌ |
| Transfer ownership | ✅ | ❌ |
| Manage settings | ✅ | ✅ |
| Manage infrastructure | ✅ | ✅ |
| Review queries | ❌ | ❌ |

**Summary**: 
- OWNER = Can manage **people**
- ADMIN = Can manage **things**
- Both are management roles, NOT review roles

### System EXPERT vs Workspace Roles

| Capability | System EXPERT | Workspace OWNER/ADMIN |
|------------|---------------|----------------------|
| Review queries | ✅ All workspaces | ❌ |
| Manage workspace | ❌ | ✅ Their workspace |
| Needs workspace membership | ❌ | ✅ |

**Summary**: 
- EXPERT = Review role (system-wide)
- OWNER/ADMIN = Management roles (workspace-specific)
- Separate concerns: review vs management

### System USER Role

**Function**: Default role with NO permissions

**Purpose**:
- Explicit marker that user has no special privileges
- Requires workspace membership for any access
- 99% of users should have this role

**Permissions**: NONE at system level, all from workspace membership

## Role Assignment Examples

### Example 1: Regular User
```
System Role: user
Workspace: "acme-corp" (role: member)
Can: Query databases in acme-corp
Cannot: Manage anything, review queries
```

### Example 2: Workspace Administrator
```
System Role: user
Workspace: "acme-corp" (role: admin)
Can: Manage settings/connections in acme-corp
Cannot: Manage admins, review queries, access other workspaces
```

### Example 3: Workspace Owner
```
System Role: user
Workspace: "acme-corp" (role: owner)
Can: Manage everything in acme-corp including admins
Cannot: Review queries, access other workspaces
```

### Example 4: System Expert
```
System Role: expert
Workspace: None needed
Can: Review queries in ALL workspaces
Cannot: Manage workspaces, manage users
```

### Example 5: Platform Admin
```
System Role: super_admin
Workspace: None needed
Can: Everything everywhere
```

## Implementation Status

### ✅ Implemented Correctly
- System roles: super_admin, expert, user
- Workspace roles: owner, admin, member
- `can_manage_admins()` - Only OWNER returns true
- `can_manage_workspace()` - OWNER and ADMIN return true
- `require_role()` - Checks single role
- `require_any_role()` - Checks multiple roles (OR logic)
- `require_expert()` - Checks system expert only
- Workspace expert role removed (no duplication)

### ✅ No Conflicts
- No role name collisions
- Clear separation: management vs review
- System roles vs workspace roles clearly defined

## Best Practices

### 1. Default Assignment
- New users → `user` system role
- Workspace creators → `owner` workspace role
- Invited users → `member` workspace role

### 2. Promotion Guidelines
- Need to review queries → Promote to `expert` system role
- Need to manage platform → Promote to `super_admin` system role
- Need to manage workspace → Add as `admin` or `owner` in workspace

### 3. Separation of Concerns
- **Management** (owner/admin): Infrastructure, settings, people
- **Review** (expert): Query approval, SQL correction
- **Usage** (member): Query execution, view results

### 4. Multiple Roles
Users can have:
- One system role (super_admin, expert, or user)
- Multiple workspace roles (owner in workspace A, member in workspace B)
- Cannot have multiple system roles

## Migration Notes

### Removed Workspace Expert Role
- Migration `81cbfeaef060` converts workspace experts to members
- Use system expert role for query review instead
- No breaking changes to existing functionality

## Summary

**System Roles** = Platform-wide capabilities
- super_admin: Everything
- expert: Review queries everywhere
- user: Nothing (needs workspace)

**Workspace Roles** = Workspace-specific permissions
- owner: Manage people + things
- admin: Manage things only
- member: Use only

**Clear, no conflicts, no duplication.**
