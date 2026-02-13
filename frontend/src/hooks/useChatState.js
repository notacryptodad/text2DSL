import { useState, useRef, useCallback } from 'react'
import useQuerySSE from './useQuerySSE'
import { useQueryHistory } from '../components/QueryHistorySidebar'

export function useChatState() {
  const [providers, setProviders] = useState([])
  const [selectedProvider, setSelectedProvider] = useState(null)
  const [messages, setMessages] = useState([])
  const [conversationId, setConversationId] = useState(null)
  const [currentQuery, setCurrentQuery] = useState('')
  const [settings, setSettings] = useState(() => {
    const saved = localStorage.getItem('querySettings')
    return saved ? JSON.parse(saved) : {
      trace_level: 'summary',
      enable_execution: false,
      max_iterations: 5,
      confidence_threshold: 0.85
    }
  })

  const messageIdCounter = useRef(0)
  const pendingQueryRef = useRef(null)
  const { addQuery: addToQueryHistory } = useQueryHistory()

  const generateMessageId = () => {
    messageIdCounter.current += 1
    return `${Date.now()}-${messageIdCounter.current}`
  }

  const addMessage = useCallback((message) => {
    setMessages((prev) => [...prev, { id: generateMessageId(), ...message }])
  }, [])

  const handleSSEMessage = useCallback((event) => {
    const { event: type, data } = event
    switch (type) {
      case 'started':
        setConversationId(data.conversation_id)
        addMessage({
          type: 'progress',
          content: 'Query processing started...',
          stage: 'started',
          progress: 0,
          timestamp: new Date()
        })
        break
      case 'progress':
        if (data.stage !== 'started') {
          addMessage({
            type: 'progress',
            content: data.message,
            stage: data.stage,
            progress: data.progress,
            timestamp: new Date()
          })
        }
        break
      case 'completed': {
        const content = data.response || data.generated_query || ''
        const isPlainText = !data.generated_query || data.generated_query.trim() === ''
        addMessage({
          type: 'assistant',
          content,
          generatedQuery: data.generated_query || '',
          responseType: isPlainText ? 'text' : 'query',
          confidence: data.confidence_score,
          executionResult: data.execution_result,
          providerId: selectedProvider?.id,
          turnId: data.turn_id,
          explanation: data.query_explanation,
          timestamp: new Date()
        })
        if (data.generated_query && pendingQueryRef.current) {
          addToQueryHistory({
            query: pendingQueryRef.current,
            generatedDSL: data.generated_query,
            providerId: selectedProvider?.id,
            providerName: selectedProvider?.name,
            executionResult: data.execution_result
          })
          pendingQueryRef.current = null
        }
        break
      }
      case 'error':
        addMessage({
          type: 'error',
          content: data.message || data.error || 'An error occurred',
          details: data.details,
          timestamp: new Date()
        })
        pendingQueryRef.current = null
        break
      default:
        console.warn('[Chat] Unknown SSE event type:', type, event)
    }
  }, [selectedProvider, addMessage, addToQueryHistory])

  const { sendQuery, connectionState, progress, cancelQuery } = useQuerySSE({
    onMessage: handleSSEMessage,
    onError: (error) => addMessage({
      type: 'error',
      content: error.message || 'An error occurred',
      timestamp: new Date()
    }),
    onComplete: (data) => setConversationId(data.conversation_id),
  })

  const isQueryRunning = connectionState === 'connecting' || connectionState === 'connected'

  const handleSendQuery = useCallback(async (query) => {
    if (!selectedProvider) {
      addMessage({
        type: 'error',
        content: 'Please select a provider first.',
        timestamp: new Date()
      })
      return
    }
    pendingQueryRef.current = query
    addMessage({ type: 'user', content: query, timestamp: new Date() })
    try {
      await sendQuery({
        provider_id: selectedProvider.id,
        query,
        conversation_id: conversationId,
        options: {
          trace_level: settings.trace_level,
          enable_execution: settings.enable_execution,
          max_iterations: settings.max_iterations,
          confidence_threshold: settings.confidence_threshold
        }
      })
    } catch (error) {
      pendingQueryRef.current = null
      addMessage({
        type: 'error',
        content: 'Failed to send query. Please try again.',
        timestamp: new Date()
      })
    }
  }, [selectedProvider, conversationId, settings, sendQuery, addMessage])

  const handleQueryChange = useCallback((query) => {
    setCurrentQuery(query)
  }, [])

  const clearMessages = useCallback(() => {
    setMessages([])
    setConversationId(null)
  }, [])

  const lastUserQuery = messages
    .filter(m => m.type === 'user')
    .slice(-1)[0]?.content || ''

  return {
    providers,
    setProviders,
    selectedProvider,
    setSelectedProvider,
    messages,
    setMessages,
    conversationId,
    setConversationId,
    currentQuery,
    setCurrentQuery,
    settings,
    setSettings,
    handleSendQuery,
    handleQueryChange,
    clearMessages,
    isQueryRunning,
    progress,
    cancelQuery,
    lastUserQuery,
    addMessage
  }
}
