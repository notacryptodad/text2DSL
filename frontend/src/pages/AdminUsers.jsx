import { useState, useEffect } from 'react'
import {
  Users,
  UserPlus,
  Edit3,
  UserX,
  UserCheck,
  Shield,
  Mail,
  Calendar,
  Search,
  X,
  Loader2,
  AlertCircle,
  CheckCircle,
  User,
  Lock,
} from 'lucide-react'
import { useAuth } from '../hooks/useAuth'

function AdminUsers() {
  const { isSuperAdmin } = useAuth()

  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [searchQuery, setSearchQuery] = useState('')

  // Modal state
  const [showModal, setShowModal] = useState(false)
  const [modalMode, setModalMode] = useState('create') // 'create' or 'edit'
  const [selectedUser, setSelectedUser] = useState(null)

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    role: 'user',
    is_active: true,
  })
  const [formLoading, setFormLoading] = useState(false)
  const [formError, setFormError] = useState('')
  const [formSuccess, setFormSuccess] = useState(false)

  const apiUrl = import.meta.env.DEV
    ? 'http://localhost:8000'
    : window.location.origin

  useEffect(() => {
    fetchUsers()
  }, [])

  const fetchUsers = async () => {
    try {
      setLoading(true)
      setError('')

      const token = localStorage.getItem('access_token')
      const response = await fetch(`${apiUrl}/api/v1/admin/users`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (!response.ok) {
        throw new Error('Failed to fetch users')
      }

      const data = await response.json()
      setUsers(data)
    } catch (err) {
      console.error('Error fetching users:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateUser = () => {
    setModalMode('create')
    setFormData({
      name: '',
      email: '',
      password: '',
      role: 'user',
      is_active: true,
    })
    setFormError('')
    setFormSuccess(false)
    setShowModal(true)
  }

  const handleEditUser = (user) => {
    setModalMode('edit')
    setSelectedUser(user)
    setFormData({
      name: user.name,
      email: user.email,
      password: '', // Don't pre-fill password
      role: user.role,
      is_active: user.is_active,
    })
    setFormError('')
    setFormSuccess(false)
    setShowModal(true)
  }

  const handleFormChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }))
    setFormError('')
    setFormSuccess(false)
  }

  const handleFormSubmit = async (e) => {
    e.preventDefault()
    setFormError('')
    setFormSuccess(false)
    setFormLoading(true)

    try {
      const token = localStorage.getItem('access_token')

      if (modalMode === 'create') {
        // Create new user
        const response = await fetch(`${apiUrl}/api/v1/admin/users`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(formData),
        })

        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.detail || 'Failed to create user')
        }

        setFormSuccess(true)
        setTimeout(() => {
          setShowModal(false)
          fetchUsers()
        }, 1500)
      } else {
        // Update existing user
        const updateData = { ...formData }
        if (!updateData.password) {
          delete updateData.password // Don't update password if not provided
        }

        const response = await fetch(`${apiUrl}/api/v1/admin/users/${selectedUser.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(updateData),
        })

        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.detail || 'Failed to update user')
        }

        setFormSuccess(true)
        setTimeout(() => {
          setShowModal(false)
          fetchUsers()
        }, 1500)
      }
    } catch (err) {
      console.error('Form submission error:', err)
      setFormError(err.message)
    } finally {
      setFormLoading(false)
    }
  }

  const handleToggleUserStatus = async (userId, currentStatus) => {
    if (!window.confirm(`Are you sure you want to ${currentStatus ? 'deactivate' : 'activate'} this user?`)) {
      return
    }

    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch(`${apiUrl}/api/v1/admin/users/${userId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          is_active: !currentStatus,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to update user status')
      }

      await fetchUsers()
    } catch (err) {
      console.error('Error toggling user status:', err)
      alert('Failed to update user status')
    }
  }

  const getRoleBadge = (role) => {
    const badges = {
      super_admin: {
        text: 'Super Admin',
        color: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
      },
      admin: {
        text: 'Admin',
        color: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
      },
      user: {
        text: 'User',
        color: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400',
      },
    }

    const badge = badges[role] || badges.user

    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${badge.color}`}>
        <Shield className="w-3 h-3 mr-1" />
        {badge.text}
      </span>
    )
  }

  const filteredUsers = users.filter((user) => {
    const query = searchQuery.toLowerCase()
    return (
      user.name.toLowerCase().includes(query) ||
      user.email.toLowerCase().includes(query) ||
      user.role.toLowerCase().includes(query)
    )
  })

  if (!isSuperAdmin) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center">
        <div className="text-center">
          <Shield className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Access Denied
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            You don't have permission to access this page.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            User Management
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Manage user accounts, roles, and permissions
          </p>
        </div>

        {/* Actions Bar */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4 mb-6">
          <div className="flex items-center justify-between">
            {/* Search */}
            <div className="flex-1 max-w-md">
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Search className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="block w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  placeholder="Search users..."
                />
              </div>
            </div>

            {/* Create User Button */}
            <button
              onClick={handleCreateUser}
              className="flex items-center space-x-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors ml-4"
            >
              <UserPlus className="w-5 h-5" />
              <span>Create User</span>
            </button>
          </div>
        </div>

        {/* Users List */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          {loading ? (
            <div className="p-12 text-center">
              <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto mb-4"></div>
              <p className="text-gray-600 dark:text-gray-400">Loading users...</p>
            </div>
          ) : error ? (
            <div className="p-12 text-center">
              <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
              <p className="text-red-600 dark:text-red-400 font-semibold mb-2">
                Error loading users
              </p>
              <p className="text-gray-600 dark:text-gray-400 text-sm">{error}</p>
              <button
                onClick={fetchUsers}
                className="mt-4 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
              >
                Retry
              </button>
            </div>
          ) : filteredUsers.length === 0 ? (
            <div className="p-12 text-center">
              <Users className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600 dark:text-gray-400 font-semibold mb-2">
                No users found
              </p>
              <p className="text-gray-500 dark:text-gray-500 text-sm">
                {searchQuery ? 'Try adjusting your search' : 'Get started by creating a user'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-700/50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      User
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Role
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Created
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {filteredUsers.map((user) => (
                    <tr key={user.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="flex-shrink-0 h-10 w-10 bg-primary-100 dark:bg-primary-900/30 rounded-full flex items-center justify-center">
                            <User className="h-5 w-5 text-primary-600 dark:text-primary-400" />
                          </div>
                          <div className="ml-4">
                            <div className="text-sm font-medium text-gray-900 dark:text-white">
                              {user.name}
                            </div>
                            <div className="text-sm text-gray-500 dark:text-gray-400 flex items-center">
                              <Mail className="w-3 h-3 mr-1" />
                              {user.email}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getRoleBadge(user.role)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {user.is_active ? (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400">
                            <UserCheck className="w-3 h-3 mr-1" />
                            Active
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400">
                            <UserX className="w-3 h-3 mr-1" />
                            Inactive
                          </span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        <div className="flex items-center">
                          <Calendar className="w-3 h-3 mr-1" />
                          {new Date(user.created_at).toLocaleDateString()}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <div className="flex items-center justify-end space-x-2">
                          <button
                            onClick={() => handleEditUser(user)}
                            className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                            title="Edit user"
                          >
                            <Edit3 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleToggleUserStatus(user.id, user.is_active)}
                            className={`p-2 rounded-lg transition-colors ${
                              user.is_active
                                ? 'text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20'
                                : 'text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20'
                            }`}
                            title={user.is_active ? 'Deactivate user' : 'Activate user'}
                          >
                            {user.is_active ? (
                              <UserX className="w-4 h-4" />
                            ) : (
                              <UserCheck className="w-4 h-4" />
                            )}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Create/Edit User Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
            {/* Background overlay */}
            <div
              className="fixed inset-0 transition-opacity bg-gray-500 dark:bg-gray-900 bg-opacity-75 dark:bg-opacity-75"
              onClick={() => setShowModal(false)}
            ></div>

            {/* Modal panel */}
            <div className="inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              {/* Header */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                  {modalMode === 'create' ? 'Create New User' : 'Edit User'}
                </h3>
                <button
                  onClick={() => setShowModal(false)}
                  className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                >
                  <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
                </button>
              </div>

              {/* Form */}
              <form onSubmit={handleFormSubmit} className="px-6 py-4">
                {/* Error/Success Messages */}
                {formError && (
                  <div className="mb-4 flex items-start space-x-3 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                    <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-red-800 dark:text-red-300">{formError}</p>
                  </div>
                )}

                {formSuccess && (
                  <div className="mb-4 flex items-start space-x-3 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                    <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-green-800 dark:text-green-300">
                      {modalMode === 'create' ? 'User created successfully!' : 'User updated successfully!'}
                    </p>
                  </div>
                )}

                <div className="space-y-4">
                  {/* Name */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Full Name
                    </label>
                    <input
                      type="text"
                      name="name"
                      required
                      value={formData.name}
                      onChange={handleFormChange}
                      className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                      disabled={formLoading || formSuccess}
                    />
                  </div>

                  {/* Email */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Email Address
                    </label>
                    <input
                      type="email"
                      name="email"
                      required
                      value={formData.email}
                      onChange={handleFormChange}
                      className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                      disabled={formLoading || formSuccess}
                    />
                  </div>

                  {/* Password */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Password {modalMode === 'edit' && '(leave blank to keep current)'}
                    </label>
                    <input
                      type="password"
                      name="password"
                      required={modalMode === 'create'}
                      value={formData.password}
                      onChange={handleFormChange}
                      className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                      placeholder={modalMode === 'create' ? 'At least 8 characters' : 'Leave blank to keep current'}
                      disabled={formLoading || formSuccess}
                    />
                  </div>

                  {/* Role */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Role
                    </label>
                    <select
                      name="role"
                      value={formData.role}
                      onChange={handleFormChange}
                      className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                      disabled={formLoading || formSuccess}
                    >
                      <option value="user">User</option>
                      <option value="admin">Admin</option>
                      <option value="super_admin">Super Admin</option>
                    </select>
                  </div>

                  {/* Active Status */}
                  <div className="flex items-center">
                    <input
                      type="checkbox"
                      name="is_active"
                      id="is_active"
                      checked={formData.is_active}
                      onChange={handleFormChange}
                      className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                      disabled={formLoading || formSuccess}
                    />
                    <label
                      htmlFor="is_active"
                      className="ml-2 block text-sm text-gray-700 dark:text-gray-300"
                    >
                      Active
                    </label>
                  </div>
                </div>

                {/* Actions */}
                <div className="mt-6 flex items-center justify-end space-x-3">
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                    disabled={formLoading}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={formLoading || formSuccess}
                    className="flex items-center space-x-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {formLoading ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        <span>{modalMode === 'create' ? 'Creating...' : 'Saving...'}</span>
                      </>
                    ) : (
                      <>
                        <CheckCircle className="w-5 h-5" />
                        <span>{modalMode === 'create' ? 'Create User' : 'Save Changes'}</span>
                      </>
                    )}
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

export default AdminUsers
