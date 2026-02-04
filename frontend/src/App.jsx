import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './hooks/useAuth'
import { WorkspaceProvider } from './contexts/WorkspaceContext'
import ProtectedRoute from './components/ProtectedRoute'
import AppLayout from './components/AppLayout'
import AdminLayout from './components/AdminLayout'
import RouteErrorBoundary from './components/RouteErrorBoundary'
import Login from './pages/Login'
import Register from './pages/Register'
import Chat from './pages/Chat'
import Review from './pages/Review'
import SchemaAnnotation from './pages/SchemaAnnotation'
import FeedbackStats from './pages/FeedbackStats'
import UserProfile from './pages/UserProfile'
import AdminUsers from './pages/AdminUsers'
import AdminDashboard from './pages/AdminDashboard'
import Workspaces from './pages/Workspaces'
import WorkspaceDetail from './pages/WorkspaceDetail'
import ProviderDetail from './pages/ProviderDetail'
import Providers from './pages/Providers'
import Connections from './pages/Connections'
import NotFound from './pages/NotFound'
import * as ROUTES from './constants/routes'

function App() {
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('darkMode')
    if (saved !== null) return saved === 'true'
    return window.matchMedia('(prefers-color-scheme: dark)').matches
  })

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
    localStorage.setItem('darkMode', darkMode)
  }, [darkMode])

  const toggleDarkMode = () => {
    setDarkMode(!darkMode)
  }

  return (
    <Router>
      <AuthProvider>
        <WorkspaceProvider>
          <Routes>
          {/* Public Routes */}
          <Route path={ROUTES.LOGIN} element={<Login />} />
          <Route path={ROUTES.REGISTER} element={<Register />} />

          {/* Protected Routes - All under /app/* with AppLayout header */}
          <Route
            path="/app/*"
            element={
              <ProtectedRoute>
                <AppLayout darkMode={darkMode} toggleDarkMode={toggleDarkMode}>
                  <RouteErrorBoundary>
                    <Routes>
                      {/* User pages */}
                      <Route path="/" element={<Chat />} />
                    <Route path="review" element={<Review />} />
                    <Route path="schema-annotation" element={<SchemaAnnotation />} />
                    <Route path="feedback-stats" element={<FeedbackStats />} />
                    <Route path="profile" element={<UserProfile />} />

                    {/* Admin pages - wrapped in AdminLayout for sidebar */}
                    <Route
                      path="admin"
                      element={
                        <ProtectedRoute requireAdmin={true}>
                          <AdminLayout>
                            <AdminDashboard />
                          </AdminLayout>
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="admin/workspaces"
                      element={
                        <ProtectedRoute requireAdmin={true}>
                          <AdminLayout>
                            <Workspaces />
                          </AdminLayout>
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="admin/workspaces/:workspaceId"
                      element={
                        <ProtectedRoute requireAdmin={true}>
                          <AdminLayout>
                            <WorkspaceDetail />
                          </AdminLayout>
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="admin/workspaces/:workspaceId/providers/:providerId"
                      element={
                        <ProtectedRoute requireAdmin={true}>
                          <AdminLayout>
                            <ProviderDetail />
                          </AdminLayout>
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="admin/providers"
                      element={
                        <ProtectedRoute requireAdmin={true}>
                          <AdminLayout>
                            <Providers />
                          </AdminLayout>
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="admin/connections"
                      element={
                        <ProtectedRoute requireAdmin={true}>
                          <AdminLayout>
                            <Connections />
                          </AdminLayout>
                        </ProtectedRoute>
                      }
                    />
                    <Route
                      path="admin/users"
                      element={
                        <ProtectedRoute requireAdmin={true}>
                          <AdminLayout>
                            <AdminUsers />
                          </AdminLayout>
                        </ProtectedRoute>
                      }
                    />
                    </Routes>
                  </RouteErrorBoundary>
                </AppLayout>
              </ProtectedRoute>
            }
          />

          {/* Redirect old /admin/* routes to /app/admin/* */}
          <Route path="/admin" element={<Navigate to={ROUTES.ADMIN} replace />} />
          <Route path="/admin/*" element={<Navigate to={ROUTES.ADMIN} replace />} />

          {/* Default Redirect */}
          <Route path="/" element={<Navigate to={ROUTES.APP} replace />} />

          {/* 404 Not Found - Catch all unmatched routes */}
          <Route path="*" element={<NotFound />} />
          </Routes>
        </WorkspaceProvider>
      </AuthProvider>
    </Router>
  )
}

export default App
