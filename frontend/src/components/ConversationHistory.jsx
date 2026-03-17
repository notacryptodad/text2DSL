import { MessageSquare, Trash2, Plus } from 'lucide-react'

function ConversationHistory({ conversations, currentId, onSelect, onNew, onDelete }) {
  const formatDate = (date) => {
    const d = new Date(date)
    const now = new Date()
    const diffMs = now - d
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  const getPreview = (conv) => {
    if (conv.messages.length === 0) return 'New conversation'
    const lastMessage = conv.messages[conv.messages.length - 1]
    if (lastMessage.type === 'user') {
      return lastMessage.content.substring(0, 60) + (lastMessage.content.length > 60 ? '...' : '')
    }
    return 'Query generated'
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 h-full flex flex-col">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
            <MessageSquare className="w-5 h-5" />
            <span>History</span>
          </h2>
          <button
            onClick={onNew}
            className="p-1.5 rounded-lg bg-primary-500 hover:bg-primary-600 text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-800"
            title="New conversation"
            aria-label="New conversation"
          >
            <Plus className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {conversations.length === 0 ? (
          <div className="p-4 text-center text-gray-500 dark:text-gray-400 text-sm">
            No conversations yet
          </div>
        ) : (
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                className={`group relative flex hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors ${
                  conv.id === currentId
                    ? 'bg-primary-50 dark:bg-primary-900/20 border-l-4 border-primary-500'
                    : 'border-l-4 border-transparent'
                }`}
              >
                <button
                  className="flex-1 min-w-0 p-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary-500 rounded-sm"
                  onClick={() => onSelect(conv.id)}
                  aria-label={`Select conversation: ${conv.provider || 'Conversation'}`}
                >
                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate pr-8">
                    {conv.provider || 'Conversation'}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 truncate pr-8">
                    {getPreview(conv)}
                  </p>
                  <p className="text-xs text-gray-400 dark:text-gray-500 mt-1 pr-8">
                    {formatDate(conv.timestamp)}
                  </p>
                </button>
                {conv.id !== currentId && (
                  <button
                    onClick={() => onDelete(conv.id)}
                    className="absolute right-3 top-3 p-1 text-gray-400 hover:text-red-500 dark:hover:text-red-400 transition-colors rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 opacity-0 group-hover:opacity-100 focus-visible:opacity-100"
                    title="Delete conversation"
                    aria-label={`Delete conversation: ${conv.provider || 'Conversation'}`}
                  >
                    <Trash2 className="w-4 h-4" aria-hidden="true" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default ConversationHistory
