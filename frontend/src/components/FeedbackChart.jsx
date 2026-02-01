import { useMemo } from 'react'
import { TrendingUp, TrendingDown } from 'lucide-react'

function FeedbackChart({ data, type = 'bar', height = 200 }) {
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return { labels: [], values: [], maxValue: 0 }

    const labels = data.map((item) => item.label || item.date || item.category)
    const values = data.map((item) => item.value || item.count || 0)
    const maxValue = Math.max(...values, 1)

    return { labels, values, maxValue }
  }, [data])

  const { labels, values, maxValue } = chartData

  // Calculate trend
  const trend = useMemo(() => {
    if (labels.length === 0) return null
    if (values.length < 2) return null
    const recent = values.slice(-3).reduce((a, b) => a + b, 0)
    const previous = values.slice(-6, -3).reduce((a, b) => a + b, 0)
    if (previous === 0) return null
    const change = ((recent - previous) / previous) * 100
    return { change: change.toFixed(1), isPositive: change > 0 }
  }, [labels.length, values])

  if (labels.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
        No data available
      </div>
    )
  }

  if (type === 'line') {
    const points = values.map((value, index) => {
      const x = (index / (values.length - 1)) * 100
      const y = 100 - (value / maxValue) * 100
      return `${x},${y}`
    })

    return (
      <div className="relative">
        {trend && (
          <div className="absolute top-0 right-0 flex items-center space-x-1 text-xs">
            {trend.isPositive ? (
              <TrendingUp className="w-4 h-4 text-green-500" />
            ) : (
              <TrendingDown className="w-4 h-4 text-red-500" />
            )}
            <span
              className={
                trend.isPositive
                  ? 'text-green-600 dark:text-green-400'
                  : 'text-red-600 dark:text-red-400'
              }
            >
              {trend.isPositive ? '+' : ''}
              {trend.change}%
            </span>
          </div>
        )}
        <svg width="100%" height={height} viewBox="0 0 100 100" preserveAspectRatio="none">
          {/* Grid lines */}
          {[0, 25, 50, 75, 100].map((y) => (
            <line
              key={y}
              x1="0"
              y1={y}
              x2="100"
              y2={y}
              stroke="currentColor"
              className="text-gray-200 dark:text-gray-700"
              strokeWidth="0.5"
            />
          ))}

          {/* Area fill */}
          <polygon
            points={`0,100 ${points.join(' ')} 100,100`}
            fill="currentColor"
            className="text-primary-200 dark:text-primary-900/30"
          />

          {/* Line */}
          <polyline
            points={points.join(' ')}
            fill="none"
            stroke="currentColor"
            className="text-primary-500"
            strokeWidth="2"
          />

          {/* Points */}
          {points.split(' ').map((point, index) => {
            const [x, y] = point.split(',')
            return (
              <circle
                key={index}
                cx={x}
                cy={y}
                r="2"
                fill="currentColor"
                className="text-primary-500"
              />
            )
          })}
        </svg>

        {/* Labels */}
        <div className="flex justify-between mt-2 text-xs text-gray-600 dark:text-gray-400">
          {labels.map((label, index) => {
            if (labels.length > 10 && index % Math.ceil(labels.length / 10) !== 0) return null
            return (
              <span key={index} className="truncate">
                {label}
              </span>
            )
          })}
        </div>
      </div>
    )
  }

  // Bar chart (default)
  return (
    <div className="relative">
      <div className="flex items-end justify-between space-x-1" style={{ height: `${height}px` }}>
        {values.map((value, index) => {
          const percentage = (value / maxValue) * 100
          return (
            <div key={index} className="flex flex-col items-center flex-1 group">
              <div className="flex-1 flex items-end w-full">
                <div
                  className="w-full bg-primary-500 dark:bg-primary-600 rounded-t transition-all hover:bg-primary-600 dark:hover:bg-primary-500 relative group"
                  style={{ height: `${percentage}%`, minHeight: value > 0 ? '4px' : '0' }}
                >
                  {/* Tooltip */}
                  <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-gray-900 dark:bg-gray-700 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10">
                    {labels[index]}: {value}
                  </div>
                </div>
              </div>
              <div className="text-xs text-gray-600 dark:text-gray-400 mt-2 truncate max-w-full text-center">
                {labels.length > 10 && index % Math.ceil(labels.length / 10) !== 0
                  ? ''
                  : labels[index]}
              </div>
            </div>
          )
        })}
      </div>

      {/* Y-axis labels */}
      <div className="absolute left-0 top-0 h-full flex flex-col justify-between text-xs text-gray-600 dark:text-gray-400 -ml-8">
        <span>{maxValue}</span>
        <span>{Math.round(maxValue / 2)}</span>
        <span>0</span>
      </div>
    </div>
  )
}

export default FeedbackChart
