import { useNavigationProgress } from '../hooks/useNavigationProgress'

function NavigationProgress() {
  const { isNavigating, progress } = useNavigationProgress()

  if (!isNavigating && progress === 0) return null

  return (
    <div className="fixed top-0 left-0 right-0 z-50 h-1">
      <div
        className="h-full bg-gradient-to-r from-primary-500 via-primary-600 to-primary-500 transition-all duration-200 ease-out shadow-lg"
        style={{
          width: `${progress}%`,
          opacity: isNavigating ? 1 : 0,
        }}
      >
        {/* Shimmer effect */}
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer" />
      </div>
    </div>
  )
}

export default NavigationProgress
