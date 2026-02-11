import { History, Clock, X } from 'lucide-react'
import ConversationHistory from '../ConversationHistory'
import QueryHistorySidebar from '../QueryHistorySidebar'

export default function ChatSidebars({
  showHistory,
  showQueryHistory,
  conversations,
  conversationId,
  providers,
  selectedProvider,
  onToggleHistory,
  onToggleQueryHistory,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onRunFromHistory,
  modKey
}) {
  return (
    <>
      {/* Query History Button */}
      <button
        onClick={onToggleQueryHistory}
        className="fixed bottom-24 right-8 p-4 rounded-full bg-indigo-500 hover:bg-indigo-600 text-white shadow-lg transition-colors z-30"
        aria-label="Toggle query history"
        title="Search Query History"
      >
        <Clock className="w-6 h-6" />
      </button>

      {/* History Button - Fixed Position */}
      <button
        onClick={onToggleHistory}
        className="group fixed bottom-8 right-8 p-4 rounded-full bg-primary-500 hover:bg-primary-600 text-white shadow-lg transition-colors z-30"
        aria-label="Toggle conversation history"
        title={`Toggle history (${modKey}+H)`}
      >
        <History className="w-6 h-6" />
        {conversations.length > 0 && (
          <span className="absolute -top-1 -right-1 w-6 h-6 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
            {conversations.length}
          </span>
        )}
        {/* Tooltip showing shortcut */}
        <span className="absolute bottom-full right-0 mb-2 px-2 py-1 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
          {modKey}+H
        </span>
      </button>

      {/* Query History Sidebar */}
      <QueryHistorySidebar
        isOpen={showQueryHistory}
        onClose={onToggleQueryHistory}
        onRunQuery={onRunFromHistory}
        providers={providers}
        currentProviderId={selectedProvider?.id}
      />

      {/* Conversation History Sidebar - Mobile */}
      {showHistory && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-black bg-opacity-50"
            onClick={onToggleHistory}
          />
          <div className="absolute right-0 top-0 h-full w-80 bg-white dark:bg-gray-800 shadow-xl">
            <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Conversation History
              </h2>
              <button
                onClick={onToggleHistory}
                className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="h-[calc(100%-64px)]">
              <ConversationHistory
                conversations={conversations}
                currentId={conversationId}
                onSelect={onSelectConversation}
                onNew={onNewConversation}
                onDelete={onDeleteConversation}
              />
            </div>
          </div>
        </div>
      )}

      {/* Desktop History Sidebar */}
      <div
        className={`hidden lg:block fixed right-0 top-0 h-full w-80 bg-white dark:bg-gray-800 shadow-xl transform transition-transform duration-300 z-40 ${
          showHistory ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700 mt-20">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Conversation History
          </h2>
          <button
            onClick={onToggleHistory}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>
        <div className="h-[calc(100%-144px)]">
          <ConversationHistory
            conversations={conversations}
            currentId={conversationId}
            onSelect={onSelectConversation}
            onNew={onNewConversation}
            onDelete={onDeleteConversation}
          />
        </div>
      </div>
    </>
  )
}
