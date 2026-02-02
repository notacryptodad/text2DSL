import { useState } from 'react'
import {
  ChevronRight,
  ChevronDown,
  Table2,
  Hash,
  Type,
  Calendar,
  ToggleLeft,
  CheckCircle,
  Circle,
} from 'lucide-react'

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
}

function SchemaTree({ schema, onTableSelect, onColumnSelect, selectedTable, annotations = {} }) {
  const [expandedTables, setExpandedTables] = useState(new Set())

  const toggleTable = (tableName) => {
    const newExpanded = new Set(expandedTables)
    if (newExpanded.has(tableName)) {
      newExpanded.delete(tableName)
    } else {
      newExpanded.add(tableName)
    }
    setExpandedTables(newExpanded)
  }

  const getDataTypeIcon = (dataType) => {
    if (!dataType) return DATA_TYPE_ICONS.default
    const type = dataType.toLowerCase()
    for (const [key, Icon] of Object.entries(DATA_TYPE_ICONS)) {
      if (type.includes(key)) return Icon
    }
    return DATA_TYPE_ICONS.default
  }

  const isTableAnnotated = (tableName) => {
    return annotations[tableName]?.description || annotations[tableName]?.columns?.some(c => c.description)
  }

  const isColumnAnnotated = (tableName, columnName) => {
    return annotations[tableName]?.columns?.find(c => c.name === columnName)?.description
  }

  // Get orphaned annotations (tables that no longer exist in schema)
  const orphanedAnnotations = Object.entries(annotations)
    .filter(([tableName, ann]) => ann._orphaned)
    .map(([tableName]) => tableName)

  if (!schema || schema.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        No schema loaded. Please select a workspace and connection.
      </div>
    )
  }

  return (
    <div className="space-y-1">
      {schema.map((table) => {
        // Support both API formats: table_name (old) and name (new)
        const tableName = table.table_name || table.name
        const isExpanded = expandedTables.has(tableName)
        const isSelected = selectedTable === tableName
        const isAnnotated = isTableAnnotated(tableName)

        return (
          <div key={tableName} className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
            <div
              onClick={() => {
                onTableSelect(tableName)
              }}
              className={`w-full flex items-center justify-between p-3 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors cursor-pointer ${
                isSelected ? 'bg-primary-50 dark:bg-primary-900/20' : ''
              }`}
            >
              <div className="flex items-center space-x-2 flex-1 min-w-0">
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    toggleTable(tableName)
                  }}
                  className="flex-shrink-0 p-0.5 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
                >
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                  )}
                </button>
                <Table2 className="w-4 h-4 text-primary-500 flex-shrink-0" />
                <span className="font-semibold text-gray-900 dark:text-white truncate text-sm">
                  {tableName}
                </span>
              </div>
              <div className="flex items-center space-x-2 flex-shrink-0 ml-2">
                <span className="text-xs text-gray-400 dark:text-gray-500">
                  {table.columns?.length || 0} cols
                </span>
                {isAnnotated ? (
                  <CheckCircle className="w-4 h-4 text-green-500" title="Annotated" />
                ) : (
                  <Circle className="w-4 h-4 text-gray-300 dark:text-gray-600" title="Not annotated" />
                )}
              </div>
            </div>

            {isExpanded && table.columns && (
              <div className="bg-gray-50 dark:bg-gray-800/50 border-t border-gray-200 dark:border-gray-700">
                {table.columns.map((column) => {
                  // Support both API formats: data_type (old) and type (new), column_name (old) and name (new)
                  const columnName = column.column_name || column.name
                  const dataType = column.data_type || column.type
                  const Icon = getDataTypeIcon(dataType)
                  const isColAnnotated = isColumnAnnotated(tableName, columnName)

                  return (
                    <div
                      key={columnName}
                      onClick={() => onColumnSelect && onColumnSelect(tableName, columnName)}
                      className="flex items-center justify-between px-8 py-2 hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors cursor-pointer"
                    >
                      <div className="flex items-center space-x-2 flex-1 min-w-0">
                        <Icon className="w-3 h-3 text-gray-400 dark:text-gray-500 flex-shrink-0" />
                        <span className="text-sm text-gray-700 dark:text-gray-300 truncate">
                          {columnName}
                        </span>
                        <span className="text-xs text-gray-500 dark:text-gray-400 font-mono flex-shrink-0">
                          {dataType}
                        </span>
                        {(column.is_nullable === false || column.nullable === false) && (
                          <span className="text-xs text-red-600 dark:text-red-400 flex-shrink-0">
                            NOT NULL
                          </span>
                        )}
                      </div>
                      {isColAnnotated && (
                        <CheckCircle className="w-3 h-3 text-green-500 flex-shrink-0 ml-2" />
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )
      })}

      {/* Orphaned Annotations */}
      {orphanedAnnotations.length > 0 && (
        <div className="mt-4 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
          <p className="text-xs font-semibold text-amber-700 dark:text-amber-300 mb-2">
            ⚠️ Orphaned Annotations ({orphanedAnnotations.length})
          </p>
          <p className="text-xs text-amber-600 dark:text-amber-400 mb-2">
            These tables no longer exist in the schema:
          </p>
          <div className="flex flex-wrap gap-1">
            {orphanedAnnotations.map(tableName => (
              <span
                key={tableName}
                className="px-2 py-0.5 text-xs bg-amber-100 dark:bg-amber-800 text-amber-700 dark:text-amber-200 rounded"
              >
                {tableName}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default SchemaTree
