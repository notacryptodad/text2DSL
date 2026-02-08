import { useState, useRef, useCallback, useEffect } from 'react'

function useQuerySSE(defaultCallbacks = {}) {
  const [connectionState, setConnectionState] = useState('idle')
  const [progress, setProgress] = useState(null)
  const abortControllerRef = useRef(null)

  const sendQuery = useCallback(async (queryRequest, runtimeCallbacks = {}) => {
    const { onMessage, onError, onComplete } = { ...defaultCallbacks, ...runtimeCallbacks }

    console.log('[SSE] queryRequest:', queryRequest)
    console.log('[SSE] callbacks merged:', { onMessage: !!onMessage, onError: !!onError, onComplete: !!onComplete })

    try {
      setConnectionState('connecting')

      const token = localStorage.getItem('access_token')

      abortControllerRef.current = new AbortController()

      console.log('[SSE] Sending request to /api/v1/query/stream')
      const response = await fetch(`/api/v1/query/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(queryRequest),
        signal: abortControllerRef.current.signal,
      })

      console.log('[SSE] Response status:', response.status)
      console.log('[SSE] Response ok:', response.ok)

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      setConnectionState('connected')
      console.log('[SSE] State: connected')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let eventCount = 0

      console.log('[SSE] Starting to read stream...')

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        eventCount++
        buffer += decoder.decode(value, { stream: true })
        console.log(`[SSE] Chunk ${eventCount}:`, value.length, 'bytes, buffer length:', buffer.length)

        const events = buffer.split('\n\n')
        buffer = events.pop() || ''

        console.log(`[SSE] Parsed ${events.length} complete events`)
        for (const event of events) {
          console.log('[SSE] Raw event:', event.substring(0, 300))
          let eventData
          try {
            // Handle events with or without 'data: ' prefix
            const jsonStr = event.startsWith('data: ') ? event.slice(6) : event
            eventData = JSON.parse(jsonStr)
          } catch (e) {
            console.error('[SSE] Failed to parse event as JSON:', e)
            continue
          }

          const eventType = eventData.event
          const eventPayload = eventData.data

          console.log('[SSE] ===== PARSED EVENT =====')
          console.log('[SSE] Event type:', eventType)
          console.log('[SSE] Event payload length:', eventPayload ? JSON.stringify(eventPayload).length : 0)
          console.log('[SSE] onMessage exists:', typeof onMessage, 'onComplete exists:', typeof onComplete)

          if (eventType === 'progress') {
            console.log('[SSE] Setting progress')
            if (eventPayload.stage === 'tool_execution') {
              console.log('[SSE] 🔧 Tool event:', eventPayload.tool, '-', eventPayload.message)
            }
            setProgress({
              stage: eventPayload.stage,
              message: eventPayload.message,
              progress: eventPayload.progress || 0,
            })
            console.log('[SSE] Progress set, calling onMessage')
            if (onMessage) {
              console.log('[SSE] Calling onMessage for progress')
              onMessage({ event: eventType, data: eventPayload })
            }
          } else if (eventType === 'completed') {
            console.log('[SSE] Handling completed event')
            setProgress(null)
            if (onComplete) {
              console.log('[SSE] Calling onComplete')
              onComplete(eventPayload)
            }
            if (onMessage) {
              console.log('[SSE] Calling onMessage for completed')
              onMessage({ event: eventType, data: eventPayload })
            }
          } else if (eventType === 'error') {
            console.log('[SSE] Handling error event')
            setProgress(null)
            if (onError) {
              onError(new Error(eventPayload.message || eventPayload.error))
            }
          } else if (onMessage) {
            console.log('[SSE] Calling onMessage for other event type:', eventType)
            onMessage({ event: eventType, data: eventPayload })
          }
        }
      }

      console.log('[SSE] Stream complete, setting state to idle')
      setConnectionState('idle')
    } catch (error) {
      if (error.name !== 'AbortError') {
        console.error('[SSE] Query error:', error)
        setConnectionState('error')
        if (onError) onError(error)
      } else {
        console.log('[SSE] Request was aborted')
      }
    }
  }, [])

  const cancelQuery = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setConnectionState('idle')
    setProgress(null)
  }, [])

  useEffect(() => {
    return () => {
      cancelQuery()
    }
  }, [cancelQuery])

  return {
    connectionState,
    progress,
    sendQuery,
    cancelQuery,
  }
}

export default useQuerySSE
