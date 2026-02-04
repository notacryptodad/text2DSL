// Centralized route constants for the application

// Public routes
export const LOGIN = '/login'
export const REGISTER = '/register'

// App routes (requires authentication)
export const APP = '/app'
export const CHAT = '/app'
export const REVIEW = '/app/review'
export const SCHEMA_ANNOTATION = '/app/schema-annotation'
export const FEEDBACK_STATS = '/app/feedback-stats'
export const PROFILE = '/app/profile'

// Admin routes (requires admin privileges)
export const ADMIN = '/app/admin'
export const ADMIN_DASHBOARD = '/app/admin'
export const ADMIN_WORKSPACES = '/app/admin/workspaces'
export const ADMIN_PROVIDERS = '/app/admin/providers'
export const ADMIN_CONNECTIONS = '/app/admin/connections'
export const ADMIN_USERS = '/app/admin/users'

// Helper functions for building dynamic routes
export const buildRoute = {
  workspaceDetail: (workspaceId) => `/app/admin/workspaces/${workspaceId}`,
  providerDetail: (workspaceId, providerId) => `/app/admin/workspaces/${workspaceId}/providers/${providerId}`,
  schemaAnnotation: (workspaceId, connectionId) => `/app/admin/schema-annotation?workspace=${workspaceId}&connection=${connectionId}`,
}

// Helper function to check if a path is an admin route
export const isAdminRoute = (pathname) => {
  return pathname.startsWith('/app/admin')
}

// Helper function to check if a path needs workspace selector in the navbar
// Note: schema-annotation has its own workspace dropdown in the page content
export const needsWorkspaceSelector = (pathname) => {
  // Only the main chat page needs the navbar workspace selector
  // Other pages either don't need it or have their own
  return pathname === '/app' || pathname === '/app/'
}

// Array of pages that need workspace selector (for backward compatibility)
export const PAGES_NEEDING_WORKSPACE = ['/app']
