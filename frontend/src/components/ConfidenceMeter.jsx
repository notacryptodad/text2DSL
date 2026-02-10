import { useState } from 'react'
import { Info, TrendingUp, TrendingDown, Minus } from 'lucide-react'

/**
 * ConfidenceMeter - Visual gauge showing query confidence with history tracking
 * 
 * Color coding:
 * - Red (<0.7): Low confidence - query may need refinement
 * - Yellow (0.7-0.85): Medium confidence - query is reasonable but could improve
 * - Green (>0.85): High confidence - query meets threshold
 * 
 * The 0.85 threshold is significant because it represents the minimum
 * confidence level for auto-execution without user confirmation.
 */
function ConfidenceMeter({ confidence, history = [], showHistory = true }) {
  const [showTooltip, setShowTooltip] = useState(false)

  if (confidence === undefined || confidence === null) return null

  const percentage = Math.round(confidence * 100)
  const thresholdPercentage = 85

  // Get color based on confidence level
  const getColor = (conf) => {
    if (conf >= 0.85) return { bg: 'bg-green-500', text: 'text-green-600 dark:text-green-400', gradient: 'from-green-400 to-green-600' }
    if (conf >= 0.7) return { bg: 'bg-yellow-500', text: 'text-yellow-600 dark:text-yellow-400', gradient: 'from-yellow-400 to-yellow-600' }
    return { bg: 'bg-red-500', text: 'text-red-600 dark:text-red-400', gradient: 'from-red-400 to-red-600' }
  }

  const colors = getColor(confidence)

  // Get confidence label
  const getConfidenceLabel = (conf) => {
    if (conf >= 0.85) return 'High'
    if (conf >= 0.7) return 'Medium'
    return 'Low'
  }

  // Calculate trend from history
  const getTrend = () => {
    if (history.length < 2) return null
    const lastConf = history[history.length - 1]
    const prevConf = history[history.length - 2]
    const diff = lastConf - prevConf
    if (diff > 0.05) return 'up'
    if (diff < -0.05) return 'down'
    return 'stable'
  }

  const trend = getTrend()

  return (
    <div className="mb-3">
      {/* Header with confidence value and info button */}
      <div className="flex items-center justify-between text-sm mb-2">
        <div className="flex items-center space-x-2">
          <span className="text-gray-600 dark:text-gray-400 font-medium">
            Confidence
          </span>
          {/* Info button with tooltip */}
          <div className="relative">
            <button
              onMouseEnter={() => setShowTooltip(true)}
              onMouseLeave={() => setShowTooltip(false)}
              onClick={() => setShowTooltip(!showTooltip)}
              className="p-0.5 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors"
              aria-label="Confidence information"
            >
              <Info className="w-3.5 h-3.5 text-gray-400 dark:text-gray-500" />
            </button>
            
            {/* Tooltip */}
            {showTooltip && (
              <div className="absolute z-50 bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-72 p-3 bg-gray-900 dark:bg-gray-700 text-white text-xs rounded-lg shadow-lg">
                <div className="font-semibold mb-2">What is Confidence?</div>
                <p className="mb-2 text-gray-200">
                  Confidence measures how certain the AI is about the generated query&apos;s accuracy.
                </p>
                <div className="space-y-1.5">
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 rounded-full bg-green-500" />
                    <span><strong>&gt;85%:</strong> High confidence, auto-execution ready</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 rounded-full bg-yellow-500" />
                    <span><strong>70-85%:</strong> Medium confidence, review recommended</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 rounded-full bg-red-500" />
                    <span><strong>&lt;70%:</strong> Low confidence, refinement needed</span>
                  </div>
                </div>
                {/* Arrow */}
                <div className="absolute top-full left-1/2 transform -translate-x-1/2 -mt-1">
                  <div className="border-8 border-transparent border-t-gray-900 dark:border-t-gray-700" />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Confidence value with trend indicator */}
        <div className="flex items-center space-x-1.5">
          {trend && (
            <span className={`${
              trend === 'up' ? 'text-green-500' : 
              trend === 'down' ? 'text-red-500' : 
              'text-gray-400'
            }`}>
              {trend === 'up' && <TrendingUp className="w-3.5 h-3.5" />}
              {trend === 'down' && <TrendingDown className="w-3.5 h-3.5" />}
              {trend === 'stable' && <Minus className="w-3.5 h-3.5" />}
            </span>
          )}
          <span className={`font-semibold ${colors.text}`}>
            {percentage}%
          </span>
          <span className={`text-xs ${colors.text} opacity-75`}>
            ({getConfidenceLabel(confidence)})
          </span>
        </div>
      </div>

      {/* Progress bar with threshold marker */}
      <div className="relative">
        {/* Background track */}
        <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-3 overflow-hidden">
          {/* Gradient fill */}
          <div
            className={`h-3 rounded-full transition-all duration-500 ease-out bg-gradient-to-r ${colors.gradient}`}
            style={{ width: `${percentage}%` }}
          />
        </div>

        {/* Threshold marker at 85% */}
        <div 
          className="absolute top-0 h-3 w-0.5 bg-gray-800 dark:bg-white opacity-60"
          style={{ left: `${thresholdPercentage}%` }}
          title="Auto-execution threshold (85%)"
        />
        
        {/* Threshold label */}
        <div 
          className="absolute -bottom-4 transform -translate-x-1/2 text-xs text-gray-500 dark:text-gray-400"
          style={{ left: `${thresholdPercentage}%` }}
        >
          <span className="text-[10px]">threshold</span>
        </div>
      </div>

      {/* Confidence history sparkline */}
      {showHistory && history.length > 1 && (
        <div className="mt-6 pt-2">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-gray-500 dark:text-gray-400">
              Iteration History
            </span>
            <span className="text-xs text-gray-400 dark:text-gray-500">
              {history.length} iterations
            </span>
          </div>
          <div className="flex items-end space-x-1 h-8">
            {history.map((conf, idx) => {
              const barColor = getColor(conf)
              const barHeight = Math.max(conf * 100, 10) // Minimum 10% height for visibility
              return (
                <div
                  key={idx}
                  className={`flex-1 rounded-t transition-all duration-300 ${barColor.bg} opacity-80 hover:opacity-100`}
                  style={{ height: `${barHeight}%` }}
                  title={`Iteration ${idx + 1}: ${Math.round(conf * 100)}%`}
                />
              )
            })}
          </div>
          {/* X-axis labels */}
          <div className="flex justify-between text-[10px] text-gray-400 dark:text-gray-500 mt-0.5">
            <span>1</span>
            {history.length > 2 && <span className="text-center">{Math.ceil(history.length / 2)}</span>}
            <span>{history.length}</span>
          </div>
        </div>
      )}
    </div>
  )
}

export default ConfidenceMeter
