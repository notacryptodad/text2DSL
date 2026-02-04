import { useState, useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'

export function useNavigationProgress() {
  const [isNavigating, setIsNavigating] = useState(false)
  const [progress, setProgress] = useState(0)
  const location = useLocation()
  const timeoutRef = useRef(null)
  const intervalRef = useRef(null)
  const prevLocationRef = useRef(location.pathname)

  useEffect(() => {
    // Check if location actually changed
    if (prevLocationRef.current === location.pathname) {
      return
    }

    // Start navigation progress
    setIsNavigating(true)
    setProgress(0)

    // Simulate progress
    let currentProgress = 0
    intervalRef.current = setInterval(() => {
      currentProgress += Math.random() * 30
      if (currentProgress >= 90) {
        currentProgress = 90
        clearInterval(intervalRef.current)
      }
      setProgress(currentProgress)
    }, 100)

    // Complete progress after a short delay to ensure page has loaded
    timeoutRef.current = setTimeout(() => {
      setProgress(100)
      setTimeout(() => {
        setIsNavigating(false)
        setProgress(0)
      }, 200)
    }, 300)

    // Update previous location
    prevLocationRef.current = location.pathname

    // Cleanup
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current)
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [location.pathname])

  return { isNavigating, progress }
}
