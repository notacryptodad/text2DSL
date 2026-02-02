/**
 * Test fixtures for workspace management tests
 * Provides real API calls for backend integration testing
 */

/**
 * Helper to create a workspace via API
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} token - Authorization token
 * @param {Object} workspaceData - Workspace creation data
 * @returns {Promise<Object>} Created workspace
 */
export async function createWorkspaceViaAPI(page, token, workspaceData) {
  // Generate slug from name if not provided
  const slug = workspaceData.slug || workspaceData.name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');

  const response = await page.request.post('http://localhost:8000/api/v1/workspaces', {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    data: {
      name: workspaceData.name,
      slug: slug,
      description: workspaceData.description || '',
      settings: workspaceData.settings || {},
    },
  });

  if (!response.ok()) {
    const errorText = await response.text();
    throw new Error(`Workspace creation failed: ${response.status()} ${errorText}`);
  }

  return await response.json();
}

/**
 * Helper to list workspaces via API
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} token - Authorization token
 * @returns {Promise<Array>} List of workspaces
 */
export async function listWorkspacesViaAPI(page, token) {
  const response = await page.request.get('http://localhost:8000/api/v1/workspaces', {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok()) {
    const errorText = await response.text();
    throw new Error(`Workspace list failed: ${response.status()} ${errorText}`);
  }

  return await response.json();
}

/**
 * Helper to create a provider via API
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} token - Authorization token
 * @param {string} workspaceId - Workspace ID
 * @param {Object} providerData - Provider creation data
 * @returns {Promise<Object>} Created provider
 */
export async function createProviderViaAPI(page, token, workspaceId, providerData) {
  const response = await page.request.post(
    `http://localhost:8000/api/v1/workspaces/${workspaceId}/providers`,
    {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      data: {
        name: providerData.name,
        type: providerData.type,
        description: providerData.description || '',
        settings: providerData.settings || {},
      },
    }
  );

  if (!response.ok()) {
    const errorText = await response.text();
    throw new Error(`Provider creation failed: ${response.status()} ${errorText}`);
  }

  return await response.json();
}

/**
 * Helper to list providers via API
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} token - Authorization token
 * @param {string} workspaceId - Workspace ID
 * @returns {Promise<Array>} List of providers
 */
export async function listProvidersViaAPI(page, token, workspaceId) {
  const response = await page.request.get(
    `http://localhost:8000/api/v1/workspaces/${workspaceId}/providers`,
    {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    }
  );

  if (!response.ok()) {
    const errorText = await response.text();
    throw new Error(`Provider list failed: ${response.status()} ${errorText}`);
  }

  return await response.json();
}

/**
 * Helper to create a connection via API
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} token - Authorization token
 * @param {string} workspaceId - Workspace ID
 * @param {string} providerId - Provider ID
 * @param {Object} connectionData - Connection creation data
 * @returns {Promise<Object>} Created connection
 */
export async function createConnectionViaAPI(page, token, workspaceId, providerId, connectionData) {
  const response = await page.request.post(
    `http://localhost:8000/api/v1/workspaces/${workspaceId}/providers/${providerId}/connections`,
    {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      data: {
        name: connectionData.name,
        host: connectionData.host,
        port: connectionData.port,
        database: connectionData.database,
        schema_name: connectionData.schema_name || null,
        credentials: {
          username: connectionData.username,
          password: connectionData.password,
        },
        connection_options: connectionData.connection_options || {},
      },
    }
  );

  if (!response.ok()) {
    const errorText = await response.text();
    throw new Error(`Connection creation failed: ${response.status()} ${errorText}`);
  }

  return await response.json();
}

/**
 * Helper to list connections via API
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} token - Authorization token
 * @param {string} workspaceId - Workspace ID
 * @param {string} providerId - Provider ID
 * @returns {Promise<Array>} List of connections
 */
export async function listConnectionsViaAPI(page, token, workspaceId, providerId) {
  const response = await page.request.get(
    `http://localhost:8000/api/v1/workspaces/${workspaceId}/providers/${providerId}/connections`,
    {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    }
  );

  if (!response.ok()) {
    const errorText = await response.text();
    throw new Error(`Connection list failed: ${response.status()} ${errorText}`);
  }

  return await response.json();
}

/**
 * Helper to test a connection via API
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} token - Authorization token
 * @param {string} workspaceId - Workspace ID
 * @param {string} providerId - Provider ID
 * @param {string} connectionId - Connection ID
 * @returns {Promise<Object>} Test result
 */
export async function testConnectionViaAPI(page, token, workspaceId, providerId, connectionId) {
  const response = await page.request.post(
    `http://localhost:8000/api/v1/workspaces/${workspaceId}/providers/${providerId}/connections/${connectionId}/test`,
    {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    }
  );

  if (!response.ok()) {
    const errorText = await response.text();
    throw new Error(`Connection test failed: ${response.status()} ${errorText}`);
  }

  return await response.json();
}

/**
 * Helper to refresh schema via API
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} token - Authorization token
 * @param {string} workspaceId - Workspace ID
 * @param {string} providerId - Provider ID
 * @param {string} connectionId - Connection ID
 * @returns {Promise<Object>} Refresh result
 */
export async function refreshSchemaViaAPI(page, token, workspaceId, providerId, connectionId) {
  const response = await page.request.post(
    `http://localhost:8000/api/v1/workspaces/${workspaceId}/providers/${providerId}/connections/${connectionId}/schema/refresh`,
    {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    }
  );

  if (!response.ok()) {
    const errorText = await response.text();
    throw new Error(`Schema refresh failed: ${response.status()} ${errorText}`);
  }

  return await response.json();
}

/**
 * Helper to delete a workspace via API
 *
 * @param {import('@playwright/test').Page} page - Playwright page object
 * @param {string} token - Authorization token
 * @param {string} workspaceId - Workspace ID
 */
export async function deleteWorkspaceViaAPI(page, token, workspaceId) {
  const response = await page.request.delete(
    `http://localhost:8000/api/v1/workspaces/${workspaceId}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    }
  );

  if (!response.ok()) {
    const errorText = await response.text();
    throw new Error(`Workspace deletion failed: ${response.status()} ${errorText}`);
  }
}
