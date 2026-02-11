import { useState, useEffect } from 'react'

export function useChatHistory() {
  const [conversations, setConversations] = useState(() => {
    const saved = localStorage.getItem('conversations')
    return saved ? JSON.parse(saved) : []
  })
  const [showHistory, setShowHistory] = useState(false)
  const [showQueryHistory, setShowQueryHistory] = useState(false)

  useEffect(() => {
    localStorage.setItem('conversations', JSON.stringify(conversations))
  }, [conversations])

  const updateConversation = (conversationId, messages, selectedProvider) => {
    if (conversationId && messages.length > 0) {
      setConversations(prev => {
        const existing = prev.find(c => c.id === conversationId)
        if (existing) {
          return prev.map(c =>
            c.id === conversationId
              ? { ...c, messages, timestamp: new Date(), provider: selectedProvider?.name }
              : c
          )
        }
        return [...prev, {
          id: conversationId,
          messages,
          timestamp: new Date(),
          provider: selectedProvider?.name
        }]
      })
    }
  }

  const handleNewConversation = () => {
    setShowHistory(false)
    return { messages: [], conversationId: null }
  }

  const handleSelectConversation = (id) => {
    const conv = conversations.find(c => c.id === id)
    if (conv) {
      setShowHistory(false)
      return { messages: conv.messages, conversationId: conv.id }
    }
    return null
  }

  const handleDeleteConversation = (id, currentConversationId) => {
    setConversations(prev => prev.filter(c => c.id !== id))
    if (currentConversationId === id) {
      return handleNewConversation()
    }
    return null
  }

  return {
    conversations,
    showHistory,
    setShowHistory,
    showQueryHistory,
    setShowQueryHistory,
    updateConversation,
    handleNewConversation,
    handleSelectConversation,
    handleDeleteConversation
  }
}
