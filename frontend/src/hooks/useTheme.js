import { useState, useEffect, useCallback } from 'react'

const STORAGE_KEY = 'darkMode'

/**
 * Hook to manage theme (dark/light mode) with localStorage persistence
 * and system preference detection on first visit.
 */
export function useTheme() {
  const [darkMode, setDarkMode] = useState(() => {
    // Check localStorage first
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved !== null) {
      return saved === 'true'
    }
    // Fall back to system preference on first visit
    return window.matchMedia('(prefers-color-scheme: dark)').matches
  })

  // Apply dark mode class to document and persist to localStorage
  useEffect(() => {
    const root = document.documentElement
    
    if (darkMode) {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
    
    localStorage.setItem(STORAGE_KEY, String(darkMode))
  }, [darkMode])

  // Listen for system preference changes (if user hasn't set a preference)
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    
    const handleChange = (e) => {
      // Only auto-switch if user hasn't explicitly set a preference
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved === null) {
        setDarkMode(e.matches)
      }
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [])

  const toggleDarkMode = useCallback(() => {
    setDarkMode(prev => !prev)
  }, [])

  const setTheme = useCallback((isDark) => {
    setDarkMode(isDark)
  }, [])

  return {
    darkMode,
    toggleDarkMode,
    setTheme,
    isDark: darkMode,
    isLight: !darkMode,
  }
}

export default useTheme
