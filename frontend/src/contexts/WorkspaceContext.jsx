import { createContext, useContext, useState, useEffect } from 'react'

const WorkspaceContext = createContext(null)

export function WorkspaceProvider({ children }) {
  const [currentWorkspace, setCurrentWorkspace] = useState(() => {
    const saved = localStorage.getItem('currentWorkspace')
    return saved ? JSON.parse(saved) : null
  })
  const [currentConnection, setCurrentConnection] = useState(() => {
    const saved = localStorage.getItem('currentConnection')
    return saved ? JSON.parse(saved) : null
  })
  const [workspaces, setWorkspaces] = useState([])
  const [loading, setLoading] = useState(true)

  // Use relative URLs to leverage Vite's proxy configuration
  const apiUrl = ''

  useEffect(() => {
    // Fetch workspaces on mount
    fetchWorkspaces()
  }, [])

  useEffect(() => {
    // Save current workspace to localStorage
    if (currentWorkspace) {
      localStorage.setItem('currentWorkspace', JSON.stringify(currentWorkspace))
    }
  }, [currentWorkspace])

  useEffect(() => {
    // Save current connection to localStorage
    if (currentConnection) {
      localStorage.setItem('currentConnection', JSON.stringify(currentConnection))
    }
  }, [currentConnection])

  const fetchWorkspaces = async () => {
    try {
      const token = localStorage.getItem('access_token')
      if (!token) {
        setLoading(false)
        return
      }

      const response = await fetch(`${apiUrl}/api/v1/admin/workspaces`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        setWorkspaces(data)

        // If no workspace is selected, select the first one
        // Use functional update to get latest state
        setCurrentWorkspace(prev => {
          if (!prev && data.length > 0) {
            return data[0]
          }
          // If current workspace is no longer available, select first one
          if (prev && !data.find(w => w.id === prev.id)) {
            return data.length > 0 ? data[0] : null
          }
          return prev
        })
      } else {
        console.error('Failed to fetch workspaces')
      }
    } catch (error) {
      console.error('Error fetching workspaces:', error)
    } finally {
      setLoading(false)
    }
  }

  const selectWorkspace = (workspace) => {
    setCurrentWorkspace(workspace)
    // Clear connection when workspace changes
    setCurrentConnection(null)
    localStorage.removeItem('currentConnection')
  }

  const selectConnection = (connection) => {
    setCurrentConnection(connection)
  }

  const refreshWorkspaces = () => {
    return fetchWorkspaces()
  }

  return (
    <WorkspaceContext.Provider
      value={{
        currentWorkspace,
        currentConnection,
        workspaces,
        loading,
        selectWorkspace,
        selectConnection,
        refreshWorkspaces,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  )
}

export function useWorkspace() {
  const context = useContext(WorkspaceContext)
  if (!context) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider')
  }
  return context
}
