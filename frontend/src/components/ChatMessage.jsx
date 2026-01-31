import { User, Bot, AlertCircle, CheckCircle, Info, Copy, Check, ChevronDown, ChevronRight, Download } from 'lucide-react'
import { useState, useEffect } from 'react'
import Prism from 'prismjs'
import '../styles/prism-custom.css'
import 'prismjs/components/prism-sql'
import 'prismjs/components/prism-mongodb'
import 'prismjs/components/prism-splunk-spl'

function ChatMessage({ message }) {
  const [copied, setCopied] = useState(false)
  const [traceExpanded, setTraceExpanded] = useState(false)
  const [agentDetailsExpanded, setAgentDetailsExpanded] = useState({})

  useEffect(() => {
    // Highlight code after render
    Prism.highlightAll()
  }, [message])

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const downloadQuery = (query, filename = 'query.sql') => {
    const blob = new Blob([query], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const toggleAgentDetails = (agentName) => {
    setAgentDetailsExpanded(prev => ({
      ...prev,
      [agentName]: !prev[agentName]
    }))
  }

  const getLanguageClass = (providerId) => {
    if (providerId?.includes('sql')) return 'language-sql'
    if (providerId?.includes('mongo')) return 'language-mongodb'
    if (providerId?.includes('splunk')) return 'language-splunk-spl'
    return 'language-sql'
  }

  if (message.type === 'user') {
    return (
      <div className="flex items-start space-x-3 justify-end">
        <div className="flex-1 max-w-3xl">
          <div className="bg-primary-500 text-white rounded-lg px-4 py-3 shadow-sm">
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 text-right">
            {formatTimestamp(message.timestamp)}
          </p>
        </div>
        <div className="flex-shrink-0">
          <div className="w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center">
            <User className="w-5 h-5 text-primary-600 dark:text-primary-400" />
          </div>
        </div>
      </div>
    )
  }

  if (message.type === 'assistant') {
    return (
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0">
          <div className="w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
            <Bot className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          </div>
        </div>
        <div className="flex-1 max-w-3xl">
          <div className="bg-gray-100 dark:bg-gray-700 rounded-lg px-4 py-3 shadow-sm">
            {/* Query */}
            <div className="mb-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase">
                  Generated Query
                </span>
                <div className="flex items-center space-x-1">
                  <button
                    onClick={() => copyToClipboard(message.content)}
                    className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors"
                    title="Copy query"
                  >
                    {copied ? (
                      <Check className="w-4 h-4 text-green-500" />
                    ) : (
                      <Copy className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                    )}
                  </button>
                  <button
                    onClick={() => downloadQuery(message.content)}
                    className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors"
                    title="Download query"
                  >
                    <Download className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                  </button>
                </div>
              </div>
              <pre className="bg-gray-900 dark:bg-gray-800 p-3 rounded text-sm overflow-x-auto">
                <code className={getLanguageClass(message.providerId)}>{message.content}</code>
              </pre>
            </div>

            {/* Confidence Score */}
            {message.confidence !== undefined && (
              <div className="mb-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-400">
                    Confidence Score
                  </span>
                  <span
                    className={`font-semibold ${
                      message.confidence >= 0.85
                        ? 'text-green-600 dark:text-green-400'
                        : message.confidence >= 0.7
                        ? 'text-yellow-600 dark:text-yellow-400'
                        : 'text-red-600 dark:text-red-400'
                    }`}
                  >
                    {(message.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2 mt-1">
                  <div
                    className={`h-2 rounded-full transition-all ${
                      message.confidence >= 0.85
                        ? 'bg-green-500'
                        : message.confidence >= 0.7
                        ? 'bg-yellow-500'
                        : 'bg-red-500'
                    }`}
                    style={{ width: `${message.confidence * 100}%` }}
                  />
                </div>
              </div>
            )}

            {/* Validation Status */}
            {message.validationStatus && (
              <div className="flex items-center space-x-2 text-sm">
                {message.validationStatus === 'valid' ? (
                  <>
                    <CheckCircle className="w-4 h-4 text-green-500" />
                    <span className="text-green-600 dark:text-green-400">
                      Query validated successfully
                    </span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-4 h-4 text-yellow-500" />
                    <span className="text-yellow-600 dark:text-yellow-400">
                      {message.validationStatus}
                    </span>
                  </>
                )}
              </div>
            )}

            {/* Execution Result */}
            {message.executionResult && (
              <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-600">
                <div className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase mb-2">
                  Execution Result
                </div>
                {message.executionResult.success ? (
                  <div className="space-y-1 text-sm">
                    <p className="text-gray-700 dark:text-gray-300">
                      <span className="font-semibold">Rows:</span>{' '}
                      {message.executionResult.row_count}
                    </p>
                    <p className="text-gray-700 dark:text-gray-300">
                      <span className="font-semibold">Time:</span>{' '}
                      {message.executionResult.execution_time_ms}ms
                    </p>
                  </div>
                ) : (
                  <p className="text-sm text-red-600 dark:text-red-400">
                    {message.executionResult.error || 'Execution failed'}
                  </p>
                )}
              </div>
            )}

            {/* Trace Info */}
            {message.trace && (
              <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-600">
                <button
                  onClick={() => setTraceExpanded(!traceExpanded)}
                  className="flex items-center justify-between w-full text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase cursor-pointer hover:text-gray-800 dark:hover:text-gray-200"
                >
                  <span>Processing Details & Reasoning Trace</span>
                  {traceExpanded ? (
                    <ChevronDown className="w-4 h-4" />
                  ) : (
                    <ChevronRight className="w-4 h-4" />
                  )}
                </button>

                {traceExpanded && (
                  <div className="mt-3 space-y-3">
                    {/* Summary Stats */}
                    <div className="grid grid-cols-3 gap-2 text-xs">
                      <div className="bg-gray-50 dark:bg-gray-800 p-2 rounded">
                        <div className="text-gray-500 dark:text-gray-400">Total Time</div>
                        <div className="text-lg font-semibold text-gray-900 dark:text-white">
                          {message.trace.orchestrator_latency_ms}ms
                        </div>
                      </div>
                      <div className="bg-gray-50 dark:bg-gray-800 p-2 rounded">
                        <div className="text-gray-500 dark:text-gray-400">Total Tokens</div>
                        <div className="text-lg font-semibold text-gray-900 dark:text-white">
                          {message.trace.total_tokens_input + message.trace.total_tokens_output}
                        </div>
                      </div>
                      <div className="bg-gray-50 dark:bg-gray-800 p-2 rounded">
                        <div className="text-gray-500 dark:text-gray-400">Cost</div>
                        <div className="text-lg font-semibold text-gray-900 dark:text-white">
                          ${message.trace.total_cost_usd.toFixed(4)}
                        </div>
                      </div>
                    </div>

                    {/* Agent Traces */}
                    <div className="space-y-2">
                      {[
                        { key: 'schema_agent', label: 'Schema Expert', icon: '🗂️' },
                        { key: 'rag_agent', label: 'RAG Retrieval', icon: '🔍' },
                        { key: 'query_builder_agent', label: 'Query Builder', icon: '⚙️' },
                        { key: 'validator_agent', label: 'Validator', icon: '✓' },
                      ].map(({ key, label, icon }) => {
                        const agent = message.trace[key]
                        if (!agent) return null

                        return (
                          <div key={key} className="bg-gray-50 dark:bg-gray-800 rounded p-2">
                            <button
                              onClick={() => toggleAgentDetails(key)}
                              className="flex items-center justify-between w-full text-left"
                            >
                              <div className="flex items-center space-x-2">
                                <span>{icon}</span>
                                <span className="text-sm font-medium text-gray-900 dark:text-white">
                                  {label}
                                </span>
                              </div>
                              <div className="flex items-center space-x-2">
                                <span className="text-xs text-gray-500 dark:text-gray-400">
                                  {agent.latency_ms}ms
                                </span>
                                {agentDetailsExpanded[key] ? (
                                  <ChevronDown className="w-3 h-3" />
                                ) : (
                                  <ChevronRight className="w-3 h-3" />
                                )}
                              </div>
                            </button>

                            {agentDetailsExpanded[key] && (
                              <div className="mt-2 pl-6 space-y-1 text-xs text-gray-700 dark:text-gray-300">
                                <div className="flex justify-between">
                                  <span>Input Tokens:</span>
                                  <span className="font-mono">{agent.tokens_input}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span>Output Tokens:</span>
                                  <span className="font-mono">{agent.tokens_output}</span>
                                </div>
                                {agent.iterations > 1 && (
                                  <div className="flex justify-between">
                                    <span>Iterations:</span>
                                    <span className="font-mono">{agent.iterations}</span>
                                  </div>
                                )}
                                {agent.details && Object.keys(agent.details).length > 0 && (
                                  <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
                                    <div className="font-semibold mb-1">Details:</div>
                                    {Object.entries(agent.details).map(([k, v]) => (
                                      <div key={k} className="flex justify-between">
                                        <span className="capitalize">{k.replace(/_/g, ' ')}:</span>
                                        <span className="font-mono">
                                          {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                                        </span>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {formatTimestamp(message.timestamp)}
          </p>
        </div>
      </div>
    )
  }

  if (message.type === 'error') {
    return (
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0">
          <div className="w-8 h-8 rounded-full bg-red-100 dark:bg-red-900 flex items-center justify-center">
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
          </div>
        </div>
        <div className="flex-1 max-w-3xl">
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg px-4 py-3">
            <p className="text-sm text-red-800 dark:text-red-300">{message.content}</p>
            {message.details && (
              <details className="mt-2">
                <summary className="text-xs text-red-600 dark:text-red-400 cursor-pointer">
                  Details
                </summary>
                <pre className="mt-1 text-xs text-red-700 dark:text-red-400 overflow-x-auto">
                  {JSON.stringify(message.details, null, 2)}
                </pre>
              </details>
            )}
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {formatTimestamp(message.timestamp)}
          </p>
        </div>
      </div>
    )
  }

  if (message.type === 'clarification') {
    return (
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0">
          <div className="w-8 h-8 rounded-full bg-yellow-100 dark:bg-yellow-900 flex items-center justify-center">
            <Info className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />
          </div>
        </div>
        <div className="flex-1 max-w-3xl">
          <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg px-4 py-3">
            <p className="text-sm font-semibold text-yellow-800 dark:text-yellow-300 mb-2">
              I need more information:
            </p>
            <ul className="list-disc list-inside space-y-1 text-sm text-yellow-700 dark:text-yellow-400">
              {Array.isArray(message.content) ? (
                message.content.map((question, idx) => <li key={idx}>{question}</li>)
              ) : (
                <li>{message.content}</li>
              )}
            </ul>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {formatTimestamp(message.timestamp)}
          </p>
        </div>
      </div>
    )
  }

  if (message.type === 'progress') {
    return (
      <div className="flex items-center justify-center">
        <div className="bg-gray-100 dark:bg-gray-700 rounded-full px-4 py-2 text-sm text-gray-600 dark:text-gray-400">
          <span className="animate-pulse">{message.content}</span>
        </div>
      </div>
    )
  }

  return null
}

export default ChatMessage
