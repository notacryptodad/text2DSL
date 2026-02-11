import { useRef, useEffect } from 'react'
import ChatMessage from '../ChatMessage'
import WelcomeScreen from '../WelcomeScreen'
import ProgressIndicator from '../ProgressIndicator'

export default function ChatMessageList({ messages, conversationId, progress, onWelcomeAction }) {
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 flex flex-col h-[calc(100vh-12rem)]">
      <div className={`flex-1 p-6 space-y-4 ${messages.length > 0 ? 'overflow-y-auto' : ''}`}>
        {messages.length === 0 ? (
          <WelcomeScreen onGetStarted={onWelcomeAction} />
        ) : (
          <>
            {messages.map((message) => (
              <ChatMessage key={message.id} message={message} conversationId={conversationId} />
            ))}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>
      <ProgressIndicator progress={progress} />
    </div>
  )
}
