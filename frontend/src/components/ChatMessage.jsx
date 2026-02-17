import { User, Bot, AlertCircle, CheckCircle, Info, Copy, Check, Download } from 'lucide-react'
import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import Prism from 'prismjs'
import '../styles/prism-custom.css'
import 'prismjs/components/prism-sql'
import 'prismjs/components/prism-mongodb'
import 'prismjs/components/prism-splunk-spl'
import FeedbackButton from './FeedbackButton'
import ConfidenceMeter from './ConfidenceMeter'
import AgentTimeline from './AgentTimeline'
import ResultsVisualization from './results/ResultsVisualization'

function ChatMessage({ message, conversationId }) {
  const [copied, setCopied] = useState(false)

  const stripThinkTags = (text) => text?.replace(/<think>[\s\S]*?<\/think>/g, '').trim() || ''

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
            {message.responseType === 'text' ? (
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{stripThinkTags(message.content)}</ReactMarkdown>
              </div>
            ) : (
              <>
                {/* Query */}
                <div className="mb-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase">
                      Generated Query
                    </span>
                    <div className="flex items-center space-x-1">
                      <button
                        onClick={() => copyToClipboard(message.generatedQuery || message.content)}
                        className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
                        title="Copy query"
                        aria-label={copied ? 'Query copied' : 'Copy query'}
                      >
                        {copied ? (
                          <Check className="w-4 h-4 text-green-500" aria-hidden="true" />
                        ) : (
                          <Copy className="w-4 h-4 text-gray-500 dark:text-gray-400" aria-hidden="true" />
                        )}
                      </button>
                      <button
                        onClick={() => downloadQuery(message.generatedQuery || message.content)}
                        className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
                        title="Download query"
                        aria-label="Download query"
                      >
                        <Download className="w-4 h-4 text-gray-500 dark:text-gray-400" aria-hidden="true" />
                      </button>
                    </div>
                  </div>
                  <div className="prose prose-sm dark:prose-invert max-w-none">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        code({ node, className, children, ...props }) {
                          const isBlock = node?.position?.start?.line !== node?.position?.end?.line || className
                          const isInsidePre = node?.parentNode?.tagName === 'pre'
                          if (isBlock || isInsidePre) {
                            return (
                              <code className={className || getLanguageClass(message.providerId)} {...props}>{children}</code>
                            )
                          }
                          return (
                            <code className="bg-gray-200 dark:bg-gray-600 px-1.5 py-0.5 rounded text-sm" {...props}>{children}</code>
                          )
                        },
                        pre({ children }) {
                          return (
                            <pre className="bg-gray-900 dark:bg-gray-800 text-gray-100 p-3 rounded text-sm overflow-x-auto">{children}</pre>
                          )
                        },
                      }}
                    >
                      {stripThinkTags(message.content)}
                    </ReactMarkdown>
                  </div>
                </div>

                {/* Query Explanation */}
                {message.explanation && (
                  <div className="mb-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded border border-blue-200 dark:border-blue-800">
                    <div className="flex items-start space-x-2">
                      <Info className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                      <div>
                        <span className="text-xs font-semibold text-blue-700 dark:text-blue-300 uppercase block mb-1">
                          Query Explanation
                        </span>
                        <p className="text-sm text-blue-900 dark:text-blue-100">
                          {message.explanation}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* Confidence Meter */}
                {message.confidence !== undefined && (
                  <ConfidenceMeter 
                    confidence={message.confidence}
                    history={message.confidenceHistory || []}
                    showHistory={message.confidenceHistory && message.confidenceHistory.length > 1}
                  />
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

                    {/* Results Visualization */}
                    {message.executionResult.success &&
                     message.executionResult.data &&
                     message.executionResult.data.length > 0 && (
                      <div className="mt-4">
                        <ResultsVisualization
                          data={message.executionResult.data}
                          rowCount={message.executionResult.row_count}
                          executionTimeMs={message.executionResult.execution_time_ms}
                        />
                      </div>
                    )}
                  </div>
                )}

                {/* Agent Timeline - Visual trace of agent processing */}
                {message.trace && (
                  <AgentTimeline 
                    trace={message.trace} 
                    progress={message.progress}
                    isProcessing={false}
                  />
                )}
              </>
            )}
          </div>

          {/* Feedback Buttons */}
          {conversationId && message.turnId && (
            <FeedbackButton
              conversationId={conversationId}
              turnId={message.turnId}
            />
          )}
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
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0">
          <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
            <Bot className="w-5 h-5 text-blue-600 dark:text-blue-400 animate-pulse" />
          </div>
        </div>
        <div className="flex-1 max-w-3xl">
          <div className="bg-gray-100 dark:bg-gray-700 rounded-lg px-4 py-3 shadow-sm">
            <AgentTimeline 
              trace={null}
              progress={{ stage: message.stage, message: message.content }}
              isProcessing={true}
            />
          </div>
        </div>
      </div>
    )
  }

  return null
}

export default ChatMessage
