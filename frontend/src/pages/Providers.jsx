import { useState, useEffect } from 'react'
import {
  Database,
  Plus,
  Search,
  Network,
  X,
  ArrowRight,
  CheckCircle,
  XCircle,
} from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'

const PROVIDER_TYPES = [
  { id: 'postgresql', name: 'PostgreSQL', icon: '🐘' },
  { id: 'mysql', name: 'MySQL', icon: '🐬' },
  { id: 'mongodb', name: 'MongoDB', icon: '🍃' },
  { id: 'sqlserver', name: 'SQL Server', icon: '📊' },
  { id: 'oracle', name: 'Oracle', icon: '🔮' },
  { id: 'splunk', name: 'Splunk', icon: '📈' },
]

function Providers() {
  const [searchParams] = useSearchParams()
  const workspaceId = searchParams.get('workspace')

  const [providers, setProviders] = useState([])
  const [workspaces, setWorkspaces] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedWorkspace, setSelectedWorkspace] = useState(workspaceId || '')
  const [formData, setFormData] = useState({
    name: '',
    type: 'postgresql',
    workspace_id: workspaceId || '',
    description: '',
  })
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    fetchProviders()
    fetchWorkspaces()
  }, [selectedWorkspace])

  const fetchProviders = async () => {
    try {
      setLoading(true)
      const apiUrl = ''

      const params = new URLSearchParams()
      if (selectedWorkspace) {
        params.append('workspace_id', selectedWorkspace)
      }

      const response = await fetch(
        `${apiUrl}/api/v1/admin/providers${params.toString() ? '?' + params : ''}`
      )
      if (response.ok) {
        const data = await response.json()
        setProviders(data)
      }
    } catch (err) {
      console.error('Error fetching providers:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchWorkspaces = async () => {
    try {
      const apiUrl = ''
      const token = localStorage.getItem('access_token')

      const response = await fetch(`${apiUrl}/api/v1/admin/workspaces`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setWorkspaces(data)
      }
    } catch (err) {
      console.error('Error fetching workspaces:', err)
    }
  }

  const handleCreateProvider = async (e) => {
    e.preventDefault()

    if (!formData.name.trim() || !formData.workspace_id) {
      alert('Please fill in all required fields')
      return
    }

    try {
      setSubmitting(true)
      const apiUrl = ''
      const token = localStorage.getItem('access_token')

      const response = await fetch(`${apiUrl}/api/v1/workspaces/${formData.workspace_id}/providers`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: formData.name,
          type: formData.type,
          description: formData.description || null,
          settings: {},
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail?.message || error.detail || 'Failed to create provider')
      }

      await fetchProviders()
      setShowModal(false)
      setFormData({
        name: '',
        type: 'postgresql',
        workspace_id: workspaceId || '',
        description: '',
      })
    } catch (err) {
      console.error('Error creating provider:', err)
      alert(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const filteredProviders = providers.filter(
    (provider) =>
      provider.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      provider.provider_type.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const getProviderIcon = (type) => {
    const provider = PROVIDER_TYPES.find((p) => p.id === type)
    return provider?.icon || '🗄️'
  }

  const getProviderTypeName = (type) => {
    const provider = PROVIDER_TYPES.find((p) => p.id === type)
    return provider?.name || type
  }

  return (
    <div className="flex min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                Database Providers
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                Manage database provider configurations
              </p>
            </div>
            <button
              onClick={() => setShowModal(true)}
              className="flex items-center space-x-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white font-semibold rounded-lg shadow-lg hover:shadow-xl transition-all"
            >
              <Plus className="w-5 h-5" />
              <span>Create Provider</span>
            </button>
          </div>

          {/* Filters */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search providers..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>

            <select
              value={selectedWorkspace}
              onChange={(e) => setSelectedWorkspace(e.target.value)}
              className="px-4 py-3 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">All Workspaces</option>
              {workspaces.map((workspace) => (
                <option key={workspace.id} value={workspace.id}>
                  {workspace.name}
                </option>
              ))}
            </select>
          </div>

          {/* Providers List */}
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div
                  key={i}
                  className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 animate-pulse"
                >
                  <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-4"></div>
                  <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full mb-2"></div>
                  <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-2/3"></div>
                </div>
              ))}
            </div>
          ) : filteredProviders.length === 0 ? (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-12 text-center">
              <Database className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600 dark:text-gray-400 font-semibold mb-2">
                {searchQuery ? 'No providers found' : 'No providers yet'}
              </p>
              <p className="text-gray-500 dark:text-gray-500 text-sm mb-6">
                {searchQuery
                  ? 'Try adjusting your search query'
                  : 'Create your first provider to get started'}
              </p>
              {!searchQuery && (
                <button
                  onClick={() => setShowModal(true)}
                  className="inline-flex items-center space-x-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white font-semibold rounded-lg transition-colors"
                >
                  <Plus className="w-4 h-4" />
                  <span>Create Provider</span>
                </button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredProviders.map((provider) => (
                <Link
                  key={provider.id}
                  to={`/app/admin/connections?provider=${provider.id}`}
                  className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:border-primary-300 dark:hover:border-primary-700 hover:shadow-md transition-all group"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center space-x-3">
                      <div className="text-3xl">{getProviderIcon(provider.provider_type)}</div>
                      <div>
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                          {provider.name}
                        </h3>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          {getProviderTypeName(provider.provider_type)}
                        </p>
                      </div>
                    </div>
                  </div>

                  {provider.description && (
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-4 line-clamp-2">
                      {provider.description}
                    </p>
                  )}

                  <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
                    <div className="flex items-center space-x-4 text-sm">
                      <div className="flex items-center space-x-1 text-gray-600 dark:text-gray-400">
                        <Network className="w-4 h-4" />
                        <span>{provider.connection_count || 0}</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        {provider.has_active_connections ? (
                          <>
                            <CheckCircle className="w-4 h-4 text-green-500" />
                            <span className="text-green-600 dark:text-green-400 text-xs">
                              Active
                            </span>
                          </>
                        ) : (
                          <>
                            <XCircle className="w-4 h-4 text-gray-400" />
                            <span className="text-gray-500 dark:text-gray-400 text-xs">
                              Inactive
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                    <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors" />
                  </div>

                  {provider.workspace_name && (
                    <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Workspace: {provider.workspace_name}
                      </p>
                    </div>
                  )}
                </Link>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Create Provider Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
            <div
              className="fixed inset-0 transition-opacity bg-gray-500 dark:bg-gray-900 bg-opacity-75 dark:bg-opacity-75"
              onClick={() => setShowModal(false)}
            ></div>

            <div className="inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <form onSubmit={handleCreateProvider}>
                <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                      Create New Provider
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

                <div className="px-6 py-4 space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Workspace *
                    </label>
                    <select
                      name="workspace_id"
                      value={formData.workspace_id}
                      onChange={(e) =>
                        setFormData({ ...formData, workspace_id: e.target.value })
                      }
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                      required
                    >
                      <option value="">Select a workspace</option>
                      {workspaces.map((workspace) => (
                        <option key={workspace.id} value={workspace.id}>
                          {workspace.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Provider Type *
                    </label>
                    <select
                      name="type"
                      value={formData.type}
                      onChange={(e) =>
                        setFormData({ ...formData, type: e.target.value })
                      }
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                      required
                    >
                      {PROVIDER_TYPES.map((type) => (
                        <option key={type.id} value={type.id}>
                          {type.icon} {type.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Provider Name *
                    </label>
                    <input
                      type="text"
                      name="name"
                      value={formData.name}
                      onChange={(e) =>
                        setFormData({ ...formData, name: e.target.value })
                      }
                      placeholder="e.g., Production DB, Analytics DB"
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Description
                    </label>
                    <textarea
                      name="description"
                      value={formData.description}
                      onChange={(e) =>
                        setFormData({ ...formData, description: e.target.value })
                      }
                      placeholder="Optional description"
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
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
                    {submitting ? 'Creating...' : 'Create Provider'}
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

export default Providers
