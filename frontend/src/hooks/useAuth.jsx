import { createContext, useContext, useState, useEffect } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  // Use relative URLs to leverage Vite's proxy configuration
  const apiUrl = ''

  useEffect(() => {
    // Check for existing token on mount
    const token = localStorage.getItem('access_token')
    if (token) {
      fetchCurrentUser(token)
    } else {
      setLoading(false)
    }
  }, [])

  const fetchCurrentUser = async (token) => {
    try {
      const response = await fetch(`${apiUrl}/api/v1/auth/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (response.ok) {
        const userData = await response.json()
        setUser(userData)
        setIsAuthenticated(true)
      } else {
        // Token is invalid, clear it
        localStorage.removeItem('access_token')
        setUser(null)
        setIsAuthenticated(false)
      }
    } catch (error) {
      console.error('Error fetching current user:', error)
      localStorage.removeItem('access_token')
      setUser(null)
      setIsAuthenticated(false)
    } finally {
      setLoading(false)
    }
  }

  const login = async (email, password) => {
    try {
      const response = await fetch(`${apiUrl}/api/v1/auth/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          password,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.message || error.detail || 'Login failed')
      }

      const data = await response.json()
      localStorage.setItem('access_token', data.access_token)
      await fetchCurrentUser(data.access_token)
      return { success: true }
    } catch (error) {
      console.error('Login error:', error)
      return { success: false, error: error.message }
    }
  }

  const register = async (name, email, password) => {
    try {
      const response = await fetch(`${apiUrl}/api/v1/users/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name,
          email,
          password,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Registration failed')
      }

      const data = await response.json()
      return { success: true, data }
    } catch (error) {
      console.error('Registration error:', error)
      return { success: false, error: error.message }
    }
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    setUser(null)
    setIsAuthenticated(false)
  }

  const updateProfile = async (updates) => {
    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch(`${apiUrl}/api/v1/users/me`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(updates),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Update failed')
      }

      const data = await response.json()
      setUser(data)
      return { success: true, data }
    } catch (error) {
      console.error('Update profile error:', error)
      return { success: false, error: error.message }
    }
  }

  const changePassword = async (currentPassword, newPassword) => {
    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch(`${apiUrl}/api/v1/users/me/password`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Password change failed')
      }

      return { success: true }
    } catch (error) {
      console.error('Change password error:', error)
      return { success: false, error: error.message }
    }
  }

  const isAdmin = user && (user.role === 'admin' || user.role === 'super_admin')
  const isSuperAdmin = user && user.role === 'super_admin'

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated,
        isAdmin,
        isSuperAdmin,
        login,
        register,
        logout,
        updateProfile,
        changePassword,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
