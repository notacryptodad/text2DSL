import { Zap, Database, Brain, CheckCircle, ArrowRight } from 'lucide-react'

function WelcomeScreen({ onGetStarted }) {
  const exampleQueries = [
    'Show me all users who signed up last month',
    'What are the top 10 orders by revenue?',
    'Find customers with more than 5 orders',
    'Count active sessions in the last 24 hours',
  ]

  return (
    <div className="flex items-center justify-center h-full p-6">
      <div className="max-w-2xl text-center">
        {/* Logo/Icon */}
        <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-primary-400 to-primary-600 rounded-2xl mb-6 shadow-lg">
          <Zap className="w-10 h-10 text-white" />
        </div>

        {/* Title */}
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-3">
          Welcome to Text2DSL
        </h2>
        <p className="text-lg text-gray-600 dark:text-gray-400 mb-8">
          Transform natural language into precise database queries using AI-powered agents
        </p>

        {/* Features */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <Database className="w-8 h-8 text-primary-500 mx-auto mb-2" />
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-1">
              Multi-Provider
            </h3>
            <p className="text-xs text-gray-600 dark:text-gray-400">
              SQL, NoSQL, Splunk, and more
            </p>
          </div>

          <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <Brain className="w-8 h-8 text-primary-500 mx-auto mb-2" />
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-1">
              AI-Powered
            </h3>
            <p className="text-xs text-gray-600 dark:text-gray-400">
              Multi-agent refinement system
            </p>
          </div>

          <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <CheckCircle className="w-8 h-8 text-primary-500 mx-auto mb-2" />
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-1">
              High Accuracy
            </h3>
            <p className="text-xs text-gray-600 dark:text-gray-400">
              95%+ accuracy with validation
            </p>
          </div>
        </div>

        {/* Example Queries */}
        <div className="mb-8">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
            Try example queries like:
          </p>
          <div className="space-y-2">
            {exampleQueries.map((query, idx) => (
              <div
                key={idx}
                className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:border-primary-300 dark:hover:border-primary-700 transition-colors cursor-pointer"
                onClick={() => onGetStarted && onGetStarted(query)}
              >
                <span className="text-primary-500 mr-2">→</span>
                {query}
              </div>
            ))}
          </div>
        </div>

        {/* CTA Button */}
        <button
          onClick={() => onGetStarted && onGetStarted()}
          className="inline-flex items-center space-x-2 px-6 py-3 bg-primary-500 hover:bg-primary-600 text-white font-semibold rounded-lg shadow-lg hover:shadow-xl transition-all"
        >
          <span>Get Started</span>
          <ArrowRight className="w-5 h-5" />
        </button>

        {/* Info */}
        <p className="mt-6 text-xs text-gray-500 dark:text-gray-400">
          Select a provider from the sidebar and start asking questions about your data
        </p>
      </div>
    </div>
  )
}

export default WelcomeScreen
