import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './hooks/useAuth'
import ProtectedRoute from './components/ProtectedRoute'
import AppLayout from './components/AppLayout'
import Login from './pages/Login'
import Register from './pages/Register'
import Chat from './pages/Chat'
import Review from './pages/Review'
import SchemaAnnotation from './pages/SchemaAnnotation'
import FeedbackStats from './pages/FeedbackStats'
import UserProfile from './pages/UserProfile'
import AdminUsers from './pages/AdminUsers'

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
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Protected Routes */}
          <Route
            path="/app/*"
            element={
              <ProtectedRoute>
                <AppLayout darkMode={darkMode} toggleDarkMode={toggleDarkMode}>
                  <Routes>
                    <Route path="/" element={<Chat />} />
                    <Route path="/review" element={<Review />} />
                    <Route path="/schema-annotation" element={<SchemaAnnotation />} />
                    <Route path="/feedback-stats" element={<FeedbackStats />} />
                    <Route path="/profile" element={<UserProfile />} />
                    <Route
                      path="/admin/users"
                      element={
                        <ProtectedRoute requireAdmin={true}>
                          <AdminUsers />
                        </ProtectedRoute>
                      }
                    />
                  </Routes>
                </AppLayout>
              </ProtectedRoute>
            }
          />

          {/* Default Redirect */}
          <Route path="/" element={<Navigate to="/app" replace />} />
          <Route path="*" element={<Navigate to="/app" replace />} />
        </Routes>
      </AuthProvider>
    </Router>
  )
}

export default App
