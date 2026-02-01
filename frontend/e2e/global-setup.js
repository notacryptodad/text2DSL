import { chromium } from '@playwright/test';
import { TEST_USERS, DEFAULT_ADMIN, loginViaAPI, createUserViaAdmin } from './fixtures/auth.fixture.js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

/**
 * Global setup script for Playwright E2E tests
 *
 * This script runs once before all tests to:
 * 1. Login as the default super admin (seeded on startup)
 * 2. Use super admin to create other test users via admin API
 * 3. Authenticate each test user
 * 4. Save authentication states to .auth/*.json files
 *
 * These saved states are then reused across tests to avoid repeated logins.
 */
async function globalSetup() {
  console.log('\n🔧 Running global setup...\n');

  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  const authDir = path.join(__dirname, '.auth');

  // Ensure .auth directory exists
  if (!fs.existsSync(authDir)) {
    fs.mkdirSync(authDir, { recursive: true });
  }

  // Wait for backend to be ready
  console.log('⏳ Waiting for backend to be ready...');
  await waitForBackend(page);
  console.log('✅ Backend is ready\n');

  // Step 1: Login as default super admin
  console.log(`🔐 Logging in as default super admin (${DEFAULT_ADMIN.email})...`);
  let adminToken;
  try {
    adminToken = await loginViaAPI(page, DEFAULT_ADMIN);
    console.log('   ✅ Super admin login successful\n');
  } catch (error) {
    console.error(`   ❌ Failed to login as super admin: ${error.message}`);
    console.error('   Make sure the seed script has been run: python src/text2x/scripts/seed_admin.py\n');
    await browser.close();
    process.exit(1);
  }

  // Step 2: Create test users via admin API
  for (const [role, credentials] of Object.entries(TEST_USERS)) {
    // Skip the super_admin as it's the default admin
    if (role === 'super_admin') {
      console.log(`ℹ️  Skipping ${role} - using default admin\n`);
      continue;
    }

    console.log(`👤 Creating test user ${role} (${credentials.email})...`);

    try {
      // Try to create the user via admin API
      await createUserViaAdmin(page, adminToken, credentials);
      console.log(`   ✅ User created successfully\n`);
    } catch (error) {
      // User might already exist, which is fine
      if (error.message.includes('409') || error.message.includes('already exists')) {
        console.log(`   ℹ️  User already exists\n`);
      } else {
        console.log(`   ⚠️  User creation failed: ${error.message}\n`);
      }
    }
  }

  // Step 3: Authenticate each user and save their state
  for (const [role, credentials] of Object.entries(TEST_USERS)) {
    console.log(`🔐 Authenticating ${role} (${credentials.email})...`);

    try {
      // Login and get token
      const token = await loginViaAPI(page, credentials);
      console.log(`   ✅ Login successful`);

      // Store token in localStorage
      await page.goto('http://localhost:5173');
      await page.evaluate((tokenValue) => {
        localStorage.setItem('access_token', tokenValue);
      }, token);

      // Save storage state to file
      const statePath = path.join(authDir, `${role}.json`);
      await context.storageState({ path: statePath });
      console.log(`   ✅ Storage state saved to ${statePath}\n`);
    } catch (error) {
      console.error(`   ❌ Failed to setup ${role}: ${error.message}\n`);
      // Continue with other users even if one fails
    }
  }

  await browser.close();
  console.log('✅ Global setup complete!\n');
}

/**
 * Wait for backend to be ready by polling the health endpoint
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 */
async function waitForBackend(page, maxRetries = 30) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await page.request.get('http://localhost:8000/health', {
        timeout: 5000,
      });

      if (response.ok()) {
        return;
      }
    } catch (error) {
      // Backend not ready yet
    }

    // Wait 2 seconds before retrying
    await new Promise(resolve => setTimeout(resolve, 2000));
  }

  throw new Error('Backend did not become ready in time');
}

export default globalSetup;
