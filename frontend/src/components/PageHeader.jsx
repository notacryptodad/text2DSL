import { ArrowLeft } from 'lucide-react'
import { useNavigate, Link } from 'react-router-dom'
import Breadcrumb from './Breadcrumb'

function PageHeader({
  breadcrumbItems,
  title,
  description,
  icon,
  showBackButton = false,
  backTo,
  actions,
}) {
  const navigate = useNavigate()

  const handleBack = () => {
    if (backTo) {
      navigate(backTo)
    } else {
      navigate(-1)
    }
  }

  return (
    <div className="mb-8">
      {/* Breadcrumb */}
      {breadcrumbItems && <Breadcrumb items={breadcrumbItems} />}

      {/* Back Button */}
      {showBackButton && (
        <button
          onClick={handleBack}
          className="inline-flex items-center text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400 transition-colors mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-1" />
          <span className="text-sm font-medium">Back</span>
        </button>
      )}

      {/* Header Content */}
      <div className="flex items-center justify-between">
        <div className="flex items-start space-x-4">
          {icon && (
            <div className="bg-primary-100 dark:bg-primary-900/30 p-3 rounded-lg">
              {icon}
            </div>
          )}
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              {title}
            </h1>
            {description && (
              <p className="text-gray-600 dark:text-gray-400">
                {description}
              </p>
            )}
          </div>
        </div>
        {actions && (
          <div className="flex items-center space-x-3">
            {actions}
          </div>
        )}
      </div>
    </div>
  )
}

export default PageHeader
