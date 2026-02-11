import { useState, useEffect, useRef, useCallback } from 'react'
import { Database, History, X, Clock } from 'lucide-react'
import ChatMessage from '../components/ChatMessage'
import ProviderSelect from '../components/ProviderSelect'
import QueryInput from '../components/QueryInput'
import QueryPreview from '../components/QueryPreview'
import ConversationHistory from '../components/ConversationHistory'
import QueryHistorySidebar, { useQueryHistory } from '../components/QueryHistorySidebar'
import ProgressIndicator from '../components/ProgressIndicator'
import SettingsPanel from '../components/SettingsPanel'
import WelcomeScreen from '../components/WelcomeScreen'
import TemplatesPicker from '../components/TemplatesPicker'
import useQuerySSE from '../hooks/useQuerySSE'
import { useWorkspace } from '../contexts/WorkspaceContext'

function Chat() {
  const { currentWorkspace } = useWorkspace()
  const [providers, setProviders] = useState([])
  const [selectedProvider, setSelectedProvider] = useState(null)
  const [messages, setMessages] = useState([])
  const [conversationId, setConversationId] = useState(null)
  const [conversations, setConversations] = useState(() => { const saved = localStorage.getItem('conversations'); return saved ? JSON.parse(saved) : [] })
  const [showHistory, setShowHistory] = useState(false)
  const [showQueryHistory, setShowQueryHistory] = useState(false)
  const [settings, setSettings] = useState(() => { const saved = localStorage.getItem('querySettings'); return saved ? JSON.parse(saved) : { trace_level: 'summary', enable_execution: false, max_iterations: 5, confidence_threshold: 0.85 } })
  const messagesEndRef = useRef(null)
  const queryInputRef = useRef(null)
  const messageIdCounter = useRef(0)
  const [currentQuery, setCurrentQuery] = useState('') // For live preview
  const pendingQueryRef = useRef(null)
  const { addQuery: addToQueryHistory } = useQueryHistory()

  const generateMessageId = () => { messageIdCounter.current += 1; return `${Date.now()}-${messageIdCounter.current}` }

  // eslint-disable-next-line no-unused-vars
  const { sendQuery, connectionState, progress, cancelQuery } = useQuerySSE({
    onMessage: (event) => handleSSEMessage(event),
    onError: (error) => addMessage({ type: 'error', content: error.message || 'An error occurred', timestamp: new Date() }),
    onComplete: (data) => setConversationId(data.conversation_id),
  })

  useEffect(() => {
    const fetchProviders = async () => {
      if (!currentWorkspace) { setProviders([]); setSelectedProvider(null); return }
      try {
        const token = localStorage.getItem('access_token')
        const response = await fetch(`/api/v1/workspaces/${currentWorkspace.id}/providers`, { headers: { Authorization: `Bearer ${token}` } })
        if (response.ok) {
          const data = await response.json()
          const formattedProviders = data.map(provider => ({ id: provider.id, name: provider.name, type: (provider.type || provider.provider_type || 'unknown').toUpperCase(), icon: getProviderIcon(provider.type || provider.provider_type || 'postgresql') }))
          setProviders(formattedProviders)
          if (!selectedProvider || !formattedProviders.find(p => p.id === selectedProvider.id)) setSelectedProvider(formattedProviders[0] || null)
        } else { setProviders([]); setSelectedProvider(null) }
      } catch (error) { console.error('Error fetching providers:', error); setProviders([]); setSelectedProvider(null) }
    }
    fetchProviders()
  }, [currentWorkspace]) // eslint-disable-line react-hooks/exhaustive-deps

  const getProviderIcon = (type) => { const icons = { sql: '🗄️', postgres: '🐘', mysql: '🐬', mongodb: '🍃', nosql: '📦', splunk: '📊' }; return icons[type.toLowerCase()] || '🔌' }
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])
  useEffect(() => { localStorage.setItem('conversations', JSON.stringify(conversations)) }, [conversations])
  useEffect(() => { localStorage.setItem('querySettings', JSON.stringify(settings)) }, [settings])

  useEffect(() => {
    if (conversationId && messages.length > 0) {
      setConversations(prev => {
        const existing = prev.find(c => c.id === conversationId)
        if (existing) return prev.map(c => c.id === conversationId ? { ...c, messages, timestamp: new Date(), provider: selectedProvider?.name } : c)
        return [...prev, { id: conversationId, messages, timestamp: new Date(), provider: selectedProvider?.name }]
      })
    }
  }, [messages, conversationId, selectedProvider])

  const handleSSEMessage = (event) => {
    const { event: type, data } = event
    switch (type) {
      case 'started': setConversationId(data.conversation_id); addMessage({ type: 'progress', content: 'Query processing started...', stage: 'started', progress: 0, timestamp: new Date() }); break
      case 'progress': if (data.stage !== 'started') addMessage({ type: 'progress', content: data.message, stage: data.stage, progress: data.progress, timestamp: new Date() }); break
      case 'completed': {
        const content = data.response || data.generated_query || ''
        const isPlainText = !data.generated_query || data.generated_query.trim() === ''
        addMessage({ type: 'assistant', content, generatedQuery: data.generated_query || '', responseType: isPlainText ? 'text' : 'query', confidence: data.confidence_score, executionResult: data.execution_result, providerId: selectedProvider?.id, turnId: data.turn_id, explanation: data.query_explanation, trace: data.reasoning_trace || data.trace, timestamp: new Date() })
        if (data.generated_query && pendingQueryRef.current) { addToQueryHistory({ query: pendingQueryRef.current, generatedDSL: data.generated_query, providerId: selectedProvider?.id, providerName: selectedProvider?.name, executionResult: data.execution_result }); pendingQueryRef.current = null }
        break
      }
      case 'error': addMessage({ type: 'error', content: data.message || data.error || 'An error occurred', details: data.details, timestamp: new Date() }); pendingQueryRef.current = null; break
      default: console.warn('[Chat] Unknown SSE event type:', type, event)
    }
  }

  const addMessage = (message) => setMessages((prev) => [...prev, { id: generateMessageId(), ...message }])

  const handleSendQuery = useCallback(async (query) => {
    if (!selectedProvider) { addMessage({ type: 'error', content: 'Please select a provider first.', timestamp: new Date() }); return }
    pendingQueryRef.current = query
    addMessage({ type: 'user', content: query, timestamp: new Date() })
    try { await sendQuery({ provider_id: selectedProvider.id, query, conversation_id: conversationId, options: { trace_level: settings.trace_level, enable_execution: settings.enable_execution, max_iterations: settings.max_iterations, confidence_threshold: settings.confidence_threshold } }) }
    catch (error) { pendingQueryRef.current = null; addMessage({ type: 'error', content: 'Failed to send query. Please try again.', timestamp: new Date() }) }
  }, [selectedProvider, conversationId, settings, sendQuery])

  const handleNewConversation = () => { setMessages([]); setConversationId(null); setShowHistory(false) }
  const handleSelectConversation = (id) => { const conv = conversations.find(c => c.id === id); if (conv) { setMessages(conv.messages); setConversationId(conv.id); setShowHistory(false) } }
  const handleDeleteConversation = (id) => { setConversations(prev => prev.filter(c => c.id !== id)); if (conversationId === id) handleNewConversation() }
  const handleWelcomeAction = (query) => { if (query) handleSendQuery(query) }
  const handleRunFromHistory = useCallback(({ query, providerId }) => { if (providerId && providers.length > 0) { const provider = providers.find(p => p.id === providerId); if (provider) setSelectedProvider(provider) }; handleSendQuery(query) }, [providers, handleSendQuery])

  // Handle using SQL from preview - sends the natural language query
  const handleUsePreviewQuery = useCallback(() => {
    if (currentQuery.trim()) {
      handleSendQuery(currentQuery)
      if (queryInputRef.current) {
        queryInputRef.current.clear()
      }
      setCurrentQuery('')
    }
  }, [currentQuery, handleSendQuery])

  // Handle query change for live preview
  const handleQueryChange = useCallback((query) => {
    setCurrentQuery(query)
  }, [])

  // Handle template selection from TemplatesPicker
  const handleSelectTemplate = useCallback((template) => {
    if (queryInputRef.current) {
      queryInputRef.current.insertTemplate(template)
    }
  }, [])

  return (
    <>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <aside className="lg:col-span-1 space-y-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 border border-gray-200 dark:border-gray-700">
              <div className="flex items-center space-x-2 mb-4"><Database className="w-5 h-5 text-primary-500" /><h2 className="text-lg font-semibold text-gray-900 dark:text-white">Provider</h2></div>
              <ProviderSelect providers={providers} selected={selectedProvider} onChange={setSelectedProvider} disabled={!currentWorkspace || providers.length === 0} />
              <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">How it works</h3>
                <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                  <li className="flex items-start space-x-2"><span className="text-primary-500 mt-0.5">1.</span><span>Select your database provider</span></li>
                  <li className="flex items-start space-x-2"><span className="text-primary-500 mt-0.5">2.</span><span>Type your query in natural language</span></li>
                  <li className="flex items-start space-x-2"><span className="text-primary-500 mt-0.5">3.</span><span>Get the generated DSL query instantly</span></li>
                </ul>
              </div>
            </div>
            <SettingsPanel settings={settings} onChange={setSettings} />
          </aside>
          <div className="lg:col-span-3">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 flex flex-col h-[calc(100vh-12rem)]">
              <div className={`flex-1 p-6 space-y-4 ${messages.length > 0 ? 'overflow-y-auto' : ''}`}>
                {messages.length === 0 ? <WelcomeScreen onGetStarted={handleWelcomeAction} /> : (<>{messages.map((message) => <ChatMessage key={message.id} message={message} conversationId={conversationId} />)}<div ref={messagesEndRef} /></>)}
              </div>
              <ProgressIndicator progress={progress} />

              {/* Input */}
              <div className="p-6 border-t border-gray-200 dark:border-gray-700">
                <div className="flex items-center mb-3">
                  <TemplatesPicker 
                    providerType={selectedProvider?.type?.toLowerCase()} 
                    onSelectTemplate={handleSelectTemplate}
                    disabled={!selectedProvider}
                  />
                </div>
                <QueryInput
                  ref={queryInputRef}
                  onSend={handleSendQuery}
                  onQueryChange={handleQueryChange}
                  disabled={!selectedProvider}
                  placeholder={
                    !selectedProvider
                      ? 'Select a provider from your workspace...'
                      : 'Ask me anything about your data...'
                  }
                />
                
                {/* Live SQL Preview */}
                <QueryPreview
                  query={currentQuery}
                  onUseQuery={handleUsePreviewQuery}
                  disabled={!selectedProvider}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
      <button onClick={() => setShowQueryHistory(!showQueryHistory)} className="fixed bottom-24 right-8 p-4 rounded-full bg-indigo-500 hover:bg-indigo-600 text-white shadow-lg transition-colors z-30" aria-label="Toggle query history" title="Search Query History"><Clock className="w-6 h-6" /></button>
      <button onClick={() => setShowHistory(!showHistory)} className="fixed bottom-8 right-8 p-4 rounded-full bg-primary-500 hover:bg-primary-600 text-white shadow-lg transition-colors z-30" aria-label="Toggle conversation history"><History className="w-6 h-6" />{conversations.length > 0 && <span className="absolute -top-1 -right-1 w-6 h-6 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">{conversations.length}</span>}</button>
      <QueryHistorySidebar isOpen={showQueryHistory} onClose={() => setShowQueryHistory(false)} onRunQuery={handleRunFromHistory} providers={providers} currentProviderId={selectedProvider?.id} />
      {showHistory && (<div className="fixed inset-0 z-50 lg:hidden"><div className="absolute inset-0 bg-black bg-opacity-50" onClick={() => setShowHistory(false)} /><div className="absolute right-0 top-0 h-full w-80 bg-white dark:bg-gray-800 shadow-xl"><div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700"><h2 className="text-lg font-semibold text-gray-900 dark:text-white">Conversation History</h2><button onClick={() => setShowHistory(false)} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"><X className="w-5 h-5 text-gray-500" /></button></div><div className="h-[calc(100%-64px)]"><ConversationHistory conversations={conversations} currentId={conversationId} onSelect={handleSelectConversation} onNew={handleNewConversation} onDelete={handleDeleteConversation} /></div></div></div>)}
      <div className={`hidden lg:block fixed right-0 top-0 h-full w-80 bg-white dark:bg-gray-800 shadow-xl transform transition-transform duration-300 z-40 ${showHistory ? 'translate-x-0' : 'translate-x-full'}`}><div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700 mt-20"><h2 className="text-lg font-semibold text-gray-900 dark:text-white">Conversation History</h2><button onClick={() => setShowHistory(false)} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"><X className="w-5 h-5 text-gray-500" /></button></div><div className="h-[calc(100%-144px)]"><ConversationHistory conversations={conversations} currentId={conversationId} onSelect={handleSelectConversation} onNew={handleNewConversation} onDelete={handleDeleteConversation} /></div></div>
    </>
  )
}

export default Chat
