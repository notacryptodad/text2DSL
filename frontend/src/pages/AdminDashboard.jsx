import { useState, useEffect } from 'react'
import { FolderKanban, Users, Activity, TrendingUp, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import PageHeader from '../components/PageHeader'
import * as ROUTES from '../constants/routes'

function AdminDashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    try {
      setLoading(true)
      const apiUrl = ''
      const token = localStorage.getItem('access_token')

      // Fetch overview statistics
      const response = await fetch(`${apiUrl}/api/v1/admin/stats`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      })
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (err) {
      console.error('Error fetching stats:', err)
    } finally {
      setLoading(false)
    }
  }

  const statCards = [
    {
      title: 'Total Workspaces',
      value: stats?.total_workspaces || 0,
      icon: FolderKanban,
      color: 'bg-blue-500',
      link: ROUTES.ADMIN_WORKSPACES,
    },
    {
      title: 'Total Users',
      value: stats?.total_users || 0,
      icon: Users,
      color: 'bg-green-500',
      link: ROUTES.ADMIN_USERS,
    },
    {
      title: 'Queries Today',
      value: stats?.queries_today || 0,
      icon: Activity,
      color: 'bg-purple-500',
    },
    {
      title: 'Active Connections',
      value: stats?.active_connections || 0,
      icon: TrendingUp,
      color: 'bg-orange-500',
      link: ROUTES.ADMIN_CONNECTIONS,
    },
  ]

  const quickLinks = [
    {
      title: 'Manage Workspaces',
      description: 'Create and configure workspaces',
      icon: FolderKanban,
      link: ROUTES.ADMIN_WORKSPACES,
      color: 'text-blue-500',
    },
    {
      title: 'Manage Users',
      description: 'Add and manage user accounts',
      icon: Users,
      link: ROUTES.ADMIN_USERS,
      color: 'text-green-500',
    },
    {
      title: 'Database Providers',
      description: 'Configure database connections',
      icon: Activity,
      link: ROUTES.ADMIN_PROVIDERS,
      color: 'text-purple-500',
    },
  ]

  const breadcrumbItems = [
    { label: 'Admin', path: ROUTES.ADMIN },
  ]

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <PageHeader
        breadcrumbItems={breadcrumbItems}
        title="Admin Dashboard"
        description="Overview of your Text2DSL system"
      />

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {statCards.map((card) => {
          const Icon = card.icon
          return (
            <div
              key={card.title}
              className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow"
            >
              <div className="flex items-center justify-between mb-4">
                <div className={`${card.color} p-3 rounded-lg`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>
                {card.link && (
                  <Link
                    to={card.link}
                    className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                  >
                    <ArrowRight className="w-5 h-5" />
                  </Link>
                )}
              </div>
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                  {card.title}
                </p>
                {loading ? (
                  <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded animate-pulse w-16"></div>
                ) : (
                  <p className="text-3xl font-bold text-gray-900 dark:text-white">
                    {card.value}
                  </p>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Quick Links */}
      <div className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Quick Actions
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {quickLinks.map((link) => {
            const Icon = link.icon
            return (
              <Link
                key={link.title}
                to={link.link}
                className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:border-primary-300 dark:hover:border-primary-700 hover:shadow-md transition-all group"
              >
                <Icon className={`w-10 h-10 ${link.color} mb-4`} />
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                  {link.title}
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {link.description}
                </p>
              </Link>
            )
          })}
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Recent Activity
          </h2>
        </div>
        <div className="p-6">
          {loading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="animate-pulse flex space-x-4">
                  <div className="w-10 h-10 bg-gray-200 dark:bg-gray-700 rounded-full"></div>
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
                    <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <Activity className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No recent activity</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default AdminDashboard
