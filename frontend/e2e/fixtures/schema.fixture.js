/**
 * Test fixtures for schema annotation tests
 * Provides mock API responses for predictable E2E testing
 */

/**
 * Mock workspace data
 */
export const MOCK_WORKSPACES = [
  {
    id: 'test-workspace-1',
    name: 'Test Workspace',
    description: 'Test workspace for e2e tests',
    created_at: '2024-01-01T00:00:00Z',
  },
];

/**
 * Mock connection data
 */
export const MOCK_CONNECTIONS = [
  {
    id: 'test-connection-1',
    name: 'Test Database',
    type: 'postgresql',
    workspace_id: 'test-workspace-1',
    created_at: '2024-01-01T00:00:00Z',
  },
];

/**
 * Mock schema data
 */
export const MOCK_SCHEMA = [
  {
    table_name: 'customers',
    columns: [
      { column_name: 'id', data_type: 'integer', is_nullable: false },
      { column_name: 'name', data_type: 'varchar', is_nullable: false },
      { column_name: 'email', data_type: 'varchar', is_nullable: false },
      { column_name: 'created_at', data_type: 'timestamp', is_nullable: true },
    ],
  },
  {
    table_name: 'orders',
    columns: [
      { column_name: 'id', data_type: 'integer', is_nullable: false },
      { column_name: 'customer_id', data_type: 'integer', is_nullable: false },
      { column_name: 'total', data_type: 'numeric', is_nullable: false },
      { column_name: 'status', data_type: 'varchar', is_nullable: false },
      { column_name: 'created_at', data_type: 'timestamp', is_nullable: true },
    ],
  },
  {
    table_name: 'products',
    columns: [
      { column_name: 'id', data_type: 'integer', is_nullable: false },
      { column_name: 'name', data_type: 'varchar', is_nullable: false },
      { column_name: 'price', data_type: 'numeric', is_nullable: false },
      { column_name: 'category', data_type: 'varchar', is_nullable: true },
    ],
  },
];

/**
 * Mock annotation data
 */
export const MOCK_ANNOTATIONS = [
  {
    table_name: 'customers',
    description: 'Customer information table',
    business_terms: ['Customer', 'Client'],
    relationships: [
      {
        target_table: 'orders',
        type: 'one_to_many',
        description: 'One customer can have many orders',
      },
    ],
    columns: [
      { name: 'id', description: 'Unique customer identifier' },
      { name: 'name', description: 'Customer full name' },
      { name: 'email', description: 'Customer email address' },
    ],
  },
];

/**
 * Mock auto-annotation response
 */
export const MOCK_AUTO_ANNOTATE_RESPONSE = {
  annotated_count: 3,
  annotations: [
    {
      table_name: 'customers',
      description: 'Stores customer information and contact details',
      business_terms: ['Customer', 'Client', 'User'],
    },
    {
      table_name: 'orders',
      description: 'Tracks customer orders and transactions',
      business_terms: ['Order', 'Transaction', 'Purchase'],
    },
    {
      table_name: 'products',
      description: 'Product catalog and inventory information',
      business_terms: ['Product', 'Item', 'SKU'],
    },
  ],
};

/**
 * Mock chat response
 */
export const MOCK_CHAT_RESPONSE = {
  conversation_id: 'test-conversation-1',
  response:
    'The customers table stores basic customer information including their name, email, and registration date. It has a one-to-many relationship with the orders table.',
};

/**
 * Helper to setup API route mocking
 */
export async function setupSchemaMocks(page) {
  // Mock workspaces endpoint
  await page.route('**/api/v1/workspaces', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_WORKSPACES),
    });
  });

  // Mock connections endpoint
  await page.route('**/api/v1/workspaces/*/connections', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_CONNECTIONS),
    });
  });

  // Mock schema endpoint
  await page.route('**/api/v1/workspaces/*/connections/*/schema', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_SCHEMA),
      });
    }
  });

  // Mock annotations endpoint
  await page.route('**/api/v1/workspaces/*/connections/*/schema/annotations', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_ANNOTATIONS),
      });
    } else if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      });
    }
  });

  // Mock auto-annotate endpoint
  await page.route('**/api/v1/workspaces/*/connections/*/schema/auto-annotate', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_AUTO_ANNOTATE_RESPONSE),
    });
  });

  // Mock chat endpoint
  await page.route('**/api/v1/workspaces/*/connections/*/schema/chat', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_CHAT_RESPONSE),
    });
  });
}
