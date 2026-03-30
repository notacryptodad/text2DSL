import { Check } from 'lucide-react'
import ConnectionHealthBadge from './ConnectionHealthBadge'

function ProviderSelect({ providers, selected, onChange, disabled = false }) {
  if (providers.length === 0) {
    return (
      <div className="text-center py-4">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No providers available in this workspace
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {providers.map((provider) => (
        <button
          key={provider.id}
          onClick={() => !disabled && onChange(provider)}
          disabled={disabled}
          aria-pressed={selected?.id === provider.id}
          className={`w-full flex items-center justify-between p-3 rounded-lg border-2 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 ${
            disabled
              ? 'opacity-50 cursor-not-allowed'
              : selected?.id === provider.id
              ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
              : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
          }`}
        >
          <div className="flex items-center space-x-3">
            <span className="text-2xl">{provider.icon}</span>
            <div className="text-left">
              <div className="flex items-center space-x-2">
                <p className="font-semibold text-gray-900 dark:text-white">
                  {provider.name}
                </p>
                <ConnectionHealthBadge providerId={provider.id} />
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {provider.type}
              </p>
            </div>
          </div>
          {selected?.id === provider.id && (
            <Check className="w-5 h-5 text-primary-500" />
          )}
        </button>
      ))}
    </div>
  )
}

export default ProviderSelect
