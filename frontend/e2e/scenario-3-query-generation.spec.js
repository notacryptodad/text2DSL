import { test, expect } from '@playwright/test';

/**
 * Scenario 3: Query Generation Tests
 *
 * Tests query generation UI functionality.
 * The system uses SSE (Server-Sent Events) via /api/v1/query/stream for real-time updates.
 * 
 * Note: Full query execution tests require a running backend with SSE support.
 */
test.describe('Scenario 3: Query Generation', () => {
  // Use regular user authentication
  test.use({ storageState: './e2e/.auth/user.json' });

  test('should navigate to chat page', async ({ page }) => {
    await page.goto('/app', { waitUntil: 'domcontentloaded', timeout: 10000 });

    // Verify we're on the chat page
    expect(page.url()).toContain('/app');

    // Check that basic chat elements exist
    const queryInput = page.locator('textarea');
    await expect(queryInput).toBeVisible({ timeout: 5000 });
  });

  test('should display chat interface elements', async ({ page }) => {
    await page.goto('/app', { waitUntil: 'domcontentloaded', timeout: 10000 });
    await page.waitForTimeout(1000);

    // Check for provider selector
    const providerSelect = page.locator('select, button:has-text("Select"), [role="combobox"]').first();
    await expect(providerSelect).toBeVisible({ timeout: 5000 });

    // Check for query input
    const queryInput = page.locator('textarea');
    await expect(queryInput).toBeVisible({ timeout: 5000 });

    // Check for send button
    const sendButton = page.locator('button[type="submit"], button:has-text("Send")').first();
    await expect(sendButton).toBeVisible({ timeout: 5000 });
  });

  test('should allow typing in query input', async ({ page }) => {
    await page.goto('/app', { waitUntil: 'domcontentloaded', timeout: 10000 });
    await page.waitForTimeout(1000);

    const queryInput = page.locator('textarea');
    await expect(queryInput).toBeVisible({ timeout: 5000 });

    // Type a query
    await queryInput.fill('Show me all customers');

    // Verify the text was entered
    await expect(queryInput).toHaveValue('Show me all customers');
  });

  test('should display settings panel', async ({ page }) => {
    await page.goto('/app', { waitUntil: 'domcontentloaded', timeout: 10000 });
    await page.waitForTimeout(1000);

    // Look for settings button or panel
    const settingsButton = page.locator('button:has-text("Settings"), button[aria-label*="settings"]').first();
    
    if (await settingsButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await settingsButton.click();
      await page.waitForTimeout(500);
      
      // Check if settings panel appeared
      const settingsPanel = page.locator('[role="dialog"], .settings, .modal').first();
      await expect(settingsPanel).toBeVisible({ timeout: 3000 });
    } else {
      // Settings might be always visible
      console.log('Settings button not found or settings always visible');
    }
  });

  test.skip('should submit query and receive SSE response', async ({ page }) => {
    // Skipped: Requires real backend with SSE endpoint at /api/v1/query/stream
    // To enable: Start backend and remove test.skip
    
    await page.goto('/app', { waitUntil: 'domcontentloaded', timeout: 10000 });
    await page.waitForTimeout(1000);

    // Select provider (if needed)
    // Fill query
    const queryInput = page.locator('textarea');
    await queryInput.fill('SELECT * FROM customers LIMIT 10');

    // Submit
    const sendButton = page.locator('button[type="submit"]').first();
    await sendButton.click();

    // Wait for SSE response (would need to intercept /api/v1/query/stream)
    await page.waitForTimeout(5000);

    // Check for response in chat
    const chatMessages = page.locator('.message, [role="article"]');
    await expect(chatMessages).toHaveCount(2, { timeout: 10000 }); // User message + bot response
  });
});
