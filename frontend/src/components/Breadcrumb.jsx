import { ChevronRight, Home } from 'lucide-react'
import { Link } from 'react-router-dom'

function Breadcrumb({ items }) {
  if (!items || items.length === 0) return null

  return (
    <nav className="flex items-center space-x-1 text-sm mb-4">
      <Link
        to="/app"
        className="flex items-center text-gray-500 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
      >
        <Home className="w-4 h-4" />
      </Link>
      
      {items.map((item, index) => (
        <div key={item.path} className="flex items-center">
          <ChevronRight className="w-4 h-4 text-gray-400 dark:text-gray-500 mx-1" />
          {index === items.length - 1 ? (
            <span className="text-gray-900 dark:text-white font-medium">
              {item.label}
            </span>
          ) : (
            <Link
              to={item.path}
              className="text-gray-500 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
            >
              {item.label}
            </Link>
          )}
        </div>
      ))}
    </nav>
  )
}

export default Breadcrumb
