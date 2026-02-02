/**
 * Integration Test: Query Generation (AI)
 * 
 * Tests full query generation flow with real Bedrock AI.
 * Requires: REAL_AI=true environment variable
 * 
 * NOTE: These tests are non-deterministic due to AI responses.
 * Run separately from CI, or use for manual validation.
 */
import { test, expect } from '@playwright/test';
import { ChatPage } from '../pages/ChatPage.js';
import { LoginPage } from '../pages/LoginPage.js';

const REAL_AI = process.env.REAL_AI === 'true';

test.describe('Integration: Query Generation (AI)', () => {
  test.skip(!REAL_AI, 'Skipped: Set REAL_AI=true to run AI tests');

  test.beforeEach(async ({ page }) => {
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login('regular.user@example.com', 'user123');
  });

  test('should generate SQL for simple customer count', async ({ page }) => {
    const chatPage = new ChatPage(page);
    await chatPage.goto();
    
    // Submit query
    await chatPage.submitQuery('How many customers do we have?');
    
    // Wait for response (AI can take 10-30 seconds)
    await page.waitForSelector('[data-testid="assistant-message"]', { 
      timeout: 60000 
    });
    
    // Verify response contains SQL
    const response = await page.textContent('[data-testid="assistant-message"]');
    expect(response.toLowerCase()).toContain('select');
    expect(response.toLowerCase()).toContain('count');
    expect(response.toLowerCase()).toContain('customers');
  });

  test('should generate SQL for product listing with filter', async ({ page }) => {
    const chatPage = new ChatPage(page);
    await chatPage.goto();
    
    await chatPage.submitQuery('Show me all products under $50');
    
    await page.waitForSelector('[data-testid="assistant-message"]', { 
      timeout: 60000 
    });
    
    const response = await page.textContent('[data-testid="assistant-message"]');
    expect(response.toLowerCase()).toContain('select');
    expect(response.toLowerCase()).toContain('products');
    expect(response.toLowerCase()).toContain('where');
    expect(response.toLowerCase()).toMatch(/price\s*<|<\s*50/);
  });

  test('should handle complex join query', async ({ page }) => {
    const chatPage = new ChatPage(page);
    await chatPage.goto();
    
    await chatPage.submitQuery('Show me all orders with customer names');
    
    await page.waitForSelector('[data-testid="assistant-message"]', { 
      timeout: 60000 
    });
    
    const response = await page.textContent('[data-testid="assistant-message"]');
    expect(response.toLowerCase()).toContain('join');
    expect(response.toLowerCase()).toContain('customers');
    expect(response.toLowerCase()).toContain('orders');
  });

  test('should show confidence score', async ({ page }) => {
    const chatPage = new ChatPage(page);
    await chatPage.goto();
    
    await chatPage.submitQuery('Total revenue by month');
    
    await page.waitForSelector('[data-testid="confidence-score"]', { 
      timeout: 60000 
    });
    
    const confidence = await page.textContent('[data-testid="confidence-score"]');
    expect(parseFloat(confidence)).toBeGreaterThan(0);
  });

  test('should handle ambiguous query with clarification', async ({ page }) => {
    const chatPage = new ChatPage(page);
    await chatPage.goto();
    
    // Intentionally vague query
    await chatPage.submitQuery('Show me the data');
    
    await page.waitForSelector('[data-testid="assistant-message"]', { 
      timeout: 60000 
    });
    
    const response = await page.textContent('[data-testid="assistant-message"]');
    // AI should either ask for clarification or make reasonable assumptions
    expect(response.length).toBeGreaterThan(10);
  });

  test('should execute generated SQL and show results', async ({ page }) => {
    const chatPage = new ChatPage(page);
    await chatPage.goto();
    
    await chatPage.submitQuery('How many products are in stock?');
    
    // Wait for execution results
    await page.waitForSelector('[data-testid="query-results"]', { 
      timeout: 90000 
    });
    
    const results = await page.locator('[data-testid="query-results"]');
    await expect(results).toBeVisible();
  });
});
