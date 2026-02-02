import { useState, useEffect } from 'react'
import {
  ArrowLeft,
  Save,
  Users,
  Database,
  Plus,
  UserPlus,
  Trash2,
  Mail,
  Shield,
  AlertCircle,
  X,
} from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import AdminSidebar from '../components/AdminSidebar'

function WorkspaceDetail() {
  const { workspaceId } = useParams()
  const [workspace, setWorkspace] = useState(null)
  const [providers, setProviders] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [showAddProviderModal, setShowAddProviderModal] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviting, setInviting] = useState(false)
  const [addingProvider, setAddingProvider] = useState(false)
  const [providerFormData, setProviderFormData] = useState({
    name: '',
    type: '',
    description: '',
  })
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    is_active: true,
  })

  useEffect(() => {
    if (workspaceId) {
      fetchWorkspace()
      fetchProviders()
    }
  }, [workspaceId])

  const fetchProviders = async () => {
    try {
      const apiUrl = ''
      const token = localStorage.getItem('access_token')

      const response = await fetch(`${apiUrl}/api/v1/workspaces/${workspaceId}/providers`, {
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

  const fetchWorkspace = async () => {
    try {
      setLoading(true)
      const apiUrl = ''
      const token = localStorage.getItem('access_token')

      const response = await fetch(`${apiUrl}/api/v1/admin/workspaces/${workspaceId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setWorkspace(data)
        setFormData({
          name: data.name,
          description: data.description || '',
          is_active: data.is_active,
        })
      }
    } catch (err) {
      console.error('Error fetching workspace:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSaveChanges = async (e) => {
    e.preventDefault()

    try {
      setSaving(true)
      const apiUrl = ''
      const token = localStorage.getItem('access_token')

      const response = await fetch(`${apiUrl}/api/v1/admin/workspaces/${workspaceId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(formData),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to update workspace')
      }

      await fetchWorkspace()
      alert('Workspace updated successfully')
    } catch (err) {
      console.error('Error updating workspace:', err)
      alert(err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleInviteAdmin = async (e) => {
    e.preventDefault()

    if (!inviteEmail.trim()) {
      alert('Please enter an email address')
      return
    }

    try {
      setInviting(true)
      const apiUrl = ''
      const token = localStorage.getItem('access_token')

      const response = await fetch(
        `${apiUrl}/api/v1/admin/workspaces/${workspaceId}/admins`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({ email: inviteEmail }),
        }
      )

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to invite admin')
      }

      await fetchWorkspace()
      setShowInviteModal(false)
      setInviteEmail('')
      alert('Admin invited successfully')
    } catch (err) {
      console.error('Error inviting admin:', err)
      alert(err.message)
    } finally {
      setInviting(false)
    }
  }

  const handleRemoveAdmin = async (adminId) => {
    if (!confirm('Are you sure you want to remove this admin?')) {
      return
    }

    try {
      const apiUrl = ''
      const token = localStorage.getItem('access_token')

      const response = await fetch(
        `${apiUrl}/api/v1/admin/workspaces/${workspaceId}/admins/${adminId}`,
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      )

      if (!response.ok) {
        throw new Error('Failed to remove admin')
      }

      await fetchWorkspace()
    } catch (err) {
      console.error('Error removing admin:', err)
      alert('Failed to remove admin')
    }
  }

  const handleAddProvider = async (e) => {
    e.preventDefault()
    
    try {
      setAddingProvider(true)
      const apiUrl = ''
      const token = localStorage.getItem('access_token')

      const response = await fetch(
        `${apiUrl}/api/v1/workspaces/${workspaceId}/providers`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({
            name: providerFormData.name,
            type: providerFormData.type,
            description: providerFormData.description || null,
          }),
        }
      )

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail?.message || error.detail || 'Failed to add provider')
      }

      await fetchProviders()
      setShowAddProviderModal(false)
      setProviderFormData({ name: '', type: '', description: '' })
      alert('Provider added successfully')
    } catch (err) {
      console.error('Error adding provider:', err)
      alert(err.message)
    } finally {
      setAddingProvider(false)
    }
  }

  const handleDeleteProvider = async (providerId, providerName) => {
    if (!confirm(`Are you sure you want to delete "${providerName}"? This will also delete all connections.`)) {
      return
    }

    try {
      const apiUrl = ''
      const token = localStorage.getItem('access_token')

      const response = await fetch(
        `${apiUrl}/api/v1/workspaces/${workspaceId}/providers/${providerId}`,
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      )

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail?.message || error.detail || 'Failed to delete provider')
      }

      await fetchProviders()
    } catch (err) {
      console.error('Error deleting provider:', err)
      alert(err.message)
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
        <AdminSidebar />
        <main className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full mx-auto mb-4"></div>
            <p className="text-gray-600 dark:text-gray-400">Loading workspace...</p>
          </div>
        </main>
      </div>
    )
  }

  if (!workspace) {
    return (
      <div className="flex min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
        <AdminSidebar />
        <main className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
            <p className="text-gray-600 dark:text-gray-400">Workspace not found</p>
            <Link
              to="/admin/workspaces"
              className="mt-4 inline-flex items-center text-primary-600 dark:text-primary-400 hover:underline"
            >
              <ArrowLeft className="w-4 h-4 mr-1" />
              Back to Workspaces
            </Link>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      <AdminSidebar />

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header */}
          <div className="mb-8">
            <Link
              to="/admin/workspaces"
              className="inline-flex items-center text-primary-600 dark:text-primary-400 hover:underline mb-4"
            >
              <ArrowLeft className="w-4 h-4 mr-1" />
              Back to Workspaces
            </Link>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              {workspace.name}
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Manage workspace settings and members
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Settings */}
            <div className="lg:col-span-2">
              <form onSubmit={handleSaveChanges}>
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 mb-6">
                  <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                      Workspace Settings
                    </h2>
                  </div>
                  <div className="p-6 space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Workspace Name
                      </label>
                      <input
                        type="text"
                        value={formData.name}
                        onChange={(e) =>
                          setFormData({ ...formData, name: e.target.value })
                        }
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Description
                      </label>
                      <textarea
                        value={formData.description}
                        onChange={(e) =>
                          setFormData({ ...formData, description: e.target.value })
                        }
                        rows={3}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                      />
                    </div>

                    <div className="flex items-center space-x-3">
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                        Active Status
                      </label>
                      <button
                        type="button"
                        onClick={() =>
                          setFormData({ ...formData, is_active: !formData.is_active })
                        }
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                          formData.is_active
                            ? 'bg-primary-500'
                            : 'bg-gray-300 dark:bg-gray-600'
                        }`}
                      >
                        <span
                          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                            formData.is_active ? 'translate-x-6' : 'translate-x-1'
                          }`}
                        />
                      </button>
                      <span className="text-sm text-gray-600 dark:text-gray-400">
                        {formData.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                  </div>
                  <div className="px-6 py-4 bg-gray-50 dark:bg-gray-700/50 border-t border-gray-200 dark:border-gray-700 flex justify-end">
                    <button
                      type="submit"
                      disabled={saving}
                      className="flex items-center space-x-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Save className="w-4 h-4" />
                      <span>{saving ? 'Saving...' : 'Save Changes'}</span>
                    </button>
                  </div>
                </div>
              </form>

              {/* Providers */}
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
                <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Database className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                      DSL Providers
                    </h2>
                  </div>
                  <button
                    onClick={() => setShowAddProviderModal(true)}
                    className="flex items-center space-x-2 px-3 py-1.5 text-sm bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Add Provider</span>
                  </button>
                </div>
                <div className="p-6">
                  {providers.length > 0 ? (
                    <div className="space-y-3">
                      {providers.map((provider) => (
                        <div
                          key={provider.id}
                          className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg"
                        >
                          <Link
                            to={`/admin/workspaces/${workspaceId}/providers/${provider.id}`}
                            className="flex items-center space-x-3 flex-1 hover:opacity-80 transition-opacity"
                          >
                            <div className="bg-primary-100 dark:bg-primary-900/30 p-2 rounded">
                              <Database className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                            </div>
                            <div>
                              <p className="font-medium text-gray-900 dark:text-white">
                                {provider.name}
                              </p>
                              <p className="text-sm text-gray-600 dark:text-gray-400">
                                {provider.type}
                              </p>
                            </div>
                          </Link>
                          <div className="flex items-center space-x-3">
                            <span className="text-sm text-gray-500 dark:text-gray-400">
                              {provider.connection_count || 0} connections
                            </span>
                            <button
                              onClick={() => handleDeleteProvider(provider.id, provider.name)}
                              className="p-2 text-red-500 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-colors"
                              title="Delete provider"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <Database className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                      <p className="text-gray-600 dark:text-gray-400 mb-4">
                        No providers configured
                      </p>
                      <button
                        onClick={() => setShowAddProviderModal(true)}
                        className="inline-flex items-center space-x-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors"
                      >
                        <Plus className="w-4 h-4" />
                        <span>Add First Provider</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Admins Sidebar */}
            <div>
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
                <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Users className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                      Admins
                    </h2>
                  </div>
                  <button
                    onClick={() => setShowInviteModal(true)}
                    className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                    title="Invite admin"
                  >
                    <UserPlus className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                  </button>
                </div>
                <div className="p-4">
                  {workspace.admins && workspace.admins.length > 0 ? (
                    <div className="space-y-3">
                      {workspace.admins.map((admin) => (
                        <div
                          key={admin.id}
                          className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
                        >
                          <div className="flex items-center space-x-3">
                            <div className="bg-primary-100 dark:bg-primary-900/30 p-2 rounded-full">
                              <Shield className="w-4 h-4 text-primary-600 dark:text-primary-400" />
                            </div>
                            <div>
                              <p className="font-medium text-gray-900 dark:text-white text-sm">
                                {admin.name || admin.email}
                              </p>
                              <p className="text-xs text-gray-600 dark:text-gray-400">
                                {admin.email}
                              </p>
                            </div>
                          </div>
                          <button
                            onClick={() => handleRemoveAdmin(admin.id)}
                            className="p-1 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-colors"
                            title="Remove admin"
                          >
                            <Trash2 className="w-4 h-4 text-red-600 dark:text-red-400" />
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <Users className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        No admins yet
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Invite Admin Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
            <div
              className="fixed inset-0 transition-opacity bg-gray-500 dark:bg-gray-900 bg-opacity-75 dark:bg-opacity-75"
              onClick={() => setShowInviteModal(false)}
            ></div>

            <div className="inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <form onSubmit={handleInviteAdmin}>
                <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                      Invite Admin
                    </h3>
                    <button
                      type="button"
                      onClick={() => setShowInviteModal(false)}
                      className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                    >
                      <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
                    </button>
                  </div>
                </div>

                <div className="px-6 py-4">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Email Address
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                    <input
                      type="email"
                      value={inviteEmail}
                      onChange={(e) => setInviteEmail(e.target.value)}
                      placeholder="admin@example.com"
                      className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                      required
                    />
                  </div>
                </div>

                <div className="px-6 py-4 bg-gray-50 dark:bg-gray-700/50 border-t border-gray-200 dark:border-gray-700 flex items-center justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => setShowInviteModal(false)}
                    disabled={inviting}
                    className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={inviting}
                    className="px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {inviting ? 'Inviting...' : 'Send Invite'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Add Provider Modal */}
      {showAddProviderModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
            <div
              className="fixed inset-0 transition-opacity bg-gray-500 dark:bg-gray-900 bg-opacity-75 dark:bg-opacity-75"
              onClick={() => setShowAddProviderModal(false)}
            ></div>

            <div className="inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <form onSubmit={handleAddProvider}>
                <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                      Add Provider
                    </h3>
                    <button
                      type="button"
                      onClick={() => setShowAddProviderModal(false)}
                      className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                    >
                      <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
                    </button>
                  </div>
                </div>
                <div className="px-6 py-4 space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Provider Name *
                    </label>
                    <input
                      type="text"
                      value={providerFormData.name}
                      onChange={(e) => setProviderFormData({ ...providerFormData, name: e.target.value })}
                      placeholder="e.g., Production PostgreSQL"
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Provider Type *
                    </label>
                    <select
                      value={providerFormData.type}
                      onChange={(e) => setProviderFormData({ ...providerFormData, type: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                      required
                    >
                      <option value="">Select type...</option>
                      <option value="postgresql">PostgreSQL</option>
                      <option value="mysql">MySQL</option>
                      <option value="athena">AWS Athena</option>
                      <option value="bigquery">BigQuery</option>
                      <option value="snowflake">Snowflake</option>
                      <option value="mongodb">MongoDB</option>
                      <option value="splunk">Splunk</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Description
                    </label>
                    <textarea
                      value={providerFormData.description}
                      onChange={(e) => setProviderFormData({ ...providerFormData, description: e.target.value })}
                      placeholder="Optional description"
                      rows={2}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                </div>
                <div className="px-6 py-4 bg-gray-50 dark:bg-gray-700/50 border-t border-gray-200 dark:border-gray-700 flex items-center justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => setShowAddProviderModal(false)}
                    disabled={addingProvider}
                    className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={addingProvider}
                    className="px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white rounded-lg transition-colors disabled:opacity-50"
                  >
                    {addingProvider ? 'Adding...' : 'Add Provider'}
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

export default WorkspaceDetail
