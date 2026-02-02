/**
 * Integration Test: Schema Retrieval
 *
 * Tests real schema introspection from PostgreSQL test database.
 * Requires: Docker stack with seeded test database
 */
import { test, expect } from '@playwright/test';

const API_BASE = 'http://localhost:8000/api/v1';

// Admin credentials from seed
const ADMIN_CREDENTIALS = {
  email: 'admin@text2dsl.com',
  password: 'Admin123!'
};

test.describe('Integration: Schema Retrieval', () => {
  let workspaceId;
  let providerId;
  let connectionId;
  let authToken;

  test.beforeAll(async ({ request }) => {
    // Authenticate and get token
    const authResponse = await request.post(`${API_BASE}/auth/token`, {
      data: {
        email: ADMIN_CREDENTIALS.email,
        password: ADMIN_CREDENTIALS.password
      }
    });
    expect(authResponse.ok()).toBeTruthy();
    const authData = await authResponse.json();
    authToken = authData.access_token;

    const headers = { 'Authorization': `Bearer ${authToken}` };

    // Create a test workspace
    const workspaceResponse = await request.post(`${API_BASE}/workspaces`, {
      headers,
      data: {
        name: `Schema Test Workspace ${Date.now()}`,
        slug: `schema-test-${Date.now()}`,
        description: 'Test workspace for schema retrieval integration tests'
      }
    });

    expect(workspaceResponse.ok()).toBeTruthy();
    const workspace = await workspaceResponse.json();
    workspaceId = workspace.id;

    // Create a PostgreSQL provider
    const providerResponse = await request.post(
      `${API_BASE}/workspaces/${workspaceId}/providers`,
      {
        headers,
        data: {
          name: 'Test PostgreSQL Provider',
          type: 'postgresql',
          description: 'Test provider for schema retrieval'
        }
      }
    );
    expect(providerResponse.ok()).toBeTruthy();
    const provider = await providerResponse.json();
    providerId = provider.id;

    // Create a connection to test database
    const connectionResponse = await request.post(
      `${API_BASE}/workspaces/${workspaceId}/providers/${providerId}/connections`,
      {
        headers,
        data: {
          name: 'Schema Test Connection',
          host: 'text2dsl-postgres-test',
          port: 5432,
          database: 'text2x',
          credentials: {
            username: 'text2x',
            password: 'text2x'
          }
        }
      }
    );
    expect(connectionResponse.ok()).toBeTruthy();
    const connection = await connectionResponse.json();
    connectionId = connection.id;

    // Trigger schema refresh
    const refreshResponse = await request.post(
      `${API_BASE}/workspaces/${workspaceId}/providers/${providerId}/connections/${connectionId}/schema/refresh`,
      { headers }
    );
    expect(refreshResponse.ok()).toBeTruthy();
  });

  test.afterAll(async ({ request }) => {
    // Clean up created resources
    const headers = { 'Authorization': `Bearer ${authToken}` };

    if (connectionId && providerId && workspaceId) {
      await request.delete(
        `${API_BASE}/workspaces/${workspaceId}/providers/${providerId}/connections/${connectionId}`,
        { headers }
      );
    }

    if (providerId && workspaceId) {
      await request.delete(
        `${API_BASE}/workspaces/${workspaceId}/providers/${providerId}`,
        { headers }
      );
    }

    if (workspaceId) {
      await request.delete(`${API_BASE}/workspaces/${workspaceId}`, { headers });
    }
  });

  test('should retrieve all tables from test database', async ({ request }) => {
    const headers = { 'Authorization': `Bearer ${authToken}` };
    const response = await request.get(
      `${API_BASE}/annotations/workspaces/${workspaceId}/connections/${connectionId}/schema`,
      { headers }
    );

    expect(response.ok()).toBeTruthy();

    const schema = await response.json();
    expect(schema.tables).toBeDefined();
    expect(schema.tables.length).toBeGreaterThan(0);
    expect(schema.table_count).toBeGreaterThan(0);

    // Check for expected test database tables
    const tableNames = schema.tables.map(t => t.name.toLowerCase());
    expect(tableNames).toContain('users');
    expect(tableNames).toContain('conversations');
    expect(tableNames).toContain('workspace_admins');
  });

  test('should retrieve columns for users table', async ({ request }) => {
    const headers = { 'Authorization': `Bearer ${authToken}` };
    const response = await request.get(
      `${API_BASE}/annotations/workspaces/${workspaceId}/connections/${connectionId}/schema`,
      { headers }
    );
    expect(response.ok()).toBeTruthy();

    const schema = await response.json();
    const usersTable = schema.tables.find(t => t.name.toLowerCase() === 'users');

    expect(usersTable).toBeDefined();
    expect(usersTable.columns).toBeDefined();
    expect(usersTable.columns.length).toBeGreaterThan(0);

    const columnNames = usersTable.columns.map(c => c.name.toLowerCase());

    expect(columnNames).toContain('id');
    expect(columnNames).toContain('email');
  });

  test('should identify primary keys', async ({ request }) => {
    const headers = { 'Authorization': `Bearer ${authToken}` };
    const response = await request.get(
      `${API_BASE}/annotations/workspaces/${workspaceId}/connections/${connectionId}/schema`,
      { headers }
    );
    const schema = await response.json();
    const usersTable = schema.tables.find(t => t.name.toLowerCase() === 'users');

    expect(usersTable).toBeDefined();
    expect(usersTable.primary_keys).toBeDefined();
    expect(usersTable.primary_keys.length).toBeGreaterThan(0);

    const pkColumnNames = usersTable.primary_keys.map(pk => pk.toLowerCase());
    expect(pkColumnNames).toContain('id');

    // Also check the column metadata
    const pkColumn = usersTable.columns.find(c => c.primary_key);
    expect(pkColumn).toBeDefined();
    expect(pkColumn.name.toLowerCase()).toBe('id');
  });

  test('should identify foreign key relationships', async ({ request }) => {
    const headers = { 'Authorization': `Bearer ${authToken}` };
    const response = await request.get(
      `${API_BASE}/annotations/workspaces/${workspaceId}/connections/${connectionId}/schema`,
      { headers }
    );
    const schema = await response.json();
    const conversationTurnsTable = schema.tables.find(t => t.name.toLowerCase() === 'conversation_turns');

    expect(conversationTurnsTable).toBeDefined();
    expect(conversationTurnsTable.foreign_keys).toBeDefined();
    expect(conversationTurnsTable.foreign_keys.length).toBeGreaterThan(0);

    // Find the foreign key for conversation_id
    const conversationFk = conversationTurnsTable.foreign_keys.find(
      fk => fk.column.toLowerCase().includes('conversation_id')
    );

    expect(conversationFk).toBeDefined();
    expect(conversationFk.references_table.toLowerCase()).toBe('conversations');
  });

  test('should retrieve table row counts', async ({ request }) => {
    const headers = { 'Authorization': `Bearer ${authToken}` };
    const response = await request.get(
      `${API_BASE}/annotations/workspaces/${workspaceId}/connections/${connectionId}/schema`,
      { headers }
    );
    expect(response.ok()).toBeTruthy();

    const schema = await response.json();

    // Check that tables have row_count information
    const usersTable = schema.tables.find(t => t.name.toLowerCase() === 'users');
    const conversationsTable = schema.tables.find(t => t.name.toLowerCase() === 'conversations');

    expect(usersTable).toBeDefined();
    expect(conversationsTable).toBeDefined();

    // Row counts may be null if not yet gathered, but should be defined
    expect(usersTable.row_count).toBeDefined();
    expect(conversationsTable.row_count).toBeDefined();
  });

  test('should handle non-existent connection gracefully', async ({ request }) => {
    const headers = { 'Authorization': `Bearer ${authToken}` };
    const fakeConnectionId = '00000000-0000-0000-0000-000000000000';
    const response = await request.get(
      `${API_BASE}/annotations/workspaces/${workspaceId}/connections/${fakeConnectionId}/schema`,
      { headers }
    );
    expect(response.status()).toBe(404);
  });
});
