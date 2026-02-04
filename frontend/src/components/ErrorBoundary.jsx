import { Component } from 'react'
import { AlertTriangle, RefreshCw, Home, ArrowLeft } from 'lucide-react'
import * as ROUTES from '../constants/routes'

class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
    this.setState({
      error,
      errorInfo,
    })
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null })
    window.location.reload()
  }

  handleGoHome = () => {
    this.setState({ hasError: false, error: null, errorInfo: null })
    window.location.href = ROUTES.APP
  }

  handleGoBack = () => {
    this.setState({ hasError: false, error: null, errorInfo: null })
    window.history.back()
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-8 max-w-2xl w-full border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-center w-16 h-16 bg-red-100 dark:bg-red-900/20 rounded-full mx-auto mb-4">
              <AlertTriangle className="w-8 h-8 text-red-600 dark:text-red-400" />
            </div>

            <h1 className="text-2xl font-bold text-gray-900 dark:text-white text-center mb-2">
              Oops! Something went wrong
            </h1>

            <p className="text-gray-600 dark:text-gray-400 text-center mb-6">
              We encountered an unexpected error. This has been logged and we&apos;ll look into it.
            </p>

            {this.state.error && (
              <details className="mb-6 bg-gray-50 dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <summary className="text-sm font-semibold text-gray-700 dark:text-gray-300 cursor-pointer">
                  Error Details
                </summary>
                <div className="mt-3 space-y-2">
                  <div className="text-sm text-red-600 dark:text-red-400 font-mono">
                    {this.state.error.toString()}
                  </div>
                  {this.state.errorInfo && (
                    <pre className="text-xs text-gray-600 dark:text-gray-400 overflow-auto max-h-48 whitespace-pre-wrap">
                      {this.state.errorInfo.componentStack}
                    </pre>
                  )}
                </div>
              </details>
            )}

            <div className="flex flex-col sm:flex-row justify-center gap-3">
              <button
                onClick={this.handleGoBack}
                className="inline-flex items-center justify-center space-x-2 px-6 py-3 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-800 dark:text-gray-200 font-semibold rounded-lg shadow-lg hover:shadow-xl transition-all"
              >
                <ArrowLeft className="w-5 h-5" />
                <span>Go Back</span>
              </button>
              <button
                onClick={this.handleGoHome}
                className="inline-flex items-center justify-center space-x-2 px-6 py-3 bg-primary-500 hover:bg-primary-600 text-white font-semibold rounded-lg shadow-lg hover:shadow-xl transition-all"
              >
                <Home className="w-5 h-5" />
                <span>Go to Home</span>
              </button>
              <button
                onClick={this.handleReset}
                className="inline-flex items-center justify-center space-x-2 px-6 py-3 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-800 dark:text-gray-200 font-semibold rounded-lg shadow-lg hover:shadow-xl transition-all"
              >
                <RefreshCw className="w-5 h-5" />
                <span>Reload</span>
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
