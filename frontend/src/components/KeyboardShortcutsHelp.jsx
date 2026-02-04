import React from 'react';
import { X } from 'lucide-react';

const KeyboardShortcutsHelp = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  const navigationShortcuts = [
    { keys: ['g', 'c'], description: 'Go to Chat' },
    { keys: ['g', 'r'], description: 'Go to Review' },
    { keys: ['g', 's'], description: 'Go to Schema Annotation' },
    { keys: ['g', 'a'], description: 'Go to Admin Dashboard' },
    { keys: ['g', 'w'], description: 'Go to Workspaces' },
  ];

  const generalShortcuts = [
    { keys: ['?'], description: 'Show keyboard shortcuts' },
    { keys: ['Escape'], description: 'Close modals' },
  ];

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-screen items-center justify-center p-4">
        {/* Overlay */}
        <div
          className="fixed inset-0 bg-gray-500 dark:bg-gray-900 bg-opacity-75 dark:bg-opacity-75 transition-opacity"
          onClick={onClose}
        />

        {/* Modal */}
        <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              Keyboard Shortcuts
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
              aria-label="Close"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* Content */}
          <div className="space-y-6">
            {/* Navigation Shortcuts */}
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                Navigation
              </h3>
              <div className="space-y-2">
                {navigationShortcuts.map((shortcut, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between py-2 px-3 rounded-lg bg-gray-50 dark:bg-gray-700/50"
                  >
                    <span className="text-gray-700 dark:text-gray-300">
                      {shortcut.description}
                    </span>
                    <div className="flex items-center gap-1">
                      {shortcut.keys.map((key, keyIndex) => (
                        <React.Fragment key={keyIndex}>
                          <kbd className="px-3 py-1.5 text-sm font-semibold text-gray-800 dark:text-gray-200 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm">
                            {key}
                          </kbd>
                          {keyIndex < shortcut.keys.length - 1 && (
                            <span className="text-gray-500 dark:text-gray-400 text-sm mx-1">
                              then
                            </span>
                          )}
                        </React.Fragment>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* General Shortcuts */}
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                General
              </h3>
              <div className="space-y-2">
                {generalShortcuts.map((shortcut, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between py-2 px-3 rounded-lg bg-gray-50 dark:bg-gray-700/50"
                  >
                    <span className="text-gray-700 dark:text-gray-300">
                      {shortcut.description}
                    </span>
                    <div className="flex items-center gap-1">
                      {shortcut.keys.map((key, keyIndex) => (
                        <kbd
                          key={keyIndex}
                          className="px-3 py-1.5 text-sm font-semibold text-gray-800 dark:text-gray-200 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm"
                        >
                          {key}
                        </kbd>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Footer tip */}
          <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
            <p className="text-sm text-gray-500 dark:text-gray-400 text-center">
              Press <kbd className="px-2 py-1 text-xs font-semibold text-gray-800 dark:text-gray-200 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded">Escape</kbd> or click outside to close
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default KeyboardShortcutsHelp;
