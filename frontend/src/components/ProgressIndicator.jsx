import { Loader2 } from 'lucide-react'

function ProgressIndicator({ progress }) {
  if (!progress) return null

  const getStageLabel = (stage) => {
    const labels = {
      started: 'Starting...',
      schema_retrieval: 'Retrieving Schema',
      rag_search: 'Finding Examples',
      query_generation: 'Generating Query',
      validation: 'Validating Query',
      execution: 'Executing Query',
      completed: 'Completed',
    }
    return labels[stage] || stage
  }

  const stages = [
    'started',
    'schema_retrieval',
    'rag_search',
    'query_generation',
    'validation',
    'execution',
    'completed',
  ]

  const currentIndex = stages.indexOf(progress.stage)

  return (
    <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
      <div className="flex items-center justify-between text-sm mb-2">
        <div className="flex items-center space-x-2">
          <Loader2 className="w-4 h-4 animate-spin text-primary-500" />
          <span className="text-gray-700 dark:text-gray-300 font-medium">
            {progress.message || getStageLabel(progress.stage)}
          </span>
        </div>
        <span className="text-gray-500 dark:text-gray-400 tabular-nums">
          {Math.round((progress.progress || 0) * 100)}%
        </span>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
        <div
          className="bg-gradient-to-r from-primary-500 to-primary-600 h-2 rounded-full transition-all duration-300 ease-out"
          style={{ width: `${(progress.progress || 0) * 100}%` }}
        />
      </div>

      {/* Stage Indicators */}
      <div className="flex items-center justify-between mt-3">
        {stages.slice(0, -1).map((stage, idx) => (
          <div key={stage} className="flex flex-col items-center flex-1">
            <div
              className={`w-2 h-2 rounded-full transition-colors ${
                idx < currentIndex
                  ? 'bg-primary-500'
                  : idx === currentIndex
                  ? 'bg-primary-500 animate-pulse'
                  : 'bg-gray-300 dark:bg-gray-600'
              }`}
            />
            <span
              className={`text-xs mt-1 transition-colors ${
                idx <= currentIndex
                  ? 'text-gray-700 dark:text-gray-300'
                  : 'text-gray-400 dark:text-gray-500'
              }`}
            >
              {getStageLabel(stage).split(' ')[0]}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default ProgressIndicator
