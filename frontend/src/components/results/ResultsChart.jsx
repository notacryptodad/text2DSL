import { useState, useMemo } from 'react'
import {
  BarChart,
  LineChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { BarChart3, LineChart as LineChartIcon } from 'lucide-react'

const CHART_COLORS = [
  '#3b82f6', // blue-500
  '#10b981', // green-500
  '#f59e0b', // amber-500
  '#ef4444', // red-500
  '#8b5cf6', // violet-500
  '#ec4899', // pink-500
  '#06b6d4', // cyan-500
  '#f97316', // orange-500
]

function ResultsChart({ data, numericColumns, maxRows = 50 }) {
  const [chartType, setChartType] = useState('bar')
  const [selectedColumns, setSelectedColumns] = useState([])

  // Initialize selected columns with first numeric column
  useMemo(() => {
    if (numericColumns.length > 0 && selectedColumns.length === 0) {
      setSelectedColumns([numericColumns[0]])
    }
  }, [numericColumns, selectedColumns.length])

  // Limit data for performance
  const chartData = useMemo(() => data.slice(0, maxRows), [data, maxRows])

  // Get first column as X-axis label (typically ID or name column)
  const xAxisKey = useMemo(() => {
    if (!data || data.length === 0) return null
    const firstRow = data[0]
    const keys = Object.keys(firstRow)
    return keys[0] || null
  }, [data])

  const toggleColumn = (col) => {
    setSelectedColumns((prev) => {
      if (prev.includes(col)) {
        return prev.filter((c) => c !== col)
      }
      return [...prev, col]
    })
  }

  if (!numericColumns || numericColumns.length === 0) {
    return (
      <div className="p-6 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
        <p className="text-center text-gray-600 dark:text-gray-400">
          No numeric data available for charting
        </p>
      </div>
    )
  }

  return (
    <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
      {/* Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
        {/* Column selection */}
        <div className="flex flex-wrap gap-2">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300 mr-2">
            Columns:
          </span>
          {numericColumns.map((col) => (
            <label
              key={col}
              className="flex items-center space-x-2 px-3 py-1 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
            >
              <input
                type="checkbox"
                checked={selectedColumns.includes(col)}
                onChange={() => toggleColumn(col)}
                className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 dark:border-gray-600 rounded"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                {col}
              </span>
            </label>
          ))}
        </div>

        {/* Chart type toggle */}
        <div className="flex space-x-2">
          <button
            onClick={() => setChartType('bar')}
            className={`flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors ${
              chartType === 'bar'
                ? 'bg-primary-500 text-white'
                : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600'
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            <span className="text-sm font-medium">Bar</span>
          </button>
          <button
            onClick={() => setChartType('line')}
            className={`flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors ${
              chartType === 'line'
                ? 'bg-primary-500 text-white'
                : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600'
            }`}
          >
            <LineChartIcon className="w-4 h-4" />
            <span className="text-sm font-medium">Line</span>
          </button>
        </div>
      </div>

      {/* Warning for large datasets */}
      {data.length > maxRows && (
        <div className="mb-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded text-sm text-yellow-800 dark:text-yellow-300">
          Showing first {maxRows} rows of {data.length} for performance
        </div>
      )}

      {/* Chart */}
      {selectedColumns.length === 0 ? (
        <div className="h-[300px] flex items-center justify-center text-gray-500 dark:text-gray-400">
          Select at least one column to display chart
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          {chartType === 'bar' ? (
            <BarChart data={chartData}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="currentColor"
                className="text-gray-300 dark:text-gray-600"
              />
              <XAxis
                dataKey={xAxisKey}
                stroke="currentColor"
                className="text-gray-600 dark:text-gray-400"
                tick={{ fill: 'currentColor' }}
                style={{ fontSize: '12px' }}
              />
              <YAxis
                stroke="currentColor"
                className="text-gray-600 dark:text-gray-400"
                tick={{ fill: 'currentColor' }}
                style={{ fontSize: '12px' }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgb(31, 41, 55)',
                  border: '1px solid rgb(75, 85, 99)',
                  borderRadius: '0.5rem',
                  color: 'rgb(243, 244, 246)',
                }}
              />
              <Legend
                wrapperStyle={{
                  fontSize: '12px',
                  color: 'rgb(107, 114, 128)',
                }}
              />
              {selectedColumns.map((col, i) => (
                <Bar
                  key={col}
                  dataKey={col}
                  fill={CHART_COLORS[i % CHART_COLORS.length]}
                />
              ))}
            </BarChart>
          ) : (
            <LineChart data={chartData}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="currentColor"
                className="text-gray-300 dark:text-gray-600"
              />
              <XAxis
                dataKey={xAxisKey}
                stroke="currentColor"
                className="text-gray-600 dark:text-gray-400"
                tick={{ fill: 'currentColor' }}
                style={{ fontSize: '12px' }}
              />
              <YAxis
                stroke="currentColor"
                className="text-gray-600 dark:text-gray-400"
                tick={{ fill: 'currentColor' }}
                style={{ fontSize: '12px' }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'rgb(31, 41, 55)',
                  border: '1px solid rgb(75, 85, 99)',
                  borderRadius: '0.5rem',
                  color: 'rgb(243, 244, 246)',
                }}
              />
              <Legend
                wrapperStyle={{
                  fontSize: '12px',
                  color: 'rgb(107, 114, 128)',
                }}
              />
              {selectedColumns.map((col, i) => (
                <Line
                  key={col}
                  type="monotone"
                  dataKey={col}
                  stroke={CHART_COLORS[i % CHART_COLORS.length]}
                  strokeWidth={2}
                  dot={{ fill: CHART_COLORS[i % CHART_COLORS.length] }}
                />
              ))}
            </LineChart>
          )}
        </ResponsiveContainer>
      )}
    </div>
  )
}

export default ResultsChart
