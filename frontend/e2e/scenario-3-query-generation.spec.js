import { test, expect } from '@playwright/test';
import { ChatPage } from './pages/ChatPage.js';

/**
 * Scenario 3: Query Generation Tests
 *
 * Tests basic chat page functionality.
 * Most tests skipped as they require AI backend processing.
 */
test.describe('Scenario 3: Query Generation', () => {
  // Use regular user authentication
  test.use({ storageState: './e2e/.auth/user.json' });

  test('should navigate to chat page', async ({ page }) => {
    const chatPage = new ChatPage(page);

    await chatPage.goto();

    // Verify we're on the chat page
    expect(page.url()).toContain('/app');

    // Check that basic chat elements exist
    const queryInput = page.locator('textarea');
    await expect(queryInput).toBeVisible();
  });

  // Skip tests requiring AI backend
  test.skip('should submit query and receive result', async ({ page }) => {
    // Requires AI backend processing
  });

  test.skip('should capture WebSocket progress messages', async ({ page }) => {
    const chatPage = new ChatPage(page);

    await chatPage.goto();

    // Setup WebSocket interception
    await chatPage.setupWebSocketInterception();

    // Submit a query
    await chatPage.submitQuery('Get all products with price greater than 100');

    // Wait a bit for messages to start coming in
    await page.waitForTimeout(3000);

    // Get WebSocket messages
    const messages = await chatPage.getWebSocketMessages();

    // Verify we received some messages
    expect(messages.length).toBeGreaterThan(0);

    // Log messages for debugging
    console.log('WebSocket messages received:', messages.length);
  });

  test.skip('should handle query execution and display results', async ({ page }) => {
    const chatPage = new ChatPage(page);

    await chatPage.goto();

    // Setup WebSocket interception
    await chatPage.setupWebSocketInterception();

    // Submit a query that should return data
    await chatPage.submitQuery('List the first 5 records from the main table');

    // Wait for completion
    await chatPage.waitForQueryCompletion(60000);

    // Wait for result message
    try {
      const resultMessage = await chatPage.waitForWebSocketMessage('result', 30000);
      expect(resultMessage).toBeTruthy();
    } catch (error) {
      // Result might be in different message type
      console.log('Result message not found with expected type, checking for any result');
    }

    // Verify result is displayed
    const result = await chatPage.getResult();
    expect(result).toBeTruthy();
  });

  test.skip('should handle multiple queries in sequence', async ({ page }) => {
    const chatPage = new ChatPage(page);

    await chatPage.goto();

    // First query
    await chatPage.setupWebSocketInterception();
    await chatPage.submitQuery('How many records are in the database?');
    await chatPage.waitForQueryCompletion(60000);

    let result = await chatPage.getResult();
    expect(result).toBeTruthy();

    // Clear messages for next query
    await chatPage.clearWebSocketMessages();

    // Second query
    await chatPage.submitQuery('What are the column names in the main table?');
    await chatPage.waitForQueryCompletion(60000);

    result = await chatPage.getResult();
    expect(result).toBeTruthy();
  });

  test.skip('should handle empty query submission', async ({ page }) => {
    // Behavior depends on backend
  });

  test.skip('should display query in chat history', async ({ page }) => {
    const chatPage = new ChatPage(page);

    await chatPage.goto();

    const testQuery = 'Show me test data';

    // Submit query
    await chatPage.setupWebSocketInterception();
    await chatPage.submitQuery(testQuery);
    await chatPage.waitForQueryCompletion(60000);

    // Check if query appears in the page
    const pageContent = await page.textContent('body');
    expect(pageContent).toContain(testQuery);
  });

  test.skip('should handle long-running query', async ({ page }) => {
    const chatPage = new ChatPage(page);

    await chatPage.goto();

    // Setup WebSocket interception
    await chatPage.setupWebSocketInterception();

    // Submit a complex query that might take longer
    await chatPage.submitQuery('Calculate the average, minimum, and maximum values for all numeric columns in the database');

    // Wait for completion with generous timeout
    await chatPage.waitForQueryCompletion(90000);

    // Verify we got a result
    const hasResult = await chatPage.hasResult();
    expect(hasResult).toBe(true);
  });

  test.skip('should maintain WebSocket connection', async ({ page }) => {
    const chatPage = new ChatPage(page);

    await chatPage.goto();

    // Setup WebSocket interception
    await chatPage.setupWebSocketInterception();

    // Submit first query
    await chatPage.submitQuery('Test query 1');
    await chatPage.waitForQueryCompletion(60000);

    // Check WebSocket connections were established
    const connections = await page.evaluate(() => window.wsConnections?.length || 0);
    expect(connections).toBeGreaterThan(0);

    // Clear messages
    await chatPage.clearWebSocketMessages();

    // Submit second query on same connection
    await chatPage.submitQuery('Test query 2');
    await chatPage.waitForQueryCompletion(60000);

    // Verify we got messages for second query
    const messages = await chatPage.getWebSocketMessages();
    expect(messages.length).toBeGreaterThan(0);
  });
});
