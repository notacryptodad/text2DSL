import { useState, useEffect, useRef } from 'react'
import { Moon, Sun, Zap, Database } from 'lucide-react'
import ChatMessage from './components/ChatMessage'
import ProviderSelect from './components/ProviderSelect'
import QueryInput from './components/QueryInput'
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

  const handleWebSocketMessage = (event) => {
    const { type, data, trace } = event

    switch (type) {
      case 'progress':
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

      case 'result':
        // Add final result message
        const result = data.result
        addMessage({
          type: 'assistant',
          content: result.generated_query,
          confidence: result.confidence_score,
          validationStatus: result.validation_status,
          executionResult: result.execution_result,
          trace: result.reasoning_trace,
          timestamp: new Date(),
        })
        break

      case 'clarification':
        // Add clarification request
        addMessage({
          type: 'clarification',
          content: data.questions || ['Please provide more details.'],
          timestamp: new Date(),
        })
        break

      case 'error':
        // Add error message
        addMessage({
          type: 'error',
          content: data.message || 'An error occurred',
          details: data.details,
          timestamp: new Date(),
        })
        break

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
        trace_level: 'summary',
        enable_execution: false,
      },
    })
  }

  const toggleDarkMode = () => {
    setDarkMode(!darkMode)
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
          <aside className="lg:col-span-1">
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
          </aside>

          {/* Chat Area */}
          <div className="lg:col-span-3">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 flex flex-col h-[calc(100vh-12rem)]">
              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {messages.length === 0 ? (
                  <div className="flex items-center justify-center h-full">
                    <div className="text-center">
                      <Zap className="w-12 h-12 text-primary-500 mx-auto mb-4" />
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                        Start a conversation
                      </h3>
                      <p className="text-gray-600 dark:text-gray-400 max-w-md">
                        Ask me anything about your data in plain English. I'll convert it to
                        the appropriate query language.
                      </p>
                      <div className="mt-6 space-y-2">
                        <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                          Try examples like:
                        </p>
                        <div className="space-y-1">
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            "Show me all users who signed up last month"
                          </p>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            "What are the top 10 orders by revenue?"
                          </p>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            "Find customers with more than 5 orders"
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <>
                    {messages.map((message) => (
                      <ChatMessage key={message.id} message={message} />
                    ))}
                    <div ref={messagesEndRef} />
                  </>
                )}
              </div>

              {/* Progress Bar */}
              {progress && (
                <div className="px-6 py-2 border-t border-gray-200 dark:border-gray-700">
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="text-gray-600 dark:text-gray-400">
                      {progress.message}
                    </span>
                    <span className="text-gray-500 dark:text-gray-500">
                      {Math.round(progress.progress * 100)}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                    <div
                      className="bg-primary-500 h-1.5 rounded-full transition-all duration-300"
                      style={{ width: `${progress.progress * 100}%` }}
                    />
                  </div>
                </div>
              )}

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
    </div>
  )
}

export default App
