import { test as base } from '@playwright/test';

/**
 * Default super admin credentials (seeded on system startup)
 * This admin is used to create other test users
 */
export const DEFAULT_ADMIN = {
  email: 'admin@text2dsl.com',
  password: 'Admin123!',
  role: 'super_admin',
  name: 'System Administrator',
};

/**
 * Test user credentials for E2E tests
 * These users are created by the super admin during global setup
 */
export const TEST_USERS = {
  super_admin: DEFAULT_ADMIN,
  admin: {
    email: 'admin.user@example.com',
    password: 'TestAdmin123!',
    role: 'super_admin',
    name: 'Test Admin User',
  },
  user: {
    email: 'regular.user@example.com',
    password: 'TestUser123!',
    role: 'user',
    name: 'Test Regular User',
  },
};

/**
 * Extended test fixtures with pre-authenticated contexts
 *
 * Usage:
 *   test('admin can do something', async ({ authenticatedPage }) => {
 *     // Page is already authenticated as admin
 *   });
 */

// Super Admin context
export const testAsSuperAdmin = base.extend({
  storageState: './e2e/.auth/super_admin.json',
});

// Admin context
export const testAsAdmin = base.extend({
  storageState: './e2e/.auth/admin.json',
});

// Expert context
export const testAsExpert = base.extend({
  storageState: './e2e/.auth/expert.json',
});

// Regular User context
export const testAsUser = base.extend({
  storageState: './e2e/.auth/user.json',
});

/**
 * Helper function to login a user via API
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {Object} credentials - User credentials with email and password
 * @returns {Promise<string>} Access token
 */
export async function loginViaAPI(page, credentials) {
  const response = await page.request.post('http://localhost:8000/api/v1/auth/token', {
    headers: {
      'Content-Type': 'application/json',
    },
    data: {
      email: credentials.email,
      password: credentials.password,
    },
  });

  if (!response.ok()) {
    throw new Error(`Login failed for ${credentials.email}: ${response.status()} ${await response.text()}`);
  }

  const data = await response.json();
  return data.access_token;
}

/**
 * Helper function to login a user via UI
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {Object} credentials - User credentials with email and password
 */
export async function loginViaUI(page, credentials) {
  await page.goto('/login');
  await page.waitForLoadState('networkidle');

  // Fill in login form
  await page.fill('input[name="email"], input[type="email"]', credentials.email);
  await page.fill('input[name="password"], input[type="password"]', credentials.password);

  // Submit form
  await page.click('button[type="submit"]');

  // Wait for navigation after successful login
  await page.waitForURL(/\/(chat|dashboard)/, { timeout: 15000 });
}

/**
 * Helper function to create a user via admin API
 * Requires super admin authentication token
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} adminToken - Super admin access token
 * @param {Object} userData - User data with email, password, name, role
 * @returns {Promise<Object>} Created user data
 */
export async function createUserViaAdmin(page, adminToken, userData) {
  const response = await page.request.post('http://localhost:8000/api/v1/admin/users', {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${adminToken}`,
    },
    data: {
      email: userData.email,
      password: userData.password,
      name: userData.name || 'Test User',
      role: userData.role || 'user',
      is_active: true,
    },
  });

  if (!response.ok()) {
    const errorText = await response.text();
    throw new Error(`User creation failed: ${response.status()} ${errorText}`);
  }

  return await response.json();
}

/**
 * Helper function to register a new user via self-registration API
 * Note: Self-registration must be enabled in config
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {Object} userData - User data with email, password, name
 * @returns {Promise<Object>} Created user data
 * @deprecated Use createUserViaAdmin instead for E2E tests
 */
export async function registerViaAPI(page, userData) {
  const response = await page.request.post('http://localhost:8000/api/v1/users/register', {
    headers: {
      'Content-Type': 'application/json',
    },
    data: {
      email: userData.email,
      password: userData.password,
      name: userData.name || 'Test User',
    },
  });

  if (!response.ok()) {
    const errorText = await response.text();
    throw new Error(`Registration failed: ${response.status()} ${errorText}`);
  }

  return await response.json();
}

/**
 * Helper function to get current user info
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} token - Access token
 * @returns {Promise<Object>} User info
 */
export async function getCurrentUser(page, token) {
  const response = await page.request.get('http://localhost:8000/api/v1/auth/me', {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok()) {
    throw new Error(`Failed to get current user: ${response.status()}`);
  }

  return await response.json();
}
