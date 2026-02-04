import { useState, useEffect } from 'react'
import {
  Network,
  Plus,
  Search,
  Server,
  X,
  Eye,
  EyeOff,
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertCircle,
  Zap,
} from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import Breadcrumb from '../components/Breadcrumb'
import * as ROUTES from '../constants/routes'

function Connections() {
  const [searchParams] = useSearchParams()
  const providerId = searchParams.get('provider')

  const [connections, setConnections] = useState([])
  const [providers, setProviders] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedProvider, setSelectedProvider] = useState(providerId || '')
  const [showPassword, setShowPassword] = useState(false)
  const [formData, setFormData] = useState({
    provider_id: providerId || '',
    name: '',
    host: '',
    port: '',
    database: '',
    username: '',
    password: '',
    ssl_enabled: false,
  })
  const [submitting, setSubmitting] = useState(false)
  const [testing, setTesting] = useState({})
  const [refreshing, setRefreshing] = useState({})

  useEffect(() => {
    fetchConnections()
    fetchProviders()
  }, [selectedProvider])

  const fetchConnections = async () => {
    try {
      setLoading(true)
      const apiUrl = ''

      const params = new URLSearchParams()
      if (selectedProvider) {
        params.append('provider_id', selectedProvider)
      }

      const response = await fetch(
        `${apiUrl}/api/v1/admin/connections${params.toString() ? '?' + params : ''}`
      )
      if (response.ok) {
        const data = await response.json()
        setConnections(data)
      }
    } catch (err) {
      console.error('Error fetching connections:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchProviders = async () => {
    try {
      const apiUrl = ''
      const token = localStorage.getItem('access_token')

      const response = await fetch(`${apiUrl}/api/v1/admin/providers`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setProviders(data)
      }
    } catch (err) {
      console.error('Error fetching providers:', err)
    }
  }

  const handleCreateConnection = async (e) => {
    e.preventDefault()

    if (!formData.provider_id || !formData.name || !formData.host || !formData.port) {
      alert('Please fill in all required fields')
      return
    }

    try {
      setSubmitting(true)
      const apiUrl = ''
      const token = localStorage.getItem('access_token')

      // Find the provider to get its workspace_id
      const provider = providers.find(p => p.id === formData.provider_id)
      if (!provider || !provider.workspace_id) {
        throw new Error('Provider not found or workspace_id missing')
      }

      const response = await fetch(`${apiUrl}/api/v1/workspaces/${provider.workspace_id}/providers/${formData.provider_id}/connections`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: formData.name,
          host: formData.host,
          port: parseInt(formData.port),
          database: formData.database || '',
          schema_name: null,
          credentials: formData.username || formData.password ? {
            username: formData.username,
            password: formData.password,
          } : null,
          connection_options: {
            ssl: formData.ssl_enabled,
          },
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail?.message || error.detail || 'Failed to create connection')
      }

      await fetchConnections()
      setShowModal(false)
      setFormData({
        provider_id: providerId || '',
        name: '',
        host: '',
        port: '',
        database: '',
        username: '',
        password: '',
        ssl_enabled: false,
      })
    } catch (err) {
      console.error('Error creating connection:', err)
      alert(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleTestConnection = async (connectionId) => {
    try {
      setTesting({ ...testing, [connectionId]: true })
      const apiUrl = ''

      // Find the connection to get its provider_id
      const connection = connections.find(c => c.id === connectionId)
      if (!connection || !connection.provider_id) {
        throw new Error('Connection or provider not found')
      }

      // Find the provider to get its workspace_id
      const provider = providers.find(p => p.id === connection.provider_id)
      if (!provider || !provider.workspace_id) {
        throw new Error('Provider workspace not found')
      }

      const response = await fetch(
        `${apiUrl}/api/v1/workspaces/${provider.workspace_id}/providers/${connection.provider_id}/connections/${connectionId}/test`,
        {
          method: 'POST',
        }
      )

      const result = await response.json()

      if (response.ok && result.success) {
        alert(`Connection test successful! ${result.message || ''}`)
        await fetchConnections()
      } else {
        alert(`Connection test failed: ${result.message || 'Unknown error'}`)
      }
    } catch (err) {
      console.error('Error testing connection:', err)
      alert(`Failed to test connection: ${err.message}`)
    } finally {
      setTesting({ ...testing, [connectionId]: false })
    }
  }

  const handleRefreshSchema = async (connectionId) => {
    try {
      setRefreshing({ ...refreshing, [connectionId]: true })
      const apiUrl = ''

      // Find the connection to get its provider_id
      const connection = connections.find(c => c.id === connectionId)
      if (!connection || !connection.provider_id) {
        throw new Error('Connection or provider not found')
      }

      // Find the provider to get its workspace_id
      const provider = providers.find(p => p.id === connection.provider_id)
      if (!provider || !provider.workspace_id) {
        throw new Error('Provider workspace not found')
      }

      const response = await fetch(
        `${apiUrl}/api/v1/workspaces/${provider.workspace_id}/providers/${connection.provider_id}/connections/${connectionId}/schema/refresh`,
        {
          method: 'POST',
        }
      )

      const result = await response.json()

      if (response.ok && result.status === 'success') {
        alert(`Schema refreshed successfully! ${result.message || ''}`)
        await fetchConnections()
      } else {
        alert(`Schema refresh failed: ${result.message || 'Unknown error'}`)
      }
    } catch (err) {
      console.error('Error refreshing schema:', err)
      alert(`Failed to refresh schema: ${err.message}`)
    } finally {
      setRefreshing({ ...refreshing, [connectionId]: false })
    }
  }

  const filteredConnections = connections.filter(
    (connection) =>
      connection.host.toLowerCase().includes(searchQuery.toLowerCase()) ||
      connection.database?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      connection.name?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const getStatusColor = (status) => {
    switch (status) {
      case 'connected':
        return 'text-green-600 dark:text-green-400'
      case 'error':
        return 'text-red-600 dark:text-red-400'
      case 'pending':
        return 'text-yellow-600 dark:text-yellow-400'
      default:
        return 'text-gray-600 dark:text-gray-400'
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'connected':
        return CheckCircle
      case 'error':
        return XCircle
      case 'pending':
        return AlertCircle
      default:
        return AlertCircle
    }
  }

  const breadcrumbItems = [
    { label: 'Admin', path: ROUTES.ADMIN },
    { label: 'Connections', path: ROUTES.ADMIN_CONNECTIONS },
  ]

  return (
    <div className="flex min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Breadcrumb */}
          <Breadcrumb items={breadcrumbItems} />

          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                Database Connections
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                Manage database connection configurations
              </p>
            </div>
            <button
              onClick={() => setShowModal(true)}
              className="flex items-center space-x-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white font-semibold rounded-lg shadow-lg hover:shadow-xl transition-all"
            >
              <Plus className="w-5 h-5" />
              <span>Add Connection</span>
            </button>
          </div>

          {/* Filters */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search connections..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <select
              value={selectedProvider}
              onChange={(e) => setSelectedProvider(e.target.value)}
              className="px-4 py-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">All Providers</option>
              {providers.map((provider) => (
                <option key={provider.id} value={provider.id}>
                  {provider.name} ({provider.provider_type})
                </option>
              ))}
            </select>
          </div>

          {/* Connections List */}
          {loading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 animate-pulse"
                >
                  <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/4 mb-4"></div>
                  <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full mb-2"></div>
                  <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
                </div>
              ))}
            </div>
          ) : filteredConnections.length === 0 ? (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-12 text-center">
              <Network className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600 dark:text-gray-400 font-semibold mb-2">
                {searchQuery ? 'No connections found' : 'No connections yet'}
              </p>
              <p className="text-gray-500 dark:text-gray-500 text-sm mb-6">
                {searchQuery
                  ? 'Try adjusting your search query'
                  : 'Add your first database connection to get started'}
              </p>
              {!searchQuery && (
                <button
                  onClick={() => setShowModal(true)}
                  className="inline-flex items-center space-x-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white font-semibold rounded-lg transition-colors"
                >
                  <Plus className="w-4 h-4" />
                  <span>Add Connection</span>
                </button>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              {filteredConnections.map((connection) => {
                const StatusIcon = getStatusIcon(connection.status)

                return (
                  <div
                    key={connection.id}
                    className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-3">
                          <div className="bg-primary-100 dark:bg-primary-900/30 p-2 rounded">
                            <Server className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                          </div>
                          <div>
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                              {connection.name || `${connection.host}:${connection.port}`}
                            </h3>
                            <p className="text-sm text-gray-600 dark:text-gray-400">
                              {connection.host}:{connection.port}
                              {connection.database && ` / ${connection.database}`}
                            </p>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                          <div>
                            <p className="text-gray-500 dark:text-gray-400 mb-1">
                              Provider
                            </p>
                            <p className="text-gray-900 dark:text-white font-medium">
                              {connection.provider_name}
                            </p>
                          </div>
                          <div>
                            <p className="text-gray-500 dark:text-gray-400 mb-1">
                              Username
                            </p>
                            <p className="text-gray-900 dark:text-white font-medium">
                              {connection.username || 'N/A'}
                            </p>
                          </div>
                          <div>
                            <p className="text-gray-500 dark:text-gray-400 mb-1">SSL</p>
                            <p className="text-gray-900 dark:text-white font-medium">
                              {connection.ssl_enabled ? 'Enabled' : 'Disabled'}
                            </p>
                          </div>
                          <div>
                            <p className="text-gray-500 dark:text-gray-400 mb-1">
                              Status
                            </p>
                            <div className="flex items-center space-x-1">
                              <StatusIcon
                                className={`w-4 h-4 ${getStatusColor(connection.status)}`}
                              />
                              <span
                                className={`font-medium capitalize ${getStatusColor(
                                  connection.status
                                )}`}
                              >
                                {connection.status || 'unknown'}
                              </span>
                            </div>
                          </div>
                        </div>

                        {connection.last_error && (
                          <div className="mt-3 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                            <p className="text-sm text-red-800 dark:text-red-400">
                              <span className="font-medium">Error:</span>{' '}
                              {connection.last_error}
                            </p>
                          </div>
                        )}
                      </div>

                      <div className="flex flex-col space-y-2 ml-4">
                        <button
                          onClick={() => handleTestConnection(connection.id)}
                          disabled={testing[connection.id]}
                          className="flex items-center space-x-2 px-3 py-1.5 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          title="Test connection"
                        >
                          <Zap className="w-4 h-4" />
                          <span>{testing[connection.id] ? 'Testing...' : 'Test'}</span>
                        </button>
                        <button
                          onClick={() => handleRefreshSchema(connection.id)}
                          disabled={refreshing[connection.id]}
                          className="flex items-center space-x-2 px-3 py-1.5 text-sm bg-purple-500 hover:bg-purple-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                          title="Refresh schema"
                        >
                          <RefreshCw
                            className={`w-4 h-4 ${
                              refreshing[connection.id] ? 'animate-spin' : ''
                            }`}
                          />
                          <span>
                            {refreshing[connection.id] ? 'Refreshing...' : 'Refresh'}
                          </span>
                        </button>
                      </div>
                    </div>

                    {connection.schema_last_updated && (
                      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          Schema last updated:{' '}
                          {new Date(connection.schema_last_updated).toLocaleString()}
                        </p>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </main>

      {/* Add Connection Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
            <div
              className="fixed inset-0 transition-opacity bg-gray-500 dark:bg-gray-900 bg-opacity-75 dark:bg-opacity-75"
              onClick={() => setShowModal(false)}
            ></div>

            <div className="inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-2xl sm:w-full">
              <form onSubmit={handleCreateConnection}>
                <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                      Add Database Connection
                    </h3>
                    <button
                      type="button"
                      onClick={() => setShowModal(false)}
                      className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                    >
                      <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
                    </button>
                  </div>
                </div>

                <div className="px-6 py-4 max-h-[60vh] overflow-y-auto space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Provider *
                    </label>
                    <select
                      name="provider_id"
                      value={formData.provider_id}
                      onChange={(e) =>
                        setFormData({ ...formData, provider_id: e.target.value })
                      }
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                      required
                    >
                      <option value="">Select a provider</option>
                      {providers.map((provider) => (
                        <option key={provider.id} value={provider.id}>
                          {provider.name} ({provider.provider_type || provider.type})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Connection Name *
                    </label>
                    <input
                      type="text"
                      name="name"
                      value={formData.name}
                      onChange={(e) =>
                        setFormData({ ...formData, name: e.target.value })
                      }
                      placeholder="e.g., Production, Staging, Development"
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
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
                        name="host"
                        value={formData.host}
                        onChange={(e) =>
                          setFormData({ ...formData, host: e.target.value })
                        }
                        placeholder="localhost or IP address"
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Port *
                      </label>
                      <input
                        type="number"
                        name="port"
                        value={formData.port}
                        onChange={(e) =>
                          setFormData({ ...formData, port: e.target.value })
                        }
                        placeholder="5432"
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                        required
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Database Name
                    </label>
                    <input
                      type="text"
                      name="database"
                      value={formData.database}
                      onChange={(e) =>
                        setFormData({ ...formData, database: e.target.value })
                      }
                      placeholder="mydatabase"
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Username
                    </label>
                    <input
                      type="text"
                      name="username"
                      value={formData.username}
                      onChange={(e) =>
                        setFormData({ ...formData, username: e.target.value })
                      }
                      placeholder="dbuser"
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Password
                    </label>
                    <div className="relative">
                      <input
                        type={showPassword ? 'text' : 'password'}
                        name="password"
                        value={formData.password}
                        onChange={(e) =>
                          setFormData({ ...formData, password: e.target.value })
                        }
                        placeholder="••••••••"
                        className="w-full px-3 py-2 pr-10 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                      >
                        {showPassword ? (
                          <EyeOff className="w-5 h-5" />
                        ) : (
                          <Eye className="w-5 h-5" />
                        )}
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center space-x-3">
                    <button
                      type="button"
                      onClick={() =>
                        setFormData({ ...formData, ssl_enabled: !formData.ssl_enabled })
                      }
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        formData.ssl_enabled
                          ? 'bg-primary-500'
                          : 'bg-gray-300 dark:bg-gray-600'
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          formData.ssl_enabled ? 'translate-x-6' : 'translate-x-1'
                        }`}
                      />
                    </button>
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Enable SSL
                    </label>
                  </div>
                </div>

                <div className="px-6 py-4 bg-gray-50 dark:bg-gray-700/50 border-t border-gray-200 dark:border-gray-700 flex items-center justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    disabled={submitting}
                    className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {submitting ? 'Adding...' : 'Add Connection'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Connections
