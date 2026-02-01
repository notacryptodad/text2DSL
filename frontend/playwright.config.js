import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for Text2DSL E2E tests
 *
 * Key features:
 * - Serial execution to avoid database conflicts
 * - Test database isolation
 * - Both backend and frontend servers auto-started
 * - Pre-authenticated user states
 */
export default defineConfig({
  testDir: './e2e',

  // Global setup to authenticate users before tests
  globalSetup: './e2e/global-setup.js',

  // Timeout configuration
  timeout: 60 * 1000, // 60 seconds per test
  expect: {
    timeout: 15 * 1000, // 15 seconds for assertions
  },

  // Test execution configuration
  fullyParallel: false, // Run tests serially to avoid race conditions
  forbidOnly: !!process.env.CI, // Fail on .only() in CI
  retries: process.env.CI ? 2 : 0, // Retry failed tests in CI
  workers: 1, // Run one test at a time

  // Reporters
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['list'],
    ['json', { outputFile: 'test-results/results.json' }]
  ],

  // Shared settings for all projects
  use: {
    // Base URL for all tests
    baseURL: 'http://localhost:5173',

    // Collect trace on first retry
    trace: 'on-first-retry',

    // Screenshot on failure
    screenshot: 'only-on-failure',

    // Video on failure
    video: 'retain-on-failure',

    // Action timeout
    actionTimeout: 15 * 1000,

    // Navigation timeout
    navigationTimeout: 30 * 1000,
  },

  // Test projects - using chromium by default
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // Uncomment to test on additional browsers
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },
  ],

  // Web servers to start before running tests
  webServer: [
    // Backend server (FastAPI)
    {
      command: 'cd .. && uvicorn src.text2x.api.app:app --host 0.0.0.0 --port 8000',
      port: 8000,
      timeout: 120 * 1000,
      reuseExistingServer: !process.env.CI,
      env: {
        // Use test database
        DATABASE_URL: process.env.TEST_DATABASE_URL || 'postgresql+asyncpg://text2x:text2x@localhost:5433/text2x',

        // Authentication settings
        ENABLE_AUTH: 'true',
        ALLOW_SELF_REGISTRATION: 'true',

        // JWT settings (use consistent values for testing)
        JWT_SECRET_KEY: 'test-secret-key-for-e2e-tests-only',
        JWT_ALGORITHM: 'HS256',
        JWT_ACCESS_TOKEN_EXPIRE_MINUTES: '120',
      },
      stdout: 'pipe',
      stderr: 'pipe',
    },

    // Frontend server (Vite)
    {
      command: 'npm run dev -- --port 5173 --host',
      port: 5173,
      timeout: 120 * 1000,
      reuseExistingServer: !process.env.CI,
      stdout: 'pipe',
      stderr: 'pipe',
    },
  ],
});
