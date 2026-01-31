import { Check } from 'lucide-react'

function ProviderSelect({ providers, selected, onChange }) {
  return (
    <div className="space-y-2">
      {providers.map((provider) => (
        <button
          key={provider.id}
          onClick={() => onChange(provider)}
          className={`w-full flex items-center justify-between p-3 rounded-lg border-2 transition-all ${
            selected.id === provider.id
              ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
              : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
          }`}
        >
          <div className="flex items-center space-x-3">
            <span className="text-2xl">{provider.icon}</span>
            <div className="text-left">
              <p className="font-semibold text-gray-900 dark:text-white">
                {provider.name}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {provider.type}
              </p>
            </div>
          </div>
          {selected.id === provider.id && (
            <Check className="w-5 h-5 text-primary-500" />
          )}
        </button>
      ))}
    </div>
  )
}

export default ProviderSelect
