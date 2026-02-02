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

    // Setup mock WebSocket responses BEFORE navigation
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

  test('mock: should handle multiple queries in sequence', async ({ page }) => {
    const chatPage = new ChatPage(page);

    // First query - setup mock before navigation
    await setupMockWebSocket(page, MOCK_QUERY_RESPONSES.countQuery.events);
    await chatPage.goto();
    await chatPage.setupWebSocketInterception();
    await chatPage.submitQuery(TEST_QUERIES.count);

    // Wait for first query completion
    await page.waitForTimeout(2000);

    let messages = await chatPage.getWebSocketMessages();
    expect(messages.length).toBeGreaterThan(0);
    let resultMessage = messages.find(m => m.type === 'result');
    expect(resultMessage).toBeTruthy();

    // Clear messages for next query
    await chatPage.clearWebSocketMessages();

    // Second query - setup new mock and reload to apply it
    await setupMockWebSocket(page, MOCK_QUERY_RESPONSES.listColumnsQuery.events);
    await page.reload(); // Reload to apply new mock
    await chatPage.setupWebSocketInterception();
    await chatPage.submitQuery(TEST_QUERIES.listColumns);

    await page.waitForTimeout(2000);

    messages = await chatPage.getWebSocketMessages();
    expect(messages.length).toBeGreaterThan(0);
    resultMessage = messages.find(m => m.type === 'result');
    expect(resultMessage).toBeTruthy();
  });

  test('mock: should handle validation errors', async ({ page }) => {
    const chatPage = new ChatPage(page);

    // Setup mock with validation error
    await setupMockWebSocket(page, MOCK_QUERY_RESPONSES.validationErrorQuery.events);

    await chatPage.goto();
    await chatPage.setupWebSocketInterception();

    await chatPage.submitQuery(TEST_QUERIES.invalid);
    await page.waitForTimeout(2000);

    const messages = await chatPage.getWebSocketMessages();
    const resultMessage = messages.find(m => m.type === 'result');

    expect(resultMessage).toBeTruthy();
    expect(resultMessage.data.result.validation_status).toBe('invalid');
    expect(resultMessage.data.result.validation_result.errors.length).toBeGreaterThan(0);
  });

  test('mock: should handle clarification requests', async ({ page }) => {
    const chatPage = new ChatPage(page);

    // Setup mock with clarification
    await setupMockWebSocket(page, MOCK_QUERY_RESPONSES.clarificationQuery.events);

    await chatPage.goto();
    await chatPage.setupWebSocketInterception();

    await chatPage.submitQuery(TEST_QUERIES.clarification);
    await page.waitForTimeout(1500);

    const messages = await chatPage.getWebSocketMessages();
    const clarificationMessage = messages.find(m => m.type === 'clarification');

    expect(clarificationMessage).toBeTruthy();
    expect(clarificationMessage.data.questions).toBeDefined();
    expect(clarificationMessage.data.questions.length).toBeGreaterThan(0);
  });

  test('mock: should handle processing errors', async ({ page }) => {
    const chatPage = new ChatPage(page);

    // Setup mock with error
    await setupMockWebSocket(page, MOCK_QUERY_RESPONSES.processingError.events);

    await chatPage.goto();
    await chatPage.setupWebSocketInterception();

    await chatPage.submitQuery(TEST_QUERIES.error);
    await page.waitForTimeout(1500);

    const messages = await chatPage.getWebSocketMessages();
    const errorMessage = messages.find(m => m.type === 'error');

    expect(errorMessage).toBeTruthy();
    expect(errorMessage.data.error).toBeTruthy();
    expect(errorMessage.data.message).toBeTruthy();
  });

  test('mock: should display query in chat history', async ({ page }) => {
    const chatPage = new ChatPage(page);

    await setupMockWebSocket(page, MOCK_QUERY_RESPONSES.simpleQuery.events);

    await chatPage.goto();

    const testQuery = TEST_QUERIES.simple;

    // Submit query
    await chatPage.setupWebSocketInterception();
    await chatPage.submitQuery(testQuery);
    await page.waitForTimeout(2500);

    // Check if query appears in the page
    const pageContent = await page.textContent('body');
    expect(pageContent).toContain(testQuery);
  });

  test('mock: should handle low confidence queries', async ({ page }) => {
    const chatPage = new ChatPage(page);

    // Setup mock with low confidence result
    await setupMockWebSocket(page, MOCK_QUERY_RESPONSES.lowConfidenceQuery.events);

    await chatPage.goto();
    await chatPage.setupWebSocketInterception();

    await chatPage.submitQuery(TEST_QUERIES.complex);
    await page.waitForTimeout(2000);

    const messages = await chatPage.getWebSocketMessages();
    const resultMessage = messages.find(m => m.type === 'result');

    expect(resultMessage).toBeTruthy();
    expect(resultMessage.data.result.confidence_score).toBeLessThan(0.7);
    expect(resultMessage.data.result.validation_result.warnings.length).toBeGreaterThan(0);
  });

  test('mock: should track multiple iterations', async ({ page }) => {
    const chatPage = new ChatPage(page);

    // Use low confidence query which has 2 iterations
    await setupMockWebSocket(page, MOCK_QUERY_RESPONSES.lowConfidenceQuery.events);

    await chatPage.goto();
    await chatPage.setupWebSocketInterception();

    await chatPage.submitQuery(TEST_QUERIES.complex);
    await page.waitForTimeout(2000);

    const messages = await chatPage.getWebSocketMessages();
    const resultMessage = messages.find(m => m.type === 'result');

    expect(resultMessage).toBeTruthy();
    expect(resultMessage.data.result.iterations).toBeGreaterThan(1);
  });

  // Tests requiring real backend integration
  test.skip('[integration] should handle real query with backend', async ({ page }) => {
    // This test requires a real backend with AI integration
    // Run with: npx playwright test scenario-3 --grep integration
    const chatPage = new ChatPage(page);

    await chatPage.goto();
    await chatPage.setupWebSocketInterception();

    await chatPage.submitQuery('List the first 5 records from the main table');
    await chatPage.waitForQueryCompletion(60000);

    const messages = await chatPage.getWebSocketMessages();
    expect(messages.length).toBeGreaterThan(0);

    const resultMessage = await chatPage.waitForWebSocketMessage('result', 30000);
    expect(resultMessage).toBeTruthy();
  });

  test.skip('[integration] should maintain WebSocket connection across queries', async ({ page }) => {
    // This test requires a real backend with WebSocket support
    const chatPage = new ChatPage(page);

    await chatPage.goto();
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
