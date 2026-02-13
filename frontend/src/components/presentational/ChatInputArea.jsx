import QueryInput from '../QueryInput'
import QueryPreview from '../QueryPreview'
import TemplatesPicker from '../TemplatesPicker'

export default function ChatInputArea({
  queryInputRef,
  onSend,
  onQueryChange,
  onUsePreviewQuery,
  onSelectTemplate,
  selectedProvider,
  currentQuery,
  lastUserQuery,
  isQueryRunning
}) {
  return (
    <div className="p-6 border-t border-gray-200 dark:border-gray-700">
      <div className="flex items-center mb-3">
        <TemplatesPicker
          providerType={selectedProvider?.type?.toLowerCase()}
          onSelectTemplate={onSelectTemplate}
          disabled={!selectedProvider}
        />
      </div>
      <QueryInput
        ref={queryInputRef}
        onSend={onSend}
        onQueryChange={onQueryChange}
        disabled={!selectedProvider}
        placeholder={
          !selectedProvider
            ? 'Select a provider from your workspace...'
            : 'Ask me anything about your data...'
        }
        lastQuery={lastUserQuery}
      />
      {isQueryRunning && (
        <p className="mt-2 text-xs text-gray-500 dark:text-gray-400 text-center">
          Press <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs">Escape</kbd> to cancel
        </p>
      )}

      {/* Live SQL Preview */}
      <QueryPreview
        query={currentQuery}
        onUseQuery={onUsePreviewQuery}
        disabled={!selectedProvider}
      />
    </div>
  )
}
