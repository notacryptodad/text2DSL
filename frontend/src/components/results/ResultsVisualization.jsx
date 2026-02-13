import { useMemo, useState } from 'react'
import { Table, BarChart3, ChevronDown, ChevronUp } from 'lucide-react'
import ResultsTable from './ResultsTable'
import ResultsChart from './ResultsChart'
import ResultsExport from './ResultsExport'

function ResultsVisualization({ data, rowCount, executionTimeMs }) {
  const [viewMode, setViewMode] = useState('table')
  const [showChart, setShowChart] = useState(false)

  // Detect all columns from data
  const columns = useMemo(() => {
    if (!data || data.length === 0) return []
    const keys = new Set()
    data.forEach((row) => Object.keys(row).forEach((k) => keys.add(k)))
    return Array.from(keys)
  }, [data])

  // Detect numeric columns for charts
  const numericColumns = useMemo(() => {
    if (!data || data.length === 0 || columns.length === 0) return []

    return columns.filter((col) => {
      // Sample first 10 rows to determine if column is numeric
      const sample = data.slice(0, Math.min(10, data.length))
      const numericCount = sample.filter((row) => {
        const val = row[col]
        return typeof val === 'number' && !isNaN(val)
      }).length

      // Consider column numeric if >50% of sample values are numbers
      return numericCount / sample.length > 0.5
    })
  }, [data, columns])

  // Handle empty results
  if (!data || data.length === 0) {
    return (
      <div className="p-6 text-center bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
        <p className="text-gray-600 dark:text-gray-400">
          Query returned no results
        </p>
      </div>
    )
  }

  // Show warning for large datasets
  const showLargeDatasetWarning = data.length > 1000

  return (
    <div className="space-y-3">
      {/* Header with metadata and controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
            <BarChart3 className="w-5 h-5" />
            <span>Query Results</span>
          </h3>
          <div className="flex items-center space-x-3 text-sm text-gray-600 dark:text-gray-400">
            <span className="font-medium">{rowCount.toLocaleString()} rows</span>
            <span className="text-gray-400 dark:text-gray-500">•</span>
            <span>{executionTimeMs}ms</span>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {/* View mode toggle */}
          <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
            <button
              onClick={() => setViewMode('table')}
              className={`flex items-center space-x-1 px-3 py-1 rounded transition-colors ${
                viewMode === 'table'
                  ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              }`}
            >
              <Table className="w-4 h-4" />
              <span className="text-sm font-medium">Table</span>
            </button>
            <button
              onClick={() => setShowChart(!showChart)}
              disabled={numericColumns.length === 0}
              className={`flex items-center space-x-1 px-3 py-1 rounded transition-colors ${
                showChart
                  ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
              } ${
                numericColumns.length === 0
                  ? 'opacity-50 cursor-not-allowed'
                  : ''
              }`}
              title={
                numericColumns.length === 0
                  ? 'No numeric columns available for charting'
                  : 'Toggle chart view'
              }
            >
              <BarChart3 className="w-4 h-4" />
              <span className="text-sm font-medium">Chart</span>
            </button>
          </div>

          {/* Export button */}
          <ResultsExport
            data={data}
            columns={columns}
            filename={`query_results_${Date.now()}`}
          />
        </div>
      </div>

      {/* Large dataset warning */}
      {showLargeDatasetWarning && (
        <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
          <p className="text-sm text-yellow-800 dark:text-yellow-300">
            Large dataset ({data.length.toLocaleString()} rows). Consider using pagination or exporting for analysis.
          </p>
        </div>
      )}

      {/* Wide table warning */}
      {columns.length > 20 && (
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <p className="text-sm text-blue-800 dark:text-blue-300">
            Wide table ({columns.length} columns). Use horizontal scroll to view all columns.
          </p>
        </div>
      )}

      {/* Chart section (collapsible) */}
      {showChart && numericColumns.length > 0 && (
        <div className="space-y-2">
          <button
            onClick={() => setShowChart(false)}
            className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
          >
            <ChevronUp className="w-4 h-4" />
            <span>Hide Chart</span>
          </button>
          <ResultsChart
            data={data}
            numericColumns={numericColumns}
            maxRows={50}
          />
        </div>
      )}

      {/* Table section */}
      <ResultsTable data={data} columns={columns} />
    </div>
  )
}

export default ResultsVisualization
