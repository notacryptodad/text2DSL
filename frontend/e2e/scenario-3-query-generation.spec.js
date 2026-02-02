import { test, expect } from '@playwright/test';
import { ChatPage } from './pages/ChatPage.js';
import { MOCK_QUERY_RESPONSES, TEST_QUERIES, setupMockWebSocket } from './fixtures/query.fixture.js';

/**
 * Scenario 3: Query Generation Tests
 *
 * Tests query generation functionality with both mocked and real AI backend.
 * Tests with 'mock:' prefix use WebSocket mocks for predictable results.
 * Tests without prefix use real backend (skipped by default in CI).
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

  test('mock: should submit query and receive result', async ({ page }) => {
    const chatPage = new ChatPage(page);

    // Setup mock WebSocket responses
    await setupMockWebSocket(page, MOCK_QUERY_RESPONSES.simpleQuery.events);

    await chatPage.goto();
    await chatPage.setupWebSocketInterception();

    // Submit query
    await chatPage.submitQuery(TEST_QUERIES.simple);

    // Wait for completion
    await page.waitForTimeout(2500); // Wait for all mock events

    // Get WebSocket messages
    const messages = await chatPage.getWebSocketMessages();

    // Verify we received messages
    expect(messages.length).toBeGreaterThan(0);

    // Verify we got progress events
    const progressEvents = messages.filter(m => m.type === 'progress');
    expect(progressEvents.length).toBeGreaterThan(0);

    // Verify we got result event
    const resultEvent = messages.find(m => m.type === 'result');
    expect(resultEvent).toBeTruthy();
    expect(resultEvent.data.result.generated_query).toContain('SELECT');
  });

  test('mock: should capture WebSocket progress messages', async ({ page }) => {
    const chatPage = new ChatPage(page);

    // Setup mock WebSocket responses
    await setupMockWebSocket(page, MOCK_QUERY_RESPONSES.simpleQuery.events);

    await chatPage.goto();

    // Setup WebSocket interception
    await chatPage.setupWebSocketInterception();

    // Submit a query
    await chatPage.submitQuery(TEST_QUERIES.simple);

    // Wait for mock events to be delivered
    await page.waitForTimeout(2500);

    // Get WebSocket messages
    const messages = await chatPage.getWebSocketMessages();

    // Verify we received some messages
    expect(messages.length).toBeGreaterThan(0);

    // Verify progress stages
    const progressMessages = messages.filter(m => m.type === 'progress');
    expect(progressMessages.length).toBeGreaterThan(3);

    // Verify stages exist
    const stages = progressMessages.map(m => m.data.stage);
    expect(stages).toContain('schema_retrieval');
    expect(stages).toContain('query_generation');
    expect(stages).toContain('validation');
  });

  test('mock: should handle query execution and display results', async ({ page }) => {
    const chatPage = new ChatPage(page);

    // Setup mock WebSocket responses
    await setupMockWebSocket(page, MOCK_QUERY_RESPONSES.countQuery.events);

    await chatPage.goto();

    // Setup WebSocket interception
    await chatPage.setupWebSocketInterception();

    // Submit a query that should return data
    await chatPage.submitQuery(TEST_QUERIES.count);

    // Wait for mock events
    await page.waitForTimeout(2000);

    // Wait for result message
    const resultMessage = await chatPage.waitForWebSocketMessage('result', 3000);
    expect(resultMessage).toBeTruthy();
    expect(resultMessage.data.result.generated_query).toBeTruthy();
    expect(resultMessage.data.result.execution_result).toBeTruthy();
    expect(resultMessage.data.result.execution_result.success).toBe(true);
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
