import { useState, useEffect, useRef } from 'react'
import {
  Database,
  Sparkles,
  MessageSquare,
  Send,
  Loader2,
  AlertCircle,
  User,
  Bot,
} from 'lucide-react'
import SchemaTree from '../components/SchemaTree'
import AnnotationEditor from '../components/AnnotationEditor'

function SchemaAnnotation() {
  const [workspaces, setWorkspaces] = useState([])
  const [selectedWorkspace, setSelectedWorkspace] = useState('')
  const [connections, setConnections] = useState([])
  const [selectedConnection, setSelectedConnection] = useState('')
  const [schema, setSchema] = useState([])
  const [annotations, setAnnotations] = useState({})
  const [selectedTable, setSelectedTable] = useState(null)
  const [showEditor, setShowEditor] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Chat state
  const [chatMessages, setChatMessages] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [conversationId, setConversationId] = useState(null)
  const chatEndRef = useRef(null)

  useEffect(() => {
    fetchWorkspaces()
  }, [])

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
    return import.meta.env.DEV ? 'http://localhost:8000' : window.location.origin
  }

  const fetchWorkspaces = async () => {
    try {
      const response = await fetch(`${getApiUrl()}/api/v1/workspaces`)
      if (!response.ok) throw new Error('Failed to fetch workspaces')
      const data = await response.json()
      setWorkspaces(data)
      if (data.length > 0) {
        setSelectedWorkspace(data[0].id)
      }
    } catch (err) {
      console.error('Error fetching workspaces:', err)
      setError('Failed to load workspaces')
    }
  }

  const fetchConnections = async (workspaceId) => {
    try {
      const response = await fetch(`${getApiUrl()}/api/v1/workspaces/${workspaceId}/connections`)
      if (!response.ok) throw new Error('Failed to fetch connections')
      const data = await response.json()
      setConnections(data)
      if (data.length > 0) {
        setSelectedConnection(data[0].id)
      }
    } catch (err) {
      console.error('Error fetching connections:', err)
      setError('Failed to load connections')
    }
  }

  const fetchSchema = async () => {
    if (!selectedWorkspace || !selectedConnection) return

    try {
      setLoading(true)
      setError(null)
      const response = await fetch(
        `${getApiUrl()}/api/v1/workspaces/${selectedWorkspace}/connections/${selectedConnection}/schema`
      )
      if (!response.ok) throw new Error('Failed to fetch schema')
      const data = await response.json()
      setSchema(data)
    } catch (err) {
      console.error('Error fetching schema:', err)
      setError('Failed to load schema')
    } finally {
      setLoading(false)
    }
  }

  const fetchAnnotations = async () => {
    if (!selectedWorkspace || !selectedConnection) return

    try {
      const response = await fetch(
        `${getApiUrl()}/api/v1/workspaces/${selectedWorkspace}/connections/${selectedConnection}/schema/annotations`
      )
      if (!response.ok) throw new Error('Failed to fetch annotations')
      const data = await response.json()

      const annotationsMap = {}
      data.forEach((ann) => {
        annotationsMap[ann.table_name] = ann
      })
      setAnnotations(annotationsMap)
    } catch (err) {
      console.error('Error fetching annotations:', err)
    }
  }

  const handleAutoAnnotate = async () => {
    if (!selectedWorkspace || !selectedConnection) return

    try {
      setChatLoading(true)
      const response = await fetch(
        `${getApiUrl()}/api/v1/workspaces/${selectedWorkspace}/connections/${selectedConnection}/schema/auto-annotate`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        }
      )

      if (!response.ok) throw new Error('Failed to auto-annotate')
      const data = await response.json()

      setChatMessages([
        ...chatMessages,
        {
          type: 'assistant',
          content: `Auto-annotation completed! Generated annotations for ${data.annotated_count} tables.`,
          timestamp: new Date(),
        },
      ])

      await fetchAnnotations()
    } catch (err) {
      console.error('Error auto-annotating:', err)
      setChatMessages([
        ...chatMessages,
        {
          type: 'error',
          content: 'Failed to auto-annotate schema. Please try again.',
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
      const response = await fetch(
        `${getApiUrl()}/api/v1/workspaces/${selectedWorkspace}/connections/${selectedConnection}/schema/chat`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: userMessage.content,
            conversation_id: conversationId,
            context: {
              selected_table: selectedTable,
              annotations: annotations,
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

      if (data.updated_annotations) {
        setAnnotations({ ...annotations, ...data.updated_annotations })
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
      const response = await fetch(
        `${getApiUrl()}/api/v1/workspaces/${selectedWorkspace}/connections/${selectedConnection}/schema/annotations`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(annotationData),
        }
      )

      if (!response.ok) throw new Error('Failed to save annotation')

      await fetchAnnotations()
      setShowEditor(false)
      setSelectedTable(null)

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
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
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
              onChange={(e) => setSelectedConnection(e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              disabled={!connections.length}
            >
              {connections.map((connection) => (
                <option key={connection.id} value={connection.id}>
                  {connection.name} ({connection.type})
                </option>
              ))}
            </select>

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

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Schema Tree */}
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4 sticky top-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Database Schema
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
                    }}
                    selectedTable={selectedTable}
                    annotations={annotations}
                  />
                </div>
              )}
            </div>
          </div>

          {/* Annotation Editor / Chat */}
          <div className="lg:col-span-2 space-y-6">
            {/* Annotation Editor */}
            {showEditor && selectedTable && (
              <AnnotationEditor
                tableName={selectedTable}
                schema={schema}
                annotation={annotations[selectedTable]}
                onSave={handleSaveAnnotation}
                onCancel={() => {
                  setShowEditor(false)
                  setSelectedTable(null)
                }}
              />
            )}

            {/* Chat Interface */}
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
      </div>
    </div>
  )
}

export default SchemaAnnotation
