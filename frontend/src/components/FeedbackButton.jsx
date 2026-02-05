import { useState } from 'react'
import { ThumbsUp, ThumbsDown, X } from 'lucide-react'

/**
 * Feedback buttons component for query results
 * Allows users to rate queries with thumbs up/down and provide detailed feedback
 */
function FeedbackButton({ conversationId, turnId, onFeedbackSubmit }) {
  const [feedback, setFeedback] = useState(null) // 'up' or 'down'
  const [showModal, setShowModal] = useState(false)
  const [correctedQuery, setCorrectedQuery] = useState('')
  const [comments, setComments] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleThumbsUp = async () => {
    setFeedback('up')

    // Submit positive feedback directly
    try {
      await submitFeedback({
        rating: 5,
        is_query_correct: true,
      })
      if (onFeedbackSubmit) onFeedbackSubmit('up')
    } catch (error) {
      console.error('Error submitting feedback:', error)
    }
  }

  const handleThumbsDown = () => {
    setFeedback('down')
    setShowModal(true)
  }

  const submitFeedback = async (feedbackData) => {
    // Use empty string to leverage Vite proxy - avoids CORS issues
    const apiUrl = ''
    const token = localStorage.getItem('access_token')

    const response = await fetch(
      `${apiUrl}/api/v1/query/conversations/${conversationId}/feedback`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(feedbackData),
      }
    )

    if (!response.ok) {
      throw new Error('Failed to submit feedback')
    }
  }

  const handleSubmitNegative = async (e) => {
    e.preventDefault()
    setSubmitting(true)

    try {
      await submitFeedback({
        rating: 1,
        is_query_correct: false,
        corrected_query: correctedQuery || null,
        comments: comments || null,
      })

      setShowModal(false)
      if (onFeedbackSubmit) onFeedbackSubmit('down')
    } catch (error) {
      console.error('Error submitting feedback:', error)
      alert('Failed to submit feedback. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleCancel = () => {
    setShowModal(false)
    setFeedback(null)
    setCorrectedQuery('')
    setComments('')
  }

  return (
    <>
      <div className="flex items-center space-x-2 mt-3 pt-3 border-t border-gray-200 dark:border-gray-600">
        <span className="text-xs text-gray-500 dark:text-gray-400">Was this helpful?</span>
        <button
          onClick={handleThumbsUp}
          disabled={feedback !== null}
          className={`p-1 rounded transition-colors ${
            feedback === 'up'
              ? 'text-green-500 bg-green-100 dark:bg-green-900'
              : 'text-gray-500 hover:text-green-500 hover:bg-gray-200 dark:hover:bg-gray-600'
          } disabled:opacity-50`}
          aria-label="Thumbs up"
          title="This query is correct"
        >
          <ThumbsUp className="w-4 h-4" />
        </button>
        <button
          onClick={handleThumbsDown}
          disabled={feedback !== null}
          className={`p-1 rounded transition-colors ${
            feedback === 'down'
              ? 'text-red-500 bg-red-100 dark:bg-red-900'
              : 'text-gray-500 hover:text-red-500 hover:bg-gray-200 dark:hover:bg-gray-600'
          } disabled:opacity-50`}
          aria-label="Thumbs down"
          title="This query needs improvement"
        >
          <ThumbsDown className="w-4 h-4" />
        </button>
        {feedback && (
          <span className="text-xs text-gray-500 dark:text-gray-400">
            Thanks for your feedback!
          </span>
        )}
      </div>

      {/* Feedback Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Help us improve
              </h2>
              <button
                onClick={handleCancel}
                className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                aria-label="Close"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            <form onSubmit={handleSubmitNegative} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  What went wrong?
                </label>
                <textarea
                  value={comments}
                  onChange={(e) => setComments(e.target.value)}
                  placeholder="Please describe the issue with this query..."
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:text-white"
                  rows="4"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Corrected Query (Optional)
                </label>
                <textarea
                  value={correctedQuery}
                  onChange={(e) => setCorrectedQuery(e.target.value)}
                  placeholder="If you know the correct query, paste it here..."
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 dark:bg-gray-700 dark:text-white font-mono text-sm"
                  rows="6"
                />
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Providing a correct query helps us improve our system
                </p>
              </div>

              <div className="flex justify-end space-x-3 pt-4">
                <button
                  type="button"
                  onClick={handleCancel}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
                >
                  {submitting ? 'Submitting...' : 'Submit Feedback'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}

export default FeedbackButton
