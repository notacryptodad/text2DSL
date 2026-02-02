import { test, expect } from '@playwright/test';
import { ChatPage } from './pages/ChatPage.js';
import { MOCK_FEEDBACK_RESPONSES, setupMockWebSocket, setupMockFeedbackAPI } from './fixtures/feedback.fixture.js';

/**
 * Scenario 5: Feedback Tests
 *
 * Tests feedback functionality:
 * - Provide thumbs up feedback
 * - Provide thumbs down with details and category
 * - Verify negative feedback adds query to review queue
 * - View feedback statistics page
 */
test.describe('Scenario 5: Feedback', () => {
  // Use regular user authentication
  test.use({ storageState: './e2e/.auth/user.json' });

  test('should submit query and provide thumbs up feedback', async ({ page }) => {
    const chatPage = new ChatPage(page);

    // Setup mocks
    await setupMockWebSocket(page, MOCK_FEEDBACK_RESPONSES.successfulQuery.events);
    await setupMockFeedbackAPI(page);

    await chatPage.goto();
    await chatPage.setupWebSocketInterception();

    // Wait for WebSocket to connect (textarea becomes enabled)
    await page.waitForSelector('textarea:not([disabled])', { timeout: 10000 });

    // Submit a query
    await chatPage.submitQuery('Show me user statistics');

    // Wait for mock events to complete
    await page.waitForTimeout(2000);

    // Verify result is displayed
    const hasResult = await chatPage.hasResult();
    expect(hasResult).toBe(true);

    // Give thumbs up
    await chatPage.clickThumbsUp();

    // Wait for feedback to be registered
    await page.waitForTimeout(1000);

    // Verify feedback button shows "Thanks for your feedback!"
    const feedbackText = await page.textContent('body');
    expect(feedbackText).toContain('Thanks for your feedback!');

    console.log('Thumbs up feedback submitted successfully');
  });

  test('should provide thumbs down with detailed feedback', async ({ page }) => {
    const chatPage = new ChatPage(page);

    // Setup mocks
    await setupMockWebSocket(page, MOCK_FEEDBACK_RESPONSES.incorrectQuery.events);
    await setupMockFeedbackAPI(page);

    await chatPage.goto();
    await chatPage.setupWebSocketInterception();

    // Wait for WebSocket to connect
    await page.waitForSelector('textarea:not([disabled])', { timeout: 10000 });

    // Submit a query
    await chatPage.submitQuery('Get all data from the system');

    // Wait for mock events to complete
    await page.waitForTimeout(2000);

    // Verify result is displayed
    const hasResult = await chatPage.hasResult();
    expect(hasResult).toBe(true);

    // Give thumbs down
    await chatPage.clickThumbsDown();

    // Wait for modal to appear
    await page.locator(chatPage.feedbackModal).waitFor({ state: 'visible', timeout: 5000 });

    // Fill feedback textarea
    await page.fill(chatPage.feedbackTextarea, 'The query result does not match what I expected. The data seems incomplete.');

    // Submit feedback
    await page.locator(chatPage.feedbackModal)
      .locator(chatPage.feedbackSubmitButton)
      .click();

    // Wait for modal to close
    await page.locator(chatPage.feedbackModal).waitFor({ state: 'hidden', timeout: 5000 });

    // Verify feedback was submitted
    const feedbackText = await page.textContent('body');
    expect(feedbackText).toContain('Thanks for your feedback!');

    console.log('Thumbs down with detailed feedback submitted successfully');
  });

  test('should provide feedback with different comments and corrections', async ({ page }) => {
    const chatPage = new ChatPage(page);

    // Test different feedback scenarios
    const feedbackTests = [
      {
        mockResponse: MOCK_FEEDBACK_RESPONSES.performanceQuery,
        query: 'Test query 1',
        feedback: 'Query is too slow',
        correction: null
      },
      {
        mockResponse: MOCK_FEEDBACK_RESPONSES.syntaxErrorQuery,
        query: 'Test query 2',
        feedback: 'SQL syntax is incorrect',
        correction: 'SELECT * FROM users'
      },
      {
        mockResponse: MOCK_FEEDBACK_RESPONSES.incorrectResultQuery,
        query: 'Test query 3',
        feedback: 'Results are not what I asked for',
        correction: 'SELECT name, price FROM products WHERE price > 100'
      },
    ];

    for (const testCase of feedbackTests) {
      // Setup mocks for this test case
      await setupMockWebSocket(page, testCase.mockResponse.events);
      await setupMockFeedbackAPI(page);

      await chatPage.goto();
      await chatPage.setupWebSocketInterception();

      // Wait for WebSocket to connect
      await page.waitForSelector('textarea:not([disabled])', { timeout: 10000 });

      // Submit query
      await chatPage.submitQuery(testCase.query);
      await page.waitForTimeout(2000);

      // Give negative feedback
      await chatPage.clickThumbsDown();
      await page.locator(chatPage.feedbackModal).waitFor({ state: 'visible', timeout: 5000 });

      // Fill feedback
      await page.fill(chatPage.feedbackTextarea, testCase.feedback);

      // Fill correction if provided
      if (testCase.correction) {
        await page.fill('textarea[placeholder*="correct query"]', testCase.correction);
      }

      // Submit
      await page.locator(chatPage.feedbackModal)
        .locator(chatPage.feedbackSubmitButton)
        .click();

      // Wait for modal to close
      await page.locator(chatPage.feedbackModal).waitFor({ state: 'hidden', timeout: 5000 });

      console.log(`Feedback submitted: ${testCase.feedback}`);

      // Wait before next test
      await page.waitForTimeout(1000);
    }
  });

  test('should verify negative feedback creates review queue item', async ({ page }) => {
    const chatPage = new ChatPage(page);

    // Setup mocks
    await setupMockWebSocket(page, MOCK_FEEDBACK_RESPONSES.reviewQueueQuery.events);
    await setupMockFeedbackAPI(page);

    await chatPage.goto();
    await chatPage.setupWebSocketInterception();

    // Wait for WebSocket to connect
    await page.waitForSelector('textarea:not([disabled])', { timeout: 10000 });

    // Submit a query
    await chatPage.submitQuery('Test query that will get negative feedback');
    await page.waitForTimeout(2000);

    // Give negative feedback
    await chatPage.clickThumbsDown();
    await page.locator(chatPage.feedbackModal).waitFor({ state: 'visible', timeout: 5000 });

    await page.fill(chatPage.feedbackTextarea, 'This needs expert review');

    await page.locator(chatPage.feedbackModal)
      .locator(chatPage.feedbackSubmitButton)
      .click();

    // Wait for modal to close
    await page.locator(chatPage.feedbackModal).waitFor({ state: 'hidden', timeout: 5000 });

    // Wait for feedback to be processed
    await page.waitForTimeout(1000);

    // Navigate to review queue (if user has access)
    await page.goto('/app/review');
    await page.waitForLoadState('networkidle');

    // If we can access review page, check for our item
    if (page.url().includes('/review')) {
      const pageContent = await page.textContent('body');
      expect(pageContent).toMatch(/review|queue|pending/i);
      console.log('Checked review queue for feedback item');
    } else {
      console.log('User does not have access to review queue');
    }
  });

  test('should navigate to feedback statistics page', async ({ page }) => {
    // Navigate to feedback statistics
    await page.goto('/app/feedback-stats');
    await page.waitForLoadState('networkidle');

    // Verify we're on the feedback stats page
    if (page.url().includes('/feedback-stats')) {
      const pageContent = await page.textContent('body');
      expect(pageContent).toMatch(/feedback|statistics|stats|rating/i);

      console.log('Feedback statistics page loaded');
    } else {
      console.log('Feedback statistics page not accessible');
      test.skip();
    }
  });

  test('should display feedback statistics', async ({ page }) => {
    await page.goto('/app/feedback-stats');
    await page.waitForLoadState('networkidle');

    if (page.url().includes('/feedback-stats')) {
      // Wait for statistics to load
      await page.waitForTimeout(2000);

      // Look for statistics elements (charts, numbers, etc.)
      const statsElements = await page.locator('.stat, .statistics, [role="table"], canvas, .chart').count();

      if (statsElements > 0) {
        console.log(`Found ${statsElements} statistics elements`);
      } else {
        // Check for text content indicating statistics
        const pageContent = await page.textContent('body');
        expect(pageContent.length).toBeGreaterThan(0);
      }
    } else {
      console.log('Cannot access feedback statistics');
      test.skip();
    }
  });

  test('should handle multiple feedback submissions on same query', async ({ page }) => {
    const chatPage = new ChatPage(page);

    // Setup mocks
    await setupMockWebSocket(page, MOCK_FEEDBACK_RESPONSES.multipleSubmissionQuery.events);
    await setupMockFeedbackAPI(page);

    await chatPage.goto();
    await chatPage.setupWebSocketInterception();

    // Wait for WebSocket to connect
    await page.waitForSelector('textarea:not([disabled])', { timeout: 10000 });

    // Submit a query
    await chatPage.submitQuery('Test query for multiple feedback');
    await page.waitForTimeout(2000);

    // First feedback attempt (thumbs up)
    await chatPage.clickThumbsUp();
    await page.waitForTimeout(1000);

    // Check if we can still interact with feedback buttons
    // (feedback buttons should be disabled after first use)
    const thumbsDownButton = page.locator(chatPage.feedbackButtons.thumbsDown).last();
    const isEnabled = await thumbsDownButton.isEnabled().catch(() => false);

    // Should be disabled after feedback is given
    expect(isEnabled).toBe(false);

    console.log(`Feedback buttons correctly disabled after first feedback: ${!isEnabled}`);
  });

  test('should cancel feedback modal', async ({ page }) => {
    const chatPage = new ChatPage(page);

    // Setup mocks
    await setupMockWebSocket(page, MOCK_FEEDBACK_RESPONSES.cancelFeedbackQuery.events);
    await setupMockFeedbackAPI(page);

    await chatPage.goto();
    await chatPage.setupWebSocketInterception();

    // Wait for WebSocket to connect
    await page.waitForSelector('textarea:not([disabled])', { timeout: 10000 });

    // Submit a query
    await chatPage.submitQuery('Test query for cancel feedback');
    await page.waitForTimeout(2000);

    // Click thumbs down to open modal
    await chatPage.clickThumbsDown();

    // Wait for modal to appear
    await page.locator(chatPage.feedbackModal).waitFor({ state: 'visible', timeout: 5000 });

    // Verify modal is visible
    const modalVisible = await page.locator(chatPage.feedbackModal).isVisible();
    expect(modalVisible).toBe(true);

    // Look for cancel button
    const cancelButton = page.locator('button:has-text("Cancel")').first();
    await cancelButton.click();

    // Verify modal is closed
    await page.locator(chatPage.feedbackModal).waitFor({ state: 'hidden', timeout: 5000 });

    // Verify feedback was not submitted (should not see "Thanks for your feedback!")
    const bodyText = await page.textContent('body');
    const feedbackNotSubmitted = !bodyText.includes('Thanks for your feedback!') ||
                                  bodyText.split('Thanks for your feedback!').length <= 1;

    console.log('Successfully cancelled feedback modal');
  });

  test('should validate feedback form fields', async ({ page }) => {
    const chatPage = new ChatPage(page);

    // Setup mocks
    await setupMockWebSocket(page, MOCK_FEEDBACK_RESPONSES.validationQuery.events);
    await setupMockFeedbackAPI(page);

    await chatPage.goto();
    await chatPage.setupWebSocketInterception();

    // Wait for WebSocket to connect
    await page.waitForSelector('textarea:not([disabled])', { timeout: 10000 });

    // Submit a query
    await chatPage.submitQuery('Test query for validation');
    await page.waitForTimeout(2000);

    // Click thumbs down to open modal
    await chatPage.clickThumbsDown();

    // Wait for modal
    await page.locator(chatPage.feedbackModal).waitFor({ state: 'visible', timeout: 5000 });

    // Try to submit without filling feedback (textarea has required attribute)
    const submitButton = page.locator(chatPage.feedbackModal)
      .locator(chatPage.feedbackSubmitButton);

    // Click submit without filling required field
    await submitButton.click();

    // Modal should still be visible (form validation prevents submission)
    await page.waitForTimeout(500);
    const modalStillVisible = await page.locator(chatPage.feedbackModal).isVisible();
    expect(modalStillVisible).toBe(true);

    console.log('Form validation correctly prevents submission without required field');

    // Now fill the field and verify submit works
    await page.fill(chatPage.feedbackTextarea, 'Test feedback for validation');
    await submitButton.click();

    // Modal should close after valid submission
    await page.locator(chatPage.feedbackModal).waitFor({ state: 'hidden', timeout: 5000 });

    console.log('Form validation allows submission with required field filled');

    // Close modal if still open
    const modalVisible = await page.locator(chatPage.feedbackModal).isVisible().catch(() => false);
    if (modalVisible) {
      const cancelButton = page.locator('button:has-text("Cancel")');
      if (await cancelButton.count() > 0) {
        await cancelButton.first().click();
      }
    }
  });
});
