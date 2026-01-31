import { useState, useEffect, useRef } from 'react'
import { Moon, Sun, Zap, Database, History, X } from 'lucide-react'
import ChatMessage from './components/ChatMessage'
import ProviderSelect from './components/ProviderSelect'
import QueryInput from './components/QueryInput'
import ConversationHistory from './components/ConversationHistory'
import ProgressIndicator from './components/ProgressIndicator'
import SettingsPanel from './components/SettingsPanel'
import WelcomeScreen from './components/WelcomeScreen'
import useWebSocket from './hooks/useWebSocket'

const PROVIDERS = [
  { id: 'sql-postgres', name: 'PostgreSQL', type: 'SQL', icon: '🐘' },
  { id: 'sql-mysql', name: 'MySQL', type: 'SQL', icon: '🐬' },
  { id: 'nosql-mongodb', name: 'MongoDB', type: 'NoSQL', icon: '🍃' },
  { id: 'splunk', name: 'Splunk', type: 'SPL', icon: '📊' },
]

function App() {
  const [darkMode, setDarkMode] = useState(() => {
    // Check system preference or localStorage
    const saved = localStorage.getItem('darkMode')
    if (saved !== null) return saved === 'true'
    return window.matchMedia('(prefers-color-scheme: dark)').matches
  })

  const [selectedProvider, setSelectedProvider] = useState(PROVIDERS[0])
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

  const { sendQuery, connectionState, progress } = useWebSocket({
    onMessage: (event) => {
      handleWebSocketMessage(event)
    },
    onError: (error) => {
      console.error('WebSocket error:', error)
      addMessage({
        type: 'error',
        content: 'Connection error. Please try again.',
        timestamp: new Date(),
      })
    },
  })

  useEffect(() => {
    // Update document class and localStorage when darkMode changes
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
    localStorage.setItem('darkMode', darkMode)
  }, [darkMode])

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
        // Update progress state
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
        // Add final result message
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
          timestamp: new Date(),
        })
        break
      }

      case 'clarification': {
        // Add clarification request
        addMessage({
          type: 'clarification',
          content: data.questions || ['Please provide more details.'],
          timestamp: new Date(),
        })
        break
      }

      case 'error': {
        // Add error message
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
    // Add user message
    addMessage({
      type: 'user',
      content: query,
      timestamp: new Date(),
    })

    // Send query via WebSocket
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
  }

  const toggleDarkMode = () => {
    setDarkMode(!darkMode)
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
      // Start with example query
      handleSendQuery(query)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 transition-colors duration-200">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="bg-primary-500 p-2 rounded-lg">
                <Zap className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                  Text2DSL
                </h1>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Natural Language to Query Converter
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              {/* Connection Status */}
              <div className="flex items-center space-x-2">
                <div
                  className={`w-2 h-2 rounded-full ${
                    connectionState === 'connected'
                      ? 'bg-green-500 animate-pulse'
                      : connectionState === 'connecting'
                      ? 'bg-yellow-500 animate-pulse'
                      : 'bg-red-500'
                  }`}
                />
                <span className="text-sm text-gray-600 dark:text-gray-400 hidden sm:inline">
                  {connectionState}
                </span>
              </div>

              {/* History Toggle */}
              <button
                onClick={() => setShowHistory(!showHistory)}
                className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors relative"
                aria-label="Toggle conversation history"
              >
                <History className="w-5 h-5 text-gray-600 dark:text-gray-300" />
                {conversations.length > 0 && (
                  <span className="absolute -top-1 -right-1 w-5 h-5 bg-primary-500 text-white text-xs rounded-full flex items-center justify-center">
                    {conversations.length}
                  </span>
                )}
              </button>

              {/* Dark Mode Toggle */}
              <button
                onClick={toggleDarkMode}
                className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                aria-label="Toggle dark mode"
              >
                {darkMode ? (
                  <Sun className="w-5 h-5 text-gray-600 dark:text-gray-300" />
                ) : (
                  <Moon className="w-5 h-5 text-gray-600" />
                )}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
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
                providers={PROVIDERS}
                selected={selectedProvider}
                onChange={setSelectedProvider}
              />

              {/* Info */}
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

            {/* Settings Panel */}
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
                      <ChatMessage key={message.id} message={message} />
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
                  disabled={connectionState !== 'connected'}
                  placeholder={
                    connectionState === 'connected'
                      ? 'Ask me anything about your data...'
                      : 'Connecting to server...'
                  }
                />
              </div>
            </div>
          </div>
        </div>
      </main>

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
  )
}

export default App
