# E2E Test Setup Guide

## Overview

The E2E test suite now uses a **seeded super admin** to create test users instead of relying on self-registration. This approach:

- ✅ Avoids dependency on self-registration being enabled
- ✅ Tests the actual admin user creation flow
- ✅ Ensures proper role-based access control testing
- ✅ Provides predictable test user setup

## Default Super Admin

The system includes a default super admin account:

- **Email**: `admin@text2dsl.com`
- **Password**: `Admin123!`
- **Role**: `super_admin`

This account is created by running the seed script.

## Quick Start

### 1. Setup Backend

```bash
# Start infrastructure
docker compose up -d

# Run migrations and seed admin
make migrate seed-admin

# Or use the combined target
make run-api
```

### 2. Setup E2E Tests

```bash
# Install Playwright and dependencies
make e2e-setup
```

### 3. Run E2E Tests

```bash
# Backend must be running on http://localhost:8000
make e2e-test
```

## How It Works

### Seed Script (`src/text2x/scripts/seed_admin.py`)

- Creates the default super admin if it doesn't exist
- Idempotent - safe to run multiple times
- Runs automatically via `make run-api` or `start_server.sh`

### Global Setup (`frontend/e2e/global-setup.js`)

1. **Wait** for backend to be ready
2. **Login** as default super admin (`admin@text2dsl.com`)
3. **Create** test users via admin API:
   - `admin.user@example.com` (super_admin role)
   - `regular.user@example.com` (user role)
4. **Authenticate** each test user
5. **Save** authentication states to `.auth/*.json`

### Test Users

Defined in `frontend/e2e/fixtures/auth.fixture.js`:

```javascript
export const TEST_USERS = {
  super_admin: {
    email: 'admin@text2dsl.com',        // Default seeded admin
    password: 'Admin123!',
    role: 'super_admin',
  },
  admin: {
    email: 'admin.user@example.com',    // Created by admin
    password: 'TestAdmin123!',
    role: 'super_admin',
  },
  user: {
    email: 'regular.user@example.com',  // Created by admin
    password: 'TestUser123!',
    role: 'user',
  },
};
```

### Test Fixtures

Use pre-authenticated contexts in your tests:

```javascript
import { testAsSuperAdmin, testAsUser } from './fixtures/auth.fixture.js';

testAsSuperAdmin('admin can manage users', async ({ page }) => {
  // Page is already authenticated as super_admin
  await page.goto('/admin/users');
  // ... test admin functionality
});

testAsUser('user can view dashboard', async ({ page }) => {
  // Page is already authenticated as regular user
  await page.goto('/dashboard');
  // ... test user functionality
});
```

## Manual Testing

To test the setup manually:

```bash
# 1. Seed the admin
python src/text2x/scripts/seed_admin.py

# 2. Login as admin
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@text2dsl.com&password=Admin123!"

# 3. Create a test user (replace TOKEN with actual token)
curl -X POST http://localhost:8000/api/v1/admin/users \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{
    "email": "newuser@example.com",
    "password": "Password123!",
    "name": "New User",
    "role": "user",
    "is_active": true
  }'
```

## Makefile Targets

```bash
make migrate         # Run database migrations
make seed-admin      # Seed default admin
make run-api         # Run migrations, seed admin, start API server
make e2e-setup       # Install Playwright and dependencies
make e2e-test        # Run E2E tests (requires backend running)
```

## CI/CD Integration

In your CI/CD pipeline:

```yaml
steps:
  - name: Start infrastructure
    run: docker compose up -d

  - name: Setup database
    run: |
      make migrate
      make seed-admin

  - name: Start API server
    run: python -m uvicorn text2x.api.app:app --host 0.0.0.0 --port 8000 &

  - name: Run E2E tests
    run: make e2e-test
```

## Troubleshooting

### "Failed to login as super admin"

- Ensure the seed script has been run: `python src/text2x/scripts/seed_admin.py`
- Check database connection settings
- Verify migrations have been applied: `alembic current`

### "User creation failed: 401"

- Check that the admin token is valid
- Ensure the admin user has `super_admin` role

### Tests fail with authentication errors

- Delete `.auth/*.json` files and re-run global setup
- Ensure backend is running on http://localhost:8000
- Check that test users were created successfully

## Migration from Self-Registration

If you have existing tests using self-registration:

1. Replace `registerViaAPI()` calls with `createUserViaAdmin()`
2. Add admin token parameter from `loginViaAPI(DEFAULT_ADMIN)`
3. Update user credentials to match new `TEST_USERS`
4. Remove `ALLOW_SELF_REGISTRATION=true` from test environment

## Security Note

The default admin credentials are for **development and testing only**. In production:

1. Change the default admin password immediately after deployment
2. Use environment variables for credentials
3. Consider removing or disabling the seed script in production
4. Use proper secrets management for sensitive credentials
