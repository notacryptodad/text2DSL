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
  Database,
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

function NestedColumnItem({ column, tableName, depth, expandedItems, onToggle, onColumnSelect, annotations }) {
  const colName = column.column_name || column.name
  const dataType = column.data_type || column.type || 'string'
  const Icon = getDataTypeIcon(dataType)
  const isObject = dataType.toLowerCase() === 'object'
  const isExpanded = expandedItems.has(`${tableName}.${colName}`)
  const hasNested = column.nested && column.nested.length > 0
  const fullName = depth === 0 ? colName : `${tableName}.${colName}`
  const isColAnnotated = annotations[tableName]?.columns?.find(c => c.name === fullName)?.description

  const paddingLeft = `${depth * 24 + 32}px`

  return (
    <>
      <div
        onClick={() => {
          if (isObject && hasNested) {
            onToggle(`${tableName}.${colName}`)
          }
          onColumnSelect && onColumnSelect(tableName, fullName)
        }}
        className="flex items-center justify-between px-4 py-1.5 hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors cursor-pointer"
      >
        <div className="flex items-center space-x-2 flex-1 min-w-0">
          {isObject && hasNested ? (
            <button
              onClick={(e) => {
                e.stopPropagation()
                onToggle(`${tableName}.${colName}`)
              }}
              className="flex-shrink-0 p-0.5 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
            >
              {isExpanded ? (
                <ChevronDown className="w-3 h-3 text-gray-500" />
              ) : (
                <ChevronRight className="w-3 h-3 text-gray-500" />
              )}
            </button>
          ) : (
            <span className="w-4 flex-shrink-0" />
          )}
          <Icon className="w-3 h-3 text-gray-400 dark:text-gray-500 flex-shrink-0" />
          <span className="text-sm text-gray-700 dark:text-gray-300 truncate">
            {colName}
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
      {isExpanded && hasNested && (
        <div className="bg-gray-50 dark:bg-gray-800/30">
          {column.nested.map((nestedCol) => (
            <NestedColumnItem
              key={nestedCol.name}
              column={nestedCol}
              tableName={fullName}
              depth={depth + 1}
              expandedItems={expandedItems}
              onToggle={onToggle}
              onColumnSelect={onColumnSelect}
              annotations={annotations}
            />
          ))}
        </div>
      )}
    </>
  )
}

function SchemaTree({ schema = [], onTableSelect, onColumnSelect, selectedTable, annotations = {} }) {
  const [expandedItems, setExpandedItems] = useState(new Set())

  const toggleItem = (itemName) => {
    const newExpanded = new Set(expandedItems)
    if (newExpanded.has(itemName)) {
      newExpanded.delete(itemName)
    } else {
      newExpanded.add(itemName)
    }
    setExpandedItems(newExpanded)
  }

  const isItemAnnotated = (itemName) => {
    return annotations[itemName]?.description || annotations[itemName]?.columns?.some(c => c.description)
  }

  const orphanedAnnotations = Object.entries(annotations)
    .filter(([tableName, ann]) => ann._orphaned)
    .map(([tableName]) => tableName)

  const schemaItems = schema.map(item => ({
    name: item.table_name || item.name,
    columns: item.columns || [],
    rowCount: item.row_count || item.document_count || 0,
    type: item.document_count ? 'mongodb' : 'sql',
  }))

  const getTotalColumns = (columns) => {
    let count = columns.length
    for (const col of columns) {
      if (col.nested) {
        count += getTotalColumns(col.nested)
      }
    }
    return count
  }

  if (schemaItems.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
        No schema loaded. Please select a workspace and connection.
      </div>
    )
  }

  return (
    <div className="space-y-1">
      {schemaItems.map((item) => {
        const itemName = item.name
        const isExpanded = expandedItems.has(itemName)
        const isSelected = selectedTable === itemName
        const isAnnotated = isItemAnnotated(itemName)
        const columns = item.columns
        const isMongoDB = item.type === 'mongodb'
        const totalCols = getTotalColumns(columns)

        return (
          <div
            key={itemName}
            className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden"
          >
            <div
              onClick={() => {
                onTableSelect(itemName)
              }}
              className={`w-full flex items-center justify-between p-3 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors cursor-pointer ${
                isSelected ? 'bg-primary-50 dark:bg-primary-900/20' : ''
              }`}
            >
              <div className="flex items-center space-x-2 flex-1 min-w-0">
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    toggleItem(itemName)
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
                  {itemName}
                </span>
              </div>
              <div className="flex items-center space-x-2 flex-shrink-0 ml-2">
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {isMongoDB
                    ? `${item.rowCount} docs`
                    : `${totalCols} cols`}
                </span>
                {isAnnotated ? (
                  <CheckCircle className="w-4 h-4 text-green-500" title="Annotated" />
                ) : (
                  <Circle className="w-4 h-4 text-gray-300 dark:text-gray-600" title="Not annotated" />
                )}
              </div>
            </div>

            {isExpanded && columns.length > 0 && (
              <div className="bg-gray-50 dark:bg-gray-800/50 border-t border-gray-200 dark:border-gray-700">
                {columns.map((col) => (
                  <NestedColumnItem
                    key={col.name}
                    column={col}
                    tableName={itemName}
                    depth={0}
                    expandedItems={expandedItems}
                    onToggle={toggleItem}
                    onColumnSelect={onColumnSelect}
                    annotations={annotations}
                  />
                ))}
              </div>
            )}
          </div>
        )
      })}

      {orphanedAnnotations.length > 0 && (
        <div className="mt-4 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
          <p className="text-xs font-semibold text-amber-700 dark:text-amber-300 mb-2">
            Orphaned Annotations ({orphanedAnnotations.length})
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
