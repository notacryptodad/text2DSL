# Role System Analysis & Clarification

## Issues Found

### ❌ CONFLICT 1: Permission Matrix Inconsistency

**Problem**: The permission matrix shows workspace OWNER and ADMIN can both review queries, but this conflicts with the EXPERT role's purpose.

**Current Matrix Says**:
- Workspace OWNER: Can review queries ✅
- Workspace ADMIN: Can review queries ✅  
- Workspace EXPERT: Can review queries ✅

**Issue**: If OWNER and ADMIN can review, why have EXPERT role?

**Recommendation**: Only EXPERT should review queries. OWNER/ADMIN manage infrastructure.

---

### ❌ CONFLICT 2: "admin" Role Name Collision

**Problem**: "admin" exists at TWO levels:
1. System-wide: Not defined in UserRole enum (missing!)
2. Workspace-level: AdminRole.ADMIN

**Current Code**:
```python
# System roles (UserRole enum)
SUPER_ADMIN = "super_admin"
EXPERT = "expert"
USER = "user"
# ❌ No "admin" here!

# Workspace roles (AdminRole enum)  
OWNER = "owner"
ADMIN = "admin"  # ← Collision!
EXPERT = "expert"  # ← Also collision!
MEMBER = "member"
```

**Issue**: `require_any_role(["super_admin", "admin"])` is ambiguous - which admin?

---

### ❌ CONFLICT 3: EXPERT Role Duplication

**Problem**: "expert" exists at BOTH levels with different scopes:
- System EXPERT: Reviews ALL workspaces
- Workspace EXPERT: Reviews ONE workspace

**Current Implementation**: Works but confusing naming.

---

## Recommended Role System (Fixed)

### System-Wide Roles (users.role)

| Role | Code | Purpose | Key Permissions |
|------|------|---------|-----------------|
| **Super Admin** | `super_admin` | Platform administrator | Everything |
| **System Expert** | `expert` | Cross-workspace reviewer | Review queries in ALL workspaces |
| **User** | `user` | Regular user | Access via workspace membership |

### Workspace-Level Roles (workspace_admins.role)

| Role | Code | Purpose | Key Permissions |
|------|------|---------|-----------------|
| **Owner** | `owner` | Workspace creator/owner | Manage admins, settings, infrastructure |
| **Admin** | `admin` | Workspace administrator | Manage settings, infrastructure (NOT admins) |
| **Expert** | `expert` | Workspace reviewer | Review queries in THIS workspace only |
| **Member** | `member` | Workspace user | Query databases, view results |

---

## Key Difference: OWNER vs ADMIN

### OWNER Can:
1. ✅ Add/remove/change other admins and members
2. ✅ Delete the workspace
3. ✅ Transfer ownership
4. ✅ Manage workspace settings
5. ✅ Manage providers and connections
6. ❌ Review queries (unless also EXPERT)

### ADMIN Can:
1. ❌ Manage other admins/members
2. ❌ Delete workspace
3. ❌ Transfer ownership
4. ✅ Manage workspace settings
5. ✅ Manage providers and connections
6. ❌ Review queries (unless also EXPERT)

### EXPERT Can:
1. ❌ Manage admins/members
2. ❌ Manage settings
3. ❌ Manage infrastructure
4. ✅ Review queries
5. ✅ Approve/reject SQL
6. ✅ Correct SQL examples
7. ✅ Mark queries as good/bad

### MEMBER Can:
1. ❌ Manage anything
2. ✅ Query databases
3. ✅ View query results
4. ✅ View workspace resources

---

## Clear Permission Matrix (Corrected)

| Action | super_admin | expert (system) | user + owner | user + admin | user + expert | user + member |
|--------|-------------|-----------------|--------------|--------------|---------------|---------------|
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
| Review queries (this workspace) | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
| Approve/reject SQL | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
| Correct SQL examples | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
| Query databases | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| View query results | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## Implementation Status

### ✅ Correctly Implemented
- `can_manage_admins()` - Only OWNER returns true
- `can_manage_workspace()` - OWNER and ADMIN return true
- System EXPERT can access review endpoints
- Workspace EXPERT can review in their workspace

### ⚠️ Needs Clarification
- Should OWNER/ADMIN be able to review queries?
  - **Current**: Yes (permission matrix says yes)
  - **Recommended**: No (that's EXPERT's job)
  
### ❌ Missing
- System-level "admin" role (if needed)
- Clear separation of review permissions from management permissions

---

## Recommendations

### 1. Separate Concerns
- **Management roles** (OWNER, ADMIN): Infrastructure only
- **Review roles** (EXPERT): Query review only
- **User role** (MEMBER): Query execution only

### 2. Allow Multiple Roles
A user can have MULTIPLE workspace roles:
- User can be both ADMIN and EXPERT
- User can be OWNER and EXPERT
- This allows flexibility without role confusion

### 3. Rename for Clarity (Optional)
Consider renaming to avoid confusion:
- System EXPERT → `system_reviewer`
- Workspace EXPERT → `workspace_reviewer`

But current naming is acceptable if documented clearly.

---

## Summary

**OWNER vs ADMIN**: 
- OWNER = Can manage people (admins/members)
- ADMIN = Can manage things (settings/infrastructure)
- Both are management roles, NOT review roles

**EXPERT**:
- Separate role for query review
- Exists at both system and workspace level
- Should NOT have management permissions

**Current Issues**:
1. Permission matrix shows OWNER/ADMIN can review (conflicts with EXPERT purpose)
2. No system-level "admin" role defined (but used in code)
3. Role name collisions between system and workspace levels
