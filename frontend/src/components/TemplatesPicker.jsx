import { useState, useMemo, useRef, useEffect } from 'react'
import { FileText, ChevronDown, Search, X, Sparkles } from 'lucide-react'
import { getTemplatesForProvider, categories } from '../constants/queryTemplates'

function TemplatesPicker({ providerType, onSelectTemplate, disabled }) {
  const [isOpen, setIsOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState(null)
  const dropdownRef = useRef(null)

  const templates = useMemo(() => getTemplatesForProvider(providerType), [providerType])
  const availableCategories = useMemo(() => {
    const categoryIds = new Set(templates.map(t => t.category))
    return categories.filter(c => categoryIds.has(c.id))
  }, [templates])

  const filteredTemplates = useMemo(() => {
    return templates.filter(template => {
      const matchesSearch = !searchQuery || 
        template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        template.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        template.template.toLowerCase().includes(searchQuery.toLowerCase())
      const matchesCategory = !selectedCategory || template.category === selectedCategory
      return matchesSearch && matchesCategory
    })
  }, [templates, searchQuery, selectedCategory])

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) setIsOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSelectTemplate = (template) => {
    if (onSelectTemplate) onSelectTemplate(template.template)
    setIsOpen(false)
    setSearchQuery('')
    setSelectedCategory(null)
  }

  const renderTemplateWithHighlights = (templateText) => {
    const parts = templateText.split(/(\{\{\w+\}\})/g)
    return parts.map((part, index) => {
      if (part.match(/^\{\{\w+\}\}$/)) {
        const placeholder = part.slice(2, -2)
        return <span key={index} className="inline-flex items-center px-1.5 py-0.5 mx-0.5 bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 rounded text-xs font-medium">{placeholder}</span>
      }
      return <span key={index}>{part}</span>
    })
  }

  const getCategoryInfo = (categoryId) => categories.find(c => c.id === categoryId) || { name: categoryId, icon: '📝' }

  return (
    <div className="relative" ref={dropdownRef}>
      <button type="button" onClick={() => setIsOpen(!isOpen)} disabled={disabled}
        className={`inline-flex items-center space-x-1.5 px-3 py-2 text-sm font-medium rounded-lg border transition-colors \${disabled ? 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-600 border-gray-200 dark:border-gray-700 cursor-not-allowed' : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 hover:border-primary-300 dark:hover:border-primary-600'}`}
        title="Query Templates">
        <FileText className="w-4 h-4" /><span>Templates</span><ChevronDown className={`w-4 h-4 transition-transform \${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute z-50 mt-2 w-96 max-h-[70vh] bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="p-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
            <div className="flex items-center space-x-2 mb-2">
              <Sparkles className="w-4 h-4 text-primary-500" />
              <h3 className="font-semibold text-gray-900 dark:text-white text-sm">Query Templates</h3>
              <span className="text-xs text-gray-500 dark:text-gray-400">({filteredTemplates.length} available)</span>
            </div>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="Search templates..."
                className="w-full pl-9 pr-8 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none text-gray-900 dark:text-white placeholder-gray-400" />
              {searchQuery && <button onClick={() => setSearchQuery('')} aria-label="Clear search" className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"><X className="w-3 h-3 text-gray-400" /></button>}
            </div>
          </div>

          <div className="p-2 border-b border-gray-200 dark:border-gray-700 flex flex-wrap gap-1">
            <button onClick={() => setSelectedCategory(null)} className={`px-2 py-1 text-xs rounded-full transition-colors \${!selectedCategory ? 'bg-primary-100 dark:bg-primary-900/50 text-primary-700 dark:text-primary-300' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'}`}>All</button>
            {availableCategories.map(category => (
              <button key={category.id} onClick={() => setSelectedCategory(category.id === selectedCategory ? null : category.id)}
                className={`px-2 py-1 text-xs rounded-full transition-colors flex items-center space-x-1 \${selectedCategory === category.id ? 'bg-primary-100 dark:bg-primary-900/50 text-primary-700 dark:text-primary-300' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-600'}`}>
                <span>{category.icon}</span><span>{category.name}</span>
              </button>
            ))}
          </div>

          <div className="overflow-y-auto max-h-80">
            {filteredTemplates.length === 0 ? (
              <div className="p-6 text-center text-gray-500 dark:text-gray-400">
                <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No templates found</p>
                <p className="text-xs mt-1">Try adjusting your search or filters</p>
              </div>
            ) : (
              <div className="p-2 space-y-1">
                {filteredTemplates.map(template => {
                  const categoryInfo = getCategoryInfo(template.category)
                  return (
                    <button key={template.id} onClick={() => handleSelectTemplate(template)} className="w-full text-left p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors group">
                      <div className="flex items-start justify-between mb-1">
                        <span className="font-medium text-gray-900 dark:text-white text-sm group-hover:text-primary-600 dark:group-hover:text-primary-400">{template.name}</span>
                        <span className="text-xs text-gray-400 flex items-center space-x-1"><span>{categoryInfo.icon}</span><span>{categoryInfo.name}</span></span>
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">{template.description}</p>
                      <div className="text-sm text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-900/30 rounded px-2 py-1.5 font-mono">{renderTemplateWithHighlights(template.template)}</div>
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          <div className="p-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
            <p className="text-xs text-gray-500 dark:text-gray-400 text-center">💡 Click a template to insert. Replace <span className="px-1 py-0.5 bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 rounded">placeholders</span> with your values.</p>
          </div>
        </div>
      )}
    </div>
  )
}

export default TemplatesPicker
