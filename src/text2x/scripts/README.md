# Database Seed Scripts

This directory contains scripts to seed initial data into the database.

## seed_admin.py

Creates the default super admin user for the system.

### Default Admin Credentials

- **Email**: `admin@text2dsl.com`
- **Password**: `Admin123!`
- **Role**: `super_admin`

### Usage

Run this script after database migrations to create the default admin:

```bash
# From project root
python src/text2x/scripts/seed_admin.py
```

Or make it executable and run directly:

```bash
chmod +x src/text2x/scripts/seed_admin.py
./src/text2x/scripts/seed_admin.py
```

### When to Run

- **Initial Setup**: After running `alembic upgrade head` for the first time
- **CI/CD**: As part of deployment scripts before starting the application
- **Docker**: In the container startup script before running the API server
- **E2E Tests**: Before running Playwright tests (done automatically in global-setup.js)

### Idempotent

The script is idempotent - it checks if the admin exists before creating it, so it's safe to run multiple times.

### Environment Variables

The script uses the same database configuration as the main application:

- `DB_HOST` (default: localhost)
- `DB_PORT` (default: 5432)
- `DB_NAME` (default: text2x)
- `DB_USER` (default: text2x)
- `DB_PASSWORD` (default: text2x)

## Integration with E2E Tests

The E2E test suite uses the default admin to create test users:

1. Global setup logs in as the default admin
2. Admin creates test users via the admin API (`POST /api/v1/admin/users`)
3. Each test user's authentication state is saved for reuse

This approach avoids using self-registration in tests and ensures proper role-based testing.
