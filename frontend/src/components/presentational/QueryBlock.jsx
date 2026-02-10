import { Copy, Check, Download } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

/**
 * QueryBlock - A presentational component for displaying generated queries
 * 
 * Props in, JSX out. No hooks, no state, no side effects.
 * All state management (copied, handlers) lives in the parent.
 */
function QueryBlock({
  query,
  languageClass = 'language-sql',
  copied = false,
  onCopy,
  onDownload,
}) {
  return (
    <div className="mb-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase">
          Generated Query
        </span>
        <div className="flex items-center space-x-1">
          <button
            onClick={onCopy}
            className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors"
            title="Copy query"
          >
            {copied ? (
              <Check className="w-4 h-4 text-green-500" />
            ) : (
              <Copy className="w-4 h-4 text-gray-500 dark:text-gray-400" />
            )}
          </button>
          <button
            onClick={onDownload}
            className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors"
            title="Download query"
          >
            <Download className="w-4 h-4 text-gray-500 dark:text-gray-400" />
          </button>
        </div>
      </div>
      <div className="prose prose-sm dark:prose-invert max-w-none">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            code({ node, className, children, ...props }) {
              const isBlock = node?.position?.start?.line !== node?.position?.end?.line || className
              const isInsidePre = node?.parentNode?.tagName === 'pre'
              if (isBlock || isInsidePre) {
                return (
                  <code className={className || languageClass} {...props}>{children}</code>
                )
              }
              return (
                <code className="bg-gray-200 dark:bg-gray-600 px-1.5 py-0.5 rounded text-sm" {...props}>{children}</code>
              )
            },
            pre({ children }) {
              return (
                <pre className="bg-gray-900 dark:bg-gray-800 text-gray-100 p-3 rounded text-sm overflow-x-auto">{children}</pre>
              )
            },
          }}
        >
          {query}
        </ReactMarkdown>
      </div>
    </div>
  )
}

export default QueryBlock
