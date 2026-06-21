import { Moon, Sun } from 'lucide-react'

/**
 * Animated theme toggle button with sun/moon icon transition.
 * Features smooth rotation and scale animations on theme change.
 */
function ThemeToggle({ darkMode, toggleDarkMode, className = '' }) {
  return (
    <button
      onClick={toggleDarkMode}
      role="switch"
      aria-checked={darkMode}
      className={`
        relative p-2 rounded-lg 
        bg-gray-100 dark:bg-gray-700 
        hover:bg-gray-200 dark:hover:bg-gray-600 
        transition-colors duration-200
        overflow-hidden
        group
        ${className}
      `}
      aria-label="Dark mode"
      title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
    >
      {/* Container for icons with animation */}
      <div className="relative w-5 h-5">
        {/* Sun Icon - visible in dark mode */}
        <Sun
          className={`
            absolute inset-0 w-5 h-5
            text-amber-500
            transition-all duration-300 ease-in-out
            ${darkMode 
              ? 'rotate-0 scale-100 opacity-100' 
              : 'rotate-90 scale-0 opacity-0'
            }
          `}
        />
        
        {/* Moon Icon - visible in light mode */}
        <Moon
          className={`
            absolute inset-0 w-5 h-5
            text-indigo-500
            transition-all duration-300 ease-in-out
            ${darkMode 
              ? '-rotate-90 scale-0 opacity-0' 
              : 'rotate-0 scale-100 opacity-100'
            }
          `}
        />
      </div>

      {/* Animated ring effect on hover */}
      <span 
        className="
          absolute inset-0 rounded-lg
          bg-gradient-to-r from-amber-400 to-indigo-400
          opacity-0 group-hover:opacity-10
          transition-opacity duration-200
        "
      />
    </button>
  )
}

export default ThemeToggle
