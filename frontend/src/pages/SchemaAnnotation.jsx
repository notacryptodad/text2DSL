import { useState, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Database,
  Sparkles,
  MessageSquare,
  Send,
  Loader2,
  AlertCircle,
  User,
  Bot,
  RefreshCw,
  Table,
} from 'lucide-react'
import SchemaTree from '../components/SchemaTree'
import AnnotationEditor from '../components/AnnotationEditor'
import { useWorkspace } from '../contexts/WorkspaceContext'

function SchemaAnnotation() {
  const [searchParams] = useSearchParams()
  const { currentWorkspace, currentConnection } = useWorkspace()
  const [workspaces, setWorkspaces] = useState([])
  const [selectedWorkspace, setSelectedWorkspace] = useState('')
  const [connections, setConnections] = useState([])
  const [selectedConnection, setSelectedConnection] = useState('')
  const [selectedProviderId, setSelectedProviderId] = useState('')
  const [schema, setSchema] = useState([])
  const [annotations, setAnnotations] = useState({})
  const [selectedTable, setSelectedTable] = useState(null)
  const [showEditor, setShowEditor] = useState(false)
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState(null)
  const [focusColumn, setFocusColumn] = useState(null)

  // Chat state
  const [chatMessages, setChatMessages] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [conversationId, setConversationId] = useState(null)
  const [autoAnnotationSuggestions, setAutoAnnotationSuggestions] = useState(null)
  const chatEndRef = useRef(null)
  const chatSectionRef = useRef(null)

  useEffect(() => {
    fetchWorkspaces()
  }, [])

  // Initialize from context or URL params
  useEffect(() => {
    const wsParam = searchParams.get('workspace')
    const connParam = searchParams.get('connection')
    
    if (wsParam) {
      setSelectedWorkspace(wsParam)
    } else if (currentWorkspace?.id) {
      setSelectedWorkspace(currentWorkspace.id)
    }
    
    if (connParam) {
      setSelectedConnection(connParam)
      // Find provider_id from connections if already loaded
      const conn = connections.find(c => c.id === connParam)
      if (conn) {
        setSelectedProviderId(conn.provider_id)
      }
    } else if (currentConnection?.id) {
      setSelectedConnection(currentConnection.id)
      setSelectedProviderId(currentConnection.provider_id)
    }
  }, [searchParams, currentWorkspace, currentConnection, connections])

  useEffect(() => {
    if (selectedWorkspace) {
      fetchConnections(selectedWorkspace)
    }
  }, [selectedWorkspace])

  useEffect(() => {
    if (selectedConnection) {
      fetchSchema()
      fetchAnnotations()
    }
  }, [selectedConnection])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  const getApiUrl = () => {
    // Use empty string to leverage Vite proxy - avoids CORS issues
    return ''
  }

  const fetchWorkspaces = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch(`${getApiUrl()}/api/v1/workspaces`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      })
      if (!response.ok) throw new Error('Failed to fetch workspaces')
      const data = await response.json()
      setWorkspaces(data)
      // Only set default if no URL param is present
      const wsParam = searchParams.get('workspace')
      if (data.length > 0 && !wsParam) {
        setSelectedWorkspace(data[0].id)
      }
    } catch (err) {
      console.error('Error fetching workspaces:', err)
      setError('Failed to load workspaces')
    }
  }

  const fetchConnections = async (workspaceId) => {
    try {
      setError(null)
      const token = localStorage.getItem('access_token')
      console.log('fetchConnections called, workspaceId:', workspaceId, 'token exists:', !!token)
      if (!token) {
        console.warn('No access token found, skipping fetchConnections')
        setError('Please log in to view connections')
        return
      }
      // First fetch providers for this workspace
      const providersUrl = `${getApiUrl()}/api/v1/workspaces/${workspaceId}/providers`
      console.log('Fetching providers from:', providersUrl)
      const providersRes = await fetch(
        providersUrl,
        {
          headers: { 'Authorization': `Bearer ${token}` },
        }
      )
      console.log('Providers response status:', providersRes.status)
      if (!providersRes.ok) {
        const errorText = await providersRes.text()
        console.error(`Failed to fetch providers: ${providersRes.status}`, errorText)
        throw new Error(`Failed to fetch providers: ${providersRes.status}`)
      }
      const providers = await providersRes.json()
      console.log('Providers fetched:', providers.length)
      
      // Fetch connections for each provider
      const allConnections = []
      for (const provider of providers) {
        const connRes = await fetch(
          `${getApiUrl()}/api/v1/workspaces/${workspaceId}/providers/${provider.id}/connections`,
          {
            headers: { 'Authorization': `Bearer ${token}` },
          }
        )
        if (connRes.ok) {
          const conns = await connRes.json()
          console.log('Connections for provider', provider.id, ':', conns.length)
          conns.forEach(c => {
            allConnections.push({ ...c, provider_id: provider.id, provider_name: provider.name })
          })
        }
      }
      
      console.log('Total connections fetched:', allConnections.length)
      setConnections(allConnections)
      
      // Check URL param or select first
      const connParam = searchParams.get('connection')
      if (connParam && allConnections.find(c => c.id === connParam)) {
        const conn = allConnections.find(c => c.id === connParam)
        setSelectedConnection(connParam)
        setSelectedProviderId(conn.provider_id)
      } else if (allConnections.length > 0) {
        setSelectedConnection(allConnections[0].id)
        setSelectedProviderId(allConnections[0].provider_id)
      }
    } catch (err) {
      console.error('Error fetching connections:', err)
      setError('Failed to load connections')
    }
  }

  const handleConnectionChange = (connId) => {
    setSelectedConnection(connId)
    const conn = connections.find(c => c.id === connId)
    if (conn) {
      setSelectedProviderId(conn.provider_id)
    }
  }

  const fetchSchema = async () => {
    if (!selectedWorkspace || !selectedConnection) return

    try {
      setLoading(true)
      setError(null)
      const token = localStorage.getItem('access_token')
      const response = await fetch(
        `${getApiUrl()}/api/v1/annotations/workspaces/${selectedWorkspace}/connections/${selectedConnection}/schema`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      )
      if (!response.ok) throw new Error('Failed to fetch schema')
      const data = await response.json()
      setSchema(data.tables || data)
    } catch (err) {
      console.error('Error fetching schema:', err)
      setError('Failed to load schema')
    } finally {
      setLoading(false)
    }
  }

  const handleRefreshSchema = async () => {
    if (!selectedWorkspace || !selectedConnection || !selectedProviderId) {
      setError('Provider ID is required to refresh schema')
      return
    }

    try {
      setRefreshing(true)
      setError(null)
      const token = localStorage.getItem('access_token')
      const response = await fetch(
        `${getApiUrl()}/api/v1/workspaces/${selectedWorkspace}/providers/${selectedProviderId}/connections/${selectedConnection}/schema/refresh`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      )
      if (!response.ok) throw new Error('Failed to refresh schema')
      const result = await response.json()
      // Re-fetch schema after refresh
      await fetchSchema()
      alert(`Schema refreshed! Found ${result.table_count || 0} tables.`)
    } catch (err) {
      console.error('Error refreshing schema:', err)
      setError('Failed to refresh schema')
    } finally {
      setRefreshing(false)
    }
  }

  const fetchAnnotations = async () => {
    if (!selectedWorkspace || !selectedConnection) return

    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch(
        `${getApiUrl()}/api/v1/annotations/workspaces/${selectedWorkspace}/connections/${selectedConnection}/schema/annotations`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      )
      // Gracefully handle missing endpoint - annotations are optional
      if (response.status === 404) {
        console.log('Annotations endpoint not found, skipping')
        setAnnotations({})
        return
      }
      if (!response.ok) throw new Error('Failed to fetch annotations')
      const data = await response.json()

      const annotationsMap = {}
      // Check if data is array or object
      const annList = Array.isArray(data) ? data : Object.values(data)
      annList.forEach((ann) => {
        if (ann.table_name) {
          // Check if table still exists in schema
          const tableExists = schema.some(t => (t.name || t.table_name) === ann.table_name)
          annotationsMap[ann.table_name] = {
            ...ann,
            _orphaned: !tableExists && schema.length > 0
          }
        }
      })
      setAnnotations(annotationsMap)
    } catch (err) {
      console.error('Error fetching annotations:', err)
      // Don't show error for annotations - they're optional
      setAnnotations({})
    }
  }

  const handleAutoAnnotate = async () => {
    if (!selectedWorkspace || !selectedConnection) return
    if (!selectedTable) {
      setChatMessages([
        ...chatMessages,
        {
          type: 'error',
          content: 'Please select a table first to auto-annotate.',
          timestamp: new Date(),
        },
      ])
      // Scroll to chat section to show the error
      chatSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      return
    }

    // Scroll to chat section immediately when auto-annotate is clicked
    chatSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })

    try {
      setChatLoading(true)
      const token = localStorage.getItem('access_token')
      const response = await fetch(
        `${getApiUrl()}/api/v1/annotations/workspaces/${selectedWorkspace}/connections/${selectedConnection}/schema/auto-annotate`,
        {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({ table_name: selectedTable }),
        }
      )

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.message || 'Failed to auto-annotate')
      }
      const data = await response.json()

      // Store the structured suggestions
      if (data.suggestions) {
        const { table_description, table_business_terms, columns } = data.suggestions

        // Create annotation structure from suggestions
        const suggestedAnnotation = {
          table_name: selectedTable,
          description: table_description || '',
          columns: columns || [],
          business_terms: table_business_terms || [],
          relationships: []
        }

        setAutoAnnotationSuggestions(suggestedAnnotation)

        // Show success message with summary
        const columnCount = columns?.length || 0
        const termsCount = table_business_terms?.length || 0
        let message = table_description
          ? `Auto-annotation completed!\n\nTable: ${table_description}\n\nGenerated descriptions for ${columnCount} column${columnCount !== 1 ? 's' : ''}.`
          : `Auto-annotation completed for table "${selectedTable}"!`
        
        if (termsCount > 0) {
          message += `\n\nSuggested ${termsCount} business term${termsCount !== 1 ? 's' : ''}: ${table_business_terms.join(', ')}`
        }

        setChatMessages([
          ...chatMessages,
          {
            type: 'assistant',
            content: message,
            timestamp: new Date(),
          },
        ])
      } else {
        setChatMessages([
          ...chatMessages,
          {
            type: 'assistant',
            content: `Auto-annotation completed for table "${selectedTable}"!`,
            timestamp: new Date(),
          },
        ])
      }

      await fetchAnnotations()
    } catch (err) {
      console.error('Error auto-annotating:', err)
      setChatMessages([
        ...chatMessages,
        {
          type: 'error',
          content: `Failed to auto-annotate: ${err.message}`,
          timestamp: new Date(),
        },
      ])
    } finally {
      setChatLoading(false)
    }
  }

  const handleSendMessage = async () => {
    if (!chatInput.trim() || !selectedWorkspace || !selectedConnection) return

    const userMessage = {
      type: 'user',
      content: chatInput.trim(),
      timestamp: new Date(),
    }

    setChatMessages([...chatMessages, userMessage])
    setChatInput('')
    setChatLoading(true)

    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch(
        `${getApiUrl()}/api/v1/agentcore/annotation_assistant/chat`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({
            message: userMessage.content,
            conversation_id: conversationId,
            context: {
              selected_table: selectedTable,
              provider_id: selectedProviderId,
              user_id: 'current_user',
            },
          }),
        }
      )

      if (!response.ok) throw new Error('Failed to send message')
      const data = await response.json()

      setConversationId(data.conversation_id)

      setChatMessages([
        ...chatMessages,
        userMessage,
        {
          type: 'assistant',
          content: data.response,
          timestamp: new Date(),
        },
      ])

      // If tools were called (e.g., save_annotation), refresh annotations
      if (data.tool_calls && data.tool_calls.length > 0) {
        const hasAnnotationSave = data.tool_calls.some(tc => tc.tool === 'save_annotation')
        if (hasAnnotationSave) {
          await fetchAnnotations()
        }
      }
    } catch (err) {
      console.error('Error sending message:', err)
      setChatMessages([
        ...chatMessages,
        userMessage,
        {
          type: 'error',
          content: 'Failed to get response. Please try again.',
          timestamp: new Date(),
        },
      ])
    } finally {
      setChatLoading(false)
    }
  }

  const handleSaveAnnotation = async (annotationData) => {
    if (!selectedWorkspace || !selectedConnection) return

    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch(
        `${getApiUrl()}/api/v1/annotations/workspaces/${selectedWorkspace}/connections/${selectedConnection}/schema/annotations`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify(annotationData),
        }
      )

      if (!response.ok) throw new Error('Failed to save annotation')

      await fetchAnnotations()
      setAutoAnnotationSuggestions(null)

      setChatMessages([
        ...chatMessages,
        {
          type: 'assistant',
          content: `Annotation for table "${annotationData.table_name}" saved successfully!`,
          timestamp: new Date(),
        },
      ])
    } catch (err) {
      console.error('Error saving annotation:', err)
      alert('Failed to save annotation. Please try again.')
    }
  }

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="flex min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      <div className="flex-1 p-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Schema Annotation
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Annotate database schemas to improve query generation accuracy
          </p>
        </div>

        {/* Workspace & Connection Selector */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4 mb-6">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Database className="w-5 h-5 text-primary-500" />
              <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                Source:
              </span>
            </div>

            <select
              value={selectedWorkspace}
              onChange={(e) => setSelectedWorkspace(e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              {workspaces.map((workspace) => (
                <option key={workspace.id} value={workspace.id}>
                  {workspace.name}
                </option>
              ))}
            </select>

            <select
              value={selectedConnection}
              onChange={(e) => handleConnectionChange(e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              disabled={!connections.length}
            >
              {connections.map((connection) => (
                <option key={connection.id} value={connection.id}>
                  {connection.name} ({connection.host}:{connection.port}/{connection.database})
                </option>
              ))}
            </select>

            <button
              onClick={handleRefreshSchema}
              disabled={!selectedConnection || refreshing}
              className="flex items-center space-x-2 px-4 py-2 bg-purple-500 text-white rounded-md hover:bg-purple-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              title="Refresh schema from database"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              <span>{refreshing ? 'Refreshing...' : 'Refresh Schema'}</span>
            </button>

            <button
              onClick={handleAutoAnnotate}
              disabled={!selectedConnection || chatLoading}
              className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-primary-500 to-primary-600 text-white rounded-md hover:from-primary-600 hover:to-primary-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Sparkles className="w-4 h-4" />
              <span>Auto-Annotate</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6 flex items-center space-x-2">
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
            <span className="text-red-800 dark:text-red-300">{error}</span>
          </div>
        )}

        {/* Main Content - Responsive layout:
            - Mobile: stacked
            - lg (1024px+): Schema | Editor+Chat stacked
            - 2xl (1536px+): Schema | Editor | Chat (3 columns)
        */}
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Schema Tree - fixed width on larger screens */}
          <div className="w-full lg:w-80 2xl:w-72 flex-shrink-0">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4 sticky top-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Schema
              </h2>
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
                </div>
              ) : (
                <div className="max-h-[calc(100vh-16rem)] overflow-y-auto">
                  <SchemaTree
                    schema={schema}
                    onTableSelect={(tableName) => {
                      setSelectedTable(tableName)
                      setShowEditor(true)
                      setAutoAnnotationSuggestions(null)
                      setFocusColumn(null)
                    }}
                    onColumnSelect={(tableName, columnName) => {
                      setSelectedTable(tableName)
                      setShowEditor(true)
                      setAutoAnnotationSuggestions(null)
                      setFocusColumn(columnName)
                    }}
                    selectedTable={selectedTable}
                    annotations={annotations}
                  />
                </div>
              )}
            </div>
          </div>

          {/* Middle section: Editor (+ Chat on non-ultra-wide) */}
          <div className="flex-1 min-w-0 space-y-6 2xl:space-y-0">
            {/* Annotation Editor or Placeholder */}
            {showEditor && selectedTable ? (
              <AnnotationEditor
                tableName={selectedTable}
                schema={schema}
                annotation={autoAnnotationSuggestions || annotations[selectedTable]}
                onSave={handleSaveAnnotation}
                onCancel={() => {
                  setShowEditor(false)
                  setSelectedTable(null)
                  setAutoAnnotationSuggestions(null)
                  setFocusColumn(null)
                }}
                focusColumn={focusColumn}
              />
            ) : (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-12">
                <div className="text-center max-w-md mx-auto">
                  <div className="w-16 h-16 bg-primary-100 dark:bg-primary-900/30 rounded-full flex items-center justify-center mx-auto mb-6">
                    <Table className="w-8 h-8 text-primary-500" />
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-3">
                    Select a Table to Annotate
                  </h3>
                  <p className="text-gray-600 dark:text-gray-400 mb-6">
                    Choose a table from the schema tree on the left to start adding annotations. 
                    Annotations help improve query generation accuracy by providing context about your data.
                  </p>
                  <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 text-left">
                    <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      💡 Quick tips:
                    </p>
                    <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                      <li>• Click on a table name to open the annotation editor</li>
                      <li>• Use <strong>Auto-Annotate</strong> to generate AI suggestions</li>
                      <li>• Add business terms and descriptions for better results</li>
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* Chat Interface - shown below editor on screens smaller than 2xl */}
            <div className="2xl:hidden" ref={chatSectionRef}>
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 flex flex-col h-[600px]">
              <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-center space-x-2">
                  <MessageSquare className="w-5 h-5 text-primary-500" />
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Annotation Assistant
                  </h2>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Chat with the AI to refine and improve your annotations
                </p>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {chatMessages.length === 0 ? (
                  <div className="text-center py-12">
                    <MessageSquare className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                    <p className="text-gray-500 dark:text-gray-400">
                      Start a conversation to get help with annotations
                    </p>
                    <div className="mt-6 space-y-2">
                      <p className="text-sm text-gray-600 dark:text-gray-400">Try asking:</p>
                      <div className="flex flex-wrap gap-2 justify-center">
                        {[
                          'What are the key tables in this schema?',
                          'Help me annotate the customers table',
                          'What relationships should I add?',
                        ].map((suggestion, idx) => (
                          <button
                            key={idx}
                            onClick={() => setChatInput(suggestion)}
                            className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                          >
                            {suggestion}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <>
                    {chatMessages.map((message, index) => (
                      <div
                        key={index}
                        className={`flex items-start space-x-3 ${
                          message.type === 'user' ? 'justify-end' : ''
                        }`}
                      >
                        {message.type !== 'user' && (
                          <div className="flex-shrink-0">
                            <div
                              className={`w-8 h-8 rounded-full flex items-center justify-center ${
                                message.type === 'error'
                                  ? 'bg-red-100 dark:bg-red-900'
                                  : 'bg-gray-100 dark:bg-gray-700'
                              }`}
                            >
                              {message.type === 'error' ? (
                                <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
                              ) : (
                                <Bot className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                              )}
                            </div>
                          </div>
                        )}
                        <div className={`flex-1 max-w-3xl ${message.type === 'user' ? 'text-right' : ''}`}>
                          <div
                            className={`rounded-lg px-4 py-3 ${
                              message.type === 'user'
                                ? 'bg-primary-500 text-white inline-block'
                                : message.type === 'error'
                                ? 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-300'
                                : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
                            }`}
                          >
                            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                          </div>
                          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                            {formatTimestamp(message.timestamp)}
                          </p>
                        </div>
                        {message.type === 'user' && (
                          <div className="flex-shrink-0">
                            <div className="w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center">
                              <User className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                    <div ref={chatEndRef} />
                  </>
                )}
              </div>

              {/* Input */}
              <div className="p-4 border-t border-gray-200 dark:border-gray-700">
                <div className="flex space-x-2">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && !chatLoading && handleSendMessage()}
                    placeholder="Ask about schema annotations..."
                    disabled={chatLoading || !selectedConnection}
                    className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
                  />
                  <button
                    onClick={handleSendMessage}
                    disabled={!chatInput.trim() || chatLoading || !selectedConnection}
                    className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {chatLoading ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <Send className="w-5 h-5" />
                    )}
                  </button>
                </div>
              </div>
            </div>
            </div>
          </div>

          {/* Chat Interface - separate column on ultra-wide (2xl+) screens */}
          <div className="hidden 2xl:block w-96 flex-shrink-0">
            <div ref={chatSectionRef} className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 flex flex-col h-[calc(100vh-12rem)] sticky top-4">
              <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-center space-x-2">
                  <MessageSquare className="w-5 h-5 text-primary-500" />
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Annotation Assistant
                  </h2>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Chat with the AI to refine annotations
                </p>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {chatMessages.length === 0 ? (
                  <div className="text-center py-8">
                    <MessageSquare className="w-10 h-10 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Start a conversation to get help
                    </p>
                  </div>
                ) : (
                  <>
                    {chatMessages.map((message, index) => (
                      <div
                        key={index}
                        className={`flex items-start space-x-2 ${
                          message.type === 'user' ? 'flex-row-reverse space-x-reverse' : ''
                        }`}
                      >
                        {message.type !== 'user' && (
                          <div className="flex-shrink-0">
                            <div
                              className={`w-7 h-7 rounded-full flex items-center justify-center ${
                                message.type === 'error'
                                  ? 'bg-red-100 dark:bg-red-900'
                                  : 'bg-gray-100 dark:bg-gray-700'
                              }`}
                            >
                              {message.type === 'error' ? (
                                <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400" />
                              ) : (
                                <Bot className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                              )}
                            </div>
                          </div>
                        )}
                        <div className={`flex-1 ${message.type === 'user' ? 'text-right' : ''}`}>
                          <div
                            className={`rounded-lg px-3 py-2 text-sm ${
                              message.type === 'user'
                                ? 'bg-primary-500 text-white inline-block'
                                : message.type === 'error'
                                ? 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-300'
                                : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
                            }`}
                          >
                            <p className="whitespace-pre-wrap">{message.content}</p>
                          </div>
                        </div>
                        {message.type === 'user' && (
                          <div className="flex-shrink-0">
                            <div className="w-7 h-7 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center">
                              <User className="w-4 h-4 text-primary-600 dark:text-primary-400" />
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                    <div ref={chatEndRef} />
                  </>
                )}
              </div>

              {/* Input */}
              <div className="p-3 border-t border-gray-200 dark:border-gray-700">
                <div className="flex space-x-2">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && !chatLoading && handleSendMessage()}
                    placeholder="Ask about annotations..."
                    className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
                    disabled={chatLoading || !selectedConnection}
                  />
                  <button
                    onClick={handleSendMessage}
                    disabled={!chatInput.trim() || chatLoading || !selectedConnection}
                    className="px-3 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {chatLoading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SchemaAnnotation
