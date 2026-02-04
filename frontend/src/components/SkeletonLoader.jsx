function SkeletonLoader({ type = 'default' }) {
  if (type === 'chat') {
    return (
      <div className="animate-pulse space-y-4 p-6">
        {/* Chat input skeleton */}
        <div className="bg-gray-200 dark:bg-gray-700 h-24 rounded-lg" />

        {/* Message skeletons */}
        {[1, 2, 3].map((i) => (
          <div key={i} className="space-y-3">
            <div className="flex items-start space-x-3">
              <div className="bg-gray-300 dark:bg-gray-600 h-10 w-10 rounded-full flex-shrink-0" />
              <div className="flex-1 space-y-2">
                <div className="bg-gray-200 dark:bg-gray-700 h-4 rounded w-3/4" />
                <div className="bg-gray-200 dark:bg-gray-700 h-4 rounded w-full" />
                <div className="bg-gray-200 dark:bg-gray-700 h-4 rounded w-5/6" />
              </div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (type === 'table') {
    return (
      <div className="animate-pulse p-6 space-y-4">
        {/* Header skeleton */}
        <div className="flex items-center justify-between mb-6">
          <div className="bg-gray-200 dark:bg-gray-700 h-8 rounded w-48" />
          <div className="bg-gray-200 dark:bg-gray-700 h-10 rounded w-32" />
        </div>

        {/* Table skeleton */}
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
          {/* Table header */}
          <div className="flex items-center space-x-4 p-4 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
            <div className="bg-gray-300 dark:bg-gray-600 h-4 rounded w-24" />
            <div className="bg-gray-300 dark:bg-gray-600 h-4 rounded w-32" />
            <div className="bg-gray-300 dark:bg-gray-600 h-4 rounded w-40" />
            <div className="bg-gray-300 dark:bg-gray-600 h-4 rounded w-20" />
          </div>

          {/* Table rows */}
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="flex items-center space-x-4 p-4 border-b border-gray-200 dark:border-gray-700 last:border-b-0"
            >
              <div className="bg-gray-200 dark:bg-gray-700 h-4 rounded w-24" />
              <div className="bg-gray-200 dark:bg-gray-700 h-4 rounded w-32" />
              <div className="bg-gray-200 dark:bg-gray-700 h-4 rounded w-40" />
              <div className="bg-gray-200 dark:bg-gray-700 h-4 rounded w-20" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (type === 'card-grid') {
    return (
      <div className="animate-pulse p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 space-y-4"
            >
              <div className="bg-gray-200 dark:bg-gray-700 h-6 rounded w-3/4" />
              <div className="space-y-2">
                <div className="bg-gray-200 dark:bg-gray-700 h-4 rounded w-full" />
                <div className="bg-gray-200 dark:bg-gray-700 h-4 rounded w-5/6" />
              </div>
              <div className="flex items-center justify-between pt-4">
                <div className="bg-gray-200 dark:bg-gray-700 h-8 rounded w-24" />
                <div className="bg-gray-200 dark:bg-gray-700 h-8 rounded w-20" />
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (type === 'form') {
    return (
      <div className="animate-pulse p-6 max-w-2xl mx-auto space-y-6">
        <div className="bg-gray-200 dark:bg-gray-700 h-8 rounded w-48 mb-6" />

        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="space-y-2">
            <div className="bg-gray-200 dark:bg-gray-700 h-4 rounded w-32" />
            <div className="bg-gray-200 dark:bg-gray-700 h-12 rounded w-full" />
          </div>
        ))}

        <div className="flex justify-end space-x-3 pt-4">
          <div className="bg-gray-200 dark:bg-gray-700 h-10 rounded w-24" />
          <div className="bg-gray-300 dark:bg-gray-600 h-10 rounded w-32" />
        </div>
      </div>
    )
  }

  // Default skeleton
  return (
    <div className="animate-pulse p-6 space-y-4">
      <div className="bg-gray-200 dark:bg-gray-700 h-8 rounded w-3/4" />
      <div className="bg-gray-200 dark:bg-gray-700 h-4 rounded w-full" />
      <div className="bg-gray-200 dark:bg-gray-700 h-4 rounded w-5/6" />
      <div className="bg-gray-200 dark:bg-gray-700 h-32 rounded w-full" />
    </div>
  )
}

export default SkeletonLoader
