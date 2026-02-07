import { useState, useEffect, useRef } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
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
  const navigate = useNavigate()
  const { currentWorkspace, workspaces, selectWorkspace, loading: wsLoading } = useWorkspace()
  const [connections, setConnections] = useState([])
  const [connLoading, setConnLoading] = useState(false)
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

  const chatEndRef = useRef(null)
  const chatSectionRef = useRef(null)
  const [chatMessages, setChatMessages] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [conversationId, setConversationId] = useState(null)
  const [autoAnnotationSuggestions, setAutoAnnotationSuggestions] = useState(null)

  const apiUrl = ''

  const wsParam = searchParams.get('workspace')
  const connParam = searchParams.get('connection')

  useEffect(() => {
    // Fetch workspaces on mount
    if (!workspaces.length && !wsLoading) {
      // Workspaces empty and not loading - nothing to do
      return
    }
    
    // If we have a workspace param, ensure it's selected
    if (wsParam && currentWorkspace?.id !== wsParam) {
      const ws = workspaces.find(w => w.id === wsParam)
      if (ws) selectWorkspace(ws)
    }
    
    // Fetch connections for current workspace
    const workspaceId = wsParam || currentWorkspace?.id
    if (workspaceId) {
      fetchConnections(workspaceId)
    }
  }, [wsLoading, wsParam, currentWorkspace, workspaces.length])

  useEffect(() => {
    if (selectedConnection) {
      fetchSchema()
      fetchAnnotations()
    }
  }, [selectedConnection])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  const fetchConnections = async (workspaceId) => {
    if (!workspaceId) return
    setConnLoading(true)
    try {
      setError(null)
      const token = localStorage.getItem('access_token')
      if (!token) {
        setError('Please log in to view connections')
        return
      }
      const providersRes = await fetch(
        `${apiUrl}/api/v1/workspaces/${workspaceId}/providers`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      )
      if (!providersRes.ok) throw new Error('Failed to fetch providers')
      const providers = await providersRes.json()

      const allConnections = []
      for (const provider of providers) {
        const connRes = await fetch(
          `${apiUrl}/api/v1/workspaces/${workspaceId}/providers/${provider.id}/connections`,
          { headers: { 'Authorization': `Bearer ${token}` } }
        )
        if (connRes.ok) {
          const conns = await connRes.json()
          conns.forEach(c => {
            allConnections.push({ ...c, provider_id: provider.id, provider_name: provider.name, workspace_id: workspaceId })
          })
        }
      }

      setConnections(allConnections)

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
    } finally {
      setConnLoading(false)
    }
  }

  const fetchSchema = async () => {
    if (!selectedConnection) return
    try {
      setLoading(true)
      setError(null)
      const token = localStorage.getItem('access_token')
      const response = await fetch(
        `${apiUrl}/api/v1/annotations/workspaces/${wsParam || currentWorkspace?.id}/providers/${selectedProviderId}/connections/${selectedConnection}/schema`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      )
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}))
        throw new Error(errData.detail || 'Failed to fetch schema')
      }
      const data = await response.json()
      const mongoCollections = (data.collections || []).map(c =>
        typeof c === 'string' ? { name: c, columns: [], document_count: 0 } : c
      )
      setSchema([...(data.tables || []), ...mongoCollections])
    } catch (err) {
      console.error('Error fetching schema:', err)
      setError('Failed to load schema: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const fetchAnnotations = async () => {
    if (!selectedConnection) return
    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch(
        `${apiUrl}/api/v1/annotations/workspaces/${wsParam || currentWorkspace?.id}/providers/${selectedProviderId}/connections/${selectedConnection}/schema/annotations`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      )
      if (response.status === 404) {
        setAnnotations({})
        return
      }
      if (!response.ok) throw new Error('Failed to fetch annotations')
      const data = await response.json()
      const annotationsMap = {}
      const annList = Array.isArray(data) ? data : Object.values(data)
      annList.forEach((ann) => {
        if (ann.table_name) {
          annotationsMap[ann.table_name] = ann
        }
      })
      setAnnotations(annotationsMap)
    } catch (err) {
      console.error('Error fetching annotations:', err)
      setAnnotations({})
    }
  }

  const handleRefreshSchema = async () => {
    if (!selectedConnection || !selectedProviderId) {
      setError('Provider ID is required to refresh schema')
      return
    }
    try {
      setRefreshing(true)
      setError(null)
      const token = localStorage.getItem('access_token')
      const wsId = wsParam || currentWorkspace?.id
      const response = await fetch(
        `${apiUrl}/api/v1/workspaces/${wsId}/providers/${selectedProviderId}/connections/${selectedConnection}/schema/refresh`,
        { method: 'POST', headers: { 'Authorization': `Bearer ${token}` } }
      )
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}))
        throw new Error(errData.message || 'Failed to refresh schema')
      }
      const result = await response.json()
      await fetchSchema()
      const count = result.table_count || result.collection_count || 0
      const type = result.collection_count ? 'collections' : 'tables'
      alert(`Schema refreshed! Found ${count} ${type}.`)
    } catch (err) {
      console.error('Error refreshing schema:', err)
      setError('Failed to refresh schema: ' + err.message)
    } finally {
      setRefreshing(false)
    }
  }

  const handleWorkspaceChange = (wsId) => {
    const ws = workspaces.find(w => w.id === wsId)
    if (ws) {
      selectWorkspace(ws)
      const params = new URLSearchParams(searchParams)
      params.set('workspace', wsId)
      navigate(`/app/admin/schema-annotation?${params.toString()}`, { replace: true })
    }
  }

  const handleConnectionChange = (connId) => {
    const conn = connections.find(c => c.id === connId)
    if (conn) {
      setSelectedConnection(connId)
      setSelectedProviderId(conn.provider_id)
      const params = new URLSearchParams(searchParams)
      params.set('connection', connId)
      navigate(`/app/admin/schema-annotation?${params.toString()}`, { replace: true })
    }
  }

  const handleAutoAnnotate = async () => {
    if (!selectedTable) {
      setChatMessages([...chatMessages, { type: 'error', content: 'Please select a table first to auto-annotate.', timestamp: new Date() }])
      chatSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      return
    }
    chatSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    try {
      setChatLoading(true)
      const token = localStorage.getItem('access_token')
      const response = await fetch(
        `${apiUrl}/api/v1/annotations/workspaces/${wsParam || currentWorkspace?.id}/providers/${selectedProviderId}/connections/${selectedConnection}/schema/auto-annotate/stream`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ table_name: selectedTable }),
        }
      )

      if (!response.ok) throw new Error('Failed to auto-annotate')

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response body')

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6))
              
              if (event.event === 'started') {
                setChatMessages([...chatMessages, { 
                  type: 'assistant', 
                  content: event.message, 
                  timestamp: new Date() 
                }])
              }
              
              if (event.event === 'progress') {
                // Update last message or add new one
                setChatMessages(prev => {
                  const updated = [...prev]
                  const last = updated[updated.length - 1]
                  if (last?.type === 'assistant') {
                    updated[updated.length - 1] = { ...last, content: event.message }
                  }
                  return updated
                })
              }
              
              if (event.event === 'completed' || event.event === 'done') {
                if (event.suggestions) {
                  const { table_description, table_business_terms, columns } = event.suggestions
                  setAutoAnnotationSuggestions({ 
                    table_name: selectedTable, 
                    description: table_description || '', 
                    columns: columns || [], 
                    business_terms: table_business_terms || [], 
                    relationships: [] 
                  })
                  setChatMessages(prev => [...prev, { 
                    type: 'assistant', 
                    content: `Auto-annotation completed!\n\nTable: ${table_description || selectedTable}\n\nGenerated descriptions for ${columns?.length || 0} columns.`, 
                    timestamp: new Date() 
                  }])
                }
                await fetchAnnotations()
              }
              
              if (event.event === 'error') {
                throw new Error(event.error)
              }
            } catch (e) {
              console.error('Error parsing SSE event:', e)
            }
          }
        }
      }
    } catch (err) {
      console.error('Error auto-annotating:', err)
      setChatMessages([...chatMessages, { type: 'error', content: `Failed to auto-annotate: ${err.message}`, timestamp: new Date() }])
    } finally {
      setChatLoading(false)
    }
  }

  const handleSendMessage = async () => {
    if (!chatInput.trim() || !selectedConnection) return
    const userMessage = { type: 'user', content: chatInput.trim(), timestamp: new Date() }
    setChatMessages([...chatMessages, userMessage])
    setChatInput('')
    setChatLoading(true)
    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch(
        `${apiUrl}/api/v1/agentcore/annotation_assistant/chat`,
        { 
          method: 'POST', 
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }, 
          body: JSON.stringify({ message: userMessage.content, conversation_id: conversationId, context: { selected_table: selectedTable, provider_id: selectedProviderId, user_id: 'current_user' } }),
          signal: AbortSignal.timeout(600000)
        }
      )
      if (!response.ok) throw new Error('Failed to send message')
      const data = await response.json()
      setConversationId(data.conversation_id)
      
      // Check if assistant cleared the conversation
      const isCleared = data.response.includes("Conversation cleared")
      if (isCleared) {
        setChatMessages([{ type: 'assistant', content: data.response, timestamp: new Date() }])
      } else {
        setChatMessages([...chatMessages, userMessage, { type: 'assistant', content: data.response, timestamp: new Date() }])
      }
      
      if (data.tool_calls?.some(tc => tc.tool === 'save_annotation')) {
        await fetchAnnotations()
      }
    } catch (err) {
      console.error('Error sending message:', err)
      setChatMessages([...chatMessages, userMessage, { type: 'error', content: 'Failed to get response. Please try again.', timestamp: new Date() }])
    } finally {
      setChatLoading(false)
    }
  }

  const handleSaveAnnotation = async (annotationData) => {
    if (!selectedConnection) return
    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch(
        `${apiUrl}/api/v1/annotations/workspaces/${wsParam || currentWorkspace?.id}/providers/${selectedProviderId}/connections/${selectedConnection}/schema/annotations`,
        { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }, body: JSON.stringify(annotationData) }
      )
      if (!response.ok) throw new Error('Failed to save annotation')
      await fetchAnnotations()
      setAutoAnnotationSuggestions(null)
      setChatMessages([...chatMessages, { type: 'assistant', content: `Annotation for table "${annotationData.table_name}" saved successfully!`, timestamp: new Date() }])
    } catch (err) {
      console.error('Error saving annotation:', err)
      alert('Failed to save annotation. Please try again.')
    }
  }

  const formatTimestamp = (timestamp) => new Date(timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })

  return (
    <div className="flex min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      <div className="flex-1 p-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">Schema Annotation</h1>
          <p className="text-gray-600 dark:text-gray-400">Annotate database schemas to improve query generation accuracy</p>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4 mb-6">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Database className="w-5 h-5 text-primary-500" />
              <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">Source:</span>
            </div>

            <select
              value={wsParam || currentWorkspace?.id || ''}
              onChange={(e) => handleWorkspaceChange(e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              disabled={wsLoading || workspaces.length === 0}
            >
              {wsLoading || workspaces.length === 0 ? (
                <option value="">Loading workspaces...</option>
              ) : (
                workspaces.map((workspace) => (
                  <option key={workspace.id} value={workspace.id}>{workspace.name}</option>
                ))
              )}
            </select>

            <select
              value={selectedConnection}
              onChange={(e) => handleConnectionChange(e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              disabled={connLoading || connections.length === 0}
            >
              {connLoading ? (
                <option value="">Loading connections...</option>
              ) : connections.length === 0 ? (
                <option value="">No connections available</option>
              ) : (
                connections.map((connection) => (
                  <option key={connection.id} value={connection.id}>{connection.name} ({connection.host}:{connection.port}/{connection.database})</option>
                ))
              )}
            </select>

            <button
              onClick={handleRefreshSchema}
              disabled={!selectedConnection || refreshing}
              className="flex items-center space-x-2 px-4 py-2 bg-purple-500 text-white rounded-md hover:bg-purple-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
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

        <div className="flex flex-col lg:flex-row gap-6">
          <div className="w-full lg:w-80 2xl:w-72 flex-shrink-0">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4 sticky top-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Schema</h2>
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
                </div>
              ) : (
                <div className="max-h-[calc(100vh-16rem)] overflow-y-auto">
                  <SchemaTree
                    schema={schema}
                    onTableSelect={(tableName) => { setSelectedTable(tableName); setShowEditor(true); setAutoAnnotationSuggestions(null); setFocusColumn(null) }}
                    onColumnSelect={(tableName, columnName) => { setSelectedTable(tableName); setShowEditor(true); setAutoAnnotationSuggestions(null); setFocusColumn(columnName) }}
                    selectedTable={selectedTable}
                    annotations={annotations}
                  />
                </div>
              )}
            </div>
          </div>

          <div className="flex-1 min-w-0 space-y-6 2xl:space-y-0">
            {showEditor && selectedTable ? (
              <AnnotationEditor
                tableName={selectedTable}
                schema={schema}
                annotation={autoAnnotationSuggestions || annotations[selectedTable]}
                onSave={handleSaveAnnotation}
                onCancel={() => { setShowEditor(false); setSelectedTable(null); setAutoAnnotationSuggestions(null); setFocusColumn(null) }}
                focusColumn={focusColumn}
              />
            ) : (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-12">
                <div className="text-center max-w-md mx-auto">
                  <div className="w-16 h-16 bg-primary-100 dark:bg-primary-900/30 rounded-full flex items-center justify-center mx-auto mb-6">
                    <Table className="w-8 h-8 text-primary-500" />
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-3">Select a Table to Annotate</h3>
                  <p className="text-gray-600 dark:text-gray-400 mb-6">Choose a table from the schema tree on the left to start adding annotations.</p>
                </div>
              </div>
            )}

            <div className="2xl:hidden" ref={chatSectionRef}>
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 flex flex-col h-[600px]">
                <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <MessageSquare className="w-5 h-5 text-primary-500" />
                    <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Annotation Assistant</h2>
                  </div>
                  {chatMessages.length > 0 && (
                    <button
                      onClick={async () => {
                        if (conversationId) {
                          try {
                            const token = localStorage.getItem('access_token')
                            await fetch(
                              `${apiUrl}/api/v1/annotations/chat/${conversationId}`,
                              { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` } }
                            )
                          } catch (err) {
                            console.error('Failed to clear server conversation:', err)
                          }
                        }
                        setChatMessages([])
                        setConversationId(null)
                      }}
                      className="text-xs text-gray-500 hover:text-red-500 px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                      title="Clear conversation history"
                    >
                      Clear
                    </button>
                  )}
                </div>
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                  {chatMessages.length === 0 ? (
                    <div className="text-center py-12">
                      <MessageSquare className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
                      <p className="text-gray-500 dark:text-gray-400">Start a conversation to get help with annotations</p>
                    </div>
                  ) : chatMessages.map((message, index) => (
                    <div key={index} className={`flex items-start space-x-3 ${message.type === 'user' ? 'justify-end' : ''}`}>
                      {message.type !== 'user' && <div className={`w-8 h-8 rounded-full flex items-center justify-center ${message.type === 'error' ? 'bg-red-100 dark:bg-red-900' : 'bg-gray-100 dark:bg-gray-700'}`}>{message.type === 'error' ? <AlertCircle className="w-5 h-5 text-red-600" /> : <Bot className="w-5 h-5 text-gray-600" />}</div>}
                      <div className={`flex-1 max-w-3xl ${message.type === 'user' ? 'text-right' : ''}`}>
                        <div className={`rounded-lg px-4 py-3 ${message.type === 'user' ? 'bg-primary-500 text-white' : message.type === 'error' ? 'bg-red-50 dark:bg-red-900/20 border border-red-200' : 'bg-gray-100 dark:bg-gray-700'}`}>
                          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                        </div>
                        <p className="text-xs text-gray-500 mt-1">{formatTimestamp(message.timestamp)}</p>
                      </div>
                      {message.type === 'user' && <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center"><User className="w-5 h-5 text-primary-600" /></div>}
                    </div>
                  ))}
                  <div ref={chatEndRef} />
                </div>
                <div className="p-4 border-t border-gray-200 dark:border-gray-700">
                  <div className="flex space-x-2">
                    <input type="text" value={chatInput} onChange={(e) => setChatInput(e.target.value)} onKeyPress={(e) => e.key === 'Enter' && !chatLoading && handleSendMessage()} placeholder="Ask about schema annotations..." disabled={chatLoading || !selectedConnection} className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50" />
                    <button onClick={handleSendMessage} disabled={!chatInput.trim() || chatLoading || !selectedConnection} className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors disabled:opacity-50">{chatLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}</button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="hidden 2xl:block w-96 flex-shrink-0">
            <div ref={chatSectionRef} className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 flex flex-col h-[calc(100vh-12rem)] sticky top-4">
              <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <MessageSquare className="w-5 h-5 text-primary-500" />
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Annotation Assistant</h2>
                </div>
                {chatMessages.length > 0 && (
                  <button
                    onClick={async () => {
                      if (conversationId) {
                        try {
                          const token = localStorage.getItem('access_token')
                          await fetch(
                            `${apiUrl}/api/v1/annotations/chat/${conversationId}`,
                            { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` } }
                          )
                        } catch (err) {
                          console.error('Failed to clear server conversation:', err)
                        }
                      }
                      setChatMessages([])
                      setConversationId(null)
                    }}
                    className="text-xs text-gray-500 hover:text-red-500 px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                    title="Clear conversation history"
                  >
                    Clear
                  </button>
                )}
              </div>
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {chatMessages.length === 0 ? (
                  <div className="text-center py-8">
                    <MessageSquare className="w-10 h-10 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
                    <p className="text-sm text-gray-500 dark:text-gray-400">Start a conversation to get help</p>
                  </div>
                ) : chatMessages.map((message, index) => (
                  <div key={index} className={`flex items-start space-x-2 ${message.type === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}>
                    {message.type !== 'user' && <div className={`w-7 h-7 rounded-full flex items-center justify-center ${message.type === 'error' ? 'bg-red-100 dark:bg-red-900' : 'bg-gray-100 dark:bg-gray-700'}`}>{message.type === 'error' ? <AlertCircle className="w-4 h-4 text-red-600" /> : <Bot className="w-4 h-4 text-gray-600" />}</div>}
                    <div className={`flex-1 ${message.type === 'user' ? 'text-right' : ''}`}>
                      <div className={`rounded-lg px-3 py-2 text-sm ${message.type === 'user' ? 'bg-primary-500 text-white' : message.type === 'error' ? 'bg-red-50 dark:bg-red-900/20 border border-red-200' : 'bg-gray-100 dark:bg-gray-700'}`}>
                        <p className="whitespace-pre-wrap">{message.content}</p>
                      </div>
                    </div>
                    {message.type === 'user' && <div className="w-7 h-7 rounded-full bg-primary-100 flex items-center justify-center"><User className="w-4 h-4 text-primary-600" /></div>}
                  </div>
                ))}
                <div ref={chatEndRef} />
              </div>
              <div className="p-3 border-t border-gray-200 dark:border-gray-700">
                <div className="flex space-x-2">
                  <input type="text" value={chatInput} onChange={(e) => setChatInput(e.target.value)} onKeyPress={(e) => e.key === 'Enter' && !chatLoading && handleSendMessage()} placeholder="Ask about annotations..." className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500" disabled={chatLoading || !selectedConnection} />
                  <button onClick={handleSendMessage} disabled={!chatInput.trim() || chatLoading || !selectedConnection} className="px-3 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors disabled:opacity-50">{chatLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}</button>
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
