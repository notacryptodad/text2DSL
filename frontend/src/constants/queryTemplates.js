// Universal templates
export const universalTemplates = [
  { id: 'show-all-where', name: 'Show all where condition', description: 'Retrieve records matching a condition', template: 'Show me all {{table_name}} where {{condition}}', category: 'retrieval', placeholders: ['table_name', 'condition'] },
  { id: 'count-grouped', name: 'Count grouped by', description: 'Count records grouped by a field', template: 'Count of {{table_name}} grouped by {{field_name}}', category: 'aggregation', placeholders: ['table_name', 'field_name'] },
  { id: 'compare-over-time', name: 'Compare over time', description: 'Compare two values over a time period', template: 'Compare {{metric_a}} and {{metric_b}} over {{time_period}}', category: 'comparison', placeholders: ['metric_a', 'metric_b', 'time_period'] },
  { id: 'top-n-by', name: 'Top N records', description: 'Get top N records by a specific field', template: 'Top {{count}} {{table_name}} by {{field_name}}', category: 'ranking', placeholders: ['count', 'table_name', 'field_name'] },
  { id: 'find-null-missing', name: 'Find null/missing values', description: 'Find records where a field is null or missing', template: 'Find {{table_name}} where {{field_name}} is null', category: 'data-quality', placeholders: ['table_name', 'field_name'] },
  { id: 'average-by-group', name: 'Average by group', description: 'Calculate average of a field grouped by another', template: 'Average {{numeric_field}} by {{group_field}} from {{table_name}}', category: 'aggregation', placeholders: ['numeric_field', 'group_field', 'table_name'] },
  { id: 'recent-records', name: 'Recent records', description: 'Get the most recent records', template: 'Show me the last {{count}} {{table_name}} ordered by {{date_field}}', category: 'retrieval', placeholders: ['count', 'table_name', 'date_field'] },
  { id: 'between-dates', name: 'Records between dates', description: 'Find records within a date range', template: 'Find {{table_name}} where {{date_field}} is between {{start_date}} and {{end_date}}', category: 'filtering', placeholders: ['table_name', 'date_field', 'start_date', 'end_date'] },
]

// SQL-specific templates
export const sqlTemplates = [
  { id: 'sql-join-tables', name: 'Join tables', description: 'Join two related tables', template: 'Join {{table_a}} with {{table_b}} on {{join_field}} and show {{fields}}', category: 'joins', placeholders: ['table_a', 'table_b', 'join_field', 'fields'], providers: ['sql', 'postgresql', 'mysql', 'postgres'] },
  { id: 'sql-subquery', name: 'Subquery filter', description: 'Filter using a subquery condition', template: 'Find {{table_name}} where {{field}} in (select {{subfield}} from {{subtable}} where {{subcondition}})', category: 'advanced', placeholders: ['table_name', 'field', 'subfield', 'subtable', 'subcondition'], providers: ['sql', 'postgresql', 'mysql', 'postgres'] },
  { id: 'sql-distinct', name: 'Distinct values', description: 'Get unique values for a field', template: 'Show distinct {{field_name}} from {{table_name}}', category: 'retrieval', placeholders: ['field_name', 'table_name'], providers: ['sql', 'postgresql', 'mysql', 'postgres'] },
  { id: 'sql-having', name: 'Group with having', description: 'Group results with a having condition', template: 'Count {{table_name}} by {{group_field}} having count {{operator}} {{threshold}}', category: 'aggregation', placeholders: ['table_name', 'group_field', 'operator', 'threshold'], providers: ['sql', 'postgresql', 'mysql', 'postgres'] },
]

// MongoDB-specific templates
export const mongoTemplates = [
  { id: 'mongo-nested-field', name: 'Query nested field', description: 'Query a nested document field', template: 'Find {{collection}} where {{parent_field}}.{{nested_field}} equals {{value}}', category: 'retrieval', placeholders: ['collection', 'parent_field', 'nested_field', 'value'], providers: ['mongodb', 'nosql', 'mongo'] },
  { id: 'mongo-array-contains', name: 'Array contains', description: 'Find documents where array contains a value', template: 'Find {{collection}} where {{array_field}} contains {{value}}', category: 'filtering', placeholders: ['collection', 'array_field', 'value'], providers: ['mongodb', 'nosql', 'mongo'] },
  { id: 'mongo-aggregate-pipeline', name: 'Aggregate with match', description: 'Aggregate with a match condition', template: 'From {{collection}}, match {{condition}} then group by {{group_field}} and sum {{sum_field}}', category: 'aggregation', placeholders: ['collection', 'condition', 'group_field', 'sum_field'], providers: ['mongodb', 'nosql', 'mongo'] },
  { id: 'mongo-exists', name: 'Field exists', description: 'Find documents where field exists', template: 'Find {{collection}} where {{field_name}} exists', category: 'data-quality', placeholders: ['collection', 'field_name'], providers: ['mongodb', 'nosql', 'mongo'] },
]

// Splunk-specific templates
export const splunkTemplates = [
  { id: 'splunk-search-index', name: 'Search index', description: 'Search within a specific index', template: 'Search {{index_name}} for {{search_term}} in the last {{time_range}}', category: 'search', placeholders: ['index_name', 'search_term', 'time_range'], providers: ['splunk'] },
  { id: 'splunk-stats', name: 'Stats by field', description: 'Calculate statistics grouped by field', template: 'From {{source}} calculate {{stats_function}} of {{field}} by {{group_field}}', category: 'aggregation', placeholders: ['source', 'stats_function', 'field', 'group_field'], providers: ['splunk'] },
  { id: 'splunk-timechart', name: 'Timechart', description: 'Create a timechart visualization', template: 'Show timechart of {{metric}} from {{source}} span={{time_span}}', category: 'visualization', placeholders: ['metric', 'source', 'time_span'], providers: ['splunk'] },
  { id: 'splunk-top', name: 'Top values', description: 'Find top values for a field', template: 'Show top {{count}} values of {{field}} from {{source}}', category: 'ranking', placeholders: ['count', 'field', 'source'], providers: ['splunk'] },
  { id: 'splunk-rare', name: 'Rare values', description: 'Find rare/uncommon values', template: 'Show rare {{field}} from {{source}} in last {{time_range}}', category: 'analysis', placeholders: ['field', 'source', 'time_range'], providers: ['splunk'] },
]

// Categories
export const categories = [
  { id: 'retrieval', name: 'Data Retrieval', icon: '📋' },
  { id: 'aggregation', name: 'Aggregation', icon: '📊' },
  { id: 'filtering', name: 'Filtering', icon: '🔍' },
  { id: 'comparison', name: 'Comparison', icon: '⚖️' },
  { id: 'ranking', name: 'Ranking', icon: '🏆' },
  { id: 'data-quality', name: 'Data Quality', icon: '✅' },
  { id: 'joins', name: 'Joins', icon: '🔗' },
  { id: 'advanced', name: 'Advanced', icon: '⚡' },
  { id: 'search', name: 'Search', icon: '🔎' },
  { id: 'visualization', name: 'Visualization', icon: '📈' },
  { id: 'analysis', name: 'Analysis', icon: '🧪' },
]

export function getTemplatesForProvider(providerType) {
  const type = (providerType || '').toLowerCase()
  let templates = [...universalTemplates]
  if (['sql', 'postgresql', 'postgres', 'mysql'].includes(type)) templates = [...templates, ...sqlTemplates]
  else if (['mongodb', 'nosql', 'mongo'].includes(type)) templates = [...templates, ...mongoTemplates]
  else if (type === 'splunk') templates = [...templates, ...splunkTemplates]
  return templates
}

export function getAllTemplates() {
  return [...universalTemplates, ...sqlTemplates, ...mongoTemplates, ...splunkTemplates]
}

export function extractPlaceholders(template) {
  const regex = /\{\{(\w+)\}\}/g
  const placeholders = []
  let match
  while ((match = regex.exec(template)) !== null) placeholders.push(match[1])
  return placeholders
}

export function fillTemplate(template, values) {
  return template.replace(/\{\{(\w+)\}\}/g, (match, placeholder) => values[placeholder] !== undefined ? values[placeholder] : match)
}

export default { universalTemplates, sqlTemplates, mongoTemplates, splunkTemplates, categories, getTemplatesForProvider, getAllTemplates, extractPlaceholders, fillTemplate }
