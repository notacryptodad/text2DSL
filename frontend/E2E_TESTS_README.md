# Playwright E2E Tests - Text2DSL

## Overview

Comprehensive end-to-end test suite for the Text2DSL application using Playwright. The test suite covers 6 user scenarios across user management, admin setup, schema annotation, query generation with WebSocket, review queue, and feedback functionality.

## Installation

Playwright and all dependencies have been installed:

```bash
npm install -D @playwright/test  # Already installed
npx playwright install           # Browser binaries installed
```

## Test Structure

```
frontend/e2e/
├── .auth/                               # Stored authentication states (gitignored)
│   ├── super_admin.json
│   ├── admin.json
│   ├── expert.json
│   └── user.json
├── fixtures/
│   └── auth.fixture.js                  # Authentication helpers and test users
├── pages/                               # Page Object Models
│   ├── LoginPage.js                     # Login page interactions
│   ├── ChatPage.js                      # Query/chat with WebSocket support
│   ├── ReviewPage.js                    # Review queue management
│   └── AdminDashboardPage.js            # Admin dashboard operations
├── global-setup.js                      # Pre-test authentication
├── scenario-0-user-management.spec.js   # User login and access control
├── scenario-1-admin-setup.spec.js       # Workspace, provider, connection setup
├── scenario-2-schema-annotation.spec.js # Schema annotation features
├── scenario-3-query-generation.spec.js  # Query generation with WebSocket
├── scenario-4-review-queue.spec.js      # Review queue operations
└── scenario-5-feedback.spec.js          # Feedback submission and stats
```

## Configuration

**File:** `playwright.config.js`

Key features:
- **Base URL:** http://localhost:5173
- **Serial execution:** Workers set to 1 to avoid race conditions
- **Test database:** Uses `text2dsl_test` (separate from dev database)
- **Auto-start servers:** Both backend (port 8000) and frontend (port 5173)
- **Authentication:** Pre-authenticated states for all user roles
- **Timeouts:** 60s per test, 15s for actions
- **Reporters:** HTML, list, and JSON

## Test Users

Four test users are created during global setup:

| Role         | Email                    | Password       |
|--------------|--------------------------|----------------|
| Super Admin  | super@text2dsl.local     | SuperAdmin123! |
| Admin        | admin@text2dsl.local     | Admin123!      |
| Expert       | expert@text2dsl.local    | Expert123!     |
| User         | user@text2dsl.local      | User123!       |

## Running Tests

### All tests
```bash
npm run test:e2e
```

### Headed mode (see browser)
```bash
npm run test:e2e:headed
```

### Debug mode
```bash
npm run test:e2e:debug
```

### UI mode (interactive)
```bash
npm run test:e2e:ui
```

### Specific scenario
```bash
npx playwright test scenario-0-user-management
npx playwright test scenario-3-query-generation --headed
```

### View test report
```bash
npm run test:e2e:report
```

## Test Scenarios

### Scenario 0: User Management
- ✅ User login with valid credentials
- ✅ Error handling for invalid credentials
- ✅ Super admin access to admin dashboard
- ✅ Regular user access restrictions
- ✅ User information display
- ✅ Logout functionality

### Scenario 1: Admin Setup
**Tests run serially with shared state**
- ✅ Create workspace
- ✅ Create PostgreSQL provider
- ✅ Add database connection
- ✅ Test connection
- ✅ Refresh database schema
- ✅ Verify resources in admin dashboard

### Scenario 2: Schema Annotation
- ✅ Navigate to schema annotation page
- ✅ Display database tables
- ✅ Request auto-annotation
- ✅ Save manual annotation
- ✅ Multi-turn chat for assistance
- ✅ View table details
- ✅ Search for tables
- ✅ Export annotations

### Scenario 3: Query Generation
**Complex WebSocket testing**
- ✅ Submit query and receive result
- ✅ Capture WebSocket progress messages
- ✅ Handle query execution
- ✅ Multiple queries in sequence
- ✅ Empty query validation
- ✅ Display query in chat history
- ✅ Handle long-running queries
- ✅ Maintain WebSocket connection

### Scenario 4: Review Queue
- ✅ Navigate to review queue
- ✅ Display queue items
- ✅ Create test item via negative feedback
- ✅ Approve queries
- ✅ Reject queries with feedback
- ✅ Correct and approve queries
- ✅ Filter by status
- ✅ Display item details
- ✅ Handle empty queue
- ✅ Refresh queue

### Scenario 5: Feedback
- ✅ Thumbs up feedback
- ✅ Thumbs down with detailed feedback
- ✅ Different feedback categories
- ✅ Verify review queue integration
- ✅ View feedback statistics
- ✅ Multiple feedback submissions
- ✅ Cancel feedback modal
- ✅ Form validation

## Key Features

### WebSocket Testing
The ChatPage POM includes sophisticated WebSocket interception:

```javascript
await chatPage.setupWebSocketInterception();
await chatPage.submitQuery('Your question');
await chatPage.waitForQueryCompletion(60000);

// Get captured messages
const messages = await chatPage.getWebSocketMessages();

// Wait for specific message type
const result = await chatPage.waitForWebSocketMessage('result', 30000);
```

### Authentication Strategy
- **Global Setup:** Authenticates all users once before tests
- **Storage States:** Saved to `.auth/*.json` files
- **Test Reuse:** Tests load pre-authenticated state
- **No Repeated Logins:** Faster test execution

### Page Object Model Pattern
Reusable, maintainable page interactions:

```javascript
const chatPage = new ChatPage(page);
await chatPage.goto();
await chatPage.submitQuery('Show me data');
const result = await chatPage.getResult();
```

### Serial Execution
Tests run one at a time to prevent:
- Database race conditions
- WebSocket connection conflicts
- Shared resource contention

## Environment Variables

Optional environment variables for database connection:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/text2dsl_test
TEST_DB_HOST=localhost
TEST_DB_PORT=5432
TEST_DB_NAME=text2dsl_test
TEST_DB_USER=postgres
TEST_DB_PASSWORD=postgres
```

## Troubleshooting

### Backend not starting
```bash
# Check if port 8000 is already in use
lsof -i :8000

# Or manually start backend before tests
cd .. && uvicorn src.text2x.api.app:app --port 8000
```

### Frontend not starting
```bash
# Check if port 5173 is in use
lsof -i :5173

# Or manually start frontend
npm run dev -- --port 5173
```

### Authentication failing
```bash
# Re-run global setup manually
node e2e/global-setup.js
```

### Test database issues
```bash
# Create test database if it doesn't exist
createdb text2dsl_test

# Or run backend migrations on test database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/text2dsl_test \
  alembic upgrade head
```

### WebSocket tests timing out
- Increase timeout in test: `await chatPage.waitForQueryCompletion(120000)`
- Check backend logs for errors
- Verify WebSocket endpoint is accessible

### System dependencies warning
If you see Playwright host validation warnings:

```bash
sudo npx playwright install-deps
```

## CI/CD Integration

The test suite is CI-ready:
- Uses `process.env.CI` to adjust behavior
- Retries failed tests 2 times in CI
- Does not reuse existing servers in CI
- Generates JSON report for CI parsing

Example GitHub Actions workflow:

```yaml
- name: Install dependencies
  run: cd frontend && npm ci

- name: Install Playwright browsers
  run: cd frontend && npx playwright install --with-deps

- name: Run E2E tests
  run: cd frontend && npm run test:e2e
  env:
    CI: true

- name: Upload test results
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: playwright-report
    path: frontend/playwright-report/
```

## Best Practices

### Test Isolation
- Each test should be independent
- Use serial execution for setup scenarios
- Clean up test data when possible

### Selectors
- Use flexible selectors (text content, aria-labels)
- Avoid fragile selectors (CSS classes, IDs)
- Prefer semantic HTML attributes

### Waiting
- Use `page.waitForLoadState('networkidle')` after navigation
- Use `element.waitFor({ state: 'visible' })` for dynamic content
- Avoid `page.waitForTimeout()` except as last resort

### Debugging
- Use `--headed` to see browser
- Use `--debug` to step through tests
- Use `page.pause()` to add breakpoints
- Check screenshots in `test-results/` on failure

## Maintenance

### Adding New Tests
1. Create spec file in `e2e/` directory
2. Import necessary POMs and fixtures
3. Use appropriate authentication state
4. Follow existing patterns

### Updating POMs
When UI changes, update selectors in page objects rather than in tests.

### Test Data
Consider adding test data fixtures in `e2e/fixtures/` for complex scenarios.

## Performance

- **Global setup:** ~30-60 seconds (one time)
- **Scenario 0:** ~30-60 seconds
- **Scenario 1:** ~60-120 seconds (serial, creates resources)
- **Scenario 2:** ~60-90 seconds
- **Scenario 3:** ~90-180 seconds (WebSocket, AI processing)
- **Scenario 4:** ~60-90 seconds
- **Scenario 5:** ~60-90 seconds

**Total runtime:** ~6-10 minutes for full suite

## Known Limitations

1. **AI dependencies:** Query generation tests depend on AI model availability
2. **Database state:** Tests assume fresh database or proper migrations
3. **WebSocket timing:** Real-time tests may be slower on CI
4. **Browser dependencies:** System must have required libraries installed

## Support

For issues or questions:
1. Check test output and screenshots in `test-results/`
2. Review HTML report: `npm run test:e2e:report`
3. Enable debug mode: `npm run test:e2e:debug`
4. Check backend logs for API errors

## Future Enhancements

Potential improvements:
- [ ] Add visual regression testing
- [ ] Add performance benchmarks
- [ ] Add accessibility testing
- [ ] Add API response mocking for faster tests
- [ ] Add test data seeding utilities
- [ ] Add cross-browser testing (Firefox, WebKit)
- [ ] Add mobile viewport testing
