import { useState, useEffect, useMemo, useRef } from 'react'
import { Save, X, AlertCircle, Link2, Plus, ChevronUp, ChevronDown } from 'lucide-react'

function AnnotationEditor({ tableName, schema, annotation, onSave, onCancel, focusColumn }) {
  const [description, setDescription] = useState('')
  const [businessTerms, setBusinessTerms] = useState([])
  const [newBusinessTerm, setNewBusinessTerm] = useState('')
  const [relationships, setRelationships] = useState([])
  const [newRelationship, setNewRelationship] = useState({ target_table: '', type: 'many_to_one', description: '', source_column: '' })
  const [columnAnnotations, setColumnAnnotations] = useState({})
  const [saving, setSaving] = useState(false)
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' })
  const columnRefs = useRef({})

  // Support both API formats: table_name (old) and name (new)
  const tableSchema = schema?.find(t => (t.table_name || t.name) === tableName)
  
  // Get discovered foreign keys from schema
  const discoveredFKs = tableSchema?.foreign_keys || []
  
  // Get FKs not yet in relationships
  const unadddedFKs = discoveredFKs.filter(fk => 
    !relationships.some(r => 
      r.source_column === fk.column && 
      r.target_table === fk.references_table
    )
  )

  const handleAddDiscoveredFK = (fk) => {
    setRelationships([...relationships, {
      source_column: fk.column,
      target_table: fk.references_table,
      target_column: fk.references_column,
      type: 'many_to_one',
      description: `FK: ${fk.column} → ${fk.references_table}.${fk.references_column}`,
      is_discovered: true
    }])
  }

  useEffect(() => {
    if (annotation) {
      setDescription(annotation.description || '')
      setBusinessTerms(annotation.business_terms || [])
      setRelationships(annotation.relationships || [])

      const colAnnotations = {}
      if (annotation.columns) {
        annotation.columns.forEach(col => {
          colAnnotations[col.name] = {
            description: col.description || '',
            sample_values: col.sample_values || ''
          }
        })
      }
      setColumnAnnotations(colAnnotations)
    } else {
      setDescription('')
      setBusinessTerms([])
      // Auto-populate relationships from discovered FKs
      const autoRelationships = discoveredFKs.map(fk => ({
        source_column: fk.column,
        target_table: fk.references_table,
        target_column: fk.references_column,
        type: 'many_to_one',
        description: `FK: ${fk.column} → ${fk.references_table}.${fk.references_column}`,
        is_discovered: true
      }))
      setRelationships(autoRelationships)
      setColumnAnnotations({})
    }
  }, [annotation, tableName, JSON.stringify(discoveredFKs)])

  // Scroll and focus on column when focusColumn changes
  useEffect(() => {
    if (focusColumn && columnRefs.current[focusColumn]) {
      columnRefs.current[focusColumn].scrollIntoView({ behavior: 'smooth', block: 'center' })
      columnRefs.current[focusColumn].focus()
    }
  }, [focusColumn])

  const handleAddBusinessTerm = () => {
    if (newBusinessTerm.trim()) {
      setBusinessTerms([...businessTerms, newBusinessTerm.trim()])
      setNewBusinessTerm('')
    }
  }

  const handleRemoveBusinessTerm = (index) => {
    setBusinessTerms(businessTerms.filter((_, i) => i !== index))
  }

  const handleAddRelationship = () => {
    if (newRelationship.target_table.trim()) {
      setRelationships([...relationships, { ...newRelationship, is_discovered: false }])
      setNewRelationship({ target_table: '', type: 'many_to_one', description: '', source_column: '' })
    }
  }

  const handleRemoveRelationship = (index) => {
    setRelationships(relationships.filter((_, i) => i !== index))
  }

  const handleColumnAnnotationChange = (columnName, field, value) => {
    setColumnAnnotations({
      ...columnAnnotations,
      [columnName]: {
        ...columnAnnotations[columnName],
        [field]: value,
      },
    })
  }

  const handleSave = async () => {
    setSaving(true)

    const annotationData = {
      table_name: tableName,
      description,
      business_terms: businessTerms,
      relationships: relationships.map(r => ({
        source_column: r.source_column,
        target_table: r.target_table,
        target_column: r.target_column,
        type: r.type,
        description: r.description
      })),
      columns: Object.entries(columnAnnotations)
        .filter(([, data]) => data.description?.trim() || data.sample_values?.trim())
        .map(([name, data]) => ({ 
          name, 
          description: data.description || '',
          sample_values: data.sample_values || ''
        })),
    }

    await onSave(annotationData)
    setSaving(false)
  }

  // Get all table names for relationship dropdown
  const allTables = schema?.map(t => t.table_name || t.name).filter(t => t !== tableName) || []

  // Sorting logic
  const handleSort = (key) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc'
    }))
  }

  const sortedColumns = useMemo(() => {
    if (!tableSchema?.columns) return []
    
    const columns = [...tableSchema.columns]
    
    if (sortConfig.key) {
      columns.sort((a, b) => {
        let aVal, bVal
        
        switch (sortConfig.key) {
          case 'name':
            aVal = (a.column_name || a.name || '').toLowerCase()
            bVal = (b.column_name || b.name || '').toLowerCase()
            break
          case 'type':
            aVal = (a.data_type || a.type || '').toLowerCase()
            bVal = (b.data_type || b.type || '').toLowerCase()
            break
          default:
            return 0
        }
        
        if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1
        if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1
        return 0
      })
    }
    
    return columns
  }, [tableSchema?.columns, sortConfig])

  const SortIcon = ({ columnKey }) => {
    if (sortConfig.key !== columnKey) {
      return <ChevronUp className="w-3 h-3 text-gray-300" />
    }
    return sortConfig.direction === 'asc' 
      ? <ChevronUp className="w-3 h-3 text-primary-500" />
      : <ChevronDown className="w-3 h-3 text-primary-500" />
  }
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
          Annotate Table: {tableName}
        </h3>
        <button
          onClick={onCancel}
          className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
        >
          <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
        </button>
      </div>

      <div className="space-y-6">
        {/* Table Description */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
            Table Description
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            placeholder="Describe what this table represents and its business purpose..."
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>

        {/* Business Terms */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
            Business Terms
          </label>
          <div className="flex space-x-2 mb-2">
            <input
              type="text"
              value={newBusinessTerm}
              onChange={(e) => setNewBusinessTerm(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleAddBusinessTerm()}
              placeholder="Add business term (e.g., Customer, Order)"
              className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <button
              onClick={handleAddBusinessTerm}
              className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors text-sm"
            >
              Add
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {businessTerms.map((term, index) => (
              <span
                key={index}
                className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400"
              >
                {term}
                <button
                  onClick={() => handleRemoveBusinessTerm(index)}
                  className="ml-2 hover:text-primary-900 dark:hover:text-primary-200"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        </div>

        {/* Relationships */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
            Relationships
          </label>
          
          {/* Unadded FK suggestions */}
          {unadddedFKs.length > 0 && (
            <div className="mb-3 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
              <p className="text-xs text-blue-700 dark:text-blue-300 mb-2">
                Discovered from foreign keys (click to add):
              </p>
              <div className="flex flex-wrap gap-2">
                {unadddedFKs.map((fk, index) => (
                  <button
                    key={index}
                    onClick={() => handleAddDiscoveredFK(fk)}
                    className="inline-flex items-center px-2 py-1 text-xs bg-blue-100 dark:bg-blue-800 text-blue-700 dark:text-blue-200 rounded hover:bg-blue-200 dark:hover:bg-blue-700 transition-colors"
                  >
                    <Plus className="w-3 h-3 mr-1" />
                    {fk.column} → {fk.references_table}
                  </button>
                ))}
              </div>
            </div>
          )}
          
          {/* Existing relationships */}
          {relationships.length > 0 && (
            <div className="space-y-2 mb-3">
              {relationships.map((rel, index) => (
                <div
                  key={index}
                  className={`flex items-center justify-between p-3 rounded-lg ${
                    rel.is_discovered 
                      ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800' 
                      : 'bg-gray-50 dark:bg-gray-700'
                  }`}
                >
                  <div className="flex items-center space-x-2 flex-1">
                    <Link2 className={`w-4 h-4 ${rel.is_discovered ? 'text-green-500' : 'text-gray-400'}`} />
                    <span className="text-sm text-gray-900 dark:text-white">
                      {rel.source_column && <span className="font-mono text-xs">{rel.source_column} → </span>}
                      <span className="font-medium">{rel.target_table}</span>
                      {rel.target_column && <span className="font-mono text-xs">.{rel.target_column}</span>}
                    </span>
                    <span className="text-xs px-2 py-0.5 rounded bg-gray-200 dark:bg-gray-600 text-gray-600 dark:text-gray-300">
                      {rel.type?.replace(/_/g, ' ')}
                    </span>
                    {rel.is_discovered && (
                      <span className="text-xs px-2 py-0.5 rounded bg-green-200 dark:bg-green-800 text-green-700 dark:text-green-300">
                        FK
                      </span>
                    )}
                  </div>
                  <button
                    onClick={() => handleRemoveRelationship(index)}
                    className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors"
                  >
                    <X className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Add new relationship */}
          <div className="space-y-2 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
            <div className="grid grid-cols-4 gap-2">
              <select
                value={newRelationship.source_column}
                onChange={(e) => setNewRelationship({ ...newRelationship, source_column: e.target.value })}
                className="px-2 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="">Source column</option>
                {tableSchema?.columns?.map(col => {
                  const colName = col.column_name || col.name
                  return <option key={colName} value={colName}>{colName}</option>
                })}
              </select>
              <select
                value={newRelationship.target_table}
                onChange={(e) => setNewRelationship({ ...newRelationship, target_table: e.target.value })}
                className="px-2 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="">Target table</option>
                {allTables.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
              <select
                value={newRelationship.type}
                onChange={(e) => setNewRelationship({ ...newRelationship, type: e.target.value })}
                className="px-2 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-xs focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="one_to_one">1:1</option>
                <option value="one_to_many">1:N</option>
                <option value="many_to_one">N:1</option>
                <option value="many_to_many">N:N</option>
              </select>
              <button
                onClick={handleAddRelationship}
                disabled={!newRelationship.target_table}
                className="flex items-center justify-center space-x-1 px-3 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors text-xs disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Plus className="w-3 h-3" />
                <span>Add</span>
              </button>
            </div>
          </div>
        </div>

        {/* Column Annotations - Table Format */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
            Column Annotations
          </label>
          {tableSchema?.columns && tableSchema.columns.length > 0 ? (
            <div className="overflow-x-auto border border-gray-200 dark:border-gray-700 rounded-lg">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th 
                      className="px-3 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 w-1/5 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600 select-none"
                      onClick={() => handleSort('name')}
                    >
                      <div className="flex items-center space-x-1">
                        <span>Column</span>
                        <SortIcon columnKey="name" />
                      </div>
                    </th>
                    <th 
                      className="px-3 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 w-1/6 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600 select-none"
                      onClick={() => handleSort('type')}
                    >
                      <div className="flex items-center space-x-1">
                        <span>Type</span>
                        <SortIcon columnKey="type" />
                      </div>
                    </th>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 w-2/5">Description</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-gray-600 dark:text-gray-300 w-1/4">Sample Values</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {sortedColumns.map((column) => {
                    const columnName = column.column_name || column.name
                    const dataType = column.data_type || column.type
                    const isNullable = column.is_nullable !== false && column.nullable !== false
                    const isPK = column.primary_key
                    return (
                      <tr key={columnName} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                        <td className="px-3 py-2">
                          <div className="flex items-center space-x-1">
                            <span className="font-mono text-gray-900 dark:text-white">{columnName}</span>
                            {isPK && (
                              <span className="text-xs px-1 py-0.5 rounded bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400">PK</span>
                            )}
                            {!isNullable && (
                              <span className="text-xs text-red-500">*</span>
                            )}
                          </div>
                        </td>
                        <td className="px-3 py-2">
                          <span className="font-mono text-xs text-gray-500 dark:text-gray-400">{dataType}</span>
                        </td>
                        <td className="px-3 py-2">
                          <input
                            type="text"
                            ref={el => columnRefs.current[columnName] = el}
                            value={columnAnnotations[columnName]?.description || ''}
                            onChange={(e) => handleColumnAnnotationChange(columnName, 'description', e.target.value)}
                            placeholder="Describe this column..."
                            className="w-full px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-xs focus:outline-none focus:ring-1 focus:ring-primary-500"
                          />
                        </td>
                        <td className="px-3 py-2">
                          <input
                            type="text"
                            value={columnAnnotations[columnName]?.sample_values || ''}
                            onChange={(e) => handleColumnAnnotationChange(columnName, 'sample_values', e.target.value)}
                            placeholder="e.g., active, pending, closed"
                            className="w-full px-2 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white text-xs focus:outline-none focus:ring-1 focus:ring-primary-500"
                          />
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="flex items-center space-x-2 text-sm text-yellow-600 dark:text-yellow-400">
              <AlertCircle className="w-4 h-4" />
              <span>No columns found for this table</span>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onCancel}
            disabled={saving}
            className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center space-x-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Save className="w-4 h-4" />
            <span>{saving ? 'Saving...' : 'Save Annotations'}</span>
          </button>
        </div>
      </div>
    </div>
  )
}

export default AnnotationEditor
