import { useState, useEffect, useCallback } from 'react'
import { Eye, Loader2, Sparkles } from 'lucide-react'

/**
 * QueryPreview - Live SQL preview as user types
 * Shows pattern-matched SQL preview with debounced updates
 */
function QueryPreview({ query, onUseQuery, disabled }) {
  const [preview, setPreview] = useState(null)
  const [isGenerating, setIsGenerating] = useState(false)

  // Pattern matching for common SQL queries
  const generatePreview = useCallback((input) => {
    if (!input || input.trim().length < 3) {
      return null
    }

    const text = input.toLowerCase().trim()
    let sql = null
    let confidence = 'low'

    // Common patterns for SELECT queries
    if (text.match(/^(show|list|get|find|display|what are|give me)\s+(all\s+)?(the\s+)?/i)) {
      const tableMatch = text.match(/(?:show|list|get|find|display|what are|give me)\s+(?:all\s+)?(?:the\s+)?(\w+)/i)
      if (tableMatch) {
        const table = tableMatch[1]
        const tableName = table.endsWith('s') ? table : `${table}s`
        sql = `SELECT * FROM ${tableName};`
        confidence = 'medium'
      }
    }

    // Count queries
    if (text.match(/^(how many|count|total|number of)\s+/i)) {
      const tableMatch = text.match(/(?:how many|count|total|number of)\s+(\w+)/i)
      if (tableMatch) {
        const table = tableMatch[1]
        const tableName = table.endsWith('s') ? table : `${table}s`
        sql = `SELECT COUNT(*) FROM ${tableName};`
        confidence = 'medium'
      }
    }

    // Filter queries with WHERE
    if (text.match(/where|with|that have|having|whose/i)) {
      const parts = text.match(/(?:show|list|get|find)\s+(?:all\s+)?(\w+)\s+(?:where|with|that have|having|whose)\s+(\w+)\s*(?:=|is|equals?|:|>|<|>=|<=)\s*['"]?(\w+)['"]?/i)
      if (parts) {
        const [, table, column, value] = parts
        const tableName = table.endsWith('s') ? table : `${table}s`
        sql = `SELECT * FROM ${tableName}\nWHERE ${column} = '${value}';`
        confidence = 'medium'
      }
    }

    // Order by queries
    if (text.match(/(?:sort|order)\s+(?:by|on)\s+/i)) {
      const parts = text.match(/(?:show|list|get|find)\s+(?:all\s+)?(\w+)\s+(?:sort|order)(?:ed)?\s+(?:by|on)\s+(\w+)/i)
      if (parts) {
        const [, table, column] = parts
        const tableName = table.endsWith('s') ? table : `${table}s`
        const desc = text.includes('desc') || text.includes('highest') || text.includes('latest') || text.includes('newest')
        sql = `SELECT * FROM ${tableName}\nORDER BY ${column}${desc ? ' DESC' : ''};`
        confidence = 'medium'
      }
    }

    // Limit queries
    if (text.match(/(?:first|top|last|latest|recent)\s+(\d+)/i)) {
      const limitMatch = text.match(/(?:first|top|last|latest|recent)\s+(\d+)\s+(\w+)/i)
      if (limitMatch) {
        const [, limit, table] = limitMatch
        const tableName = table.endsWith('s') ? table : `${table}s`
        const isLatest = text.match(/last|latest|recent/i)
        sql = `SELECT * FROM ${tableName}${isLatest ? '\nORDER BY created_at DESC' : ''}\nLIMIT ${limit};`
        confidence = 'medium'
      }
    }

    // Specific column selection
    if (text.match(/(?:show|get|list)\s+(?:only\s+)?(?:the\s+)?(\w+(?:\s*,\s*\w+)*)\s+(?:from|of|in)\s+(\w+)/i)) {
      const parts = text.match(/(?:show|get|list)\s+(?:only\s+)?(?:the\s+)?(\w+(?:\s*,\s*\w+)*)\s+(?:from|of|in)\s+(\w+)/i)
      if (parts) {
        const [, columns, table] = parts
        const tableName = table.endsWith('s') ? table : `${table}s`
        const cleanColumns = columns.replace(/\s+/g, ', ')
        sql = `SELECT ${cleanColumns} FROM ${tableName};`
        confidence = 'medium'
      }
    }

    // Join hints - lower confidence
    if (text.match(/(?:with|and)\s+(?:their|its|the)\s+(\w+)/i) && sql) {
      confidence = 'low'
    }

    // Aggregate queries
    if (text.match(/(?:average|avg|sum|min|max|total)\s+(?:of\s+)?(\w+)\s+(?:from|in|of)\s+(\w+)/i)) {
      const parts = text.match(/(?:average|avg|sum|min|max|total)\s+(?:of\s+)?(\w+)\s+(?:from|in|of)\s+(\w+)/i)
      if (parts) {
        const [, column, table] = parts
        const tableName = table.endsWith('s') ? table : `${table}s`
        let func = 'SUM'
        if (text.match(/average|avg/i)) func = 'AVG'
        else if (text.match(/min/i)) func = 'MIN'
        else if (text.match(/max/i)) func = 'MAX'
        sql = `SELECT ${func}(${column}) FROM ${tableName};`
        confidence = 'medium'
      }
    }

    // Group by queries
    if (text.match(/(?:group|by|per|each)\s+(\w+)/i) && text.match(/count|total|sum|average/i)) {
      const groupMatch = text.match(/(?:per|each|by|group by)\s+(\w+)/i)
      const tableMatch = text.match(/(?:from|in|of)\s+(\w+)/i) || text.match(/(\w+)\s+(?:per|each|by)/i)
      if (groupMatch && tableMatch) {
        const groupCol = groupMatch[1]
        const table = tableMatch[1]
        const tableName = table.endsWith('s') ? table : `${table}s`
        sql = `SELECT ${groupCol}, COUNT(*) as count\nFROM ${tableName}\nGROUP BY ${groupCol};`
        confidence = 'medium'
      }
    }

    if (!sql) {
      return null
    }

    return { sql, confidence, isPreview: true }
  }, [])

  // Debounced preview generation
  useEffect(() => {
    if (!query || disabled) {
      setPreview(null)
      return
    }

    setIsGenerating(true)
    
    const timeoutId = setTimeout(() => {
      const result = generatePreview(query)
      setPreview(result)
      setIsGenerating(false)
    }, 350) // 350ms debounce

    return () => clearTimeout(timeoutId)
  }, [query, disabled, generatePreview])

  // Don't render if no query or too short
  if (!query || query.trim().length < 3) {
    return null
  }

  return (
    <div className="mt-3 rounded-lg border border-dashed border-gray-300 dark:border-gray-600 bg-gray-50/50 dark:bg-gray-800/50 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-gray-100/80 dark:bg-gray-700/50 border-b border-gray-200 dark:border-gray-600">
        <div className="flex items-center gap-2">
          {isGenerating ? (
            <Loader2 className="w-4 h-4 text-primary-500 animate-spin" />
          ) : (
            <Eye className="w-4 h-4 text-primary-500" />
          )}
          <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
            Live Preview
          </span>
          {preview && (
            <span className={`
              text-xs px-1.5 py-0.5 rounded-full
              ${preview.confidence === 'high' 
                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' 
                : preview.confidence === 'medium'
                ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'}
            `}>
              {preview.confidence === 'high' ? 'High confidence' : 
               preview.confidence === 'medium' ? 'Pattern match' : 'Best guess'}
            </span>
          )}
        </div>
        
        {preview && onUseQuery && (
          <button
            onClick={() => onUseQuery(preview.sql)}
            className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded transition-colors"
            title="Use this query"
          >
            <Sparkles className="w-3.5 h-3.5" />
            Use Query
          </button>
        )}
      </div>

      {/* Preview Content */}
      <div className="p-3">
        {isGenerating ? (
          <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
            <span>Generating preview...</span>
          </div>
        ) : preview ? (
          <div className="relative">
            <pre className="text-sm font-mono text-gray-700 dark:text-gray-300 whitespace-pre-wrap overflow-x-auto">
              {preview.sql}
            </pre>
            <div className="absolute top-0 right-0">
              <span className="text-xs text-gray-400 dark:text-gray-500 italic">
                preview
              </span>
            </div>
          </div>
        ) : (
          <div className="text-sm text-gray-500 dark:text-gray-400 italic">
            Keep typing to see a SQL preview...
          </div>
        )}
      </div>

      {/* Footer hint */}
      {preview && (
        <div className="px-3 py-1.5 bg-gray-100/50 dark:bg-gray-700/30 border-t border-gray-200 dark:border-gray-600">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            💡 This is a pattern-based preview. Press Enter to generate the final query with AI.
          </p>
        </div>
      )}
    </div>
  )
}

export default QueryPreview
