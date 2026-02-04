import { useState } from 'react'
import { LayoutDashboard, FolderKanban, Users, Database, Network, ChevronLeft, ChevronRight, ArrowLeft } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'

function AdminSidebar() {
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(() => {
    return localStorage.getItem('adminSidebarCollapsed') === 'true'
  })

  const toggleCollapsed = () => {
    const newState = !collapsed
    setCollapsed(newState)
    localStorage.setItem('adminSidebarCollapsed', String(newState))
  }

  const navItems = [
    { name: 'Dashboard', path: '/admin', icon: LayoutDashboard },
    { name: 'Workspaces', path: '/admin/workspaces', icon: FolderKanban },
    { name: 'Providers', path: '/admin/providers', icon: Database },
    { name: 'Connections', path: '/admin/connections', icon: Network },
    { name: 'Users', path: '/admin/users', icon: Users },
  ]

  const isActive = (path) => {
    if (path === '/admin') return location.pathname === '/admin'
    return location.pathname.startsWith(path)
  }

  return (
    <aside className={`bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 h-screen flex flex-col transition-all duration-300 ${collapsed ? 'w-16' : 'w-64'}`}>
      <div className={`p-4 border-b border-gray-200 dark:border-gray-700 flex items-center ${collapsed ? 'justify-center' : 'justify-between'}`}>
        {!collapsed && (
          <div>
            <h2 className="text-lg font-bold text-gray-900 dark:text-white">Admin</h2>
          </div>
        )}
        <button
          onClick={toggleCollapsed}
          className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400"
          title={collapsed ? 'Expand' : 'Collapse'}
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      <nav className="flex-1 p-2 space-y-1 overflow-y-auto">
        {/* Back to App link */}
        <Link
          to="/app"
          title={collapsed ? 'Back to App' : undefined}
          className={`flex items-center ${collapsed ? 'justify-center' : 'space-x-3'} px-3 py-2.5 rounded-lg transition-colors text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 mb-2 border-b border-gray-200 dark:border-gray-700 pb-3`}
        >
          <ArrowLeft className="w-5 h-5 flex-shrink-0" />
          {!collapsed && <span className="font-medium text-sm">Back to App</span>}
        </Link>

        {navItems.map((item) => {
          const Icon = item.icon
          const active = isActive(item.path)

          return (
            <Link
              key={item.path}
              to={item.path}
              title={collapsed ? item.name : undefined}
              className={`flex items-center ${collapsed ? 'justify-center' : 'space-x-3'} px-3 py-2.5 rounded-lg transition-colors ${
                active
                  ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              {!collapsed && <span className="font-medium text-sm">{item.name}</span>}
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}

export default AdminSidebar
