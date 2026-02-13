import { test, expect } from '@playwright/test';

test.describe('Admin Login and Provider Selection', () => {
  test('admin can login and select PostgreSQL provider', async ({ page }) => {
    // Navigate to login page
    await page.goto('http://localhost:5173');
    await expect(page).toHaveURL(/.*login/);

    // Fill in admin credentials
    await page.getByRole('textbox', { name: 'Email address' }).fill('admin@text2dsl.com');
    await page.getByRole('textbox', { name: 'Password' }).fill('Admin123!');

    // Click sign in
    await page.getByRole('button', { name: 'Sign in' }).click();

    // Verify redirect to app
    await expect(page).toHaveURL(/.*\/app/);

    // Wait for providers to load
    await page.waitForSelector('text=PostgreSQL', { timeout: 10000 });
    await page.waitForSelector('text=MongoDB', { timeout: 10000 });

    // Verify PostgreSQL provider is visible and connected
    const postgresProvider = page.getByRole('button', { name: /PostgreSQL.*Connected/i });
    await expect(postgresProvider).toBeVisible();

    // Verify MongoDB provider is visible and connected
    const mongoProvider = page.getByRole('button', { name: /MongoDB.*Connected/i });
    await expect(mongoProvider).toBeVisible();

    // Select PostgreSQL provider
    await postgresProvider.click();

    // Verify PostgreSQL is selected (button should remain visible and clickable)
    await expect(postgresProvider).toBeVisible();

    // Verify chat input is enabled
    const chatInput = page.getByRole('textbox', { name: /Ask me anything/i });
    await expect(chatInput).toBeEnabled();
  });
});
