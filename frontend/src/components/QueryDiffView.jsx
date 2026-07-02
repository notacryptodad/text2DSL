import { useState } from 'react'
import { diffLines } from 'diff'
import { GitCompare, Code, ChevronLeft, ChevronRight } from 'lucide-react'
import Prism from 'prismjs'
import 'prismjs/components/prism-sql'
import 'prismjs/components/prism-mongodb'
import 'prismjs/components/prism-splunk-spl'

function QueryDiffView({ iterations, providerId }) {
  const [viewMode, setViewMode] = useState('inline')
  const [showDiff, setShowDiff] = useState(true)
  const [currentPairIndex, setCurrentPairIndex] = useState(0)

  const getLanguageClass = (pid) => {
    if (pid?.includes('sql') || pid?.includes('postgres') || pid?.includes('mysql') || pid?.includes('athena')) return 'sql'
    if (pid?.includes('mongo')) return 'mongodb'
    if (pid?.includes('splunk')) return 'splunk-spl'
    return 'sql'
  }

  const language = getLanguageClass(providerId)

  const highlightCode = (code) => {
    try {
      return Prism.highlight(code || '', Prism.languages[language] || Prism.languages.sql, language)
    } catch { return code }
  }

  if (!iterations || iterations.length < 2) {
    const query = iterations?.[0]?.query || ''
    return (
      <div className="query-diff-view">
        <div className="bg-gray-900 dark:bg-gray-950 rounded overflow-x-auto">
          <pre className="p-3 text-sm text-gray-100">
            <code className={'language-' + language} dangerouslySetInnerHTML={{ __html: highlightCode(query) }} />
          </pre>
        </div>
      </div>
    )
  }

  const diffPairs = iterations.slice(0, -1).map((iter, idx) => ({ before: iter, after: iterations[idx + 1], index: idx }))
  const currentPair = diffPairs[currentPairIndex]
  const oldQuery = currentPair?.before?.query || ''
  const newQuery = currentPair?.after?.query || ''
  const changeReason = currentPair?.after?.reason || 'Query refined'
  const lineDiff = diffLines(oldQuery, newQuery)

  const renderInlineDiff = () => (
    <div className="bg-gray-900 dark:bg-gray-950 rounded overflow-x-auto">
      <pre className="p-3 text-sm leading-relaxed">
        {lineDiff.map((part, index) => {
          const bgClass = part.added ? 'bg-green-900/40 text-green-200' : part.removed ? 'bg-red-900/40 text-red-200 line-through' : 'text-gray-100'
          const prefix = part.added ? '+ ' : part.removed ? '- ' : '  '
          return (
            <span key={index} className={'block ' + bgClass}>
              {part.value.split('\n').filter(line => line !== '').map((line, lineIdx) => (
                <span key={lineIdx} className="block">
                  <span className="text-gray-500 select-none">{prefix}</span>
                  <code dangerouslySetInnerHTML={{ __html: highlightCode(line) }} />
                </span>
              ))}
            </span>
          )
        })}
      </pre>
    </div>
  )

  const renderSideBySide = () => {
    const alignedRows = []
    lineDiff.forEach((part) => {
      const lines = part.value.split('\n').filter(l => l !== '' || part.value === '\n')
      if (part.removed) lines.forEach(line => alignedRows.push({ old: line, new: null, type: 'removed' }))
      else if (part.added) lines.forEach(line => alignedRows.push({ old: null, new: line, type: 'added' }))
      else lines.forEach(line => alignedRows.push({ old: line, new: line, type: 'unchanged' }))
    })
    return (
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-gray-900 dark:bg-gray-950 rounded overflow-x-auto">
          <div className="px-3 py-1 bg-red-900/30 border-b border-gray-700 text-xs text-red-300 font-semibold">Iteration {currentPair.before.iteration || currentPairIndex + 1}</div>
          <pre className="p-3 text-sm leading-relaxed">
            {alignedRows.map((row, idx) => row.old === null ? <span key={idx} className="block text-gray-600">&nbsp;</span> : (
              <span key={idx} className={'block ' + (row.type === 'removed' ? 'bg-red-900/30 text-red-200' : 'text-gray-100')}>
                <code dangerouslySetInnerHTML={{ __html: highlightCode(row.old) }} />
              </span>
            ))}
          </pre>
        </div>
        <div className="bg-gray-900 dark:bg-gray-950 rounded overflow-x-auto">
          <div className="px-3 py-1 bg-green-900/30 border-b border-gray-700 text-xs text-green-300 font-semibold">Iteration {currentPair.after.iteration || currentPairIndex + 2}</div>
          <pre className="p-3 text-sm leading-relaxed">
            {alignedRows.map((row, idx) => row.new === null ? <span key={idx} className="block text-gray-600">&nbsp;</span> : (
              <span key={idx} className={'block ' + (row.type === 'added' ? 'bg-green-900/30 text-green-200' : 'text-gray-100')}>
                <code dangerouslySetInnerHTML={{ __html: highlightCode(row.new) }} />
              </span>
            ))}
          </pre>
        </div>
      </div>
    )
  }

  const renderFullQuery = () => {
    const query = iterations[iterations.length - 1]?.query || ''
    return (
      <div className="bg-gray-900 dark:bg-gray-950 rounded overflow-x-auto">
        <pre className="p-3 text-sm text-gray-100">
          <code className={'language-' + language} dangerouslySetInnerHTML={{ __html: highlightCode(query) }} />
        </pre>
      </div>
    )
  }

  return (
    <div className="query-diff-view space-y-3">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center space-x-2">
          <button onClick={() => setShowDiff(true)} className={'flex items-center space-x-1 px-3 py-1.5 rounded text-xs font-medium transition-colors ' + (showDiff ? 'bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600')}>
            <GitCompare className="w-3.5 h-3.5" /><span>Diff View</span>
          </button>
          <button onClick={() => setShowDiff(false)} className={'flex items-center space-x-1 px-3 py-1.5 rounded text-xs font-medium transition-colors ' + (!showDiff ? 'bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600')}>
            <Code className="w-3.5 h-3.5" /><span>Full Query</span>
          </button>
        </div>
        {showDiff && (
          <div className="flex items-center space-x-2">
            <span className="text-xs text-gray-500 dark:text-gray-400">View:</span>
            <select value={viewMode} onChange={(e) => setViewMode(e.target.value)} className="text-xs bg-gray-100 dark:bg-gray-700 border-0 rounded px-2 py-1 text-gray-700 dark:text-gray-300 focus:ring-1 focus:ring-primary-500">
              <option value="inline">Inline</option>
              <option value="sideBySide">Side-by-Side</option>
            </select>
          </div>
        )}
      </div>
      {showDiff && diffPairs.length > 1 && (
        <div className="flex items-center justify-between bg-gray-50 dark:bg-gray-800 rounded px-3 py-2">
          <button
            onClick={() => setCurrentPairIndex(Math.max(0, currentPairIndex - 1))}
            disabled={currentPairIndex === 0}
            className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            aria-label="Previous iteration"
            title="Previous iteration"
          >
            <ChevronLeft className="w-4 h-4 text-gray-600 dark:text-gray-400" />
          </button>
          <div className="text-xs text-gray-600 dark:text-gray-400">
            <span className="font-semibold">Iteration {currentPair.before.iteration || currentPairIndex + 1} to {currentPair.after.iteration || currentPairIndex + 2}</span>
            <span className="mx-2">|</span>
            <span>{currentPairIndex + 1} of {diffPairs.length} changes</span>
          </div>
          <button
            onClick={() => setCurrentPairIndex(Math.min(diffPairs.length - 1, currentPairIndex + 1))}
            disabled={currentPairIndex === diffPairs.length - 1}
            className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            aria-label="Next iteration"
            title="Next iteration"
          >
            <ChevronRight className="w-4 h-4 text-gray-600 dark:text-gray-400" />
          </button>
        </div>
      )}
      {showDiff && changeReason && (
        <div className="flex items-center space-x-2 text-xs text-gray-600 dark:text-gray-400 bg-yellow-50 dark:bg-yellow-900/20 rounded px-3 py-2 border border-yellow-200 dark:border-yellow-800">
          <span className="font-semibold">Change reason:</span><span>{changeReason}</span>
        </div>
      )}
      {showDiff ? (viewMode === 'inline' ? renderInlineDiff() : renderSideBySide()) : renderFullQuery()}
      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 pt-1">
        <span>{iterations.length} iteration{iterations.length !== 1 ? 's' : ''} total</span>
        {showDiff && <span>{lineDiff.filter(p => p.added).length} additions, {lineDiff.filter(p => p.removed).length} removals</span>}
      </div>
    </div>
  )
}

export default QueryDiffView
