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

function SchemaTree({ schema, onTableSelect, selectedTable, annotations = {} }) {
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
        const isExpanded = expandedTables.has(table.table_name)
        const isSelected = selectedTable === table.table_name
        const isAnnotated = isTableAnnotated(table.table_name)

        return (
          <div key={table.table_name} className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
            <button
              onClick={() => {
                toggleTable(table.table_name)
                onTableSelect(table.table_name)
              }}
              className={`w-full flex items-center justify-between p-3 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors ${
                isSelected ? 'bg-primary-50 dark:bg-primary-900/20' : ''
              }`}
            >
              <div className="flex items-center space-x-2 flex-1 min-w-0">
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    toggleTable(table.table_name)
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
                  {table.table_name}
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
            </button>

            {isExpanded && table.columns && (
              <div className="bg-gray-50 dark:bg-gray-800/50 border-t border-gray-200 dark:border-gray-700">
                {table.columns.map((column) => {
                  const Icon = getDataTypeIcon(column.data_type)
                  const isColAnnotated = isColumnAnnotated(table.table_name, column.column_name)

                  return (
                    <div
                      key={column.column_name}
                      className="flex items-center justify-between px-8 py-2 hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors"
                    >
                      <div className="flex items-center space-x-2 flex-1 min-w-0">
                        <Icon className="w-3 h-3 text-gray-400 dark:text-gray-500 flex-shrink-0" />
                        <span className="text-sm text-gray-700 dark:text-gray-300 truncate">
                          {column.column_name}
                        </span>
                        <span className="text-xs text-gray-500 dark:text-gray-400 font-mono flex-shrink-0">
                          {column.data_type}
                        </span>
                        {column.is_nullable === false && (
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
    </div>
  )
}

export default SchemaTree
