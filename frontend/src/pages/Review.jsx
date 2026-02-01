import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  CheckCircle,
  XCircle,
  Edit3,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Filter,
  Calendar,
  Database,
  AlertTriangle,
  X,
  Copy,
  Check,
  BarChart3,
} from 'lucide-react'
import Prism from 'prismjs'
import '../styles/prism-custom.css'
import 'prismjs/components/prism-sql'

const PROVIDERS = [
  { id: 'sql-postgres', name: 'PostgreSQL' },
  { id: 'sql-mysql', name: 'MySQL' },
  { id: 'nosql-mongodb', name: 'MongoDB' },
  { id: 'splunk', name: 'Splunk' },
]

const STATUS_OPTIONS = [
  { value: 'pending_review', label: 'Pending Review' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
]

function Review() {
  const [queueItems, setQueueItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedItem, setSelectedItem] = useState(null)
  const [showModal, setShowModal] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [correctedQuery, setCorrectedQuery] = useState('')
  const [feedback, setFeedback] = useState('')
  const [copied, setCopied] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  // Filters
  const [selectedProvider, setSelectedProvider] = useState('all')
  const [selectedStatus, setSelectedStatus] = useState('all')
  const [sortBy, setSortBy] = useState('priority') // priority, date, confidence

  // Pagination
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize] = useState(10)
  const [totalPages, setTotalPages] = useState(1)

  // Statistics
  const [stats, setStats] = useState(null)

  useEffect(() => {
    fetchQueueItems()
    fetchStats()
  }, [currentPage, selectedProvider, selectedStatus])

  useEffect(() => {
    // Highlight code when modal opens or correctedQuery changes
    if (showModal) {
      setTimeout(() => Prism.highlightAll(), 0)
    }
  }, [showModal, correctedQuery])

  const fetchQueueItems = async () => {
    try {
      setLoading(true)
      setError(null)

      const params = new URLSearchParams({
        page: currentPage,
        page_size: pageSize,
      })

      if (selectedProvider !== 'all') {
        params.append('provider_id', selectedProvider)
      }

      if (selectedStatus !== 'all') {
        params.append('status_filter', selectedStatus)
      }

      const apiUrl = import.meta.env.DEV
        ? 'http://localhost:8000'
        : window.location.origin

      const response = await fetch(`${apiUrl}/api/v1/review/queue?${params}`)
      if (!response.ok) {
        throw new Error('Failed to fetch review queue')
      }

      const data = await response.json()
      setQueueItems(data)

      // Calculate total pages (rough estimate since backend doesn't return total count)
      setTotalPages(data.length === pageSize ? currentPage + 1 : currentPage)
    } catch (err) {
      console.error('Error fetching queue:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const fetchStats = async () => {
    try {
      const apiUrl = import.meta.env.DEV
        ? 'http://localhost:8000'
        : window.location.origin

      const response = await fetch(`${apiUrl}/api/v1/review/stats`)
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (err) {
      console.error('Error fetching stats:', err)
    }
  }

  const handleViewDetails = async (item) => {
    try {
      const apiUrl = import.meta.env.DEV
        ? 'http://localhost:8000'
        : window.location.origin

      const response = await fetch(`${apiUrl}/api/v1/review/queue/${item.id}`)
      if (!response.ok) {
        throw new Error('Failed to fetch item details')
      }

      const details = await response.json()
      setSelectedItem(details)
      setCorrectedQuery(details.expert_corrected_query || details.generated_query)
      setFeedback('')
      setEditMode(false)
      setShowModal(true)
    } catch (err) {
      console.error('Error fetching details:', err)
      alert('Failed to load item details')
    }
  }

  const handleApprove = async (withCorrection = false) => {
    if (!selectedItem) return

    try {
      setSubmitting(true)

      const apiUrl = import.meta.env.DEV
        ? 'http://localhost:8000'
        : window.location.origin

      const payload = {
        approved: true,
        corrected_query: withCorrection ? correctedQuery : null,
        feedback: feedback || null,
      }

      const response = await fetch(
        `${apiUrl}/api/v1/review/queue/${selectedItem.id}`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        }
      )

      if (!response.ok) {
        throw new Error('Failed to update review item')
      }

      // Refresh the queue
      await fetchQueueItems()
      await fetchStats()

      // Close modal
      setShowModal(false)
      setSelectedItem(null)
    } catch (err) {
      console.error('Error approving item:', err)
      alert('Failed to approve item')
    } finally {
      setSubmitting(false)
    }
  }

  const handleReject = async () => {
    if (!selectedItem) return

    if (!window.confirm('Are you sure you want to reject this query?')) {
      return
    }

    try {
      setSubmitting(true)

      const apiUrl = import.meta.env.DEV
        ? 'http://localhost:8000'
        : window.location.origin

      const payload = {
        approved: false,
        feedback: feedback || null,
      }

      const response = await fetch(
        `${apiUrl}/api/v1/review/queue/${selectedItem.id}`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        }
      )

      if (!response.ok) {
        throw new Error('Failed to update review item')
      }

      // Refresh the queue
      await fetchQueueItems()
      await fetchStats()

      // Close modal
      setShowModal(false)
      setSelectedItem(null)
    } catch (err) {
      console.error('Error rejecting item:', err)
      alert('Failed to reject item')
    } finally {
      setSubmitting(false)
    }
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
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

  const getConfidenceColor = (score) => {
    if (score >= 0.85) return 'text-green-600 dark:text-green-400'
    if (score >= 0.7) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-red-600 dark:text-red-400'
  }

  const getConfidenceBgColor = (score) => {
    if (score >= 0.85) return 'bg-green-500'
    if (score >= 0.7) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  const getReasonBadge = (reason) => {
    const badges = {
      low_confidence: {
        icon: AlertTriangle,
        text: 'Low Confidence',
        color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
      },
      validation_failed: {
        icon: XCircle,
        text: 'Validation Failed',
        color: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
      },
      user_reported: {
        icon: AlertCircle,
        text: 'User Reported',
        color: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
      },
      pending_review: {
        icon: AlertCircle,
        text: 'Pending Review',
        color: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400',
      },
    }

    const badge = badges[reason] || badges.pending_review
    const Icon = badge.icon

    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${badge.color}`}>
        <Icon className="w-3 h-3 mr-1" />
        {badge.text}
      </span>
    )
  }

  const sortedItems = [...queueItems].sort((a, b) => {
    switch (sortBy) {
      case 'priority':
        return b.priority - a.priority
      case 'date':
        return new Date(b.created_at) - new Date(a.created_at)
      case 'confidence':
        return a.confidence_score - b.confidence_score
      default:
        return 0
    }
  })

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                Expert Review Dashboard
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                Review and approve queries pending expert validation
              </p>
            </div>
            <Link
              to="/app/feedback-stats"
              className="flex items-center space-x-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
            >
              <BarChart3 className="w-4 h-4" />
              <span>View Feedback Stats</span>
            </Link>
          </div>
        </div>

        {/* Statistics */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
              <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                Pending Reviews
              </div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {stats.pending_reviews || 0}
              </div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
              <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                Approved
              </div>
              <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                {stats.status_breakdown?.approved || 0}
              </div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
              <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                Rejected
              </div>
              <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                {stats.status_breakdown?.rejected || 0}
              </div>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
              <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                Oldest Pending
              </div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {stats.oldest_age_hours ? `${Math.round(stats.oldest_age_hours)}h` : 'N/A'}
              </div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4 mb-6">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Filter className="w-5 h-5 text-gray-500 dark:text-gray-400" />
              <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                Filters:
              </span>
            </div>

            {/* Provider Filter */}
            <select
              value={selectedProvider}
              onChange={(e) => {
                setSelectedProvider(e.target.value)
                setCurrentPage(1)
              }}
              className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="all">All Providers</option>
              {PROVIDERS.map((provider) => (
                <option key={provider.id} value={provider.id}>
                  {provider.name}
                </option>
              ))}
            </select>

            {/* Status Filter */}
            <select
              value={selectedStatus}
              onChange={(e) => {
                setSelectedStatus(e.target.value)
                setCurrentPage(1)
              }}
              className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="all">All Statuses</option>
              {STATUS_OPTIONS.map((status) => (
                <option key={status.value} value={status.value}>
                  {status.label}
                </option>
              ))}
            </select>

            {/* Sort By */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="priority">Sort by Priority</option>
              <option value="date">Sort by Date</option>
              <option value="confidence">Sort by Confidence</option>
            </select>
          </div>
        </div>

        {/* Queue Items */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              Review Queue ({sortedItems.length} items)
            </h2>
          </div>

          {loading ? (
            <div className="p-12 text-center">
              <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto mb-4"></div>
              <p className="text-gray-600 dark:text-gray-400">Loading review queue...</p>
            </div>
          ) : error ? (
            <div className="p-12 text-center">
              <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
              <p className="text-red-600 dark:text-red-400 font-semibold mb-2">
                Error loading queue
              </p>
              <p className="text-gray-600 dark:text-gray-400 text-sm">{error}</p>
              <button
                onClick={fetchQueueItems}
                className="mt-4 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
              >
                Retry
              </button>
            </div>
          ) : sortedItems.length === 0 ? (
            <div className="p-12 text-center">
              <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
              <p className="text-gray-600 dark:text-gray-400 font-semibold mb-2">
                No items to review
              </p>
              <p className="text-gray-500 dark:text-gray-500 text-sm">
                All queries have been reviewed!
              </p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200 dark:divide-gray-700">
              {sortedItems.map((item) => (
                <div
                  key={item.id}
                  className="p-6 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      {/* Query Text */}
                      <div className="mb-3">
                        <p className="text-base font-medium text-gray-900 dark:text-white mb-1">
                          &quot;{item.user_input}&quot;
                        </p>
                        <p className="text-sm text-gray-500 dark:text-gray-400 font-mono truncate">
                          {item.generated_query}
                        </p>
                      </div>

                      {/* Metadata */}
                      <div className="flex items-center space-x-4 text-sm">
                        {/* Confidence Score */}
                        <div className="flex items-center space-x-1">
                          <span className="text-gray-500 dark:text-gray-400">
                            Confidence:
                          </span>
                          <span className={`font-semibold ${getConfidenceColor(item.confidence_score)}`}>
                            {(item.confidence_score * 100).toFixed(0)}%
                          </span>
                        </div>

                        {/* Provider */}
                        <div className="flex items-center space-x-1 text-gray-600 dark:text-gray-400">
                          <Database className="w-4 h-4" />
                          <span>
                            {PROVIDERS.find((p) => p.id === item.provider_id)?.name || item.provider_id}
                          </span>
                        </div>

                        {/* Date */}
                        <div className="flex items-center space-x-1 text-gray-600 dark:text-gray-400">
                          <Calendar className="w-4 h-4" />
                          <span>{formatDate(item.created_at)}</span>
                        </div>

                        {/* Reason Badge */}
                        {getReasonBadge(item.reason_for_review)}
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex items-center space-x-2 ml-4">
                      <button
                        onClick={() => handleViewDetails(item)}
                        className="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                      >
                        View Details
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Pagination */}
          {!loading && !error && sortedItems.length > 0 && (
            <div className="p-4 border-t border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  Page {currentPage} of {totalPages}
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    className="p-2 rounded-md bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => setCurrentPage((p) => p + 1)}
                    disabled={sortedItems.length < pageSize}
                    className="p-2 rounded-md bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Detail Modal */}
      {showModal && selectedItem && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen px-4 pt-4 pb-20 text-center sm:block sm:p-0">
            {/* Background overlay */}
            <div
              className="fixed inset-0 transition-opacity bg-gray-500 dark:bg-gray-900 bg-opacity-75 dark:bg-opacity-75"
              onClick={() => setShowModal(false)}
            ></div>

            {/* Modal panel */}
            <div className="inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full">
              {/* Header */}
              <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                  Review Query Details
                </h3>
                <button
                  onClick={() => setShowModal(false)}
                  className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                >
                  <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
                </button>
              </div>

              {/* Content */}
              <div className="px-6 py-4 max-h-[70vh] overflow-y-auto">
                {/* Natural Language Query */}
                <div className="mb-6">
                  <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                    Natural Language Query
                  </label>
                  <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 border border-gray-200 dark:border-gray-600">
                    <p className="text-gray-900 dark:text-white">
                      {selectedItem.natural_language_query}
                    </p>
                  </div>
                </div>

                {/* Generated Query */}
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300">
                      Generated Query
                    </label>
                    <button
                      onClick={() => copyToClipboard(selectedItem.generated_query)}
                      className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                      title="Copy query"
                    >
                      {copied ? (
                        <Check className="w-4 h-4 text-green-500" />
                      ) : (
                        <Copy className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                      )}
                    </button>
                  </div>
                  <pre className="bg-gray-900 dark:bg-gray-800 p-4 rounded-lg text-sm overflow-x-auto">
                    <code className="language-sql">{selectedItem.generated_query}</code>
                  </pre>
                </div>

                {/* Metadata */}
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">
                      Confidence Score
                    </label>
                    <div className="flex items-center space-x-2">
                      <div className="flex-1 bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full transition-all ${getConfidenceBgColor(selectedItem.metadata?.original_confidence || 0)}`}
                          style={{ width: `${(selectedItem.metadata?.original_confidence || 0) * 100}%` }}
                        />
                      </div>
                      <span className={`text-sm font-semibold ${getConfidenceColor(selectedItem.metadata?.original_confidence || 0)}`}>
                        {((selectedItem.metadata?.original_confidence || 0) * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">
                      Provider
                    </label>
                    <p className="text-gray-900 dark:text-white">
                      {PROVIDERS.find((p) => p.id === selectedItem.provider_id)?.name || selectedItem.provider_id}
                    </p>
                  </div>
                </div>

                {/* Feedback Category */}
                {selectedItem.feedback_category && (
                  <div className="mb-6">
                    <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                      Feedback Category
                    </label>
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-400">
                      {selectedItem.feedback_category.replace(/_/g, ' ').toUpperCase()}
                    </span>
                    {selectedItem.feedback_comment && (
                      <p className="mt-2 text-sm text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-700 rounded p-3">
                        &quot;{selectedItem.feedback_comment}&quot;
                      </p>
                    )}
                  </div>
                )}

                {/* Edit Mode */}
                {editMode && (
                  <div className="mb-6">
                    <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                      Corrected Query
                    </label>
                    <textarea
                      value={correctedQuery}
                      onChange={(e) => setCorrectedQuery(e.target.value)}
                      rows={10}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                      placeholder="Enter corrected query..."
                    />
                  </div>
                )}

                {/* Feedback/Notes */}
                <div className="mb-6">
                  <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                    Comments / Notes
                  </label>
                  <textarea
                    value={feedback}
                    onChange={(e) => setFeedback(e.target.value)}
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                    placeholder="Add your feedback or notes..."
                  />
                </div>
              </div>

              {/* Footer Actions */}
              <div className="px-6 py-4 bg-gray-50 dark:bg-gray-700/50 border-t border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    {!editMode ? (
                      <button
                        onClick={() => setEditMode(true)}
                        disabled={submitting}
                        className="flex items-center space-x-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        <Edit3 className="w-4 h-4" />
                        <span>Edit & Approve</span>
                      </button>
                    ) : (
                      <button
                        onClick={() => setEditMode(false)}
                        disabled={submitting}
                        className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        Cancel Edit
                      </button>
                    )}
                  </div>

                  <div className="flex items-center space-x-2">
                    <button
                      onClick={handleReject}
                      disabled={submitting}
                      className="flex items-center space-x-2 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      <XCircle className="w-4 h-4" />
                      <span>Reject</span>
                    </button>
                    <button
                      onClick={() => handleApprove(editMode)}
                      disabled={submitting}
                      className="flex items-center space-x-2 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      <CheckCircle className="w-4 h-4" />
                      <span>{editMode ? 'Approve with Correction' : 'Approve'}</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Review
