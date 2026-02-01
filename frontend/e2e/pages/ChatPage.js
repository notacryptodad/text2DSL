/**
 * Page Object Model for Chat/Query Page
 *
 * Handles complex WebSocket interactions for real-time query processing
 */
export class ChatPage {
  constructor(page) {
    this.page = page;

    // Selectors
    this.queryInput = 'textarea[placeholder*="question"], textarea[placeholder*="query"], textarea';
    this.submitButton = 'button:has-text("Send"), button:has-text("Submit"), button[type="submit"]';
    this.loadingIndicator = '.loading, [role="status"], .animate-spin';
    this.resultContainer = '.result, .query-result, .response';
    this.feedbackButtons = {
      thumbsUp: 'button[aria-label*="thumbs up"], button:has-text("👍")',
      thumbsDown: 'button[aria-label*="thumbs down"], button:has-text("👎")',
    };
    this.feedbackModal = '[role="dialog"], .modal';
    this.feedbackTextarea = 'textarea[name="feedback"], textarea[placeholder*="feedback"]';
    this.feedbackCategorySelect = 'select[name="category"]';
    this.feedbackSubmitButton = 'button:has-text("Submit"), button[type="submit"]';
  }

  /**
   * Navigate to chat page
   */
  async goto() {
    await this.page.goto('/app');
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Setup WebSocket message interception
   * Call this before submitting a query to capture WebSocket messages
   */
  async setupWebSocketInterception() {
    await this.page.evaluate(() => {
      // Store WebSocket messages in a global array
      window.wsMessages = [];
      window.wsConnections = [];

      // Override WebSocket constructor
      const OriginalWebSocket = window.WebSocket;
      window.WebSocket = function(...args) {
        const ws = new OriginalWebSocket(...args);
        window.wsConnections.push(ws);

        // Capture messages
        ws.addEventListener('message', (event) => {
          try {
            const data = JSON.parse(event.data);
            window.wsMessages.push(data);
          } catch {
            // Not JSON, store as-is
            window.wsMessages.push(event.data);
          }
        });

        return ws;
      };
    });
  }

  /**
   * Get captured WebSocket messages
   *
   * @returns {Promise<Array>} Array of WebSocket messages
   */
  async getWebSocketMessages() {
    return await this.page.evaluate(() => window.wsMessages || []);
  }

  /**
   * Clear captured WebSocket messages
   */
  async clearWebSocketMessages() {
    await this.page.evaluate(() => {
      window.wsMessages = [];
    });
  }

  /**
   * Submit a query
   *
   * @param {string} query - The query text
   */
  async submitQuery(query) {
    await this.page.fill(this.queryInput, query);
    await this.page.click(this.submitButton);
  }

  /**
   * Wait for query to complete processing
   *
   * @param {number} timeout - Maximum time to wait (default 60s)
   */
  async waitForQueryCompletion(timeout = 60000) {
    // Wait for loading indicator to appear
    try {
      await this.page.locator(this.loadingIndicator).first().waitFor({
        state: 'visible',
        timeout: 5000,
      });
    } catch {
      // Loading indicator might not appear for fast queries
    }

    // Wait for loading indicator to disappear
    await this.page.locator(this.loadingIndicator).first().waitFor({
      state: 'hidden',
      timeout: timeout,
    });

    // Wait a bit for UI to settle
    await this.page.waitForTimeout(500);
  }

  /**
   * Wait for a specific WebSocket message type
   *
   * @param {string} messageType - Type of message to wait for (e.g., 'result', 'clarification', 'error')
   * @param {number} timeout - Maximum time to wait
   * @returns {Promise<Object>} The matching message
   */
  async waitForWebSocketMessage(messageType, timeout = 30000) {
    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
      const messages = await this.getWebSocketMessages();
      const matchingMessage = messages.find(msg => msg.type === messageType || msg.message_type === messageType);

      if (matchingMessage) {
        return matchingMessage;
      }

      await this.page.waitForTimeout(500);
    }

    throw new Error(`WebSocket message of type '${messageType}' not received within ${timeout}ms`);
  }

  /**
   * Get the latest query result
   *
   * @returns {Promise<string|null>} Result text or null
   */
  async getResult() {
    try {
      const resultElement = await this.page.locator(this.resultContainer).last();
      await resultElement.waitFor({ state: 'visible', timeout: 5000 });
      return await resultElement.textContent();
    } catch {
      return null;
    }
  }

  /**
   * Click thumbs up feedback button
   */
  async clickThumbsUp() {
    const button = this.page.locator(this.feedbackButtons.thumbsUp).last();
    await button.waitFor({ state: 'visible', timeout: 5000 });
    await button.click();
  }

  /**
   * Click thumbs down feedback button
   */
  async clickThumbsDown() {
    const button = this.page.locator(this.feedbackButtons.thumbsDown).last();
    await button.waitFor({ state: 'visible', timeout: 5000 });
    await button.click();
  }

  /**
   * Submit detailed feedback (after clicking thumbs down)
   *
   * @param {string} feedback - Feedback text
   * @param {string} category - Feedback category
   */
  async submitDetailedFeedback(feedback, category) {
    // Wait for feedback modal to appear
    await this.page.locator(this.feedbackModal).waitFor({ state: 'visible', timeout: 5000 });

    // Fill in feedback
    await this.page.fill(this.feedbackTextarea, feedback);

    if (category) {
      await this.page.selectOption(this.feedbackCategorySelect, category);
    }

    // Submit
    await this.page.locator(this.feedbackModal)
      .locator(this.feedbackSubmitButton)
      .click();

    // Wait for modal to close
    await this.page.locator(this.feedbackModal).waitFor({ state: 'hidden', timeout: 5000 });
  }

  /**
   * Check if a result is displayed
   *
   * @returns {Promise<boolean>}
   */
  async hasResult() {
    try {
      const resultElement = this.page.locator(this.resultContainer).last();
      await resultElement.waitFor({ state: 'visible', timeout: 2000 });
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Handle clarification request
   * Waits for clarification UI and responds with answer
   *
   * @param {string} answer - Answer to clarification
   */
  async respondToClarification(answer) {
    // Wait for clarification UI to appear
    const clarificationInput = this.page.locator('textarea[placeholder*="clarification"], input[placeholder*="clarification"]');
    await clarificationInput.waitFor({ state: 'visible', timeout: 10000 });

    // Fill and submit answer
    await clarificationInput.fill(answer);
    await this.page.click('button:has-text("Submit"), button:has-text("Send")');
  }
}
