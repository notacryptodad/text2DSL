/**
 * Page Object Model for Admin Dashboard Page
 */
export class AdminDashboardPage {
  constructor(page) {
    this.page = page;

    // Selectors
    this.workspacesTab = 'a:has-text("Workspaces"), button:has-text("Workspaces")';
    this.providersTab = 'a:has-text("Providers"), button:has-text("Providers")';
    this.connectionsTab = 'a:has-text("Connections"), button:has-text("Connections")';
    this.usersTab = 'a:has-text("Users"), button:has-text("Users")';
    this.createButton = 'button:has-text("Create"), button:has-text("Add"), button:has-text("New")';
    this.modal = '[role="dialog"], .modal';
    this.submitButton = 'button[type="submit"], button:has-text("Save"), button:has-text("Create")';
    this.testConnectionButton = 'button:has-text("Test"), button:has-text("Test Connection")';
    this.refreshSchemaButton = 'button:has-text("Refresh"), button:has-text("Refresh Schema")';
    this.successMessage = '[role="alert"].success, .success-message, .text-green-500';
    this.errorMessage = '[role="alert"].error, .error-message, .text-red-500';
  }

  /**
   * Navigate to admin dashboard
   */
  async goto() {
    await this.page.goto('/admin');
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Navigate to workspaces tab
   */
  async goToWorkspaces() {
    await this.page.click(this.workspacesTab);
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Navigate to providers tab
   */
  async goToProviders() {
    await this.page.click(this.providersTab);
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Navigate to connections tab
   */
  async goToConnections() {
    await this.page.click(this.connectionsTab);
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Navigate to users tab
   */
  async goToUsers() {
    await this.page.click(this.usersTab);
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Create a new workspace
   *
   * @param {Object} workspaceData - Workspace data
   * @param {string} workspaceData.name - Workspace name
   * @param {string} workspaceData.description - Workspace description
   */
  async createWorkspace(workspaceData) {
    await this.goToWorkspaces();

    // Click create button
    await this.page.click(this.createButton);

    // Wait for modal
    await this.page.locator(this.modal).waitFor({ state: 'visible', timeout: 5000 });

    // Fill in workspace details
    await this.page.fill('input[name="name"]', workspaceData.name);

    if (workspaceData.description) {
      await this.page.fill('textarea[name="description"], input[name="description"]', workspaceData.description);
    }

    // Submit
    await this.page.locator(this.modal).locator(this.submitButton).click();

    // Wait for modal to close
    await this.page.locator(this.modal).waitFor({ state: 'hidden', timeout: 5000 });
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Create a new provider
   *
   * @param {Object} providerData - Provider data
   * @param {string} providerData.name - Provider name
   * @param {string} providerData.type - Provider type (e.g., 'postgresql')
   */
  async createProvider(providerData) {
    await this.goToProviders();

    // Click create button
    await this.page.click(this.createButton);

    // Wait for modal
    await this.page.locator(this.modal).waitFor({ state: 'visible', timeout: 5000 });

    // Fill in provider details
    await this.page.fill('input[name="name"]', providerData.name);
    await this.page.selectOption('select[name="type"]', providerData.type);

    // Submit
    await this.page.locator(this.modal).locator(this.submitButton).click();

    // Wait for modal to close
    await this.page.locator(this.modal).waitFor({ state: 'hidden', timeout: 5000 });
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Create a new database connection
   *
   * @param {Object} connectionData - Connection data
   * @param {string} connectionData.name - Connection name
   * @param {string} connectionData.host - Database host
   * @param {number} connectionData.port - Database port
   * @param {string} connectionData.database - Database name
   * @param {string} connectionData.username - Database username
   * @param {string} connectionData.password - Database password
   */
  async createConnection(connectionData) {
    await this.goToConnections();

    // Click create button
    await this.page.click(this.createButton);

    // Wait for modal
    await this.page.locator(this.modal).waitFor({ state: 'visible', timeout: 5000 });

    // Fill in connection details
    await this.page.fill('input[name="name"]', connectionData.name);
    await this.page.fill('input[name="host"]', connectionData.host);
    await this.page.fill('input[name="port"]', connectionData.port.toString());
    await this.page.fill('input[name="database"]', connectionData.database);
    await this.page.fill('input[name="username"]', connectionData.username);
    await this.page.fill('input[name="password"]', connectionData.password);

    // Submit
    await this.page.locator(this.modal).locator(this.submitButton).click();

    // Wait for modal to close
    await this.page.locator(this.modal).waitFor({ state: 'hidden', timeout: 5000 });
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Test a database connection by name
   *
   * @param {string} connectionName - Name of the connection to test
   * @returns {Promise<boolean>} True if test succeeded
   */
  async testConnection(connectionName) {
    await this.goToConnections();

    // Find the connection row and click test button
    const connectionRow = this.page.locator(`tr:has-text("${connectionName}")`);
    await connectionRow.locator(this.testConnectionButton).click();

    // Wait for success or error message
    try {
      await this.page.locator(this.successMessage).waitFor({ state: 'visible', timeout: 10000 });
      return true;
    } catch {
      try {
        await this.page.locator(this.errorMessage).waitFor({ state: 'visible', timeout: 2000 });
        return false;
      } catch {
        throw new Error('No test result message appeared');
      }
    }
  }

  /**
   * Refresh schema for a connection
   *
   * @param {string} connectionName - Name of the connection
   */
  async refreshSchema(connectionName) {
    await this.goToConnections();

    // Find the connection row and click refresh button
    const connectionRow = this.page.locator(`tr:has-text("${connectionName}")`);
    await connectionRow.locator(this.refreshSchemaButton).click();

    // Wait for success message
    await this.page.locator(this.successMessage).waitFor({ state: 'visible', timeout: 30000 });
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Check if user has access to admin dashboard
   *
   * @returns {Promise<boolean>}
   */
  async hasAdminAccess() {
    await this.page.goto('/admin');
    await this.page.waitForLoadState('networkidle');

    // Check if we're still on /admin (not redirected)
    return this.page.url().includes('/admin');
  }

  /**
   * Get success message text
   *
   * @returns {Promise<string|null>}
   */
  async getSuccessMessage() {
    try {
      const element = this.page.locator(this.successMessage).first();
      await element.waitFor({ state: 'visible', timeout: 2000 });
      return await element.textContent();
    } catch {
      return null;
    }
  }

  /**
   * Get error message text
   *
   * @returns {Promise<string|null>}
   */
  async getErrorMessage() {
    try {
      const element = this.page.locator(this.errorMessage).first();
      await element.waitFor({ state: 'visible', timeout: 2000 });
      return await element.textContent();
    } catch {
      return null;
    }
  }
}
