/**
 * Page Object Model for Login Page
 */
export class LoginPage {
  constructor(page) {
    this.page = page;

    // Selectors
    this.emailInput = 'input[name="email"], input[type="email"]';
    this.passwordInput = 'input[name="password"], input[type="password"]';
    this.submitButton = 'button[type="submit"]';
    this.registerLink = 'a:has-text("Register"), a:has-text("Sign up")';
    this.errorMessage = '[role="alert"], .error-message, .text-red-500';
  }

  /**
   * Navigate to login page
   */
  async goto() {
    await this.page.goto('/login');
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Perform login with credentials
   *
   * @param {string} email - User email
   * @param {string} password - User password
   */
  async login(email, password) {
    await this.page.fill(this.emailInput, email);
    await this.page.fill(this.passwordInput, password);
    await this.page.click(this.submitButton);
  }

  /**
   * Wait for successful login navigation
   */
  async waitForSuccessfulLogin() {
    await this.page.waitForURL(/\/(chat|dashboard)/, { timeout: 15000 });
  }

  /**
   * Get error message text
   *
   * @returns {Promise<string|null>} Error message or null if not found
   */
  async getErrorMessage() {
    try {
      const errorElement = await this.page.locator(this.errorMessage).first();
      await errorElement.waitFor({ state: 'visible', timeout: 5000 });
      return await errorElement.textContent();
    } catch {
      return null;
    }
  }

  /**
   * Check if we're on the login page
   *
   * @returns {Promise<boolean>}
   */
  async isOnLoginPage() {
    return this.page.url().includes('/login');
  }
}
