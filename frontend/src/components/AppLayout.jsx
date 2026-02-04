import { useState, useRef, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import {
  Moon,
  Sun,
  Zap,
  MessageSquare,
  ClipboardCheck,
  User,
  LogOut,
  Settings,
  Users,
  ChevronDown,
  Tag,
  BarChart3,
  LayoutDashboard,
  FolderKanban,
  Database,
  Network,
  Keyboard,
} from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { useKeyboardShortcuts } from '../hooks/useKeyboardShortcuts'
import WorkspaceSelector from './WorkspaceSelector'
import NavigationProgress from './NavigationProgress'
import KeyboardShortcutsHelp from './KeyboardShortcutsHelp'
import * as ROUTES from '../constants/routes'

function AppLayout({ children, darkMode, toggleDarkMode }) {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout, isSuperAdmin } = useAuth()
  const { showHelpModal, setShowHelpModal } = useKeyboardShortcuts()
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [showAdminMenu, setShowAdminMenu] = useState(false)
  const adminMenuRef = useRef(null)

  const handleLogout = () => {
    logout()
    navigate(ROUTES.LOGIN)
  }

  const isActive = (path) => {
    return location.pathname === path
  }

  const isAdminActive = () => {
    return ROUTES.isAdminRoute(location.pathname)
  }

  // Close admin menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (adminMenuRef.current && !adminMenuRef.current.contains(event.target)) {
        setShowAdminMenu(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Pages that need workspace selector (workspace-scoped operations)
  const showWorkspaceSelector = ROUTES.needsWorkspaceSelector(location.pathname)

  const adminMenuItems = [
    { name: 'Dashboard', path: ROUTES.ADMIN_DASHBOARD, icon: LayoutDashboard },
    { name: 'Workspaces', path: ROUTES.ADMIN_WORKSPACES, icon: FolderKanban },
    { name: 'Providers', path: ROUTES.ADMIN_PROVIDERS, icon: Database },
    { name: 'Connections', path: ROUTES.ADMIN_CONNECTIONS, icon: Network },
    { name: 'Users', path: ROUTES.ADMIN_USERS, icon: Users },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 transition-colors duration-200">
      {/* Navigation Progress Bar */}
      <NavigationProgress />

      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-6">
              <Link to={ROUTES.APP} className="flex items-center space-x-3">
                <div className="bg-primary-500 p-2 rounded-lg">
                  <Zap className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                    Text2DSL
                  </h1>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Natural Language to Query Converter
                  </p>
                </div>
              </Link>

              {/* Workspace Selector - only on pages that need it */}
              {user && showWorkspaceSelector && <WorkspaceSelector />}

              {/* Navigation Tabs */}
              <nav className="hidden md:flex items-center space-x-1 border-l border-gray-200 dark:border-gray-700 pl-6">
                <Link
                  to={ROUTES.CHAT}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                    isActive(ROUTES.CHAT)
                      ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                >
                  <MessageSquare className="w-4 h-4" />
                  <span className="font-medium">Chat</span>
                </Link>
                <Link
                  to={ROUTES.REVIEW}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                    isActive(ROUTES.REVIEW)
                      ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                >
                  <ClipboardCheck className="w-4 h-4" />
                  <span className="font-medium">Review</span>
                </Link>
                <Link
                  to={ROUTES.SCHEMA_ANNOTATION}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                    isActive(ROUTES.SCHEMA_ANNOTATION)
                      ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                >
                  <Tag className="w-4 h-4" />
                  <span className="font-medium">Schema</span>
                </Link>
                <Link
                  to={ROUTES.FEEDBACK_STATS}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                    isActive(ROUTES.FEEDBACK_STATS)
                      ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                >
                  <BarChart3 className="w-4 h-4" />
                  <span className="font-medium">Feedback</span>
                </Link>
                
                {/* Admin Dropdown Menu */}
                {isSuperAdmin && (
                  <div className="relative" ref={adminMenuRef}>
                    <button
                      onClick={() => setShowAdminMenu(!showAdminMenu)}
                      className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                        isAdminActive()
                          ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
                          : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                      }`}
                    >
                      <LayoutDashboard className="w-4 h-4" />
                      <span className="font-medium">Admin</span>
                      <ChevronDown className={`w-4 h-4 transition-transform ${showAdminMenu ? 'rotate-180' : ''}`} />
                    </button>

                    {/* Admin Dropdown */}
                    {showAdminMenu && (
                      <div className="absolute left-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-1 z-30">
                        {adminMenuItems.map((item) => {
                          const Icon = item.icon
                          const active = item.path === ROUTES.ADMIN_DASHBOARD
                            ? location.pathname === ROUTES.ADMIN_DASHBOARD
                            : location.pathname.startsWith(item.path)

                          return (
                            <Link
                              key={item.path}
                              to={item.path}
                              onClick={() => setShowAdminMenu(false)}
                              className={`flex items-center space-x-3 px-4 py-2 text-sm transition-colors ${
                                active
                                  ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-400'
                                  : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                              }`}
                            >
                              <Icon className="w-4 h-4" />
                              <span>{item.name}</span>
                            </Link>
                          )
                        })}
                      </div>
                    )}
                  </div>
                )}
              </nav>
            </div>

            <div className="flex items-center space-x-4">
              {/* Dark Mode Toggle */}
              <button
                onClick={toggleDarkMode}
                className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                aria-label="Toggle dark mode"
              >
                {darkMode ? (
                  <Sun className="w-5 h-5 text-gray-600 dark:text-gray-300" />
                ) : (
                  <Moon className="w-5 h-5 text-gray-600" />
                )}
              </button>

              {/* Keyboard Shortcuts Button */}
              <button
                onClick={() => setShowHelpModal(true)}
                className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                aria-label="Keyboard shortcuts"
                title="Keyboard shortcuts (?)"
              >
                <Keyboard className="w-5 h-5 text-gray-600 dark:text-gray-300" />
              </button>

              {/* User Menu */}
              <div className="relative">
                <button
                  onClick={() => setShowUserMenu(!showUserMenu)}
                  className="flex items-center space-x-2 p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                >
                  <div className="bg-primary-500 p-1 rounded-full">
                    <User className="w-4 h-4 text-white" />
                  </div>
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300 hidden sm:inline">
                    {user?.name}
                  </span>
                  <ChevronDown className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                </button>

                {/* Dropdown Menu */}
                {showUserMenu && (
                  <>
                    <div
                      className="fixed inset-0 z-10"
                      onClick={() => setShowUserMenu(false)}
                    ></div>
                    <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-1 z-20">
                      <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-700">
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          {user?.name}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {user?.email}
                        </p>
                      </div>
                      <Link
                        to={ROUTES.PROFILE}
                        onClick={() => setShowUserMenu(false)}
                        className="flex items-center space-x-2 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                      >
                        <Settings className="w-4 h-4" />
                        <span>Profile Settings</span>
                      </Link>
                      <button
                        onClick={handleLogout}
                        className="w-full flex items-center space-x-2 px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                      >
                        <LogOut className="w-4 h-4" />
                        <span>Sign out</span>
                      </button>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main>{children}</main>

      {/* Keyboard Shortcuts Help Modal */}
      <KeyboardShortcutsHelp
        isOpen={showHelpModal}
        onClose={() => setShowHelpModal(false)}
      />
    </div>
  )
}

export default AppLayout
