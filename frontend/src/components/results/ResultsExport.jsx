import { useState } from 'react'
import { FileSpreadsheet, FileJson, Copy, Download, Check } from 'lucide-react'

function ResultsExport({ data, columns, filename = 'query_results' }) {
  const [showDropdown, setShowDropdown] = useState(false)
  const [copySuccess, setCopySuccess] = useState(false)

  const exportToCSV = () => {
    // RFC 4180 compliant CSV export
    const escapeCSVValue = (val) => {
      if (val == null) return ''
      const str = String(val)
      if (str.includes(',') || str.includes('"') || str.includes('\n')) {
        return `"${str.replace(/"/g, '""')}"`
      }
      return str
    }

    const headers = columns.join(',')
    const rows = data.map((row) =>
      columns.map((col) => escapeCSVValue(row[col])).join(',')
    )
    const csv = [headers, ...rows].join('\n')

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${filename}.csv`
    link.click()
    URL.revokeObjectURL(url)
    setShowDropdown(false)
  }

  const exportToJSON = () => {
    const json = JSON.stringify(data, null, 2)
    const blob = new Blob([json], { type: 'application/json;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${filename}.json`
    link.click()
    URL.revokeObjectURL(url)
    setShowDropdown(false)
  }

  const copyToClipboard = async () => {
    try {
      // TSV format for spreadsheet pasting
      const tsv = [
        columns.join('\t'),
        ...data.map((row) =>
          columns.map((col) => (row[col] ?? '')).join('\t')
        ),
      ].join('\n')

      await navigator.clipboard.writeText(tsv)
      setCopySuccess(true)
      setTimeout(() => {
        setCopySuccess(false)
        setShowDropdown(false)
      }, 1500)
    } catch (err) {
      console.error('Failed to copy to clipboard:', err)
      alert('Failed to copy to clipboard. Please try again.')
    }
  }

  return (
    <div className="relative">
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className="flex items-center space-x-2 px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors text-sm font-medium"
      >
        <Download className="w-4 h-4" />
        <span>Export</span>
      </button>

      {showDropdown && (
        <>
          {/* Backdrop to close dropdown */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setShowDropdown(false)}
          />

          {/* Dropdown menu */}
          <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-1 z-20">
            <button
              onClick={exportToCSV}
              className="w-full flex items-center space-x-3 px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              <FileSpreadsheet className="w-4 h-4 text-green-600 dark:text-green-400" />
              <span>Export as CSV</span>
            </button>

            <button
              onClick={exportToJSON}
              className="w-full flex items-center space-x-3 px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              <FileJson className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <span>Export as JSON</span>
            </button>

            <button
              onClick={copyToClipboard}
              className="w-full flex items-center space-x-3 px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              {copySuccess ? (
                <>
                  <Check className="w-4 h-4 text-green-600 dark:text-green-400" />
                  <span className="text-green-600 dark:text-green-400">
                    Copied!
                  </span>
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                  <span>Copy to Clipboard</span>
                </>
              )}
            </button>
          </div>
        </>
      )}
    </div>
  )
}

export default ResultsExport
