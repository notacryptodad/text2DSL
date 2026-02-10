import { useState, useEffect, useRef } from 'react'
import { Check, Search, Database } from 'lucide-react'
import { getModifierKey } from '../hooks/useKeyboardShortcuts'

function ProviderSwitchModal({ isOpen, onClose, providers, selectedProvider, onSelect }) {
  const [search, setSearch] = useState('')
  const [highlightedIndex, setHighlightedIndex] = useState(0)
  const inputRef = useRef(null)
  const modKey = getModifierKey()

  const filteredProviders = providers.filter(provider =>
    provider.name.toLowerCase().includes(search.toLowerCase()) ||
    provider.type.toLowerCase().includes(search.toLowerCase())
  )

  useEffect(() => {
    if (isOpen) {
      setSearch('')
      setHighlightedIndex(0)
      // Focus input after modal opens
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [isOpen])

  useEffect(() => {
    // Reset highlighted index when filtered results change
    setHighlightedIndex(0)
  }, [search])

  const handleKeyDown = (e) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setHighlightedIndex(prev =>
          prev < filteredProviders.length - 1 ? prev + 1 : 0
        )
        break
      case 'ArrowUp':
        e.preventDefault()
        setHighlightedIndex(prev =>
          prev > 0 ? prev - 1 : filteredProviders.length - 1
        )
        break
      case 'Enter':
        e.preventDefault()
        if (filteredProviders[highlightedIndex]) {
          onSelect(filteredProviders[highlightedIndex])
        }
        break
      case 'Escape':
        e.preventDefault()
        onClose()
        break
      default:
        break
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-start justify-center pt-[20vh] p-4">
        {/* Overlay */}
        <div
          className="fixed inset-0 bg-gray-500 dark:bg-gray-900 bg-opacity-75 dark:bg-opacity-75 transition-opacity"
          onClick={onClose}
        />

        {/* Modal */}
        <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full overflow-hidden">
          {/* Search Input */}
          <div className="p-4 border-b border-gray-200 dark:border-gray-700">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                ref={inputRef}
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Search providers..."
                className="w-full pl-10 pr-4 py-3 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
                autoFocus
              />
            </div>
            <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
              Use ↑↓ to navigate, Enter to select, Esc to close
            </p>
          </div>

          {/* Provider List */}
          <div className="max-h-64 overflow-y-auto">
            {filteredProviders.length === 0 ? (
              <div className="p-4 text-center text-gray-500 dark:text-gray-400">
                <Database className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>No providers found</p>
              </div>
            ) : (
              <div className="py-2">
                {filteredProviders.map((provider, index) => (
                  <button
                    key={provider.id}
                    onClick={() => onSelect(provider)}
                    onMouseEnter={() => setHighlightedIndex(index)}
                    className={`w-full flex items-center justify-between px-4 py-3 transition-colors ${
                      index === highlightedIndex
                        ? 'bg-primary-50 dark:bg-primary-900/20'
                        : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <span className="text-2xl">{provider.icon}</span>
                      <div className="text-left">
                        <p className="font-medium text-gray-900 dark:text-white">
                          {provider.name}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {provider.type}
                        </p>
                      </div>
                    </div>
                    {selectedProvider?.id === provider.id && (
                      <Check className="w-5 h-5 text-primary-500" />
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="p-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
            <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
              Press <kbd className="px-1.5 py-0.5 text-xs bg-gray-100 dark:bg-gray-700 rounded">{modKey}+K</kbd> anytime to switch providers
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ProviderSwitchModal
