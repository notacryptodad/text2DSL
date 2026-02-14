import { useState, useEffect, useRef, useImperativeHandle, forwardRef } from 'react'
import { Send, Loader2 } from 'lucide-react'

const QueryInput = forwardRef(function QueryInput({ onSend, disabled, placeholder, onQueryChange, lastQuery }, ref) {
  const [query, setQuery] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const textareaRef = useRef(null)

  // Notify parent of query changes for live preview
  useEffect(() => {
    if (onQueryChange) {
      onQueryChange(query)
    }
  }, [query, onQueryChange])

  // Expose methods via ref
  useImperativeHandle(ref, () => ({
    getValue: () => query,
    setValue: (value) => setQuery(value),
    focus: () => textareaRef.current?.focus(),
    clear: () => setQuery(''),
    setQuery: (text) => setQuery(text),
    getQuery: () => query,
    submit: () => handleSubmit({ preventDefault: () => {} }),
  }))

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!query.trim() || disabled || isLoading) return

    setIsLoading(true)
    try {
      await onSend(query)
      setQuery('')
    } catch (error) {
      console.error('Error sending query:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    // Regular Enter (without Shift) or Ctrl/Cmd+Enter to send
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
      return
    }

    // Up Arrow to recall last query when input is empty
    if (e.key === 'ArrowUp' && query.trim() === '' && lastQuery) {
      e.preventDefault()
      setQuery(lastQuery)
      return
    }
  }

  // Detect Mac for tooltip
  const isMac = typeof navigator !== 'undefined' && navigator.platform.toUpperCase().indexOf('MAC') >= 0
  const modKey = isMac ? '⌘' : 'Ctrl'

  return (
    <form onSubmit={handleSubmit} className="flex items-end space-x-3">
      <div className="flex-1">
        <textarea
          ref={textareaRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled || isLoading}
          rows={1}
          className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none resize-none text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 disabled:opacity-50 disabled:cursor-not-allowed"
          style={{
            minHeight: '48px',
            maxHeight: '120px',
          }}
          onInput={(e) => {
            e.target.style.height = 'auto'
            e.target.style.height = e.target.scrollHeight + 'px'
          }}
          aria-describedby="query-input-help"
        />
        <p id="query-input-help" className="mt-1 text-xs text-gray-500 dark:text-gray-400">
          Press Enter to send • {modKey}+Enter also works • ↑ for last query
        </p>
      </div>
      <button
        type="submit"
        disabled={disabled || isLoading || !query.trim()}
        className="group relative flex-shrink-0 p-3 bg-primary-500 hover:bg-primary-600 disabled:bg-gray-300 dark:disabled:bg-gray-700 text-white rounded-lg transition-colors disabled:cursor-not-allowed shadow-sm hover:shadow-md"
        aria-label="Send query"
        title={`Send query (${modKey}+Enter)`}
      >
        {isLoading ? (
          <Loader2 className="w-5 h-5 animate-spin" />
        ) : (
          <Send className="w-5 h-5" />
        )}
      </button>
    </form>
  )
})

export default QueryInput
