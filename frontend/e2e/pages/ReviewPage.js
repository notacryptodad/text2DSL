/**
 * Page Object Model for Review Queue Page
 */
export class ReviewPage {
  constructor(page) {
    this.page = page;

    // Selectors - updated to match Review.jsx implementation
    this.queueContainer = '.bg-white.dark\\:bg-gray-800.rounded-lg';
    this.queueItem = '.p-6.hover\\:bg-gray-50';
    this.viewDetailsButton = 'button:has-text("View Details")';
    this.approveButton = 'button:has-text("Approve")';
    this.rejectButton = 'button:has-text("Reject")';
    this.editButton = 'button:has-text("Edit")';
    this.statusFilter = 'select';
    this.detailModal = '.fixed.inset-0.z-50';
    this.correctionTextarea = 'textarea';
    this.feedbackTextarea = 'textarea[placeholder*="feedback"], textarea[placeholder*="Comments"]';
  }

  /**
   * Navigate to review queue page
   */
  async goto() {
    await this.page.goto('/app/review');
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

    // Click "View Details" button to open modal
    const viewButton = items[index].locator(this.viewDetailsButton);
    await viewButton.click();

    // Wait for modal to open
    await this.page.locator(this.detailModal).waitFor({ state: 'visible', timeout: 5000 });

    // Click approve button in modal
    await this.page.locator(this.detailModal).locator(this.approveButton).click();

    // Wait for modal to close and queue to update
    await this.page.locator(this.detailModal).waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {});
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

    // Click "View Details" button to open modal
    const viewButton = items[index].locator(this.viewDetailsButton);
    await viewButton.click();

    // Wait for modal to open
    await this.page.locator(this.detailModal).waitFor({ state: 'visible', timeout: 5000 });

    // If feedback is provided, fill it in
    if (feedback) {
      const feedbackField = this.page.locator(this.detailModal).locator(this.feedbackTextarea);
      await feedbackField.fill(feedback);
    }

    // Click reject button in modal
    await this.page.locator(this.detailModal).locator(this.rejectButton).click();

    // Handle confirmation dialog if it appears
    this.page.once('dialog', dialog => dialog.accept());

    // Wait for modal to close and queue to update
    await this.page.locator(this.detailModal).waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {});
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

    // Click "View Details" button to open modal
    const viewButton = items[index].locator(this.viewDetailsButton);
    await viewButton.click();

    // Wait for modal to open
    await this.page.locator(this.detailModal).waitFor({ state: 'visible', timeout: 5000 });

    // Click "Edit & Approve" button to enable editing
    await this.page.locator(this.detailModal).locator(this.editButton).click();

    // Wait for textarea to appear
    await this.page.waitForTimeout(500);

    // Fill in corrected SQL
    const textarea = this.page.locator(this.detailModal).locator(this.correctionTextarea).first();
    await textarea.fill(correctedSQL);

    // Click "Approve with Correction" button
    await this.page.locator(this.detailModal).locator('button:has-text("Approve with Correction")').click();

    // Wait for modal to close and queue to update
    await this.page.locator(this.detailModal).waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {});
    await this.page.waitForTimeout(1000);
  }

  /**
   * Filter queue by status
   *
   * @param {string} status - Status to filter by (e.g., 'pending_review', 'approved', 'rejected')
   */
  async filterByStatus(status) {
    // The status filter is the second select on the page
    const statusSelect = this.page.locator('select').nth(1);
    await statusSelect.selectOption(status);
    await this.page.waitForLoadState('networkidle');
    await this.page.waitForTimeout(500);
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
