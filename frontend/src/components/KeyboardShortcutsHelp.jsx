import React from 'react';
import { X, Keyboard } from 'lucide-react';

const KeyboardShortcutsHelp = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  // Detect if user is on Mac for proper modifier key display
  const isMac = typeof navigator !== 'undefined' && navigator.platform.toUpperCase().indexOf('MAC') >= 0;
  const modKey = isMac ? '⌘' : 'Ctrl';

  const chatShortcuts = [
    { keys: [modKey, 'K'], description: 'Quick provider switch', separator: '+' },
    { keys: [modKey, 'H'], description: 'Toggle history sidebar', separator: '+' },
    { keys: ['↑'], description: 'Recall last query (in empty input)' },
    { keys: [modKey, 'Enter'], description: 'Send query', separator: '+' },
    { keys: ['Escape'], description: 'Cancel running query' },
    { keys: [modKey, 'L'], description: 'Clear chat', separator: '+' },
    { keys: [modKey, '?'], description: 'Show this help', separator: '+' },
  ];

  const navigationShortcuts = [
    { keys: ['g', 'c'], description: 'Go to Chat', separator: 'then' },
    { keys: ['g', 'r'], description: 'Go to Review', separator: 'then' },
    { keys: ['g', 's'], description: 'Go to Schema Annotation', separator: 'then' },
    { keys: ['g', 'a'], description: 'Go to Admin Dashboard', separator: 'then' },
    { keys: ['g', 'w'], description: 'Go to Workspaces', separator: 'then' },
  ];

  const generalShortcuts = [
    { keys: ['?'], description: 'Show keyboard shortcuts (when not in input)' },
    { keys: ['Escape'], description: 'Close modals' },
  ];

  const renderShortcutKeys = (shortcut) => (
    <div className="flex items-center gap-1">
      {shortcut.keys.map((key, keyIndex) => (
        <React.Fragment key={keyIndex}>
          <kbd className="px-2 py-1 text-sm font-semibold text-gray-800 dark:text-gray-200 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm min-w-[28px] text-center">
            {key}
          </kbd>
          {keyIndex < shortcut.keys.length - 1 && shortcut.separator && (
            <span className="text-gray-500 dark:text-gray-400 text-xs mx-0.5">
              {shortcut.separator}
            </span>
          )}
        </React.Fragment>
      ))}
    </div>
  );

  const ShortcutSection = ({ title, shortcuts, icon }) => (
    <div>
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
        {icon}
        {title}
      </h3>
      <div className="space-y-2">
        {shortcuts.map((shortcut, index) => (
          <div
            key={index}
            className="flex items-center justify-between py-2 px-3 rounded-lg bg-gray-50 dark:bg-gray-700/50 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            <span className="text-gray-700 dark:text-gray-300">
              {shortcut.description}
            </span>
            {renderShortcutKeys(shortcut)}
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        {/* Overlay */}
        <div
          className="fixed inset-0 bg-gray-500 dark:bg-gray-900 bg-opacity-75 dark:bg-opacity-75 transition-opacity"
          onClick={onClose}
        />

        {/* Modal */}
        <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-w-2xl w-full p-6 transform transition-all">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary-100 dark:bg-primary-900/30 rounded-lg">
                <Keyboard className="w-6 h-6 text-primary-600 dark:text-primary-400" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                Keyboard Shortcuts
              </h2>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              aria-label="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="space-y-6 max-h-[60vh] overflow-y-auto pr-2">
            {/* Chat Shortcuts */}
            <ShortcutSection
              title="Chat"
              shortcuts={chatShortcuts}
              icon={<span className="text-lg">💬</span>}
            />

            {/* Navigation Shortcuts */}
            <ShortcutSection
              title="Navigation"
              shortcuts={navigationShortcuts}
              icon={<span className="text-lg">🧭</span>}
            />

            {/* General Shortcuts */}
            <ShortcutSection
              title="General"
              shortcuts={generalShortcuts}
              icon={<span className="text-lg">⚡</span>}
            />
          </div>

          {/* Footer tip */}
          <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
            <p className="text-sm text-gray-500 dark:text-gray-400 text-center">
              Press <kbd className="px-2 py-0.5 text-xs font-semibold text-gray-800 dark:text-gray-200 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded">Escape</kbd> or click outside to close
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default KeyboardShortcutsHelp;
