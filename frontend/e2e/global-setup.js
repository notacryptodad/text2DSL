import { chromium } from '@playwright/test';
import { TEST_USERS, loginViaAPI, registerViaAPI } from './fixtures/auth.fixture.js';
import fs from 'fs';
import path from 'path';

/**
 * Global setup script for Playwright E2E tests
 *
 * This script runs once before all tests to:
 * 1. Ensure test users exist in the database
 * 2. Authenticate each test user
 * 3. Save authentication states to .auth/*.json files
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

  // Authenticate each user and save their state
  for (const [role, credentials] of Object.entries(TEST_USERS)) {
    console.log(`🔐 Authenticating ${role} (${credentials.email})...`);

    try {
      // Try to register the user (in case they don't exist)
      try {
        await registerViaAPI(page, credentials);
        console.log(`   ✅ User registered`);
      } catch (error) {
        // User might already exist, which is fine
        if (error.message.includes('409') || error.message.includes('already exists')) {
          console.log(`   ℹ️  User already exists`);
        } else {
          console.log(`   ⚠️  Registration failed: ${error.message}`);
        }
      }

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
      const response = await page.request.get('http://localhost:8000/api/v1/health', {
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
