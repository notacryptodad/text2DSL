import { Settings, Eye, EyeOff, Zap, Brain } from 'lucide-react'
import { useState } from 'react'

function SettingsPanel({ settings, onChange }) {
  const [isExpanded, setIsExpanded] = useState(false)

  const handleChange = (key, value) => {
    onChange({ ...settings, [key]: value })
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4 border border-gray-200 dark:border-gray-700">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center justify-between w-full text-left"
      >
        <div className="flex items-center space-x-2">
          <Settings className="w-5 h-5 text-primary-500" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Settings</h2>
        </div>
        {isExpanded ? (
          <EyeOff className="w-4 h-4 text-gray-500" />
        ) : (
          <Eye className="w-4 h-4 text-gray-500" />
        )}
      </button>

      {isExpanded && (
        <div className="mt-4 space-y-4">
          {/* Trace Level */}
          <div>
            <label className="flex items-center space-x-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <Brain className="w-4 h-4" />
              <span>Reasoning Trace Level</span>
            </label>
            <select
              value={settings.trace_level}
              onChange={(e) => handleChange('trace_level', e.target.value)}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none"
            >
              <option value="none">None - Faster</option>
              <option value="summary">Summary - Balanced</option>
              <option value="full">Full - Detailed</option>
            </select>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Higher levels provide more details but may be slower
            </p>
          </div>

          {/* Enable Execution */}
          <div>
            <label className="flex items-center space-x-2 text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <Zap className="w-4 h-4" />
              <span>Execute Queries</span>
            </label>
            <div className="flex items-center space-x-3">
              <button
                onClick={() => handleChange('enable_execution', !settings.enable_execution)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.enable_execution ? 'bg-primary-500' : 'bg-gray-300 dark:bg-gray-600'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.enable_execution ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {settings.enable_execution ? 'Enabled' : 'Disabled'}
              </span>
            </div>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Execute queries against the database to verify results
            </p>
          </div>

          {/* Max Iterations */}
          <div>
            <label className="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <span>Max Iterations</span>
              <span className="text-primary-500 font-mono">{settings.max_iterations}</span>
            </label>
            <input
              type="range"
              min="1"
              max="10"
              value={settings.max_iterations}
              onChange={(e) => handleChange('max_iterations', parseInt(e.target.value))}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-500"
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Maximum refinement attempts before giving up
            </p>
          </div>

          {/* Confidence Threshold */}
          <div>
            <label className="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <span>Confidence Threshold</span>
              <span className="text-primary-500 font-mono">
                {(settings.confidence_threshold * 100).toFixed(0)}%
              </span>
            </label>
            <input
              type="range"
              min="0"
              max="100"
              value={settings.confidence_threshold * 100}
              onChange={(e) => handleChange('confidence_threshold', parseInt(e.target.value) / 100)}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-primary-500"
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Minimum confidence score to accept a query
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

export default SettingsPanel
