import { test, expect } from '@playwright/test';
import { ChatPage } from './pages/ChatPage.js';
import { TEST_QUERIES } from './fixtures/query.fixture.js';

test.describe('Scenario 6: UX Enhancements', () => {
  test.beforeEach(async ({ page }) => {
    // Mock user endpoint
    await page.route('**/api/v1/auth/me', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: 'user-1', email: 'test@example.com', role: 'user' })
      });
    });

    // Mock workspaces endpoint
    await page.route('**/api/v1/workspaces', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([{ id: 'ws-1', name: 'Test Workspace' }])
      });
    });

    // Mock workspace providers endpoint
    await page.route('**/api/v1/workspaces/*/providers', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([{ id: 'prov-1', name: 'Test Provider', type: 'postgres' }])
      });
    });

    // Mock providers endpoint (generic)
    await page.route('**/api/v1/providers', async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([{ id: 'prov-1', name: 'Test Provider', type: 'postgres' }])
        });
      });

    // Mock query stream endpoint - minimal mock to prevent errors, even if we don't fully verify the stream result
    await page.route('**/api/v1/query/stream', async route => {
      const responseBody = `data: {"event": "started", "data": {"conversation_id": "conv-1"}}

data: {"event": "progress", "data": {"stage": "query_generation", "message": "Thinking...", "progress": 0.5}}

data: {"event": "completed", "data": {"response": "Here is the result", "generated_query": "SELECT * FROM table", "execution_result": {"success": true, "row_count": 5, "execution_time_ms": 10}, "turn_id": "turn-1"}}
`;
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: responseBody
      });
    });

    // Set token and mock local storage before navigation
    await page.addInitScript(() => {
      localStorage.setItem('access_token', 'mock-token');
      localStorage.setItem('current_workspace', JSON.stringify({ id: 'ws-1', name: 'Test Workspace' }));
    });
  });

  test('should submit query using Control+Enter shortcut', async ({ page }) => {
    const chatPage = new ChatPage(page);
    await chatPage.goto();

    const queryInput = page.locator('textarea[aria-label="Query input"]');
    await queryInput.waitFor({ state: 'visible' });
    await queryInput.fill(TEST_QUERIES.simple);

    // Test Control+Enter
    await page.keyboard.press('Control+Enter');

    // Verify user message appears - this confirms submission happened
    await expect(page.locator('.bg-primary-500', { hasText: TEST_QUERIES.simple })).toBeVisible({ timeout: 10000 });
  });

  test('should submit query using Meta+Enter shortcut', async ({ page }) => {
    const chatPage = new ChatPage(page);
    await chatPage.goto();

    const queryInput = page.locator('textarea[aria-label="Query input"]');
    await queryInput.waitFor({ state: 'visible' });
    await queryInput.fill(TEST_QUERIES.count);

    // Test Meta+Enter
    await page.keyboard.press('Meta+Enter');

    // Verify user message appears
    await expect(page.locator('.bg-primary-500', { hasText: TEST_QUERIES.count })).toBeVisible({ timeout: 10000 });
  });

  test('should have aria-label on query input', async ({ page }) => {
    const chatPage = new ChatPage(page);
    await chatPage.goto();

    const queryInput = page.locator('textarea[aria-label="Query input"]');
    await expect(queryInput).toBeVisible();
  });
});
