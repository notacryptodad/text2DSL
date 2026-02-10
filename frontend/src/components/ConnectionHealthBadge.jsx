import { useState } from 'react'
import { WifiOff, AlertTriangle, HelpCircle, RefreshCw, CheckCircle } from 'lucide-react'
import useConnectionHealth, { HEALTH_STATUS } from '../hooks/useConnectionHealth'

function ConnectionHealthBadge({ providerId, className = '' }) {
  const [showTooltip, setShowTooltip] = useState(false)
  const { health, isChecking, checkHealth } = useConnectionHealth(providerId, {
    checkInterval: 30000,
    autoStart: true,
  })

  const getStatusConfig = () => {
    switch (health.status) {
      case HEALTH_STATUS.CONNECTED:
        return { color: 'bg-green-500', ringColor: 'ring-green-500/30', textColor: 'text-green-600 dark:text-green-400', Icon: CheckCircle, label: 'Connected' }
      case HEALTH_STATUS.DEGRADED:
        return { color: 'bg-yellow-500', ringColor: 'ring-yellow-500/30', textColor: 'text-yellow-600 dark:text-yellow-400', Icon: AlertTriangle, label: 'Degraded' }
      case HEALTH_STATUS.DISCONNECTED:
        return { color: 'bg-red-500', ringColor: 'ring-red-500/30', textColor: 'text-red-600 dark:text-red-400', Icon: WifiOff, label: 'Disconnected' }
      default:
        return { color: 'bg-gray-400', ringColor: 'ring-gray-400/30', textColor: 'text-gray-500 dark:text-gray-400', Icon: HelpCircle, label: 'Unknown' }
    }
  }

  const statusConfig = isChecking
    ? { color: 'bg-blue-500', ringColor: 'ring-blue-500/30', textColor: 'text-blue-600 dark:text-blue-400', Icon: RefreshCw, label: 'Checking...' }
    : getStatusConfig()

  const { color, ringColor, textColor, Icon, label } = statusConfig

  const formatLatency = (ms) => {
    if (ms === null || ms === undefined) return 'N/A'
    if (ms < 1000) return `${Math.round(ms)}ms`
    return `${(ms / 1000).toFixed(1)}s`
  }

  const formatLastCheck = (date) => {
    if (!date) return 'Never'
    const diff = Math.floor((new Date() - new Date(date)) / 1000)
    if (diff < 60) return 'Just now'
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
    return new Date(date).toLocaleDateString()
  }

  const handleTestConnection = (e) => { e.stopPropagation(); checkHealth() }

  if (!providerId) return null

  return (
    <div className={`relative inline-flex items-center ${className}`}>
      <button
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        onClick={() => setShowTooltip(!showTooltip)}
        className="relative flex items-center space-x-1.5 focus:outline-none"
        aria-label={`Connection status: ${label}`}
      >
        <span className="relative flex h-3 w-3">
          {health.status === HEALTH_STATUS.CONNECTED && (
            <span className={`absolute inline-flex h-full w-full rounded-full ${color} opacity-75 animate-ping`} />
          )}
          <span className={`relative inline-flex rounded-full h-3 w-3 ${color} ring-2 ${ringColor}`} />
        </span>
      </button>

      {showTooltip && (
        <div className="absolute left-1/2 transform -translate-x-1/2 top-full mt-2 z-50" onMouseEnter={() => setShowTooltip(true)} onMouseLeave={() => setShowTooltip(false)}>
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-3 w-56">
            <div className="flex items-center space-x-2 mb-2">
              <Icon className={`w-4 h-4 ${textColor} ${isChecking ? 'animate-spin' : ''}`} />
              <span className={`font-medium ${textColor}`}>{label}</span>
            </div>
            <div className="space-y-1.5 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500 dark:text-gray-400">Latency:</span>
                <span className="text-gray-900 dark:text-white font-medium">{formatLatency(health.latency)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500 dark:text-gray-400">Last check:</span>
                <span className="text-gray-900 dark:text-white font-medium">{formatLastCheck(health.lastCheck)}</span>
              </div>
              {health.tableCount !== null && (
                <div className="flex justify-between">
                  <span className="text-gray-500 dark:text-gray-400">Tables:</span>
                  <span className="text-gray-900 dark:text-white font-medium">{health.tableCount}</span>
                </div>
              )}
              {health.message && (
                <div className="pt-1.5 border-t border-gray-200 dark:border-gray-700">
                  <p className="text-xs text-gray-600 dark:text-gray-400">{health.message}</p>
                </div>
              )}
              {health.error && health.status === HEALTH_STATUS.DISCONNECTED && (
                <div className="pt-1.5">
                  <p className="text-xs text-red-500 truncate" title={health.error}>{health.error}</p>
                </div>
              )}
            </div>
            <button onClick={handleTestConnection} disabled={isChecking} className="mt-3 w-full flex items-center justify-center space-x-2 px-3 py-1.5 text-sm font-medium text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-900/20 hover:bg-primary-100 dark:hover:bg-primary-900/30 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
              <RefreshCw className={`w-3.5 h-3.5 ${isChecking ? 'animate-spin' : ''}`} />
              <span>{isChecking ? 'Testing...' : 'Test Connection'}</span>
            </button>
          </div>
          <div className="absolute left-1/2 transform -translate-x-1/2 -top-1.5 w-3 h-3 bg-white dark:bg-gray-800 border-l border-t border-gray-200 dark:border-gray-700 rotate-45" />
        </div>
      )}
    </div>
  )
}

export default ConnectionHealthBadge
