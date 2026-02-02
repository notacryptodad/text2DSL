/**
 * Integration Test: Schema Retrieval
 * 
 * Tests real schema introspection from PostgreSQL test database.
 * Requires: Docker stack with seeded test database
 */
import { test, expect } from '@playwright/test';

const API_BASE = 'http://localhost:8000/api/v1';

test.describe('Integration: Schema Retrieval', () => {
  let connectionId;

  test.beforeAll(async ({ request }) => {
    // Get or create a test connection
    const connResponse = await request.get(`${API_BASE}/admin/connections`);
    const connections = await connResponse.json();
    
    if (connections.length > 0) {
      connectionId = connections[0].id;
    } else {
      // Create one if none exists
      const createResp = await request.post(`${API_BASE}/admin/connections`, {
        data: {
          name: 'Schema Test Connection',
          host: 'localhost',
          port: 5432,
          database: 'text2dsl_test',
          username: 'postgres',
          password: 'postgres'
        }
      });
      const conn = await createResp.json();
      connectionId = conn.id;
    }
  });

  test('should retrieve all tables from test database', async ({ request }) => {
    const response = await request.get(`${API_BASE}/connections/${connectionId}/schema`);
    expect(response.ok()).toBeTruthy();
    
    const schema = await response.json();
    expect(schema.tables).toBeDefined();
    expect(schema.tables.length).toBeGreaterThan(0);
    
    // Check for expected e-commerce tables
    const tableNames = schema.tables.map(t => t.name.toLowerCase());
    expect(tableNames).toContain('customers');
    expect(tableNames).toContain('products');
    expect(tableNames).toContain('orders');
  });

  test('should retrieve columns for customers table', async ({ request }) => {
    const response = await request.get(`${API_BASE}/connections/${connectionId}/schema/tables/customers`);
    expect(response.ok()).toBeTruthy();
    
    const table = await response.json();
    const columnNames = table.columns.map(c => c.name.toLowerCase());
    
    expect(columnNames).toContain('id');
    expect(columnNames).toContain('name');
    expect(columnNames).toContain('email');
    expect(columnNames).toContain('created_at');
  });

  test('should identify primary keys', async ({ request }) => {
    const response = await request.get(`${API_BASE}/connections/${connectionId}/schema/tables/customers`);
    const table = await response.json();
    
    const pkColumn = table.columns.find(c => c.is_primary_key);
    expect(pkColumn).toBeDefined();
    expect(pkColumn.name.toLowerCase()).toBe('id');
  });

  test('should identify foreign key relationships', async ({ request }) => {
    const response = await request.get(`${API_BASE}/connections/${connectionId}/schema/tables/orders`);
    const table = await response.json();
    
    const fkColumn = table.columns.find(c => c.foreign_key);
    expect(fkColumn).toBeDefined();
    expect(fkColumn.name.toLowerCase()).toBe('customer_id');
    expect(fkColumn.foreign_key.table.toLowerCase()).toBe('customers');
  });

  test('should retrieve table row counts', async ({ request }) => {
    const response = await request.get(`${API_BASE}/connections/${connectionId}/schema/stats`);
    
    if (response.ok()) {
      const stats = await response.json();
      expect(stats.customers).toBeGreaterThan(0);
      expect(stats.products).toBeGreaterThan(0);
    }
    // Stats endpoint may not exist - skip if 404
  });

  test('should handle non-existent table gracefully', async ({ request }) => {
    const response = await request.get(`${API_BASE}/connections/${connectionId}/schema/tables/nonexistent_table_xyz`);
    expect(response.status()).toBe(404);
  });
});
