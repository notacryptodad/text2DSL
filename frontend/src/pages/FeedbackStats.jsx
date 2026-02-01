import { useState, useEffect } from 'react'
import {
  ThumbsUp,
  ThumbsDown,
  TrendingUp,
  AlertCircle,
  Filter,
  BarChart3,
  Download,
  RefreshCw,
} from 'lucide-react'
import FeedbackChart from '../components/FeedbackChart'

const CATEGORY_LABELS = {
  wrong_table: 'Wrong Table',
  wrong_columns: 'Wrong Columns',
  wrong_join: 'Wrong Join',
  syntax_error: 'Syntax Error',
  performance: 'Performance Issue',
  incomplete: 'Incomplete Query',
  other: 'Other',
}

function FeedbackStats() {
  const [stats, setStats] = useState(null)
  const [feedbackList, setFeedbackList] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Filters
  const [dateRange, setDateRange] = useState('7d') // 7d, 30d, 90d, all
  const [selectedWorkspace, setSelectedWorkspace] = useState('all')
  const [workspaces, setWorkspaces] = useState([])

  // Pagination
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize] = useState(20)

  useEffect(() => {
    fetchWorkspaces()
    fetchStats()
    fetchFeedbackList()
  }, [dateRange, selectedWorkspace, currentPage])

  const getApiUrl = () => {
    return import.meta.env.DEV ? 'http://localhost:8000' : window.location.origin
  }

  const fetchWorkspaces = async () => {
    try {
      const response = await fetch(`${getApiUrl()}/api/v1/workspaces`)
      if (response.ok) {
        const data = await response.json()
        setWorkspaces(data)
      }
    } catch (err) {
      console.error('Error fetching workspaces:', err)
    }
  }

  const fetchStats = async () => {
    try {
      setLoading(true)
      setError(null)

      const params = new URLSearchParams({
        date_range: dateRange,
      })
      if (selectedWorkspace !== 'all') {
        params.append('workspace_id', selectedWorkspace)
      }

      const response = await fetch(`${getApiUrl()}/api/v1/feedback/stats?${params}`)
      if (!response.ok) throw new Error('Failed to fetch feedback statistics')

      const data = await response.json()
      setStats(data)
    } catch (err) {
      console.error('Error fetching stats:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const fetchFeedbackList = async () => {
    try {
      const params = new URLSearchParams({
        page: currentPage,
        page_size: pageSize,
        date_range: dateRange,
      })
      if (selectedWorkspace !== 'all') {
        params.append('workspace_id', selectedWorkspace)
      }

      const response = await fetch(`${getApiUrl()}/api/v1/feedback?${params}`)
      if (!response.ok) throw new Error('Failed to fetch feedback list')

      const data = await response.json()
      setFeedbackList(data)
    } catch (err) {
      console.error('Error fetching feedback list:', err)
    }
  }

  const handleRefresh = () => {
    fetchStats()
    fetchFeedbackList()
  }

  const exportData = () => {
    if (!stats) return

    const csvContent = [
      ['Metric', 'Value'],
      ['Total Feedback', stats.total_feedback],
      ['Positive', stats.positive_count],
      ['Negative', stats.negative_count],
      ['Satisfaction Rate', `${stats.satisfaction_rate}%`],
      [''],
      ['Category', 'Count'],
      ...Object.entries(stats.category_breakdown || {}).map(([category, count]) => [
        CATEGORY_LABELS[category] || category,
        count,
      ]),
    ]
      .map((row) => row.join(','))
      .join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `feedback-stats-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  const formatDate = (dateString) => {
    const date = new Date(dateString)
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                Feedback Statistics
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                Track user feedback and query quality metrics
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={handleRefresh}
                className="p-2 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                title="Refresh data"
              >
                <RefreshCw className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              </button>
              <button
                onClick={exportData}
                disabled={!stats}
                className="flex items-center space-x-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Download className="w-4 h-4" />
                <span>Export</span>
              </button>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4 mb-6">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Filter className="w-5 h-5 text-gray-500 dark:text-gray-400" />
              <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                Filters:
              </span>
            </div>

            <select
              value={dateRange}
              onChange={(e) => {
                setDateRange(e.target.value)
                setCurrentPage(1)
              }}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="7d">Last 7 days</option>
              <option value="30d">Last 30 days</option>
              <option value="90d">Last 90 days</option>
              <option value="all">All time</option>
            </select>

            <select
              value={selectedWorkspace}
              onChange={(e) => {
                setSelectedWorkspace(e.target.value)
                setCurrentPage(1)
              }}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="all">All Workspaces</option>
              {workspaces.map((workspace) => (
                <option key={workspace.id} value={workspace.id}>
                  {workspace.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto mb-4"></div>
            <p className="text-gray-600 dark:text-gray-400">Loading statistics...</p>
          </div>
        ) : error ? (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-8 text-center">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <p className="text-red-600 dark:text-red-400 font-semibold mb-2">
              Error loading statistics
            </p>
            <p className="text-gray-600 dark:text-gray-400 text-sm">{error}</p>
          </div>
        ) : stats ? (
          <>
            {/* Overview Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Total Feedback</span>
                  <BarChart3 className="w-5 h-5 text-gray-400" />
                </div>
                <div className="text-2xl font-bold text-gray-900 dark:text-white">
                  {stats.total_feedback || 0}
                </div>
              </div>

              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Positive</span>
                  <ThumbsUp className="w-5 h-5 text-green-500" />
                </div>
                <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                  {stats.positive_count || 0}
                </div>
              </div>

              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Negative</span>
                  <ThumbsDown className="w-5 h-5 text-red-500" />
                </div>
                <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                  {stats.negative_count || 0}
                </div>
              </div>

              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Satisfaction</span>
                  <TrendingUp className="w-5 h-5 text-primary-500" />
                </div>
                <div className="text-2xl font-bold text-primary-600 dark:text-primary-400">
                  {stats.satisfaction_rate ? `${stats.satisfaction_rate.toFixed(1)}%` : 'N/A'}
                </div>
              </div>
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
              {/* Feedback Over Time */}
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Feedback Over Time
                </h3>
                {stats.timeline && stats.timeline.length > 0 ? (
                  <FeedbackChart data={stats.timeline} type="line" height={250} />
                ) : (
                  <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                    No timeline data available
                  </div>
                )}
              </div>

              {/* Category Breakdown */}
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                  Issue Categories
                </h3>
                {stats.category_breakdown && Object.keys(stats.category_breakdown).length > 0 ? (
                  <FeedbackChart
                    data={Object.entries(stats.category_breakdown).map(([category, count]) => ({
                      label: CATEGORY_LABELS[category] || category,
                      value: count,
                    }))}
                    type="bar"
                    height={250}
                  />
                ) : (
                  <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                    No category data available
                  </div>
                )}
              </div>
            </div>

            {/* Recent Feedback */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
              <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Recent Feedback
                </h3>
              </div>

              {feedbackList.length === 0 ? (
                <div className="p-12 text-center text-gray-500 dark:text-gray-400">
                  No feedback available
                </div>
              ) : (
                <div className="divide-y divide-gray-200 dark:divide-gray-700">
                  {feedbackList.map((feedback) => (
                    <div key={feedback.id} className="p-6 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-3 mb-2">
                            {feedback.helpful ? (
                              <ThumbsUp className="w-4 h-4 text-green-500 flex-shrink-0" />
                            ) : (
                              <ThumbsDown className="w-4 h-4 text-red-500 flex-shrink-0" />
                            )}
                            {feedback.category && (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400">
                                {CATEGORY_LABELS[feedback.category] || feedback.category}
                              </span>
                            )}
                            <span className="text-xs text-gray-500 dark:text-gray-400">
                              {formatDate(feedback.created_at)}
                            </span>
                          </div>

                          {feedback.query && (
                            <p className="text-sm text-gray-600 dark:text-gray-400 mb-1 font-mono truncate">
                              {feedback.query}
                            </p>
                          )}

                          {feedback.comment && (
                            <p className="text-sm text-gray-700 dark:text-gray-300">
                              &quot;{feedback.comment}&quot;
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Pagination */}
              {feedbackList.length > 0 && (
                <div className="p-4 border-t border-gray-200 dark:border-gray-700">
                  <div className="flex items-center justify-between">
                    <button
                      onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                      className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Previous
                    </button>
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      Page {currentPage}
                    </span>
                    <button
                      onClick={() => setCurrentPage((p) => p + 1)}
                      disabled={feedbackList.length < pageSize}
                      className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </div>
          </>
        ) : null}
      </div>
    </div>
  )
}

export default FeedbackStats
