import { useState, useEffect, useRef, useCallback } from 'react'

/**
 * Custom hook for managing WebSocket connection to the Text2DSL backend
 */
function useWebSocket({ onMessage, onError, onOpen, onClose }) {
  const [connectionState, setConnectionState] = useState('disconnected')
  const [progress, setProgress] = useState(null)
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const reconnectAttemptsRef = useRef(0)
  const maxReconnectAttempts = 5
  const reconnectDelay = 3000

  const connect = useCallback(() => {
    try {
      // Determine WebSocket URL based on current location
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = window.location.hostname
      const port = window.location.port || (protocol === 'wss:' ? '443' : '80')

      // In development, connect to proxy which forwards to backend
      // Use current window location to work with port forwarding
      const wsUrl = `${protocol}//${host}:${port}/ws/query`

      console.log('Connecting to WebSocket:', wsUrl)
      setConnectionState('connecting')

      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('WebSocket connected')
        setConnectionState('connected')
        reconnectAttemptsRef.current = 0
        if (onOpen) onOpen()
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          console.log('WebSocket message:', data)

          // Update progress if it's a progress event
          if (data.type === 'progress') {
            setProgress({
              stage: data.data.stage,
              message: data.data.message,
              progress: data.data.progress || 0,
            })
          } else if (data.type === 'result') {
            // Clear progress on result
            setProgress(null)
          }

          if (onMessage) onMessage(data)
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
          if (onError) onError(error)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setConnectionState('error')
        if (onError) onError(error)
      }

      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason)
        setConnectionState('disconnected')
        setProgress(null)
        wsRef.current = null

        if (onClose) onClose(event)

        // Attempt to reconnect if not intentionally closed
        if (event.code !== 1000 && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current++
          console.log(
            `Attempting to reconnect (${reconnectAttemptsRef.current}/${maxReconnectAttempts})...`
          )
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, reconnectDelay)
        }
      }

      wsRef.current = ws
    } catch (error) {
      console.error('Error creating WebSocket:', error)
      setConnectionState('error')
      if (onError) onError(error)
    }
  }, [onMessage, onError, onOpen, onClose])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnecting')
      wsRef.current = null
    }

    setConnectionState('disconnected')
    setProgress(null)
  }, [])

  const sendQuery = useCallback(
    async (queryRequest) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        throw new Error('WebSocket is not connected')
      }

      try {
        console.log('Sending query:', queryRequest)
        wsRef.current.send(JSON.stringify(queryRequest))
      } catch (error) {
        console.error('Error sending query:', error)
        throw error
      }
    },
    []
  )

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    connect()

    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  return {
    connectionState,
    progress,
    sendQuery,
    connect,
    disconnect,
  }
}

export default useWebSocket
