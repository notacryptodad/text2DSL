import { useEffect, useRef, useCallback } from 'react'
import { useWorkspace } from '../../contexts/WorkspaceContext'
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts'
import { useChatState } from '../../hooks/useChatState'
import { useChatHistory } from '../../hooks/useChatHistory'
import ChatHeader from '../presentational/ChatHeader'
import ChatMessageList from '../presentational/ChatMessageList'
import ChatInputArea from '../presentational/ChatInputArea'
import ChatSidebars from '../presentational/ChatSidebars'
import KeyboardShortcutsHelp from '../KeyboardShortcutsHelp'

export default function ChatContainer() {
  const { currentWorkspace } = useWorkspace()
  const queryInputRef = useRef(null)

  // Custom hooks for state management
  const {
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
    lastUserQuery
  } = useChatState()

  const {
    conversations,
    showHistory,
    setShowHistory,
    showQueryHistory,
    setShowQueryHistory,
    updateConversation,
    handleNewConversation,
    handleSelectConversation,
    handleDeleteConversation
  } = useChatHistory()

  // Persist settings to localStorage
  useEffect(() => {
    localStorage.setItem('querySettings', JSON.stringify(settings))
  }, [settings])

  // Update conversation history when messages change
  useEffect(() => {
    updateConversation(conversationId, messages, selectedProvider)
  }, [messages, conversationId, selectedProvider, updateConversation])

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
        const response = await fetch(`/api/v1/workspaces/${currentWorkspace.id}/providers`, {
          headers: { Authorization: `Bearer ${token}` }
        })
        if (response.ok) {
          const data = await response.json()
          const formattedProviders = data.map(provider => ({
            id: provider.id,
            name: provider.name,
            type: (provider.type || provider.provider_type || 'unknown').toUpperCase(),
            icon: getProviderIcon(provider.type || provider.provider_type || 'postgresql')
          }))
          setProviders(formattedProviders)
          if (!selectedProvider || !formattedProviders.find(p => p.id === selectedProvider.id)) {
            setSelectedProvider(formattedProviders[0] || null)
          }
        } else {
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
  }, [currentWorkspace, setProviders, setSelectedProvider]) // eslint-disable-line react-hooks/exhaustive-deps

  const getProviderIcon = (type) => {
    const icons = {
      sql: '🗄️',
      postgres: '🐘',
      mysql: '🐬',
      mongodb: '🍃',
      nosql: '📦',
      splunk: '📊'
    }
    return icons[type.toLowerCase()] || '🔌'
  }

  // Keyboard shortcut handlers
  const handleProviderSwitch = useCallback(() => {
    if (providers.length <= 1) return
    const currentIndex = providers.findIndex(p => p.id === selectedProvider?.id)
    const nextIndex = (currentIndex + 1) % providers.length
    setSelectedProvider(providers[nextIndex])
  }, [providers, selectedProvider, setSelectedProvider])

  const handleToggleHistory = useCallback(() => {
    setShowHistory(prev => !prev)
  }, [setShowHistory])

  const handleSendQueryShortcut = useCallback(() => {
    queryInputRef.current?.submit?.()
  }, [])

  const handleCancelQuery = useCallback(() => {
    if (isQueryRunning) {
      cancelQuery()
    }
  }, [isQueryRunning, cancelQuery])

  const handleClearChat = useCallback(() => {
    clearMessages()
    queryInputRef.current?.focus?.()
  }, [clearMessages])

  const handleRecallLastQuery = useCallback(() => {
    if (lastUserQuery) {
      queryInputRef.current?.setQuery?.(lastUserQuery)
    }
  }, [lastUserQuery])

  // Initialize keyboard shortcuts
  const { showHelpModal, setShowHelpModal } = useKeyboardShortcuts({
    onProviderSwitch: handleProviderSwitch,
    onToggleHistory: handleToggleHistory,
    onSendQuery: handleSendQueryShortcut,
    onCancelQuery: handleCancelQuery,
    onClearChat: handleClearChat,
    onRecallLastQuery: handleRecallLastQuery,
    isQueryRunning: isQueryRunning,
  })

  // Handle conversation selection
  const onSelectConversation = useCallback((id) => {
    const result = handleSelectConversation(id)
    if (result) {
      setMessages(result.messages)
      setConversationId(result.conversationId)
    }
  }, [handleSelectConversation, setMessages, setConversationId])

  // Handle new conversation
  const onNewConversation = useCallback(() => {
    const result = handleNewConversation()
    setMessages(result.messages)
    setConversationId(result.conversationId)
  }, [handleNewConversation, setMessages, setConversationId])

  // Handle delete conversation
  const onDeleteConversation = useCallback((id) => {
    const result = handleDeleteConversation(id, conversationId)
    if (result) {
      setMessages(result.messages)
      setConversationId(result.conversationId)
    }
  }, [handleDeleteConversation, conversationId, setMessages, setConversationId])

  // Handle running query from history
  const handleRunFromHistory = useCallback(({ query, providerId }) => {
    if (providerId && providers.length > 0) {
      const provider = providers.find(p => p.id === providerId)
      if (provider) setSelectedProvider(provider)
    }
    handleSendQuery(query)
  }, [providers, setSelectedProvider, handleSendQuery])

  // Handle using SQL from preview
  const handleUsePreviewQuery = useCallback(() => {
    if (currentQuery.trim()) {
      handleSendQuery(currentQuery)
      if (queryInputRef.current) {
        queryInputRef.current.clear()
      }
      setCurrentQuery('')
    }
  }, [currentQuery, handleSendQuery, setCurrentQuery])

  // Handle template selection
  const handleSelectTemplate = useCallback((template) => {
    if (queryInputRef.current) {
      queryInputRef.current.insertTemplate(template)
    }
  }, [])

  // Detect Mac for keyboard shortcut hints
  const isMac = typeof navigator !== 'undefined' && navigator.platform.toUpperCase().indexOf('MAC') >= 0
  const modKey = isMac ? '⌘' : 'Ctrl'

  return (
    <>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <ChatHeader
            providers={providers}
            selectedProvider={selectedProvider}
            currentWorkspace={currentWorkspace}
            settings={settings}
            modKey={modKey}
            onProviderChange={setSelectedProvider}
            onSettingsChange={setSettings}
            onShowShortcuts={() => setShowHelpModal(true)}
          />
          <div className="lg:col-span-3">
            <ChatMessageList
              messages={messages}
              conversationId={conversationId}
              progress={progress}
              onWelcomeAction={handleSendQuery}
            />
            <ChatInputArea
              queryInputRef={queryInputRef}
              onSend={handleSendQuery}
              onQueryChange={handleQueryChange}
              onUsePreviewQuery={handleUsePreviewQuery}
              onSelectTemplate={handleSelectTemplate}
              selectedProvider={selectedProvider}
              currentQuery={currentQuery}
              lastUserQuery={lastUserQuery}
              isQueryRunning={isQueryRunning}
            />
          </div>
        </div>
      </div>

      <ChatSidebars
        showHistory={showHistory}
        showQueryHistory={showQueryHistory}
        conversations={conversations}
        conversationId={conversationId}
        providers={providers}
        selectedProvider={selectedProvider}
        onToggleHistory={handleToggleHistory}
        onToggleQueryHistory={() => setShowQueryHistory(!showQueryHistory)}
        onSelectConversation={onSelectConversation}
        onNewConversation={onNewConversation}
        onDeleteConversation={onDeleteConversation}
        onRunFromHistory={handleRunFromHistory}
        modKey={modKey}
      />

      <KeyboardShortcutsHelp
        isOpen={showHelpModal}
        onClose={() => setShowHelpModal(false)}
      />
    </>
  )
}
