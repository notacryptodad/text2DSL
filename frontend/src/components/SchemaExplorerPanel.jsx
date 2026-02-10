import { useState, useEffect, useMemo } from 'react'
import {
  ChevronRight,
  ChevronDown,
  Table2,
  Hash,
  Type,
  Calendar,
  ToggleLeft,
  Search,
  X,
  PanelLeftClose,
  Loader2,
  Database,
} from 'lucide-react'
import { useWorkspace } from '../contexts/WorkspaceContext'

const DATA_TYPE_ICONS = {
  integer: Hash,
  bigint: Hash,
  smallint: Hash,
  numeric: Hash,
  decimal: Hash,
  real: Hash,
  'double precision': Hash,
  varchar: Type,
  char: Type,
  text: Type,
  string: Type,
  date: Calendar,
  timestamp: Calendar,
  time: Calendar,
  boolean: ToggleLeft,
  default: Type,
  objectid: Type,
  datetime: Calendar,
  array: Type,
  object: Type,
}

function getDataTypeIcon(dataType) {
  if (!dataType) return DATA_TYPE_ICONS.default
  const type = dataType.toLowerCase()
  for (const [key, Icon] of Object.entries(DATA_TYPE_ICONS)) {
    if (type.includes(key)) return Icon
  }
  return DATA_TYPE_ICONS.default
}

function SchemaExplorerPanel({ isOpen, onClose, onInsertText, providerId }) {
  const { currentWorkspace } = useWorkspace()
  const [schema, setSchema] = useState([])
  const [annotations, setAnnotations] = useState({})
  const [expandedTables, setExpandedTables] = useState(new Set())
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Fetch schema and annotations when provider changes
  useEffect(() => {
    if (!providerId || !currentWorkspace || !isOpen) return
    
    const fetchData = async () => {
      setLoading(true)
      setError(null)
      
      try {
        const token = localStorage.getItem('access_token')
        if (!token) {
          setError('Please log in to view schema')
          return
        }

        // Fetch schema
        const schemaRes = await fetch(
          `/api/v1/workspaces/${currentWorkspace.id}/providers/${providerId}/schema`,
          { headers: { Authorization: `Bearer ${token}` } }
        )
        
        if (!schemaRes.ok) {
          throw new Error('Failed to fetch schema')
        }
        
        const schemaData = await schemaRes.json()
        setSchema(schemaData.tables || schemaData || [])

        // Fetch annotations
        try {
          const annotationsRes = await fetch(
            `/api/v1/workspaces/${currentWorkspace.id}/providers/${providerId}/annotations`,
            { headers: { Authorization: `Bearer ${token}` } }
          )
          
          if (annotationsRes.ok) {
            const annotationsData = await annotationsRes.json()
            // Convert array to object keyed by table name
            const annotationsMap = {}
            if (Array.isArray(annotationsData)) {
              annotationsData.forEach(ann => {
                annotationsMap[ann.table_name] = ann
              })
            } else {
              Object.assign(annotationsMap, annotationsData)
            }
            setAnnotations(annotationsMap)
          }
        } catch (annErr) {
          console.warn('Could not fetch annotations:', annErr)
        }
      } catch (err) {
        console.error('Error fetching schema:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [providerId, currentWorkspace, isOpen])

  // Process schema items
  const schemaItems = useMemo(() => {
    return schema.map(item => ({
      name: item.table_name || item.name,
      columns: item.columns || [],
      rowCount: item.row_count || item.document_count || 0,
      type: item.document_count ? 'mongodb' : 'sql',
    }))
  }, [schema])

  // Filter schema based on search query
  const filteredItems = useMemo(() => {
    if (!searchQuery.trim()) return schemaItems
    
    const query = searchQuery.toLowerCase()
    return schemaItems.map(item => {
      const tableMatches = item.name.toLowerCase().includes(query)
      const matchingColumns = item.columns.filter(col => {
        const colName = (col.column_name || col.name || col).toLowerCase()
        return colName.includes(query)
      })
      
      // Include table if name matches or has matching columns
      if (tableMatches || matchingColumns.length > 0) {
        return {
          ...item,
          columns: tableMatches ? item.columns : matchingColumns,
          highlighted: !tableMatches && matchingColumns.length > 0,
        }
      }
      return null
    }).filter(Boolean)
  }, [schemaItems, searchQuery])

  // Auto-expand tables with matching columns when searching
  useEffect(() => {
    if (searchQuery.trim()) {
      const tablesToExpand = new Set()
      filteredItems.forEach(item => {
        if (item.highlighted) {
          tablesToExpand.add(item.name)
        }
      })
      if (tablesToExpand.size > 0) {
        setExpandedTables(prev => new Set([...prev, ...tablesToExpand]))
      }
    }
  }, [filteredItems, searchQuery])

  const toggleTable = (tableName) => {
    setExpandedTables(prev => {
      const newSet = new Set(prev)
      if (newSet.has(tableName)) {
        newSet.delete(tableName)
      } else {
        newSet.add(tableName)
      }
      return newSet
    })
  }

  const handleItemClick = (text) => {
    if (onInsertText) {
      onInsertText(text)
    }
  }

  const getColumnAnnotation = (tableName, columnName) => {
    const tableAnn = annotations[tableName]
    if (!tableAnn?.columns) return null
    const col = tableAnn.columns.find(c => c.name === columnName)
    return col?.description || null
  }

  const isPrimaryKey = (column) => {
    return column.is_primary_key || column.primary_key || column.key === 'PRI'
  }

  const isForeignKey = (column) => {
    return column.is_foreign_key || column.foreign_key || column.key === 'MUL'
  }

  if (!isOpen) return null

  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 w-72 flex-shrink-0">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center space-x-2">
          <Database className="w-5 h-5 text-primary-500" />
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
            Schema Explorer
          </h2>
        </div>
        <button
          onClick={onClose}
          className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
          aria-label="Close schema explorer"
          title="Close (⌘/)"
        >
          <PanelLeftClose className="w-4 h-4 text-gray-500 dark:text-gray-400" />
        </button>
      </div>

      {/* Search */}
      <div className="p-2 border-b border-gray-200 dark:border-gray-700">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search tables or columns..."
            className="w-full pl-8 pr-8 py-1.5 text-sm bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none text-gray-900 dark:text-white placeholder-gray-400"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
            >
              <X className="w-3 h-3 text-gray-400" />
            </button>
          )}
        </div>
      </div>

      {/* Schema Tree */}
      <div className="flex-1 overflow-y-auto p-2">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 text-primary-500 animate-spin" />
          </div>
        ) : error ? (
          <div className="text-center py-8 px-4">
            <p className="text-sm text-red-500">{error}</p>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="text-center py-8 px-4">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {searchQuery ? 'No matching tables or columns' : 'No schema available'}
            </p>
          </div>
        ) : (
          <div className="space-y-1">
            {filteredItems.map((item) => {
              const isExpanded = expandedTables.has(item.name)
              const columns = item.columns

              return (
                <div key={item.name} className="rounded overflow-hidden">
                  {/* Table Row */}
                  <div
                    className="flex items-center px-2 py-1.5 hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded cursor-pointer group"
                  >
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        toggleTable(item.name)
                      }}
                      className="flex-shrink-0 p-0.5 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
                    >
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                      )}
                    </button>
                    <Table2 className="w-4 h-4 text-primary-500 mx-1.5 flex-shrink-0" />
                    <button
                      onClick={() => handleItemClick(item.name)}
                      className="flex-1 text-left text-sm font-medium text-gray-800 dark:text-gray-200 truncate hover:text-primary-600 dark:hover:text-primary-400"
                      title={`Click to insert "${item.name}"`}
                    >
                      {item.name}
                    </button>
                    <span className="text-xs text-gray-400 dark:text-gray-500 ml-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      click to insert
                    </span>
                  </div>

                  {/* Columns */}
                  {isExpanded && columns.length > 0 && (
                    <div className="ml-5 border-l border-gray-200 dark:border-gray-700">
                      {columns.map((col) => {
                        const colName = col.column_name || col.name || col
                        const dataType = col.data_type || col.type || 'string'
                        const Icon = getDataTypeIcon(dataType)
                        const annotation = getColumnAnnotation(item.name, colName)
                        const isPK = isPrimaryKey(col)
                        const isFK = isForeignKey(col)

                        return (
                          <button
                            key={colName}
                            onClick={() => handleItemClick(colName)}
                            className="w-full flex items-center px-2 py-1 hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded-r text-left group"
                            title={annotation ? `${colName}: ${annotation}` : `Click to insert "${colName}"`}
                          >
                            <Icon className="w-3 h-3 text-gray-400 dark:text-gray-500 flex-shrink-0 mr-1.5" />
                            <span className="flex-1 text-sm text-gray-700 dark:text-gray-300 truncate hover:text-primary-600 dark:hover:text-primary-400">
                              {colName}
                            </span>
                            {isPK && (
                              <span className="ml-1 flex-shrink-0" title="Primary Key">
                                🔑
                              </span>
                            )}
                            {isFK && (
                              <span className="ml-1 flex-shrink-0" title="Foreign Key">
                                🔗
                              </span>
                            )}
                            {annotation && (
                              <span className="ml-1 text-xs text-gray-400 dark:text-gray-500 truncate max-w-[80px] italic">
                                {annotation}
                              </span>
                            )}
                          </button>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Footer with hint */}
      <div className="p-2 border-t border-gray-200 dark:border-gray-700">
        <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
          Click item to insert • <kbd className="px-1 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs">⌘/</kbd> to toggle
        </p>
      </div>
    </div>
  )
}

export default SchemaExplorerPanel
