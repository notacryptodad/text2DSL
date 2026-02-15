// @ts-check
import { test, expect } from '@playwright/test';
import { DEFAULT_ADMIN } from './fixtures/auth.fixture.js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * UI Features E2E Tests
 * 
 * Tests for newly implemented UI features in text2DSL:
 * - #53 Confidence Meter
 * - #55 Dark/Light Mode Toggle
 * - #62 Design System (component organization)
 * - #58 Query History Sidebar
 * - #63 Keyboard Shortcuts
 */

// Use pre-authenticated super admin context
test.describe('UI Features', () => {
  // Use storage state from global setup
  test.use({ storageState: './e2e/.auth/super_admin.json' });

  test.describe('#55 Dark/Light Mode Toggle', () => {
    test('should display theme toggle button in header', async ({ page }) => {
      await page.goto('http://localhost:5173/app');
      await page.waitForLoadState('networkidle');
      
      // Wait for app to fully load
      await expect(page.locator('h1:text("Text2DSL")')).toBeVisible({ timeout: 15000 });
      
      // Look for the theme toggle button (it has aria-label for accessibility)
      const themeToggle = page.locator('button[aria-label*="mode"]');
      await expect(themeToggle).toBeVisible({ timeout: 10000 });
    });

    test('should toggle between dark and light mode', async ({ page }) => {
      await page.goto('http://localhost:5173/app');
      await page.waitForLoadState('networkidle');
      await expect(page.locator('h1:text("Text2DSL")')).toBeVisible({ timeout: 15000 });
      
      const html = page.locator('html');
      const themeToggle = page.locator('button[aria-label*="mode"]');
      await expect(themeToggle).toBeVisible({ timeout: 10000 });
      
      // Get initial state
      const initialDark = await html.evaluate((el) => el.classList.contains('dark'));
      
      // Click toggle
      await themeToggle.click();
      await page.waitForTimeout(500);
      
      // Check state changed
      const afterToggle = await html.evaluate((el) => el.classList.contains('dark'));
      expect(afterToggle).not.toBe(initialDark);
      
      // Toggle back
      await themeToggle.click();
      await page.waitForTimeout(500);
      
      const afterSecondToggle = await html.evaluate((el) => el.classList.contains('dark'));
      expect(afterSecondToggle).toBe(initialDark);
    });

    test('should persist theme preference in localStorage', async ({ page }) => {
      await page.goto('http://localhost:5173/app');
      await page.waitForLoadState('networkidle');
      await expect(page.locator('h1:text("Text2DSL")')).toBeVisible({ timeout: 15000 });
      
      const themeToggle = page.locator('button[aria-label*="mode"]');
      await expect(themeToggle).toBeVisible({ timeout: 10000 });
      
      // Click toggle to change theme
      await themeToggle.click();
      await page.waitForTimeout(500);
      
      // Check localStorage
      const storedValue = await page.evaluate(() => localStorage.getItem('darkMode'));
      expect(storedValue).toBeTruthy();
      
      // Reload and verify persistence
      const currentDarkClass = await page.locator('html').evaluate((el) => el.classList.contains('dark'));
      await page.reload();
      await page.waitForLoadState('networkidle');
      
      const afterReloadDark = await page.locator('html').evaluate((el) => el.classList.contains('dark'));
      expect(afterReloadDark).toBe(currentDarkClass);
    });
  });

  test.describe('#63 Keyboard Shortcuts', () => {
    test('should navigate with g+c sequence (go to Chat)', async ({ page }) => {
      await page.goto('http://localhost:5173/app/review');
      await page.waitForLoadState('networkidle');
      
      // Click away from any inputs
      await page.click('body');
      await page.waitForTimeout(200);
      
      // Press g, then c
      await page.keyboard.press('g');
      await page.waitForTimeout(100);
      await page.keyboard.press('c');
      
      // Should navigate to app/chat or /app
      await expect(page).toHaveURL(/\/app(\/chat)?$/, { timeout: 5000 });
    });

    test('should display keyboard shortcut button in header', async ({ page }) => {
      await page.goto('http://localhost:5173/app');
      await page.waitForLoadState('networkidle');
      await expect(page.locator('h1:text("Text2DSL")')).toBeVisible({ timeout: 15000 });
      
      // Look for keyboard icon button - the button with keyboard icon (lucide-keyboard)
      const keyboardButton = page.locator('button:has(.lucide-keyboard)');
      await expect(keyboardButton).toBeVisible({ timeout: 10000 });
    });

    test('should open modal when clicking keyboard button', async ({ page }) => {
      await page.goto('http://localhost:5173/app');
      await page.waitForLoadState('networkidle');
      await expect(page.locator('h1:text("Text2DSL")')).toBeVisible({ timeout: 15000 });
      
      // Find and click the keyboard button
      const keyboardButton = page.locator('button:has(.lucide-keyboard)');
      await keyboardButton.click();
      await page.waitForTimeout(500);
      
      // Modal should appear
      await expect(page.locator('h2:text("Keyboard Shortcuts")')).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('#58 Query History Sidebar', () => {
    test('should display history toggle button', async ({ page }) => {
      await page.goto('http://localhost:5173/app');
      await page.waitForLoadState('networkidle');
      await expect(page.locator('h1:text("Text2DSL")')).toBeVisible({ timeout: 15000 });
      
      // Look for history button - it has a lucide-history icon (floating button)
      const historyButton = page.locator('button:has(.lucide-history)');
      await expect(historyButton).toBeVisible({ timeout: 10000 });
    });

    test('history button is clickable', async ({ page }) => {
      await page.goto('http://localhost:5173/app');
      await page.waitForLoadState('networkidle');
      await expect(page.locator('h1:text("Text2DSL")')).toBeVisible({ timeout: 15000 });
      
      // Find the history button
      const historyButton = page.locator('button:has(.lucide-history)');
      await expect(historyButton).toBeVisible({ timeout: 10000 });
      
      // Click should not throw error
      await historyButton.click();
    });
  });

  test.describe('#62 Design System - Component Organization', () => {
    test('should have presentational components folder', async () => {
      // Check that the presentational folder exists with README
      const presentationalPath = path.join(__dirname, '../src/components/presentational');
      const exists = fs.existsSync(presentationalPath);
      expect(exists).toBeTruthy();
      
      // Check README exists
      const readmePath = path.join(presentationalPath, 'README.md');
      const readmeExists = fs.existsSync(readmePath);
      expect(readmeExists).toBeTruthy();
    });

    test('should have containers components folder', async () => {
      // Check that the containers folder exists with README
      const containersPath = path.join(__dirname, '../src/components/containers');
      const exists = fs.existsSync(containersPath);
      expect(exists).toBeTruthy();
      
      // Check README exists
      const readmePath = path.join(containersPath, 'README.md');
      const readmeExists = fs.existsSync(readmePath);
      expect(readmeExists).toBeTruthy();
    });

    test('should have QueryBlock presentational component', async () => {
      const queryBlockPath = path.join(__dirname, '../src/components/presentational/QueryBlock.jsx');
      const exists = fs.existsSync(queryBlockPath);
      expect(exists).toBeTruthy();
    });
  });

  test.describe('#53 Confidence Meter', () => {
    test('should have ConfidenceMeter component available', async () => {
      // Verify the component exists
      const componentPath = path.join(__dirname, '../src/components/ConfidenceMeter.jsx');
      const exists = fs.existsSync(componentPath);
      expect(exists).toBeTruthy();
    });

    test('should render chat page without errors', async ({ page }) => {
      await page.goto('http://localhost:5173/app');
      await page.waitForLoadState('networkidle');
      
      // Verify page loads without errors - look for main elements
      await expect(page.locator('h1:text("Text2DSL")')).toBeVisible({ timeout: 15000 });
      const chatArea = page.locator('.bg-white, .dark\\:bg-gray-800').first();
      await expect(chatArea).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe('Chat Page Functionality', () => {
    test('should display provider section header', async ({ page }) => {
      await page.goto('http://localhost:5173/app');
      await page.waitForLoadState('networkidle');
      await expect(page.locator('h1:text("Text2DSL")')).toBeVisible({ timeout: 15000 });
      
      // Look for Provider header in sidebar
      const providerSection = page.locator('h2:text("Provider")');
      await expect(providerSection).toBeVisible({ timeout: 10000 });
    });

    test('should display query input field', async ({ page }) => {
      await page.goto('http://localhost:5173/app');
      await page.waitForLoadState('networkidle');
      await expect(page.locator('h1:text("Text2DSL")')).toBeVisible({ timeout: 15000 });
      
      // Look for input field (textarea)
      const queryInput = page.locator('textarea').first();
      await expect(queryInput).toBeVisible({ timeout: 10000 });
    });

    test('should display "How it works" guide', async ({ page }) => {
      await page.goto('http://localhost:5173/app');
      await page.waitForLoadState('networkidle');
      await expect(page.locator('h1:text("Text2DSL")')).toBeVisible({ timeout: 15000 });
      
      // Check for how it works section
      const howItWorks = page.locator('h3:text("How it works")');
      await expect(howItWorks).toBeVisible({ timeout: 10000 });
      
      // Check for steps
      await expect(page.locator('text=Select your database provider')).toBeVisible();
      await expect(page.locator('text=Type your query in natural language')).toBeVisible();
    });
  });

  test.describe('Navigation', () => {
    test('should display navigation links in header', async ({ page }) => {
      await page.goto('http://localhost:5173/app');
      await page.waitForLoadState('networkidle');
      await expect(page.locator('h1:text("Text2DSL")')).toBeVisible({ timeout: 15000 });
      
      // Look for navigation links - they contain text "Chat", "Review", etc.
      await expect(page.locator('text=Chat').first()).toBeVisible({ timeout: 10000 });
      await expect(page.locator('text=Review').first()).toBeVisible({ timeout: 10000 });
      await expect(page.locator('text=Schema').first()).toBeVisible({ timeout: 10000 });
      await expect(page.locator('text=Feedback').first()).toBeVisible({ timeout: 10000 });
    });

    test('should display Admin menu for super admin', async ({ page }) => {
      await page.goto('http://localhost:5173/app');
      await page.waitForLoadState('networkidle');
      await expect(page.locator('h1:text("Text2DSL")')).toBeVisible({ timeout: 15000 });
      
      // Admin menu should be visible for super admin
      const adminButton = page.locator('button:has-text("Admin")').first();
      await expect(adminButton).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe('User Menu', () => {
    test('should display user menu button', async ({ page }) => {
      await page.goto('http://localhost:5173/app');
      await page.waitForLoadState('networkidle');
      await expect(page.locator('h1:text("Text2DSL")')).toBeVisible({ timeout: 15000 });
      
      // Look for user icon/button in header - find the dropdown trigger with chevron
      const userButton = page.locator('header button').filter({ has: page.locator('.lucide-chevron-down') }).first();
      await expect(userButton).toBeVisible({ timeout: 10000 });
    });

    test('should open user dropdown menu', async ({ page }) => {
      await page.goto('http://localhost:5173/app');
      await page.waitForLoadState('networkidle');
      await expect(page.locator('h1:text("Text2DSL")')).toBeVisible({ timeout: 15000 });
      
      // Find and click user menu button
      const userMenuButton = page.locator('header button').filter({ has: page.locator('.lucide-chevron-down') }).last();
      await userMenuButton.click();
      await page.waitForTimeout(500);
      
      // Should see profile and logout options
      await expect(page.locator('text=Profile Settings')).toBeVisible({ timeout: 5000 });
      await expect(page.locator('text=Sign out')).toBeVisible();
    });
  });

  test.describe('Application Header', () => {
    test('should display application logo and title', async ({ page }) => {
      await page.goto('http://localhost:5173/app');
      await page.waitForLoadState('networkidle');
      
      // Check for Text2DSL branding
      const title = page.locator('h1:text("Text2DSL")');
      await expect(title).toBeVisible({ timeout: 15000 });
      
      // Check for subtitle
      const subtitle = page.locator('text=Natural Language to Query Converter');
      await expect(subtitle).toBeVisible();
    });
  });

  test.describe('ThemeToggle Component', () => {
    test('should have proper accessibility attributes', async ({ page }) => {
      await page.goto('http://localhost:5173/app');
      await page.waitForLoadState('networkidle');
      await expect(page.locator('h1:text("Text2DSL")')).toBeVisible({ timeout: 15000 });
      
      const themeToggle = page.locator('button[aria-label*="mode"]');
      await expect(themeToggle).toBeVisible({ timeout: 10000 });
      
      // Check aria-label is present and meaningful
      const ariaLabel = await themeToggle.getAttribute('aria-label');
      expect(ariaLabel).toBeTruthy();
      expect(ariaLabel?.toLowerCase()).toContain('mode');
    });

    test('should have tooltip/title attribute', async ({ page }) => {
      await page.goto('http://localhost:5173/app');
      await page.waitForLoadState('networkidle');
      await expect(page.locator('h1:text("Text2DSL")')).toBeVisible({ timeout: 15000 });
      
      const themeToggle = page.locator('button[aria-label*="mode"]');
      const title = await themeToggle.getAttribute('title');
      expect(title).toBeTruthy();
    });
  });
});

// Login tests - don't use storage state
test.describe('Login Page', () => {
  test('should display login form', async ({ page }) => {
    await page.goto('http://localhost:5173/login');
    await page.waitForLoadState('networkidle');
    
    // Check for login form elements
    await expect(page.locator('input[name="email"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('input[name="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should login successfully with valid credentials', async ({ page }) => {
    await page.goto('http://localhost:5173/login');
    await page.waitForLoadState('networkidle');
    
    await page.fill('input[name="email"]', DEFAULT_ADMIN.email);
    await page.fill('input[name="password"]', DEFAULT_ADMIN.password);
    await page.click('button[type="submit"]');
    
    // Should redirect to app
    await expect(page).toHaveURL(/\/app/, { timeout: 15000 });
  });

  test('should toggle password visibility', async ({ page }) => {
    await page.goto('http://localhost:5173/login');
    await page.waitForLoadState('networkidle');

    const passwordInput = page.locator('input[name="password"]');
    // Look for button with aria-label containing "password" (Show password / Hide password)
    const toggleButton = page.locator('button[aria-label*="password"]');

    // Initial state should be password
    await expect(passwordInput).toHaveAttribute('type', 'password');

    // Click toggle to show password
    await toggleButton.click();
    await expect(passwordInput).toHaveAttribute('type', 'text');

    // Click toggle to hide password
    await toggleButton.click();
    await expect(passwordInput).toHaveAttribute('type', 'password');
  });
});

// Component file existence tests (don't need browser)
test.describe('Component Files Exist', () => {
  const componentsToCheck = [
    { name: 'ConfidenceMeter', path: 'src/components/ConfidenceMeter.jsx' },
    { name: 'ThemeToggle', path: 'src/components/ThemeToggle.jsx' },
    { name: 'KeyboardShortcutsHelp', path: 'src/components/KeyboardShortcutsHelp.jsx' },
    { name: 'ConversationHistory', path: 'src/components/ConversationHistory.jsx' },
    { name: 'ChatMessage', path: 'src/components/ChatMessage.jsx' },
    { name: 'AppLayout', path: 'src/components/AppLayout.jsx' },
  ];

  for (const component of componentsToCheck) {
    test(`${component.name} component exists`, async () => {
      const componentPath = path.join(__dirname, '..', component.path);
      const exists = fs.existsSync(componentPath);
      expect(exists).toBeTruthy();
    });
  }
});

test.describe('Hooks Files Exist', () => {
  const hooksToCheck = [
    { name: 'useTheme', path: 'src/hooks/useTheme.js' },
    { name: 'useKeyboardShortcuts', path: 'src/hooks/useKeyboardShortcuts.js' },
    { name: 'useAuth', path: 'src/hooks/useAuth.jsx' },
    { name: 'useQuerySSE', path: 'src/hooks/useQuerySSE.js' },
  ];

  for (const hook of hooksToCheck) {
    test(`${hook.name} hook exists`, async () => {
      const hookPath = path.join(__dirname, '..', hook.path);
      const exists = fs.existsSync(hookPath);
      expect(exists).toBeTruthy();
    });
  }
});
