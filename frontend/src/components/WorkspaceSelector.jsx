import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Building2, ChevronDown, Settings } from 'lucide-react'
import { useWorkspace } from '../contexts/WorkspaceContext'

function WorkspaceSelector() {
  const { currentWorkspace, workspaces, selectWorkspace } = useWorkspace()
  const [showDropdown, setShowDropdown] = useState(false)

  if (!currentWorkspace || workspaces.length === 0) {
    return null
  }

  const handleSelectWorkspace = (workspace) => {
    selectWorkspace(workspace)
    setShowDropdown(false)
  }

  return (
    <div className="relative">
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className="flex items-center space-x-2 px-3 py-2 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
      >
        <div className="flex items-center space-x-2">
          <Building2 className="w-4 h-4 text-primary-500" />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {currentWorkspace.name}
          </span>
        </div>
        <ChevronDown className="w-4 h-4 text-gray-500 dark:text-gray-400" />
      </button>

      {/* Dropdown Menu */}
      {showDropdown && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setShowDropdown(false)}
          ></div>
          <div className="absolute left-0 mt-2 w-64 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-1 z-20">
            <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-700">
              <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
                Select Workspace
              </p>
            </div>
            <div className="max-h-64 overflow-y-auto">
              {workspaces.map((workspace) => (
                <button
                  key={workspace.id}
                  onClick={() => handleSelectWorkspace(workspace)}
                  className={`w-full flex items-start space-x-3 px-4 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors ${
                    currentWorkspace.id === workspace.id
                      ? 'bg-primary-50 dark:bg-primary-900/20'
                      : ''
                  }`}
                >
                  <Building2
                    className={`w-5 h-5 mt-0.5 ${
                      currentWorkspace.id === workspace.id
                        ? 'text-primary-500'
                        : 'text-gray-400'
                    }`}
                  />
                  <div className="flex-1 min-w-0">
                    <p
                      className={`text-sm font-medium ${
                        currentWorkspace.id === workspace.id
                          ? 'text-primary-700 dark:text-primary-400'
                          : 'text-gray-900 dark:text-white'
                      }`}
                    >
                      {workspace.name}
                    </p>
                    {workspace.description && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                        {workspace.description}
                      </p>
                    )}
                  </div>
                  {currentWorkspace.id === workspace.id && (
                    <div className="flex-shrink-0">
                      <div className="w-2 h-2 bg-primary-500 rounded-full"></div>
                    </div>
                  )}
                </button>
              ))}
            </div>
            <div className="border-t border-gray-200 dark:border-gray-700">
              <Link
                to="/admin/workspaces"
                onClick={() => setShowDropdown(false)}
                className="flex items-center space-x-2 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                <Settings className="w-4 h-4" />
                <span>Manage Workspaces</span>
              </Link>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default WorkspaceSelector
