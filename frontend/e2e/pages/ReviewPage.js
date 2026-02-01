/**
 * Page Object Model for Review Queue Page
 */
export class ReviewPage {
  constructor(page) {
    this.page = page;

    // Selectors
    this.queueContainer = '.review-queue, [data-testid="review-queue"]';
    this.queueItem = '.review-item, .queue-item, [data-testid="review-item"]';
    this.approveButton = 'button:has-text("Approve")';
    this.rejectButton = 'button:has-text("Reject")';
    this.correctButton = 'button:has-text("Correct"), button:has-text("Edit")';
    this.statusFilter = 'select[name="status"], [aria-label="Filter by status"]';
    this.correctionModal = '[role="dialog"], .modal';
    this.correctionTextarea = 'textarea[name="correction"], textarea[placeholder*="correct"]';
    this.correctionSubmitButton = 'button:has-text("Save"), button:has-text("Submit")';
    this.feedbackTextarea = 'textarea[name="feedback"], textarea[placeholder*="feedback"]';
  }

  /**
   * Navigate to review queue page
   */
  async goto() {
    await this.page.goto('/review');
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Get all review queue items
   *
   * @returns {Promise<Array>} Array of queue item elements
   */
  async getQueueItems() {
    await this.page.waitForLoadState('networkidle');
    return await this.page.locator(this.queueItem).all();
  }

  /**
   * Get count of items in queue
   *
   * @returns {Promise<number>}
   */
  async getQueueItemCount() {
    const items = await this.getQueueItems();
    return items.length;
  }

  /**
   * Get the first queue item
   *
   * @returns {Promise<Object>} Queue item element
   */
  async getFirstQueueItem() {
    const items = await this.getQueueItems();
    return items.length > 0 ? items[0] : null;
  }

  /**
   * Approve a query by index
   *
   * @param {number} index - Index of the item (0-based)
   */
  async approveByIndex(index = 0) {
    const items = await this.getQueueItems();
    if (items.length <= index) {
      throw new Error(`No item at index ${index}`);
    }

    const approveButton = items[index].locator(this.approveButton);
    await approveButton.click();

    // Wait for item to be removed from queue
    await this.page.waitForTimeout(1000);
  }

  /**
   * Reject a query by index with optional feedback
   *
   * @param {number} index - Index of the item (0-based)
   * @param {string} feedback - Optional rejection feedback
   */
  async rejectByIndex(index = 0, feedback = null) {
    const items = await this.getQueueItems();
    if (items.length <= index) {
      throw new Error(`No item at index ${index}`);
    }

    const rejectButton = items[index].locator(this.rejectButton);
    await rejectButton.click();

    // If feedback is provided, fill it in
    if (feedback) {
      try {
        await this.page.locator(this.feedbackTextarea).waitFor({ state: 'visible', timeout: 2000 });
        await this.page.fill(this.feedbackTextarea, feedback);

        // Submit feedback
        const submitButton = this.page.locator('button:has-text("Submit"), button:has-text("Reject")');
        await submitButton.click();
      } catch {
        // No feedback field, rejection might be immediate
      }
    }

    // Wait for item to be removed from queue
    await this.page.waitForTimeout(1000);
  }

  /**
   * Correct and approve a query by index
   *
   * @param {number} index - Index of the item (0-based)
   * @param {string} correctedSQL - Corrected SQL query
   */
  async correctAndApproveByIndex(index = 0, correctedSQL) {
    const items = await this.getQueueItems();
    if (items.length <= index) {
      throw new Error(`No item at index ${index}`);
    }

    const correctButton = items[index].locator(this.correctButton);
    await correctButton.click();

    // Wait for correction modal
    await this.page.locator(this.correctionModal).waitFor({ state: 'visible', timeout: 5000 });

    // Fill in corrected SQL
    await this.page.fill(this.correctionTextarea, correctedSQL);

    // Submit correction
    await this.page.locator(this.correctionModal)
      .locator(this.correctionSubmitButton)
      .click();

    // Wait for modal to close
    await this.page.locator(this.correctionModal).waitFor({ state: 'hidden', timeout: 5000 });

    // Wait for item to be processed
    await this.page.waitForTimeout(1000);
  }

  /**
   * Filter queue by status
   *
   * @param {string} status - Status to filter by (e.g., 'pending', 'approved', 'rejected')
   */
  async filterByStatus(status) {
    await this.page.selectOption(this.statusFilter, status);
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Get text content of a queue item
   *
   * @param {number} index - Index of the item (0-based)
   * @returns {Promise<string>}
   */
  async getItemText(index = 0) {
    const items = await this.getQueueItems();
    if (items.length <= index) {
      throw new Error(`No item at index ${index}`);
    }

    return await items[index].textContent();
  }

  /**
   * Check if queue is empty
   *
   * @returns {Promise<boolean>}
   */
  async isQueueEmpty() {
    const count = await this.getQueueItemCount();
    return count === 0;
  }

  /**
   * Wait for queue to load
   */
  async waitForQueueLoad() {
    await this.page.waitForLoadState('networkidle');
    // Wait a bit for any animations
    await this.page.waitForTimeout(500);
  }
}
