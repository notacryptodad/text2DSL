import { Database, Keyboard } from 'lucide-react'
import ProviderSelect from '../ProviderSelect'
import SettingsPanel from '../SettingsPanel'

export default function ChatHeader({
  providers,
  selectedProvider,
  currentWorkspace,
  settings,
  modKey,
  onProviderChange,
  onSettingsChange,
  onShowShortcuts
}) {
  return (
    <aside className="lg:col-span-1 space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6 border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <Database className="w-5 h-5 text-primary-500" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Provider
            </h2>
          </div>
          <span className="text-xs text-gray-400 dark:text-gray-500" title={`${modKey}+K to switch`}>
            {modKey}+K
          </span>
        </div>
        <ProviderSelect
          providers={providers}
          selected={selectedProvider}
          onChange={onProviderChange}
          disabled={!currentWorkspace || providers.length === 0}
        />

        <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">How it works</h3>
          <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
            <li className="flex items-start space-x-2"><span className="text-primary-500 mt-0.5">1.</span><span>Select your database provider</span></li>
            <li className="flex items-start space-x-2"><span className="text-primary-500 mt-0.5">2.</span><span>Type your query in natural language</span></li>
            <li className="flex items-start space-x-2"><span className="text-primary-500 mt-0.5">3.</span><span>Get the generated DSL query instantly</span></li>
          </ul>
        </div>
      </div>
      <SettingsPanel settings={settings} onChange={onSettingsChange} />

      {/* Keyboard Shortcuts Button */}
      <button
        onClick={onShowShortcuts}
        className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors text-sm"
        title={`${modKey}+? for shortcuts`}
      >
        <Keyboard className="w-4 h-4" />
        <span>Keyboard Shortcuts</span>
        <kbd className="ml-2 px-1.5 py-0.5 text-xs bg-gray-200 dark:bg-gray-600 rounded">
          {modKey}+?
        </kbd>
      </button>
    </aside>
  )
}
