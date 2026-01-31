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
            className="p-1.5 rounded-lg bg-primary-500 hover:bg-primary-600 text-white transition-colors"
            title="New conversation"
          >
            <Plus className="w-4 h-4" />
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
                className={`p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors ${
                  conv.id === currentId
                    ? 'bg-primary-50 dark:bg-primary-900/20 border-l-4 border-primary-500'
                    : ''
                }`}
                onClick={() => onSelect(conv.id)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {conv.provider || 'Conversation'}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 truncate">
                      {getPreview(conv)}
                    </p>
                    <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                      {formatDate(conv.timestamp)}
                    </p>
                  </div>
                  {conv.id !== currentId && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        onDelete(conv.id)
                      }}
                      className="ml-2 p-1 text-gray-400 hover:text-red-500 dark:hover:text-red-400 transition-colors"
                      title="Delete conversation"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default ConversationHistory
