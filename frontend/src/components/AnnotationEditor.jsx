import { useState, useEffect } from 'react'
import { Save, X, AlertCircle } from 'lucide-react'

function AnnotationEditor({ tableName, schema, annotation, onSave, onCancel }) {
  const [description, setDescription] = useState('')
  const [businessTerms, setBusinessTerms] = useState([])
  const [newBusinessTerm, setNewBusinessTerm] = useState('')
  const [relationships, setRelationships] = useState([])
  const [newRelationship, setNewRelationship] = useState({ target_table: '', type: 'one_to_many', description: '' })
  const [columnAnnotations, setColumnAnnotations] = useState({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (annotation) {
      setDescription(annotation.description || '')
      setBusinessTerms(annotation.business_terms || [])
      setRelationships(annotation.relationships || [])

      const colAnnotations = {}
      if (annotation.columns) {
        annotation.columns.forEach(col => {
          colAnnotations[col.name] = col.description || ''
        })
      }
      setColumnAnnotations(colAnnotations)
    } else {
      setDescription('')
      setBusinessTerms([])
      setRelationships([])
      setColumnAnnotations({})
    }
  }, [annotation, tableName])

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
      setRelationships([...relationships, { ...newRelationship }])
      setNewRelationship({ target_table: '', type: 'one_to_many', description: '' })
    }
  }

  const handleRemoveRelationship = (index) => {
    setRelationships(relationships.filter((_, i) => i !== index))
  }

  const handleColumnAnnotationChange = (columnName, value) => {
    setColumnAnnotations({
      ...columnAnnotations,
      [columnName]: value,
    })
  }

  const handleSave = async () => {
    setSaving(true)

    const annotationData = {
      table_name: tableName,
      description,
      business_terms: businessTerms,
      relationships,
      columns: Object.entries(columnAnnotations)
        .filter(([, desc]) => desc.trim())
        .map(([name, desc]) => ({ name, description: desc })),
    }

    await onSave(annotationData)
    setSaving(false)
  }

  const tableSchema = schema?.find(t => t.table_name === tableName)

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
          <div className="space-y-2 mb-2">
            <div className="grid grid-cols-3 gap-2">
              <input
                type="text"
                value={newRelationship.target_table}
                onChange={(e) => setNewRelationship({ ...newRelationship, target_table: e.target.value })}
                placeholder="Target table"
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <select
                value={newRelationship.type}
                onChange={(e) => setNewRelationship({ ...newRelationship, type: e.target.value })}
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="one_to_one">One to One</option>
                <option value="one_to_many">One to Many</option>
                <option value="many_to_one">Many to One</option>
                <option value="many_to_many">Many to Many</option>
              </select>
              <input
                type="text"
                value={newRelationship.description}
                onChange={(e) => setNewRelationship({ ...newRelationship, description: e.target.value })}
                placeholder="Description (optional)"
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <button
              onClick={handleAddRelationship}
              className="w-full px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors text-sm"
            >
              Add Relationship
            </button>
          </div>
          <div className="space-y-2">
            {relationships.map((rel, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg"
              >
                <div className="flex-1">
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {rel.target_table}
                  </span>
                  <span className="mx-2 text-sm text-gray-500 dark:text-gray-400">
                    ({rel.type.replace(/_/g, ' ')})
                  </span>
                  {rel.description && (
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      - {rel.description}
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
        </div>

        {/* Column Annotations */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
            Column Annotations
          </label>
          {tableSchema?.columns && tableSchema.columns.length > 0 ? (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {tableSchema.columns.map((column) => (
                <div key={column.column_name} className="space-y-1">
                  <label className="text-sm text-gray-700 dark:text-gray-300 font-medium">
                    {column.column_name}
                    <span className="ml-2 text-xs text-gray-500 dark:text-gray-400 font-mono">
                      {column.data_type}
                    </span>
                  </label>
                  <input
                    type="text"
                    value={columnAnnotations[column.column_name] || ''}
                    onChange={(e) => handleColumnAnnotationChange(column.column_name, e.target.value)}
                    placeholder="Describe this column..."
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              ))}
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
