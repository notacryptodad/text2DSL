import { useState, useEffect } from 'react'
import { 
  ChevronDown, 
  ChevronRight, 
  CheckCircle2, 
  XCircle, 
  Loader2, 
  Clock, 
  ChevronUp,
  Zap,
  Brain,
  Database,
  Search,
  FileCode,
  ShieldCheck
} from 'lucide-react'

const AGENTS = [
  { key: 'schema_agent', label: 'Schema Expert', icon: Database, description: 'Analyzes database schema and identifies relevant tables/fields' },
  { key: 'rag_agent', label: 'RAG Retrieval', icon: Search, description: 'Finds similar queries from the knowledge base' },
  { key: 'query_builder_agent', label: 'Query Builder', icon: FileCode, description: 'Generates the DSL query based on context' },
  { key: 'validator_agent', label: 'Validator', icon: ShieldCheck, description: 'Validates query syntax and semantics' },
]

function StatusBadge({ status }) {
  const configs = {
    pending: { bg: 'bg-gray-100 dark:bg-gray-700', text: 'text-gray-500 dark:text-gray-400', label: 'Pending', icon: Clock },
    running: { bg: 'bg-blue-100 dark:bg-blue-900/30', text: 'text-blue-600 dark:text-blue-400', label: 'Running', icon: Loader2, animate: true },
    complete: { bg: 'bg-green-100 dark:bg-green-900/30', text: 'text-green-600 dark:text-green-400', label: 'Complete', icon: CheckCircle2 },
    error: { bg: 'bg-red-100 dark:bg-red-900/30', text: 'text-red-600 dark:text-red-400', label: 'Error', icon: XCircle },
  }
  const config = configs[status] || configs.pending
  const Icon = config.icon
  return (
    <span className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
      {Icon && <Icon className={`w-3 h-3 ${config.animate ? 'animate-spin' : ''}`} />}
      <span>{config.label}</span>
    </span>
  )
}

function DurationIndicator({ durationMs }) {
  if (durationMs === undefined || durationMs === null) return null
  const formatDuration = (ms) => ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(2)}s`
  return (
    <span className="inline-flex items-center space-x-1 text-xs text-gray-500 dark:text-gray-400">
      <Clock className="w-3 h-3" />
      <span className="tabular-nums">{formatDuration(durationMs)}</span>
    </span>
  )
}

function TokenUsage({ input, output }) {
  const total = (input || 0) + (output || 0)
  if (total === 0) return null
  return (
    <div className="flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400">
      <Zap className="w-3 h-3" />
      <span className="tabular-nums">{total.toLocaleString()} tokens</span>
      <span className="text-gray-400 dark:text-gray-500">({input?.toLocaleString() || 0} in / {output?.toLocaleString() || 0} out)</span>
    </div>
  )
}

function AgentNode({ agent, data, isExpanded, onToggle, isLast, progress }) {
  const Icon = agent.icon
  let status = 'pending'
  if (data) status = data.error ? 'error' : 'complete'
  const stageMapping = { 'schema_agent': 'schema_retrieval', 'rag_agent': 'rag_search', 'query_builder_agent': 'query_generation', 'validator_agent': 'validation' }
  if (!data && progress?.stage === stageMapping[agent.key]) status = 'running'
  const hasDetails = data && (data.details || data.reasoning || data.tokens_input > 0)

  return (
    <div className="relative">
      {!isLast && <div className="absolute left-4 top-8 w-0.5 h-full bg-gray-200 dark:bg-gray-700" />}
      <button
        type="button"
        className={`w-full text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 relative flex items-start space-x-3 p-3 rounded-lg transition-colors ${status === 'running' ? 'bg-blue-50 dark:bg-blue-900/10' : ''} ${status === 'error' ? 'bg-red-50 dark:bg-red-900/10' : ''} ${hasDetails ? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50' : ''}`}
        onClick={hasDetails ? onToggle : undefined}
        disabled={!hasDetails}
        aria-expanded={isExpanded ? 'true' : 'false'}
      >
        <div className={`relative z-10 flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${status === 'complete' ? 'bg-green-100 dark:bg-green-900/30' : ''} ${status === 'running' ? 'bg-blue-100 dark:bg-blue-900/30' : ''} ${status === 'error' ? 'bg-red-100 dark:bg-red-900/30' : ''} ${status === 'pending' ? 'bg-gray-100 dark:bg-gray-700' : ''}`}>
          {status === 'running' ? <Loader2 className="w-4 h-4 text-blue-500 animate-spin" /> : status === 'complete' ? <CheckCircle2 className="w-4 h-4 text-green-500" /> : status === 'error' ? <XCircle className="w-4 h-4 text-red-500" /> : <Icon className="w-4 h-4 text-gray-400" />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="font-medium text-gray-900 dark:text-white text-sm">{agent.label}</span>
              <StatusBadge status={status} />
            </div>
            <div className="flex items-center space-x-2">
              {data?.latency_ms !== undefined && <DurationIndicator durationMs={data.latency_ms} />}
              {hasDetails && (isExpanded ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />)}
            </div>
          </div>
          {status === 'pending' && <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{agent.description}</p>}
          {status === 'running' && progress?.message && <p className="text-xs text-blue-600 dark:text-blue-400 mt-1 animate-pulse">{progress.message}</p>}
          {status === 'error' && data?.error && <p className="text-xs text-red-600 dark:text-red-400 mt-1">{data.error}</p>}
          {isExpanded && data && (
            <div className="mt-3 space-y-3 text-xs border-t border-gray-200 dark:border-gray-700 pt-3">
              {(data.tokens_input > 0 || data.tokens_output > 0) && <TokenUsage input={data.tokens_input} output={data.tokens_output} />}
              {data.iterations > 1 && <div className="flex items-center space-x-2 text-gray-500 dark:text-gray-400"><Brain className="w-3 h-3" /><span>{data.iterations} iterations</span></div>}
              {data.reasoning && <div className="bg-gray-50 dark:bg-gray-800 rounded p-2"><div className="font-semibold text-gray-700 dark:text-gray-300 mb-1 flex items-center space-x-1"><Brain className="w-3 h-3" /><span>Reasoning</span></div><p className="text-gray-600 dark:text-gray-400 whitespace-pre-wrap">{data.reasoning}</p></div>}
              {data.details && Object.keys(data.details).length > 0 && <div className="bg-gray-50 dark:bg-gray-800 rounded p-2"><div className="font-semibold text-gray-700 dark:text-gray-300 mb-1">Details</div><div className="space-y-1">{Object.entries(data.details).map(([key, value]) => <div key={key} className="flex justify-between text-gray-600 dark:text-gray-400"><span className="capitalize">{key.replace(/_/g, ' ')}</span><span className="font-mono text-gray-800 dark:text-gray-200">{typeof value === 'object' ? JSON.stringify(value) : String(value)}</span></div>)}</div></div>}
              {data.output && <div className="bg-gray-50 dark:bg-gray-800 rounded p-2"><div className="font-semibold text-gray-700 dark:text-gray-300 mb-1">Output</div><pre className="text-gray-600 dark:text-gray-400 whitespace-pre-wrap font-mono text-xs overflow-x-auto max-h-40">{typeof data.output === 'string' ? data.output.substring(0, 500) + (data.output.length > 500 ? '...' : '') : JSON.stringify(data.output, null, 2).substring(0, 500)}</pre></div>}
            </div>
          )}
        </div>
      </button>
    </div>
  )
}

function TimelineSummary({ trace }) {
  if (!trace) return null
  return (
    <div className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded-lg text-xs">
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-1"><Clock className="w-3 h-3 text-gray-400" /><span className="text-gray-600 dark:text-gray-300 tabular-nums">{trace.orchestrator_latency_ms}ms total</span></div>
        <div className="flex items-center space-x-1"><Zap className="w-3 h-3 text-gray-400" /><span className="text-gray-600 dark:text-gray-300 tabular-nums">{(trace.total_tokens_input + trace.total_tokens_output).toLocaleString()} tokens</span></div>
        {trace.total_cost_usd > 0 && <div className="text-gray-600 dark:text-gray-300 tabular-nums">${trace.total_cost_usd.toFixed(4)}</div>}
      </div>
    </div>
  )
}

function AgentTimeline({ trace, progress, defaultExpanded = false }) {
  const [expandedAgents, setExpandedAgents] = useState({})
  const [allExpanded, setAllExpanded] = useState(defaultExpanded)

  useEffect(() => {
    if (defaultExpanded) {
      const initial = {}
      AGENTS.forEach(agent => { initial[agent.key] = true })
      setExpandedAgents(initial)
    } else {
      setExpandedAgents({})
    }
  }, [trace, defaultExpanded])

  const toggleAgent = (key) => setExpandedAgents(prev => ({ ...prev, [key]: !prev[key] }))
  const toggleAll = () => {
    const newState = !allExpanded
    setAllExpanded(newState)
    const newExpanded = {}
    AGENTS.forEach(agent => { if (trace?.[agent.key]) newExpanded[agent.key] = newState })
    setExpandedAgents(newExpanded)
  }

  const visibleAgents = AGENTS.filter(agent => trace?.[agent.key] || (progress && !trace))
  const agentsToShow = visibleAgents.length > 0 ? visibleAgents : (progress ? AGENTS : [])
  if (agentsToShow.length === 0 && !trace) return null

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide">Agent Processing Timeline</h4>
        {trace && <button onClick={toggleAll} className="flex items-center space-x-1 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors">{allExpanded ? <><ChevronUp className="w-3 h-3" /><span>Collapse All</span></> : <><ChevronDown className="w-3 h-3" /><span>Expand All</span></>}</button>}
      </div>
      {trace && <TimelineSummary trace={trace} />}
      <div className="relative">
        {agentsToShow.map((agent, index) => <AgentNode key={agent.key} agent={agent} data={trace?.[agent.key]} isExpanded={expandedAgents[agent.key] || false} onToggle={() => toggleAgent(agent.key)} isLast={index === agentsToShow.length - 1} progress={progress} />)}
      </div>
    </div>
  )
}

export default AgentTimeline
