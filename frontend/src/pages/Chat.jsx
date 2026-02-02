import { useState, useEffect, useRef } from 'react'
import { Database, History, X } from 'lucide-react'
import ChatMessage from '../components/ChatMessage'
import ProviderSelect from '../components/ProviderSelect'
import QueryInput from '../components/QueryInput'
import ConversationHistory from '../components/ConversationHistory'
import ProgressIndicator from '../components/ProgressIndicator'
import SettingsPanel from '../components/SettingsPanel'
import WelcomeScreen from '../components/WelcomeScreen'
import useWebSocket from '../hooks/useWebSocket'
import { useWorkspace } from '../contexts/WorkspaceContext'

function Chat() {
  const { currentWorkspace } = useWorkspace()
  const [providers, setProviders] = useState([])
  const [selectedProvider, setSelectedProvider] = useState(null)
  const [messages, setMessages] = useState([])
  const [conversationId, setConversationId] = useState(null)
  const [conversations, setConversations] = useState(() => {
    const saved = localStorage.getItem('conversations')
    return saved ? JSON.parse(saved) : []
  })
  const [showHistory, setShowHistory] = useState(false)
  const [settings, setSettings] = useState(() => {
    const saved = localStorage.getItem('querySettings')
    return saved ? JSON.parse(saved) : {
      trace_level: 'summary',
      enable_execution: false,
      max_iterations: 5,
      confidence_threshold: 0.85,
    }
  })
  const messagesEndRef = useRef(null)

    const { sendQuery, connectionState, progress, connect } = useWebSocket({
    onMessage: (event) => {
      handleWebSocketMessage(event)
    },
    onError: (error) => {
      console.error('WebSocket error:', error)
      // Only show error if we were actually trying to send something
      if (connectionState === 'connected') {
        addMessage({
          type: 'error',
          content: 'Connection error. Please try again.',
          timestamp: new Date(),
        })
      }
    },
  })

  // Fetch providers when workspace changes
  useEffect(() => {
    const fetchProviders = async () => {
      if (!currentWorkspace) {
        setProviders([])
        setSelectedProvider(null)
        return
      }

      try {
        const token = localStorage.getItem('access_token')
        const response = await fetch(`/api/v1/admin/workspaces/${currentWorkspace.id}/providers`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        })

        if (response.ok) {
          const data = await response.json()
          // Transform the provider data to match the expected format
          const formattedProviders = data.map(provider => ({
            id: provider.id,
            name: provider.name,
            type: provider.provider_type.toUpperCase(),
            icon: getProviderIcon(provider.provider_type),
          }))
          setProviders(formattedProviders)

          // Select first provider if none selected or current is not in list
          if (!selectedProvider || !formattedProviders.find(p => p.id === selectedProvider.id)) {
            setSelectedProvider(formattedProviders[0] || null)
          }
        } else {
          console.error('Failed to fetch providers')
          setProviders([])
          setSelectedProvider(null)
        }
      } catch (error) {
        console.error('Error fetching providers:', error)
        setProviders([])
        setSelectedProvider(null)
      }
    }

    fetchProviders()
  }, [currentWorkspace])

  const getProviderIcon = (type) => {
    const icons = {
      sql: '🗄️',
      postgres: '🐘',
      mysql: '🐬',
      mongodb: '🍃',
      nosql: '📦',
      splunk: '📊',
    }
    return icons[type.toLowerCase()] || '🔌'
  }

  useEffect(() => {
    // Scroll to bottom when messages change
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    // Save conversations to localStorage
    localStorage.setItem('conversations', JSON.stringify(conversations))
  }, [conversations])

  useEffect(() => {
    // Save settings to localStorage
    localStorage.setItem('querySettings', JSON.stringify(settings))
  }, [settings])

  useEffect(() => {
    // Update current conversation
    if (conversationId && messages.length > 0) {
      setConversations(prev => {
        const existing = prev.find(c => c.id === conversationId)
        if (existing) {
          return prev.map(c => c.id === conversationId
            ? { ...c, messages, timestamp: new Date(), provider: selectedProvider.name }
            : c
          )
        } else {
          return [...prev, {
            id: conversationId,
            messages,
            timestamp: new Date(),
            provider: selectedProvider.name,
          }]
        }
      })
    }
  }, [messages, conversationId, selectedProvider])

  const handleWebSocketMessage = (event) => {
    const { type, data } = event

    switch (type) {
      case 'progress': {
        if (data.stage === 'started') {
          setConversationId(data.conversation_id)
          addMessage({
            type: 'progress',
            content: data.message,
            stage: data.stage,
            progress: data.progress,
            timestamp: new Date(),
          })
        }
        break
      }

      case 'result': {
        const result = data.result
        addMessage({
          type: 'assistant',
          content: result.generated_query,
          confidence: result.confidence_score,
          validationStatus: result.validation_status,
          executionResult: result.execution_result,
          trace: result.reasoning_trace,
          providerId: selectedProvider.id,
          iterations: result.iterations,
          turnId: result.turn_id,
          explanation: result.query_explanation,
          timestamp: new Date(),
        })
        break
      }

      case 'clarification': {
        addMessage({
          type: 'clarification',
          content: data.questions || ['Please provide more details.'],
          timestamp: new Date(),
        })
        break
      }

      case 'error': {
        addMessage({
          type: 'error',
          content: data.message || 'An error occurred',
          details: data.details,
          timestamp: new Date(),
        })
        break
      }

      default:
        console.warn('Unknown event type:', type)
    }
  }

  const addMessage = (message) => {
    setMessages((prev) => [...prev, { id: Date.now(), ...message }])
  }

  const handleSendQuery = async (query) => {
    if (!selectedProvider) {
      addMessage({
        type: 'error',
        content: 'Please select a provider first.',
        timestamp: new Date(),
      })
      return
    }

    // Connect WebSocket if not connected
    if (connectionState !== 'connected') {
      connect()
      // Wait a moment for connection
      await new Promise(resolve => setTimeout(resolve, 1000))
    }

    addMessage({
      type: 'user',
      content: query,
      timestamp: new Date(),
    })

    try {
      await sendQuery({
        provider_id: selectedProvider.id,
        query,
        conversation_id: conversationId,
        options: {
          trace_level: settings.trace_level,
          enable_execution: settings.enable_execution,
          max_iterations: settings.max_iterations,
          confidence_threshold: settings.confidence_threshold,
        },
      })
    } catch (error) {
      addMessage({
        type: 'error',
        content: 'Failed to send query. Please try again.',
        timestamp: new Date(),
      })
    }
  }

  const handleNewConversation = () => {
    setMessages([])
    setConversationId(null)
    setShowHistory(false)
  }

  const handleSelectConversation = (id) => {
    const conv = conversations.find(c => c.id === id)
    if (conv) {
      setMessages(conv.messages)
      setConversationId(conv.id)
      setShowHistory(false)
    }
  }

  const handleDeleteConversation = (id) => {
    setConversations(prev => prev.filter(c => c.id !== id))
    if (conversationId === id) {
      handleNewConversation()
    }
  }

  const handleWelcomeAction = (query) => {
    if (query) {
      handleSendQuery(query)
    }
  }

  return (
    <>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Sidebar */}
          <aside className="lg:col-span-1 space-y-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center space-x-2 mb-4">
                <Database className="w-5 h-5 text-primary-500" />
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Provider
                </h2>
              </div>
              <ProviderSelect
                providers={providers}
                selected={selectedProvider}
                onChange={setSelectedProvider}
                disabled={!currentWorkspace || providers.length === 0}
              />

              <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
                  How it works
                </h3>
                <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                  <li className="flex items-start space-x-2">
                    <span className="text-primary-500 mt-0.5">1.</span>
                    <span>Select your database provider</span>
                  </li>
                  <li className="flex items-start space-x-2">
                    <span className="text-primary-500 mt-0.5">2.</span>
                    <span>Type your query in natural language</span>
                  </li>
                  <li className="flex items-start space-x-2">
                    <span className="text-primary-500 mt-0.5">3.</span>
                    <span>Get the generated DSL query instantly</span>
                  </li>
                </ul>
              </div>
            </div>

            <SettingsPanel settings={settings} onChange={setSettings} />
          </aside>

          {/* Chat Area */}
          <div className="lg:col-span-3">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 flex flex-col h-[calc(100vh-12rem)]">
              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {messages.length === 0 ? (
                  <WelcomeScreen onGetStarted={handleWelcomeAction} />
                ) : (
                  <>
                    {messages.map((message) => (
                      <ChatMessage
                        key={message.id}
                        message={message}
                        conversationId={conversationId}
                      />
                    ))}
                    <div ref={messagesEndRef} />
                  </>
                )}
              </div>

              {/* Progress Indicator */}
              <ProgressIndicator progress={progress} />

              {/* Input */}
              <div className="p-6 border-t border-gray-200 dark:border-gray-700">
                <QueryInput
                  onSend={handleSendQuery}
                  disabled={connectionState !== 'connected' || !selectedProvider}
                  placeholder={
                    !selectedProvider
                      ? 'Select a provider from your workspace...'
                      : connectionState === 'connected'
                      ? 'Ask me anything about your data...'
                      : 'Connecting to server...'
                  }
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* History Button - Fixed Position */}
      <button
        onClick={() => setShowHistory(!showHistory)}
        className="fixed bottom-8 right-8 p-4 rounded-full bg-primary-500 hover:bg-primary-600 text-white shadow-lg transition-colors z-30"
        aria-label="Toggle conversation history"
      >
        <History className="w-6 h-6" />
        {conversations.length > 0 && (
          <span className="absolute -top-1 -right-1 w-6 h-6 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
            {conversations.length}
          </span>
        )}
      </button>

      {/* Conversation History Sidebar */}
      {showHistory && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-black bg-opacity-50"
            onClick={() => setShowHistory(false)}
          />
          <div className="absolute right-0 top-0 h-full w-80 bg-white dark:bg-gray-800 shadow-xl">
            <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Conversation History
              </h2>
              <button
                onClick={() => setShowHistory(false)}
                className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="h-[calc(100%-64px)]">
              <ConversationHistory
                conversations={conversations}
                currentId={conversationId}
                onSelect={handleSelectConversation}
                onNew={handleNewConversation}
                onDelete={handleDeleteConversation}
              />
            </div>
          </div>
        </div>
      )}

      {/* Desktop History Sidebar */}
      <div
        className={`hidden lg:block fixed right-0 top-0 h-full w-80 bg-white dark:bg-gray-800 shadow-xl transform transition-transform duration-300 z-40 ${
          showHistory ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700 mt-20">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Conversation History
          </h2>
          <button
            onClick={() => setShowHistory(false)}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>
        <div className="h-[calc(100%-144px)]">
          <ConversationHistory
            conversations={conversations}
            currentId={conversationId}
            onSelect={handleSelectConversation}
            onNew={handleNewConversation}
            onDelete={handleDeleteConversation}
          />
        </div>
      </div>
    </>
  )
}

export default Chat
