import { useState, useRef, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  Menu,
  X,
  MessageSquare,
  ClipboardCheck,
  Tag,
  BarChart3,
  LayoutDashboard,
  FolderKanban,
  Database,
  Network,
  Users,
} from 'lucide-react'
import * as ROUTES from '../constants/routes'

function MobileNav({ isSuperAdmin }) {
  const [isOpen, setIsOpen] = useState(false)
  const location = useLocation()
  const drawerRef = useRef(null)

  const isActive = (path) => {
    return location.pathname === path
  }

  const isAdminActive = (path) => {
    if (path === ROUTES.ADMIN_DASHBOARD) {
      return location.pathname === ROUTES.ADMIN_DASHBOARD
    }
    return location.pathname.startsWith(path)
  }

  // Close on navigation
  const handleLinkClick = () => {
    setIsOpen(false)
  }

  // Close when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (drawerRef.current && !drawerRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  // Prevent body scroll when drawer is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = 'unset'
    }

    return () => {
      document.body.style.overflow = 'unset'
    }
  }, [isOpen])

  const mainNavItems = [
    { name: 'Chat', path: ROUTES.CHAT, icon: MessageSquare },
    { name: 'Review', path: ROUTES.REVIEW, icon: ClipboardCheck },
    { name: 'Schema', path: ROUTES.SCHEMA_ANNOTATION, icon: Tag },
    { name: 'Feedback', path: ROUTES.FEEDBACK_STATS, icon: BarChart3 },
  ]

  const adminMenuItems = [
    { name: 'Dashboard', path: ROUTES.ADMIN_DASHBOARD, icon: LayoutDashboard },
    { name: 'Workspaces', path: ROUTES.ADMIN_WORKSPACES, icon: FolderKanban },
    { name: 'Providers', path: ROUTES.ADMIN_PROVIDERS, icon: Database },
    { name: 'Connections', path: ROUTES.ADMIN_CONNECTIONS, icon: Network },
    { name: 'Users', path: ROUTES.ADMIN_USERS, icon: Users },
  ]

  return (
    <>
      {/* Hamburger Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="md:hidden p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
        aria-label="Open mobile menu"
      >
        <Menu className="w-5 h-5 text-gray-600 dark:text-gray-300" />
      </button>

      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden transition-opacity"
          aria-hidden="true"
        />
      )}

      {/* Slide-out Drawer */}
      <div
        ref={drawerRef}
        className={`fixed top-0 left-0 h-full w-64 bg-white dark:bg-gray-800 shadow-xl z-50 transform transition-transform duration-300 ease-in-out md:hidden ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Menu
          </h2>
          <button
            onClick={() => setIsOpen(false)}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            aria-label="Close mobile menu"
          >
            <X className="w-5 h-5 text-gray-600 dark:text-gray-300" />
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="p-4">
          <div className="space-y-1">
            {mainNavItems.map((item) => {
              const Icon = item.icon
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={handleLinkClick}
                  className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
                    isActive(item.path)
                      ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span className="font-medium">{item.name}</span>
                </Link>
              )
            })}
          </div>

          {/* Admin Section */}
          {isSuperAdmin && (
            <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
              <h3 className="px-4 mb-2 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Admin
              </h3>
              <div className="space-y-1">
                {adminMenuItems.map((item) => {
                  const Icon = item.icon
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      onClick={handleLinkClick}
                      className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
                        isAdminActive(item.path)
                          ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
                          : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                      }`}
                    >
                      <Icon className="w-5 h-5" />
                      <span className="font-medium">{item.name}</span>
                    </Link>
                  )
                })}
              </div>
            </div>
          )}
        </nav>
      </div>
    </>
  )
}

export default MobileNav
