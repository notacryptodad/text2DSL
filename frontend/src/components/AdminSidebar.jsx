import { LayoutDashboard, FolderKanban, Users, Settings, Database, Network } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'

function AdminSidebar() {
  const location = useLocation()

  const navItems = [
    {
      name: 'Dashboard',
      path: '/admin',
      icon: LayoutDashboard,
    },
    {
      name: 'Workspaces',
      path: '/admin/workspaces',
      icon: FolderKanban,
    },
    {
      name: 'Providers',
      path: '/admin/providers',
      icon: Database,
    },
    {
      name: 'Connections',
      path: '/admin/connections',
      icon: Network,
    },
    {
      name: 'Users',
      path: '/admin/users',
      icon: Users,
    },
    {
      name: 'Settings',
      path: '/admin/settings',
      icon: Settings,
    },
  ]

  const isActive = (path) => {
    if (path === '/admin') {
      return location.pathname === '/admin'
    }
    return location.pathname.startsWith(path)
  }

  return (
    <aside className="bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 h-screen w-64 flex flex-col">
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white">
          Admin Panel
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          Workspace Management
        </p>
      </div>

      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon
          const active = isActive(item.path)

          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
                active
                  ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              <Icon className="w-5 h-5" />
              <span className="font-medium">{item.name}</span>
            </Link>
          )
        })}
      </nav>

      <div className="p-4 border-t border-gray-200 dark:border-gray-700">
        <div className="bg-primary-50 dark:bg-primary-900/20 rounded-lg p-4">
          <p className="text-sm text-primary-900 dark:text-primary-300 font-medium mb-1">
            Need help?
          </p>
          <p className="text-xs text-primary-700 dark:text-primary-400">
            Check the documentation or contact support
          </p>
        </div>
      </div>
    </aside>
  )
}

export default AdminSidebar
