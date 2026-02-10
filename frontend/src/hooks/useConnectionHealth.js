import { useState, useEffect, useCallback, useRef } from 'react'

export const HEALTH_STATUS = {
  CONNECTED: 'connected',
  DEGRADED: 'degraded',
  DISCONNECTED: 'disconnected',
  UNKNOWN: 'unknown',
  CHECKING: 'checking',
}

const DEFAULT_CHECK_INTERVAL = 30000

function useConnectionHealth(providerId, options = {}) {
  const { checkInterval = DEFAULT_CHECK_INTERVAL, autoStart = true } = options

  const [health, setHealth] = useState({
    status: HEALTH_STATUS.UNKNOWN,
    latency: null,
    lastCheck: null,
    message: null,
    error: null,
    tableCount: null,
  })

  const [isChecking, setIsChecking] = useState(false)
  const intervalRef = useRef(null)
  const mountedRef = useRef(true)

  const checkHealth = useCallback(async () => {
    if (!providerId) {
      setHealth({
        status: HEALTH_STATUS.UNKNOWN,
        latency: null,
        lastCheck: null,
        message: 'No provider selected',
        error: null,
        tableCount: null,
      })
      return
    }

    setIsChecking(true)

    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch(`/api/v1/providers/${providerId}/health`, {
        headers: { Authorization: `Bearer ${token}` },
      })

      if (!mountedRef.current) return

      if (response.ok) {
        const data = await response.json()
        setHealth({
          status: data.status || HEALTH_STATUS.UNKNOWN,
          latency: data.latency_ms,
          lastCheck: data.last_check ? new Date(data.last_check) : new Date(),
          message: data.message,
          error: data.error || null,
          tableCount: data.table_count ?? null,
        })
      } else if (response.status === 404) {
        setHealth({
          status: HEALTH_STATUS.DISCONNECTED,
          latency: null,
          lastCheck: new Date(),
          message: 'Provider not found',
          error: 'Provider not found',
          tableCount: null,
        })
      } else {
        const errorText = await response.text()
        setHealth({
          status: HEALTH_STATUS.DISCONNECTED,
          latency: null,
          lastCheck: new Date(),
          message: 'Failed to check health',
          error: errorText,
          tableCount: null,
        })
      }
    } catch (error) {
      if (!mountedRef.current) return
      setHealth({
        status: HEALTH_STATUS.DISCONNECTED,
        latency: null,
        lastCheck: new Date(),
        message: 'Network error',
        error: error.message,
        tableCount: null,
      })
    } finally {
      if (mountedRef.current) setIsChecking(false)
    }
  }, [providerId])

  const startChecking = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current)
    checkHealth()
    intervalRef.current = setInterval(checkHealth, checkInterval)
  }, [checkHealth, checkInterval])

  const stopChecking = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    if (providerId && autoStart) {
      startChecking()
    } else if (!providerId) {
      stopChecking()
      setHealth({
        status: HEALTH_STATUS.UNKNOWN,
        latency: null,
        lastCheck: null,
        message: null,
        error: null,
        tableCount: null,
      })
    }
    return () => {
      mountedRef.current = false
      stopChecking()
    }
  }, [providerId, autoStart, startChecking, stopChecking])

  return { health, isChecking, checkHealth, startChecking, stopChecking }
}

export default useConnectionHealth
