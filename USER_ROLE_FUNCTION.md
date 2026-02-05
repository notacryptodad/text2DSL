# System "user" Role - Function and Purpose

## What is the "user" System Role?

The `user` system role is the **default role** for regular users. It has NO special permissions at the system level.

## Key Characteristics

### 1. Default Role
```python
# When creating a new user
role: UserRole = Field(default=UserRole.USER)

# Self-registration always creates "user" role
role=UserRole.USER  # Self-registered users are always regular users
```

### 2. No System-Level Permissions

The "user" role **cannot**:
- ❌ Manage system settings
- ❌ Manage all workspaces
- ❌ Manage all users
- ❌ Review queries across all workspaces
- ❌ Access admin endpoints

### 3. Workspace-Dependent Permissions

Users with "user" role can ONLY access resources through **workspace membership**:

```
user (system role) + workspace owner = Can manage workspace
user (system role) + workspace admin = Can manage workspace settings
user (system role) + workspace member = Can query databases
```

## Comparison with Other System Roles

| System Role | Purpose | Permissions |
|-------------|---------|-------------|
| **super_admin** | Platform administrator | Everything, bypasses workspace checks |
| **expert** | System-wide reviewer | Review queries in ALL workspaces |
| **user** | Regular user | NONE - needs workspace membership |

## Permission Flow

### For "user" Role:
1. User authenticates → Gets "user" system role
2. User tries to access workspace → System checks workspace_admins table
3. If workspace membership exists → Permissions from workspace role
4. If no workspace membership → Access denied

### For "super_admin" Role:
1. User authenticates → Gets "super_admin" system role
2. User tries to access anything → Access granted (bypasses workspace checks)

### For "expert" Role:
1. User authenticates → Gets "expert" system role
2. User tries to review queries → Access granted for ALL workspaces
3. User tries to manage workspace → Needs workspace membership

## Code Evidence

### No Endpoints Require "user" Role
```bash
# Search results:
grep -r "require_role.*user" src/text2x/api/routes/
# Result: 0 matches
```

**Meaning**: No endpoint specifically requires "user" role. It's just the default.

### Most Endpoints Use Basic Auth
```python
# 45 endpoints use basic authentication
current_user: User = Depends(get_current_active_user)
# This accepts ANY authenticated user (super_admin, expert, or user)

# 24 endpoints have specific role requirements
current_user: User = Depends(require_role("super_admin"))
current_user: User = Depends(require_expert())
# These reject "user" role
```

## Practical Example

### User with "user" System Role:

**Scenario 1: No workspace membership**
```
User: john@example.com (role: user)
Workspaces: None
Result: Can login, but cannot access any workspaces
```

**Scenario 2: Member of workspace**
```
User: john@example.com (role: user)
Workspace: "acme-corp" (role: member)
Result: Can query databases in "acme-corp" workspace
```

**Scenario 3: Admin of workspace**
```
User: john@example.com (role: user)
Workspace: "acme-corp" (role: admin)
Result: Can manage settings/connections in "acme-corp" workspace
```

### User with "expert" System Role:

**Scenario: No workspace membership needed**
```
User: expert@example.com (role: expert)
Workspaces: None
Result: Can review queries in ALL workspaces (system-wide access)
```

## Summary

### The "user" System Role:

**Function**: Default role with NO system-level permissions

**Purpose**: 
- Distinguish regular users from privileged users (super_admin, expert)
- Require explicit workspace membership for access
- Prevent accidental privilege escalation

**Analogy**: 
- `super_admin` = Root user
- `expert` = Auditor (read-only across all)
- `user` = Regular employee (needs department assignment)

**In Practice**:
- 99% of users should have "user" role
- They get permissions through workspace membership
- Only promote to expert/super_admin when needed

## Is "user" Role Necessary?

### Yes, because:

1. **Explicit default**: Makes it clear this user has no special privileges
2. **Security**: Prevents "no role" = "all access" bugs
3. **Clarity**: `if role == "user"` is clearer than `if role not in ["super_admin", "expert"]`
4. **Future-proof**: Easy to add more system roles later

### Could be removed if:
- You want "no system role" to mean "regular user"
- You're okay with implicit defaults
- You never plan to add more system roles

**Recommendation**: Keep it. Explicit is better than implicit.
