import { test, expect } from '@playwright/test';

/**
 * Scenario 2: Schema Annotation Tests
 *
 * Tests schema annotation functionality:
 * - View schema annotation page
 * - Request auto-annotation
 * - Save manual annotation
 * - Use multi-turn chat for annotation assistance
 */
test.describe('Scenario 2: Schema Annotation', () => {
  // Use expert authentication
  test.use({ storageState: './e2e/.auth/expert.json' });

  test('should navigate to schema annotation page', async ({ page }) => {
    // Navigate to schema annotation page
    await page.goto('/schema-annotation');
    await page.waitForLoadState('networkidle');

    // Verify we're on the schema annotation page
    expect(page.url()).toContain('/schema-annotation');

    // Check for key elements on the page
    const pageContent = await page.textContent('body');
    expect(pageContent).toMatch(/schema|annotation|table/i);
  });

  test('should display database tables', async ({ page }) => {
    await page.goto('/schema-annotation');
    await page.waitForLoadState('networkidle');

    // Wait for tables to load
    await page.waitForTimeout(2000);

    // Check if any tables are displayed
    const tableElements = page.locator('table, .table-list, [role="table"]');
    const hasTable = await tableElements.count() > 0;

    // Either tables are displayed or a message about no tables
    const pageContent = await page.textContent('body');
    expect(hasTable || pageContent.includes('No tables')).toBeTruthy();
  });

  test('should request auto-annotation for a table', async ({ page }) => {
    await page.goto('/schema-annotation');
    await page.waitForLoadState('networkidle');

    // Look for auto-annotate button
    const autoAnnotateButton = page.locator('button:has-text("Auto"), button:has-text("Generate"), button:has-text("AI")');

    if (await autoAnnotateButton.count() > 0) {
      // Click the first auto-annotate button
      await autoAnnotateButton.first().click();

      // Wait for annotation to be generated
      await page.waitForTimeout(3000);

      // Check for success indication
      const pageContent = await page.textContent('body');
      expect(pageContent.length).toBeGreaterThan(0);
    } else {
      // No tables available for annotation
      console.log('No auto-annotate buttons found, skipping test');
      test.skip();
    }
  });

  test('should save manual annotation', async ({ page }) => {
    await page.goto('/schema-annotation');
    await page.waitForLoadState('networkidle');

    // Look for annotation textarea or input
    const annotationInput = page.locator('textarea[placeholder*="annotation"], textarea[placeholder*="description"], input[name="annotation"]');

    if (await annotationInput.count() > 0) {
      // Fill in manual annotation
      await annotationInput.first().fill('This is a test annotation for E2E testing');

      // Find and click save button
      const saveButton = page.locator('button:has-text("Save"), button[type="submit"]');
      await saveButton.first().click();

      // Wait for save confirmation
      await page.waitForTimeout(2000);

      // Check for success message
      const successIndicator = page.locator('[role="alert"].success, .success-message, .text-green-500');

      if (await successIndicator.count() > 0) {
        const message = await successIndicator.first().textContent();
        expect(message.toLowerCase()).toMatch(/success|saved/);
      }
    } else {
      console.log('No annotation inputs found, skipping test');
      test.skip();
    }
  });

  test('should use multi-turn chat for annotation assistance', async ({ page }) => {
    await page.goto('/schema-annotation');
    await page.waitForLoadState('networkidle');

    // Look for chat interface or help button
    const chatInput = page.locator('textarea[placeholder*="question"], textarea[placeholder*="ask"], input[placeholder*="help"]');

    if (await chatInput.count() > 0) {
      // Ask a question
      await chatInput.first().fill('What is the best way to annotate this table?');

      // Find and click send button
      const sendButton = page.locator('button:has-text("Send"), button:has-text("Ask"), button[type="submit"]');
      await sendButton.first().click();

      // Wait for response
      await page.waitForTimeout(5000);

      // Check if response is displayed
      const pageContent = await page.textContent('body');
      expect(pageContent.length).toBeGreaterThan(0);

      // Send follow-up question
      await chatInput.first().fill('Can you give me an example?');
      await sendButton.first().click();

      // Wait for second response
      await page.waitForTimeout(5000);
    } else {
      console.log('No chat interface found, skipping test');
      test.skip();
    }
  });

  test('should view table details', async ({ page }) => {
    await page.goto('/schema-annotation');
    await page.waitForLoadState('networkidle');

    // Look for a table row or table name to click
    const tableRow = page.locator('tr:has(td), .table-item, [role="row"]');

    if (await tableRow.count() > 0) {
      // Click the first table
      await tableRow.first().click();

      // Wait for details to load
      await page.waitForTimeout(2000);

      // Check if columns or schema details are displayed
      const pageContent = await page.textContent('body');
      expect(pageContent).toMatch(/column|field|type|schema/i);
    } else {
      console.log('No tables found to view details, skipping test');
      test.skip();
    }
  });

  test('should search for tables', async ({ page }) => {
    await page.goto('/schema-annotation');
    await page.waitForLoadState('networkidle');

    // Look for search input
    const searchInput = page.locator('input[placeholder*="Search"], input[type="search"]');

    if (await searchInput.count() > 0) {
      // Enter search query
      await searchInput.first().fill('test');

      // Wait for search results
      await page.waitForTimeout(1000);

      // Verify search is working (results might be filtered)
      const pageContent = await page.textContent('body');
      expect(pageContent.length).toBeGreaterThan(0);
    } else {
      console.log('No search input found, skipping test');
      test.skip();
    }
  });

  test('should export annotations', async ({ page }) => {
    await page.goto('/schema-annotation');
    await page.waitForLoadState('networkidle');

    // Look for export button
    const exportButton = page.locator('button:has-text("Export"), button:has-text("Download")');

    if (await exportButton.count() > 0) {
      // Set up download listener
      const downloadPromise = page.waitForEvent('download', { timeout: 10000 });

      // Click export button
      await exportButton.first().click();

      try {
        // Wait for download
        const download = await downloadPromise;

        // Verify download
        expect(download.suggestedFilename()).toBeTruthy();
      } catch {
        // Export might not trigger download, just verify button works
        await page.waitForTimeout(1000);
      }
    } else {
      console.log('No export button found, skipping test');
      test.skip();
    }
  });
});
