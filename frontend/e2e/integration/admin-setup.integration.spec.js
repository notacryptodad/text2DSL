/**
 * Integration Test: Admin Setup Flow
 * 
 * Tests real CRUD operations against PostgreSQL database.
 * Requires: Docker stack running (make docker-up)
 */
import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage.js';

// Test data cleanup
const createdResources = {
  workspaces: [],
  providers: [],
  connections: []
};

test.describe('Integration: Admin Setup', () => {
  test.beforeAll(async () => {
    // Verify backend is healthy
    const response = await fetch('http://localhost:8000/health');
    const health = await response.json();
    expect(health.status).toBe('healthy');
    expect(health.services.database.status).toBe('healthy');
  });

  test.afterAll(async ({ request }) => {
    // Cleanup created resources in reverse order
    for (const connId of createdResources.connections) {
      await request.delete(`http://localhost:8000/api/v1/admin/connections/${connId}`);
    }
    for (const providerId of createdResources.providers) {
      await request.delete(`http://localhost:8000/api/v1/admin/providers/${providerId}`);
    }
    for (const workspaceId of createdResources.workspaces) {
      await request.delete(`http://localhost:8000/api/v1/workspaces/${workspaceId}`);
    }
  });

  test('should create workspace via real API', async ({ page, request }) => {
    // Login as admin
    const loginPage = new LoginPage(page);
    await loginPage.goto();
    await loginPage.login('super.admin@example.com', 'admin123');
    
    // Create workspace via API
    const workspaceName = `Integration Test ${Date.now()}`;
    const response = await request.post('http://localhost:8000/api/v1/workspaces', {
      data: { name: workspaceName, description: 'Integration test workspace' }
    });
    
    expect(response.ok()).toBeTruthy();
    const workspace = await response.json();
    expect(workspace.name).toBe(workspaceName);
    expect(workspace.id).toBeTruthy();
    
    createdResources.workspaces.push(workspace.id);
  });

  test('should create PostgreSQL provider', async ({ request }) => {
    const response = await request.post('http://localhost:8000/api/v1/admin/providers', {
      data: {
        name: 'Test PostgreSQL',
        provider_type: 'postgresql',
        workspace_id: createdResources.workspaces[0]
      }
    });
    
    expect(response.ok()).toBeTruthy();
    const provider = await response.json();
    expect(provider.provider_type).toBe('postgresql');
    
    createdResources.providers.push(provider.id);
  });

  test('should create database connection', async ({ request }) => {
    const response = await request.post('http://localhost:8000/api/v1/admin/connections', {
      data: {
        name: 'Test Connection',
        provider_id: createdResources.providers[0],
        host: 'localhost',
        port: 5432,
        database: 'text2dsl_test',
        username: 'postgres',
        password: 'postgres'
      }
    });
    
    expect(response.ok()).toBeTruthy();
    const connection = await response.json();
    expect(connection.name).toBe('Test Connection');
    
    createdResources.connections.push(connection.id);
  });

  test('should test database connection successfully', async ({ request }) => {
    const connId = createdResources.connections[0];
    const response = await request.post(`http://localhost:8000/api/v1/connections/${connId}/test`);
    
    expect(response.ok()).toBeTruthy();
    const result = await response.json();
    expect(result.success).toBe(true);
  });

  test('should retrieve real schema from test database', async ({ request }) => {
    const connId = createdResources.connections[0];
    const response = await request.get(`http://localhost:8000/api/v1/connections/${connId}/schema`);
    
    expect(response.ok()).toBeTruthy();
    const schema = await response.json();
    
    // Verify expected tables from seed data exist
    const tableNames = schema.tables.map(t => t.name);
    expect(tableNames).toContain('customers');
    expect(tableNames).toContain('products');
    expect(tableNames).toContain('orders');
    expect(tableNames).toContain('order_items');
  });
});
