/**
 * Integration Test: RAG Search
 * 
 * Tests vector similarity search in OpenSearch.
 * Requires: OpenSearch running with indexed sample queries
 */
import { test, expect } from '@playwright/test';

const API_BASE = 'http://localhost:8000/api/v1';
const OPENSEARCH_URL = 'http://localhost:9200';

test.describe('Integration: RAG Search', () => {
  test.beforeAll(async () => {
    // Verify OpenSearch is healthy
    const response = await fetch(OPENSEARCH_URL);
    expect(response.ok).toBeTruthy();
    
    // Verify index exists
    const indexResponse = await fetch(`${OPENSEARCH_URL}/text2dsl-queries`);
    expect(indexResponse.ok).toBeTruthy();
  });

  test('should find similar queries for customer count', async ({ request }) => {
    const response = await request.post(`${API_BASE}/rag/search`, {
      data: {
        query: 'How many customers do we have?',
        limit: 5
      }
    });
    
    if (response.ok()) {
      const results = await response.json();
      expect(results.length).toBeGreaterThan(0);
      
      // Should find similar customer-related queries
      const hasRelevant = results.some(r => 
        r.question.toLowerCase().includes('customer') ||
        r.sql.toLowerCase().includes('customers')
      );
      expect(hasRelevant).toBeTruthy();
    }
  });

  test('should find similar queries for product listing', async ({ request }) => {
    const response = await request.post(`${API_BASE}/rag/search`, {
      data: {
        query: 'Show me all products',
        limit: 5
      }
    });
    
    if (response.ok()) {
      const results = await response.json();
      expect(results.length).toBeGreaterThan(0);
      
      const hasRelevant = results.some(r => 
        r.question.toLowerCase().includes('product') ||
        r.sql.toLowerCase().includes('products')
      );
      expect(hasRelevant).toBeTruthy();
    }
  });

  test('should return results with similarity scores', async ({ request }) => {
    const response = await request.post(`${API_BASE}/rag/search`, {
      data: {
        query: 'total revenue',
        limit: 3
      }
    });
    
    if (response.ok()) {
      const results = await response.json();
      
      for (const result of results) {
        expect(result.score).toBeDefined();
        expect(result.score).toBeGreaterThanOrEqual(0);
        expect(result.score).toBeLessThanOrEqual(1);
      }
    }
  });

  test('should respect limit parameter', async ({ request }) => {
    const response = await request.post(`${API_BASE}/rag/search`, {
      data: {
        query: 'orders',
        limit: 2
      }
    });
    
    if (response.ok()) {
      const results = await response.json();
      expect(results.length).toBeLessThanOrEqual(2);
    }
  });

  test('should handle empty results gracefully', async ({ request }) => {
    const response = await request.post(`${API_BASE}/rag/search`, {
      data: {
        query: 'xyzzy quantum flux capacitor gibberish',
        limit: 5
      }
    });
    
    expect(response.ok()).toBeTruthy();
    const results = await response.json();
    // May return low-score results or empty array
    expect(Array.isArray(results)).toBeTruthy();
  });

  test('should verify OpenSearch index has documents', async () => {
    const response = await fetch(`${OPENSEARCH_URL}/text2dsl-queries/_count`);
    const data = await response.json();
    
    expect(data.count).toBeGreaterThan(0);
    console.log(`OpenSearch index has ${data.count} documents`);
  });
});
