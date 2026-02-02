import { useState, useEffect } from 'react'
import {
  ArrowLeft,
  Database,
  Plus,
  Trash2,
  Settings,
  Link as LinkIcon,
  AlertCircle,
  Check,
  X,
  RefreshCw,
  TestTube,
} from 'lucide-react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import AdminSidebar from '../components/AdminSidebar'

function ProviderDetail() {
  const { workspaceId, providerId } = useParams()
  const navigate = useNavigate()
  const [provider, setProvider] = useState(null)
  const [connections, setConnections] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAddConnectionModal, setShowAddConnectionModal] = useState(false)
  const [addingConnection, setAddingConnection] = useState(false)
  const [testingConnection, setTestingConnection] = useState(null)
  const [toast, setToast] = useState(null)
  const [connectionFormData, setConnectionFormData] = useState({
    name: '',
    host: '',
    port: '',
    database: '',
    username: '',
    password: '',
  })

  const showToast = (type, message) => {
    setToast({ type, message })
    setTimeout(() => setToast(null), 4000)
  }

  useEffect(() => {
    if (workspaceId && providerId) {
      fetchProvider()
      fetchConnections()
    }
  }, [workspaceId, providerId])

  const fetchProvider = async () => {
    try {
      const apiUrl = ''
      const token = localStorage.getItem('access_token')

      const response = await fetch(
        `${apiUrl}/api/v1/workspaces/${workspaceId}/providers/${providerId}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      )
      if (response.ok) {
        const data = await response.json()
        setProvider(data)
      } else {
        showToast('error', 'Failed to load provider')
        navigate(`/admin/workspaces/${workspaceId}`)
      }
    } catch (err) {
      console.error('Error fetching provider:', err)
      showToast('error', 'Failed to load provider')
    } finally {
      setLoading(false)
    }
  }

  const fetchConnections = async () => {
    try {
      const apiUrl = ''
      const token = localStorage.getItem('access_token')

      const response = await fetch(
        `${apiUrl}/api/v1/workspaces/${workspaceId}/providers/${providerId}/connections`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      )
      if (response.ok) {
        const data = await response.json()
        setConnections(data)
      }
    } catch (err) {
      console.error('Error fetching connections:', err)
    }
  }

  const getDefaultPort = (type) => {
    const ports = {
      postgresql: '5432',
      mysql: '3306',
      mongodb: '27017',
      athena: '',
      bigquery: '',
      snowflake: '',
      splunk: '8089',
    }
    return ports[type] || ''
  }

  const handleAddConnection = async (e) => {
    e.preventDefault()

    try {
      setAddingConnection(true)
      const apiUrl = ''
      const token = localStorage.getItem('access_token')

      const response = await fetch(
        `${apiUrl}/api/v1/workspaces/${workspaceId}/providers/${providerId}/connections`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({
            name: connectionFormData.name,
            connection_string: buildConnectionString(),
            settings: {
              host: connectionFormData.host,
              port: connectionFormData.port,
              database: connectionFormData.database,
              username: connectionFormData.username,
            },
          }),
        }
      )

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail?.message || error.detail || 'Failed to add connection')
      }

      await fetchConnections()
      setShowAddConnectionModal(false)
      setConnectionFormData({
        name: '',
        host: '',
        port: '',
        database: '',
        username: '',
        password: '',
      })
      showToast('success', 'Connection added successfully')
    } catch (err) {
      console.error('Error adding connection:', err)
      showToast('error', err.message)
    } finally {
      setAddingConnection(false)
    }
  }

  const buildConnectionString = () => {
    const { host, port, database, username, password } = connectionFormData
    if (provider?.type === 'postgresql') {
      return `postgresql://${username}:${password}@${host}:${port}/${database}`
    } else if (provider?.type === 'mysql') {
      return `mysql://${username}:${password}@${host}:${port}/${database}`
    }
    return `${host}:${port}/${database}`
  }

  const handleTestConnection = async (connectionId) => {
    try {
      setTestingConnection(connectionId)
      const apiUrl = ''
      const token = localStorage.getItem('access_token')

      const response = await fetch(
        `${apiUrl}/api/v1/workspaces/${workspaceId}/providers/${providerId}/connections/${connectionId}/test`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      )

      const result = await response.json()
      if (response.ok && result.success) {
        showToast('success', 'Connection successful!')
      } else {
        showToast('error', result.error || 'Connection failed')
      }
    } catch (err) {
      console.error('Error testing connection:', err)
      showToast('error', 'Failed to test connection')
    } finally {
      setTestingConnection(null)
    }
  }

  const handleDeleteConnection = async (connectionId, connectionName) => {
    if (!confirm(`Are you sure you want to delete "${connectionName}"?`)) {
      return
    }

    try {
      const apiUrl = ''
      const token = localStorage.getItem('access_token')

      const response = await fetch(
        `${apiUrl}/api/v1/workspaces/${workspaceId}/providers/${providerId}/connections/${connectionId}`,
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      )

      if (!response.ok) {
        throw new Error('Failed to delete connection')
      }

      await fetchConnections()
      showToast('success', 'Connection deleted')
    } catch (err) {
      console.error('Error deleting connection:', err)
      showToast('error', err.message)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
        <AdminSidebar />
        <main className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full mx-auto mb-4"></div>
            <p className="text-gray-600 dark:text-gray-400">Loading provider...</p>
          </div>
        </main>
      </div>
    )
  }

  if (!provider) {
    return (
      <div className="flex min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
        <AdminSidebar />
        <main className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <p className="text-gray-600 dark:text-gray-400">Provider not found</p>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      <AdminSidebar />

      <main className="flex-1 p-8">
        {/* Header */}
        <div className="mb-8">
          <Link
            to={`/admin/workspaces/${workspaceId}`}
            className="inline-flex items-center text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white mb-4"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Workspace
          </Link>

          <div className="flex items-center space-x-4">
            <div className="bg-primary-100 dark:bg-primary-900/30 p-3 rounded-lg">
              <Database className="w-8 h-8 text-primary-600 dark:text-primary-400" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                {provider.name}
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                {provider.type} • {provider.description || 'No description'}
              </p>
            </div>
          </div>
        </div>

        {/* Connections Section */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <LinkIcon className="w-5 h-5 text-gray-400" />
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Connections
              </h2>
            </div>
            <button
              onClick={() => {
                setConnectionFormData({
                  ...connectionFormData,
                  port: getDefaultPort(provider.type),
                })
                setShowAddConnectionModal(true)
              }}
              className="inline-flex items-center space-x-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>Add Connection</span>
            </button>
          </div>

          <div className="p-6">
            {connections.length > 0 ? (
              <div className="space-y-3">
                {connections.map((conn) => (
                  <div
                    key={conn.id}
                    className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg"
                  >
                    <div className="flex items-center space-x-3">
                      <div className={`w-3 h-3 rounded-full ${
                        conn.is_active ? 'bg-green-500' : 'bg-gray-400'
                      }`} />
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white">
                          {conn.name}
                        </p>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          {conn.settings?.host}:{conn.settings?.port}/{conn.settings?.database}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleTestConnection(conn.id)}
                        disabled={testingConnection === conn.id}
                        className="p-2 text-blue-500 hover:bg-blue-100 dark:hover:bg-blue-900/30 rounded transition-colors disabled:opacity-50"
                        title="Test connection"
                      >
                        {testingConnection === conn.id ? (
                          <RefreshCw className="w-4 h-4 animate-spin" />
                        ) : (
                          <TestTube className="w-4 h-4" />
                        )}
                      </button>
                      <button
                        onClick={() => handleDeleteConnection(conn.id, conn.name)}
                        className="p-2 text-red-500 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-colors"
                        title="Delete connection"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <LinkIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600 dark:text-gray-400 mb-4">
                  No connections configured
                </p>
                <button
                  onClick={() => {
                    setConnectionFormData({
                      ...connectionFormData,
                      port: getDefaultPort(provider.type),
                    })
                    setShowAddConnectionModal(true)
                  }}
                  className="inline-flex items-center space-x-2 text-primary-600 dark:text-primary-400 hover:underline"
                >
                  <Plus className="w-4 h-4" />
                  <span>Add First Connection</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Add Connection Modal */}
      {showAddConnectionModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
            <div
              className="fixed inset-0 transition-opacity bg-gray-500 dark:bg-gray-900 bg-opacity-75 dark:bg-opacity-75"
              onClick={() => setShowAddConnectionModal(false)}
            ></div>

            <div className="inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <form onSubmit={handleAddConnection}>
                <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                      Add Connection
                    </h3>
                    <button
                      type="button"
                      onClick={() => setShowAddConnectionModal(false)}
                      className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                    >
                      <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
                    </button>
                  </div>
                </div>
                <div className="px-6 py-4 space-y-4 max-h-96 overflow-y-auto">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Connection Name *
                    </label>
                    <input
                      type="text"
                      value={connectionFormData.name}
                      onChange={(e) => setConnectionFormData({ ...connectionFormData, name: e.target.value })}
                      placeholder="e.g., Production DB"
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                      required
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Host *
                      </label>
                      <input
                        type="text"
                        value={connectionFormData.host}
                        onChange={(e) => setConnectionFormData({ ...connectionFormData, host: e.target.value })}
                        placeholder="localhost"
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Port *
                      </label>
                      <input
                        type="text"
                        value={connectionFormData.port}
                        onChange={(e) => setConnectionFormData({ ...connectionFormData, port: e.target.value })}
                        placeholder={getDefaultPort(provider?.type)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                        required
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Database *
                    </label>
                    <input
                      type="text"
                      value={connectionFormData.database}
                      onChange={(e) => setConnectionFormData({ ...connectionFormData, database: e.target.value })}
                      placeholder="mydb"
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                      required
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Username *
                      </label>
                      <input
                        type="text"
                        value={connectionFormData.username}
                        onChange={(e) => setConnectionFormData({ ...connectionFormData, username: e.target.value })}
                        placeholder="postgres"
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Password *
                      </label>
                      <input
                        type="password"
                        value={connectionFormData.password}
                        onChange={(e) => setConnectionFormData({ ...connectionFormData, password: e.target.value })}
                        placeholder="••••••••"
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                        required
                      />
                    </div>
                  </div>
                </div>
                <div className="px-6 py-4 bg-gray-50 dark:bg-gray-700/50 border-t border-gray-200 dark:border-gray-700 flex items-center justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => setShowAddConnectionModal(false)}
                    disabled={addingConnection}
                    className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={addingConnection}
                    className="px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors disabled:opacity-50"
                  >
                    {addingConnection ? 'Adding...' : 'Add Connection'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Toast Notification */}
      {toast && (
        <div className={`fixed bottom-4 right-4 z-50 flex items-center space-x-3 px-4 py-3 rounded-lg shadow-lg transition-all ${
          toast.type === 'success' 
            ? 'bg-green-500 text-white' 
            : 'bg-red-500 text-white'
        }`}>
          {toast.type === 'success' ? (
            <Check className="w-5 h-5" />
          ) : (
            <AlertCircle className="w-5 h-5" />
          )}
          <span>{toast.message}</span>
          <button 
            onClick={() => setToast(null)}
            className="ml-2 hover:opacity-80"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  )
}

export default ProviderDetail
