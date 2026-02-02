import { test, expect } from '@playwright/test';
import { loginViaAPI, TEST_USERS } from './fixtures/auth.fixture.js';
import {
  createWorkspaceViaAPI,
  listWorkspacesViaAPI,
  createProviderViaAPI,
  listProvidersViaAPI,
  createConnectionViaAPI,
  listConnectionsViaAPI,
  testConnectionViaAPI,
  refreshSchemaViaAPI,
  deleteWorkspaceViaAPI,
} from './fixtures/workspace.fixture.js';

/**
 * Scenario 1: Admin Setup Tests
 *
 * Tests the complete admin setup workflow using REAL backend API calls:
 * - Create workspace
 * - Configure provider
 * - Add database connection
 * - Test connection
 * - Refresh schema
 *
 * These tests run serially and share state to set up the environment
 * for subsequent test scenarios.
 */

// Configure tests to run serially with shared state
test.describe.configure({ mode: 'serial' });

// Admin setup tests - testing real backend integration
test.describe('Scenario 1: Admin Setup', () => {
  let adminToken;
  let workspaceId;
  let providerId;
  let connectionId;
  let workspaceName;
  let providerName;
  let connectionName;

  test.beforeAll(async ({ browser }) => {
    // Generate unique names for this test run
    const timestamp = Date.now();
    workspaceName = `Test Workspace ${timestamp}`;
    providerName = `Test Provider ${timestamp}`;
    connectionName = `Test Connection ${timestamp}`;

    // Get admin token for API calls
    const context = await browser.newContext();
    const page = await context.newPage();
    adminToken = await loginViaAPI(page, TEST_USERS.super_admin);
    await context.close();
  });

  test.afterAll(async ({ browser }) => {
    // Clean up: delete the test workspace
    if (workspaceId && adminToken) {
      try {
        const context = await browser.newContext();
        const page = await context.newPage();
        await deleteWorkspaceViaAPI(page, adminToken, workspaceId);
        await context.close();
        console.log(`✅ Cleaned up test workspace: ${workspaceId}`);
      } catch (error) {
        console.warn(`⚠️  Failed to clean up workspace: ${error.message}`);
      }
    }
  });

  test('should create a new workspace', async ({ page }) => {
    // Create workspace via API
    const workspace = await createWorkspaceViaAPI(page, adminToken, {
      name: workspaceName,
      description: 'Test workspace for E2E tests',
    });

    // Store workspace ID for subsequent tests
    workspaceId = workspace.id;

    // Verify workspace was created
    expect(workspace.name).toBe(workspaceName);
    expect(workspace.description).toBe('Test workspace for E2E tests');
    expect(workspace.id).toBeTruthy();

    console.log(`✅ Created workspace: ${workspace.id}`);
  });

  test('should list workspaces', async ({ page }) => {
    // List workspaces via API
    const workspaces = await listWorkspacesViaAPI(page, adminToken);

    // Verify our workspace is in the list
    expect(Array.isArray(workspaces)).toBe(true);
    const ourWorkspace = workspaces.find(w => w.id === workspaceId);
    expect(ourWorkspace).toBeTruthy();
    expect(ourWorkspace.name).toBe(workspaceName);
  });

  test('should create a PostgreSQL provider', async ({ page }) => {
    // Create provider via API
    const provider = await createProviderViaAPI(page, adminToken, workspaceId, {
      name: providerName,
      type: 'postgresql',
      description: 'Test PostgreSQL provider',
    });

    // Store provider ID for subsequent tests
    providerId = provider.id;

    // Verify provider was created
    expect(provider.name).toBe(providerName);
    expect(provider.type).toBe('postgresql');
    expect(provider.workspace_id).toBe(workspaceId);
    expect(provider.id).toBeTruthy();

    console.log(`✅ Created provider: ${provider.id}`);
  });

  test('should list providers', async ({ page }) => {
    // List providers via API
    const providers = await listProvidersViaAPI(page, adminToken, workspaceId);

    // Verify our provider is in the list
    expect(Array.isArray(providers)).toBe(true);
    const ourProvider = providers.find(p => p.id === providerId);
    expect(ourProvider).toBeTruthy();
    expect(ourProvider.name).toBe(providerName);
  });

  test('should create a database connection', async ({ page }) => {
    // Create connection via API
    const connection = await createConnectionViaAPI(page, adminToken, workspaceId, providerId, {
      name: connectionName,
      host: process.env.TEST_DB_HOST || 'localhost',
      port: parseInt(process.env.TEST_DB_PORT || '5432'),
      database: process.env.TEST_DB_NAME || 'text2x',
      username: process.env.TEST_DB_USER || 'text2x',
      password: process.env.TEST_DB_PASSWORD || 'text2x',
    });

    // Store connection ID for subsequent tests
    connectionId = connection.id;

    // Verify connection was created
    expect(connection.name).toBe(connectionName);
    expect(connection.host).toBe(process.env.TEST_DB_HOST || 'localhost');
    expect(connection.provider_id).toBe(providerId);
    expect(connection.id).toBeTruthy();

    console.log(`✅ Created connection: ${connection.id}`);
  });

  test('should list connections', async ({ page }) => {
    // List connections via API
    const connections = await listConnectionsViaAPI(page, adminToken, workspaceId, providerId);

    // Verify our connection is in the list
    expect(Array.isArray(connections)).toBe(true);
    const ourConnection = connections.find(c => c.id === connectionId);
    expect(ourConnection).toBeTruthy();
    expect(ourConnection.name).toBe(connectionName);
  });

  test('should test database connection successfully', async ({ page }) => {
    // Test the connection via API
    const testResult = await testConnectionViaAPI(page, adminToken, workspaceId, providerId, connectionId);

    // Verify test succeeded
    expect(testResult.success).toBe(true);
    expect(testResult.message).toBeTruthy();
    expect(testResult.latency_ms).toBeGreaterThan(0);

    console.log(`✅ Connection test succeeded: ${testResult.message}`);
  });

  test('should refresh database schema', async ({ page }) => {
    // Refresh schema via API
    const refreshResult = await refreshSchemaViaAPI(page, adminToken, workspaceId, providerId, connectionId);

    // Verify refresh succeeded
    expect(refreshResult.status).toBe('success');
    expect(refreshResult.message).toBeTruthy();
    expect(refreshResult.table_count).toBeGreaterThanOrEqual(0);

    console.log(`✅ Schema refresh succeeded: ${refreshResult.table_count} tables found`);
  });
});
