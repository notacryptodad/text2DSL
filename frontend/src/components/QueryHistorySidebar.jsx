import { useState, useCallback, createContext, useContext, useMemo } from 'react'
import { X, Search, Play, Clock, Database, Trash2 } from 'lucide-react'

// Context for query history state
const QueryHistoryContext = createContext(null)

// Hook to access query history
export function useQueryHistory() {
  const context = useContext(QueryHistoryContext)
  if (!context) {
    // Return a no-op when used outside provider (for initial render)
    return {
      queries: [],
      addQuery: () => {},
      removeQuery: () => {},
      clearHistory: () => {}
    }
  }
  return context
}

// Provider component to wrap the app
export function QueryHistoryProvider({ children }) {
  const [queries, setQueries] = useState(() => {
    const saved = localStorage.getItem('queryHistory')
    return saved ? JSON.parse(saved) : []
  })

  const addQuery = useCallback((query) => {
    setQueries(prev => {
      const newQueries = [
        {
          id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          timestamp: new Date().toISOString(),
          ...query
        },
        ...prev
      ].slice(0, 100) // Keep last 100 queries
      localStorage.setItem('queryHistory', JSON.stringify(newQueries))
      return newQueries
    })
  }, [])

  const removeQuery = useCallback((id) => {
    setQueries(prev => {
      const newQueries = prev.filter(q => q.id !== id)
      localStorage.setItem('queryHistory', JSON.stringify(newQueries))
      return newQueries
    })
  }, [])

  const clearHistory = useCallback(() => {
    setQueries([])
    localStorage.removeItem('queryHistory')
  }, [])

  const value = useMemo(() => ({
    queries,
    addQuery,
    removeQuery,
    clearHistory
  }), [queries, addQuery, removeQuery, clearHistory])

  return (
    <QueryHistoryContext.Provider value={value}>
      {children}
    </QueryHistoryContext.Provider>
  )
}

// Sidebar component
function QueryHistorySidebar({ isOpen, onClose, onRunQuery, providers = [], currentProviderId }) {
  const [searchTerm, setSearchTerm] = useState('')
  const [filterProviderId, setFilterProviderId] = useState('')
  
  // Get history from localStorage directly since we might not have provider
  const [queries, setQueries] = useState(() => {
    const saved = localStorage.getItem('queryHistory')
    return saved ? JSON.parse(saved) : []
  })

  // Refresh queries when sidebar opens
  const refreshQueries = useCallback(() => {
    const saved = localStorage.getItem('queryHistory')
    setQueries(saved ? JSON.parse(saved) : [])
  }, [])

  // Refresh on open
  useState(() => {
    if (isOpen) refreshQueries()
  }, [isOpen, refreshQueries])

  const filteredQueries = useMemo(() => {
    return queries.filter(q => {
      const matchesSearch = !searchTerm || 
        q.query?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        q.generatedDSL?.toLowerCase().includes(searchTerm.toLowerCase())
      const matchesProvider = !filterProviderId || q.providerId === filterProviderId
      return matchesSearch && matchesProvider
    })
  }, [queries, searchTerm, filterProviderId])

  const handleRunQuery = (query) => {
    onRunQuery({
      query: query.query,
      providerId: query.providerId || currentProviderId
    })
    onClose()
  }

  const handleDelete = (id, e) => {
    e.stopPropagation()
    const newQueries = queries.filter(q => q.id !== id)
    localStorage.setItem('queryHistory', JSON.stringify(newQueries))
    setQueries(newQueries)
  }

  const formatDate = (timestamp) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now - date
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:bg-opacity-30"
        onClick={onClose}
      />
      
      {/* Sidebar */}
      <div className="fixed right-0 top-0 h-full w-96 max-w-full bg-white dark:bg-gray-800 shadow-xl z-50 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-2">
            <Clock className="w-5 h-5 text-indigo-500" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Query History</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Search and Filter */}
        <div className="p-4 space-y-3 border-b border-gray-200 dark:border-gray-700">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search queries..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          
          {providers.length > 0 && (
            <select
              value={filterProviderId}
              onChange={(e) => setFilterProviderId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All Providers</option>
              {providers.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          )}
        </div>

        {/* Query List */}
        <div className="flex-1 overflow-y-auto">
          {filteredQueries.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500 dark:text-gray-400 p-8">
              <Clock className="w-12 h-12 mb-4 opacity-50" />
              <p className="text-center">
                {searchTerm || filterProviderId 
                  ? 'No queries match your filters' 
                  : 'No query history yet'}
              </p>
              <p className="text-sm text-center mt-2 opacity-75">
                Your queries will appear here as you use the chat
              </p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200 dark:divide-gray-700">
              {filteredQueries.map((query) => (
                <div
                  key={query.id}
                  className="p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors group"
                  onClick={() => handleRunQuery(query)}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400">
                      <Clock className="w-3 h-3" />
                      <span>{formatDate(query.timestamp)}</span>
                      {query.providerName && (
                        <>
                          <span>•</span>
                          <div className="flex items-center space-x-1">
                            <Database className="w-3 h-3" />
                            <span>{query.providerName}</span>
                          </div>
                        </>
                      )}
                    </div>
                    <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={(e) => handleDelete(query.id, e)}
                        className="p-1 hover:bg-red-100 dark:hover:bg-red-900/30 rounded text-red-500"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                      <button
                        className="p-1 hover:bg-indigo-100 dark:hover:bg-indigo-900/30 rounded text-indigo-500"
                        title="Run query"
                      >
                        <Play className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                  
                  <p className="text-sm text-gray-900 dark:text-white mb-2 line-clamp-2">
                    {query.query}
                  </p>
                  
                  {query.generatedDSL && (
                    <pre className="text-xs bg-gray-100 dark:bg-gray-900 p-2 rounded overflow-x-auto text-gray-600 dark:text-gray-400 line-clamp-3">
                      {query.generatedDSL}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        {queries.length > 0 && (
          <div className="p-4 border-t border-gray-200 dark:border-gray-700">
            <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
              {filteredQueries.length} of {queries.length} queries
            </p>
          </div>
        )}
      </div>
    </>
  )
}

export default QueryHistorySidebar
