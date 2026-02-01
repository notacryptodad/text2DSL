import { useState, useEffect } from 'react'
import { User, Mail, Lock, Save, AlertCircle, CheckCircle, Loader2, Shield } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'

function UserProfile() {
  const { user, updateProfile, changePassword } = useAuth()

  // Profile form state
  const [profileData, setProfileData] = useState({
    name: '',
    email: '',
  })
  const [profileLoading, setProfileLoading] = useState(false)
  const [profileError, setProfileError] = useState('')
  const [profileSuccess, setProfileSuccess] = useState(false)

  // Password form state
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  })
  const [passwordLoading, setPasswordLoading] = useState(false)
  const [passwordError, setPasswordError] = useState('')
  const [passwordSuccess, setPasswordSuccess] = useState(false)

  useEffect(() => {
    if (user) {
      setProfileData({
        name: user.name || '',
        email: user.email || '',
      })
    }
  }, [user])

  const handleProfileChange = (e) => {
    const { name, value } = e.target
    setProfileData((prev) => ({ ...prev, [name]: value }))
    setProfileError('')
    setProfileSuccess(false)
  }

  const handleProfileSubmit = async (e) => {
    e.preventDefault()
    setProfileError('')
    setProfileSuccess(false)
    setProfileLoading(true)

    try {
      const result = await updateProfile(profileData)

      if (result.success) {
        setProfileSuccess(true)
        setTimeout(() => setProfileSuccess(false), 3000)
      } else {
        setProfileError(result.error || 'Failed to update profile')
      }
    } catch (err) {
      setProfileError('An unexpected error occurred')
    } finally {
      setProfileLoading(false)
    }
  }

  const handlePasswordChange = (e) => {
    const { name, value } = e.target
    setPasswordData((prev) => ({ ...prev, [name]: value }))
    setPasswordError('')
    setPasswordSuccess(false)
  }

  const handlePasswordSubmit = async (e) => {
    e.preventDefault()
    setPasswordError('')
    setPasswordSuccess(false)
    setPasswordLoading(true)

    // Validation
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      setPasswordError('New passwords do not match')
      setPasswordLoading(false)
      return
    }

    if (passwordData.newPassword.length < 8) {
      setPasswordError('Password must be at least 8 characters long')
      setPasswordLoading(false)
      return
    }

    try {
      const result = await changePassword(
        passwordData.currentPassword,
        passwordData.newPassword
      )

      if (result.success) {
        setPasswordSuccess(true)
        setPasswordData({
          currentPassword: '',
          newPassword: '',
          confirmPassword: '',
        })
        setTimeout(() => setPasswordSuccess(false), 3000)
      } else {
        setPasswordError(result.error || 'Failed to change password')
      }
    } catch (err) {
      setPasswordError('An unexpected error occurred')
    } finally {
      setPasswordLoading(false)
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

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Your Profile
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Manage your account settings and preferences
          </p>
        </div>

        {/* User Info Card */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-6">
          <div className="flex items-center space-x-4">
            <div className="bg-primary-100 dark:bg-primary-900/30 p-4 rounded-full">
              <User className="w-8 h-8 text-primary-600 dark:text-primary-400" />
            </div>
            <div className="flex-1">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                {user.name}
              </h2>
              <p className="text-gray-600 dark:text-gray-400">{user.email}</p>
            </div>
            {getRoleBadge(user.role)}
          </div>

          <div className="mt-4 grid grid-cols-2 gap-4 pt-4 border-t border-gray-200 dark:border-gray-700">
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Status</p>
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                {user.is_active ? (
                  <span className="text-green-600 dark:text-green-400">Active</span>
                ) : (
                  <span className="text-red-600 dark:text-red-400">Inactive</span>
                )}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500 dark:text-gray-400">Member since</p>
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                {new Date(user.created_at).toLocaleDateString()}
              </p>
            </div>
          </div>
        </div>

        {/* Edit Profile Form */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Edit Profile
          </h3>

          <form onSubmit={handleProfileSubmit} className="space-y-4">
            {/* Profile Error/Success */}
            {profileError && (
              <div className="flex items-start space-x-3 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-red-800 dark:text-red-300">{profileError}</p>
              </div>
            )}

            {profileSuccess && (
              <div className="flex items-start space-x-3 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-green-800 dark:text-green-300">
                  Profile updated successfully
                </p>
              </div>
            )}

            {/* Name Field */}
            <div>
              <label
                htmlFor="name"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
              >
                Full name
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <User className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  id="name"
                  name="name"
                  type="text"
                  required
                  value={profileData.name}
                  onChange={handleProfileChange}
                  className="block w-full pl-10 pr-3 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  disabled={profileLoading}
                />
              </div>
            </div>

            {/* Email Field */}
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
              >
                Email address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  id="email"
                  name="email"
                  type="email"
                  required
                  value={profileData.email}
                  onChange={handleProfileChange}
                  className="block w-full pl-10 pr-3 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  disabled={profileLoading}
                />
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={profileLoading}
              className="flex items-center justify-center space-x-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {profileLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Saving...</span>
                </>
              ) : (
                <>
                  <Save className="w-5 h-5" />
                  <span>Save Changes</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Change Password Form */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            Change Password
          </h3>

          <form onSubmit={handlePasswordSubmit} className="space-y-4">
            {/* Password Error/Success */}
            {passwordError && (
              <div className="flex items-start space-x-3 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-red-800 dark:text-red-300">{passwordError}</p>
              </div>
            )}

            {passwordSuccess && (
              <div className="flex items-start space-x-3 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-green-800 dark:text-green-300">
                  Password changed successfully
                </p>
              </div>
            )}

            {/* Current Password */}
            <div>
              <label
                htmlFor="currentPassword"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
              >
                Current password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  id="currentPassword"
                  name="currentPassword"
                  type="password"
                  required
                  value={passwordData.currentPassword}
                  onChange={handlePasswordChange}
                  className="block w-full pl-10 pr-3 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  disabled={passwordLoading}
                />
              </div>
            </div>

            {/* New Password */}
            <div>
              <label
                htmlFor="newPassword"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
              >
                New password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  id="newPassword"
                  name="newPassword"
                  type="password"
                  required
                  value={passwordData.newPassword}
                  onChange={handlePasswordChange}
                  className="block w-full pl-10 pr-3 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  placeholder="At least 8 characters"
                  disabled={passwordLoading}
                />
              </div>
            </div>

            {/* Confirm New Password */}
            <div>
              <label
                htmlFor="confirmPassword"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
              >
                Confirm new password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type="password"
                  required
                  value={passwordData.confirmPassword}
                  onChange={handlePasswordChange}
                  className="block w-full pl-10 pr-3 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  disabled={passwordLoading}
                />
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={passwordLoading}
              className="flex items-center justify-center space-x-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {passwordLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Changing password...</span>
                </>
              ) : (
                <>
                  <Lock className="w-5 h-5" />
                  <span>Change Password</span>
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

export default UserProfile
