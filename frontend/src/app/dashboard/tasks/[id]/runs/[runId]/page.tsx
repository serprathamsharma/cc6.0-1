'use client'
import { useParams, useRouter } from 'next/navigation'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { tasksApi, streamRunEvents, type RunEvent, type RecordOut } from '@/lib/api'
import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle, XCircle, Loader2, Pause, X, Download, MessageSquare, RefreshCw } from 'lucide-react'
import { statusBg, formatDate, qualityBadge } from '@/lib/utils'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

function NodeStatusIcon({ status }: { status: string }) {
  if (status === 'done') return <CheckCircle className="h-4 w-4 text-green-500" />
  if (status === 'failed') return <XCircle className="h-4 w-4 text-red-500" />
  if (status === 'running') return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
  return <div className="h-4 w-4 rounded-full border-2 border-muted" />
}

export default function RunPage() {
  const { id, runId } = useParams()
  const router = useRouter()
  const qc = useQueryClient()
  const [events, setEvents] = useState<RunEvent[]>([])
  const [selectedRecord, setSelectedRecord] = useState<RecordOut | null>(null)
  const [chatQ, setChatQ] = useState('')
  const [chatAnswer, setChatAnswer] = useState<{ answer: string; sql: string | null; rows: Record<string, unknown>[] } | null>(null)
  const [chatLoading, setChatLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'monitor' | 'results' | 'sources' | 'compliance' | 'chat'>('monitor')
  const [exportLoading, setExportLoading] = useState(false)
  const logsRef = useRef<HTMLDivElement>(null)

  const { data: run, refetch: refetchRun } = useQuery({
    queryKey: ['run', id, runId],
    queryFn: () => tasksApi.getRun(id as string, runId as string),
    refetchInterval: (q) => {
      const status = q.state.data?.status
      return status === 'running' || status === 'queued' ? 2000 : false
    },
  })

  const { data: workflows } = useQuery({
    queryKey: ['workflows', id],
    queryFn: () => tasksApi.listWorkflows(id as string),
  })

  const { data: records } = useQuery({
    queryKey: ['records', id, runId],
    queryFn: () => tasksApi.getRecords(id as string, runId as string),
    enabled: !!run && (run.status === 'completed' || run.records_found > 0),
    refetchInterval: run?.status === 'running' ? 5000 : false,
  })

  const { data: sources } = useQuery({
    queryKey: ['sources', id, runId],
    queryFn: () => tasksApi.getSources(id as string, runId as string),
    enabled: !!run,
  })

  // Stream SSE events
  useEffect(() => {
    if (!run || run.status === 'completed' || run.status === 'failed') return
    const cleanup = streamRunEvents(
      id as string, runId as string,
      (ev) => {
        setEvents(prev => [...prev, ev])
        setTimeout(() => logsRef.current?.scrollTo(0, 99999), 100)
      },
      () => qc.invalidateQueries({ queryKey: ['run', id, runId] }),
    )
    return cleanup
  }, [run?.status, id, runId, qc])

  const latestWorkflow = workflows?.[0]
  const nodes = latestWorkflow?.dag.nodes || []

  const handleExport = async (fmt: string) => {
    setExportLoading(true)
    try {
      const res = await tasksApi.export(id as string, runId as string, fmt)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `scoutiq_${(runId as string).slice(0, 8)}.${fmt}`
      a.click()
    } finally {
      setExportLoading(false)
    }
  }

  const handleChat = async () => {
    if (!chatQ.trim()) return
    setChatLoading(true)
    try {
      const res = await tasksApi.chat(id as string, runId as string, chatQ)
      setChatAnswer(res)
    } finally {
      setChatLoading(false)
    }
  }

  const qualityData = records ? [
    { range: '90-100', count: records.filter(r => r.quality_score >= 90).length },
    { range: '80-90', count: records.filter(r => r.quality_score >= 80 && r.quality_score < 90).length },
    { range: '70-80', count: records.filter(r => r.quality_score >= 70 && r.quality_score < 80).length },
    { range: '<70', count: records.filter(r => r.quality_score < 70).length },
  ] : []

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="p-6 border-b bg-card flex items-center justify-between">
        <div>
          <h1 className="font-bold text-lg">Run Monitor</h1>
          {run && (
            <div className="flex items-center gap-3 mt-1">
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusBg(run.status)}`}>
                {run.demo_mode && '[DEMO] '}{run.status}
              </span>
              <span className="text-xs text-muted-foreground">
                {run.pages_fetched} pages · {run.records_deduped} records · ${run.total_cost_usd.toFixed(4)}
              </span>
            </div>
          )}
        </div>
        <div className="flex gap-2">
          {['csv', 'xlsx', 'json', 'parquet'].map(fmt => (
            <button
              key={fmt}
              onClick={() => handleExport(fmt)}
              disabled={exportLoading || !run || run.records_deduped === 0}
              className="flex items-center gap-1 px-3 py-1.5 border rounded-lg text-xs hover:bg-muted disabled:opacity-50"
            >
              <Download className="h-3 w-3" />
              {fmt.toUpperCase()}
            </button>
          ))}
          {run?.status === 'running' && (
            <button
              onClick={() => tasksApi.cancelRun(id as string, runId as string).then(() => refetchRun())}
              className="flex items-center gap-1 px-3 py-1.5 border border-destructive text-destructive rounded-lg text-xs hover:bg-destructive/10"
            >
              <X className="h-3 w-3" /> Cancel
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b flex">
        {(['monitor', 'results', 'sources', 'compliance', 'chat'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors capitalize ${
              activeTab === tab ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            {tab === 'chat' ? '💬 Ask Dataset' : tab.replace('_', ' ')}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-auto p-6">
        {activeTab === 'monitor' && (
          <div className="grid grid-cols-3 gap-6">
            {/* Node progress */}
            <div className="col-span-1 space-y-2">
              <h3 className="font-semibold text-sm mb-3">Workflow Nodes</h3>
              {nodes.map(node => (
                <div key={node.id} className="flex items-center gap-3 p-3 bg-card border rounded-lg">
                  <NodeStatusIcon status={run?.node_states?.[node.id] || 'pending'} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{node.label}</p>
                    <p className="text-xs text-muted-foreground">{node.tool}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Logs */}
            <div className="col-span-2">
              <h3 className="font-semibold text-sm mb-3">Live Logs</h3>
              <div
                ref={logsRef}
                className="h-80 overflow-auto bg-black rounded-xl p-4 font-mono text-xs space-y-1"
              >
                {events.map((ev, i) => (
                  <div key={i} className={`flex gap-2 ${
                    ev.level === 'error' ? 'text-red-400' :
                    ev.level === 'warn' ? 'text-yellow-400' :
                    'text-green-300'
                  }`}>
                    <span className="text-gray-500 flex-shrink-0">
                      {new Date(ev.occurred_at).toLocaleTimeString()}
                    </span>
                    {ev.node_id && <span className="text-blue-400">[{ev.node_id}]</span>}
                    <span>{ev.message}</span>
                  </div>
                ))}
                {events.length === 0 && (
                  <p className="text-gray-500">{run?.status === 'queued' ? 'Waiting for worker...' : 'No events yet.'}</p>
                )}
              </div>

              {/* Quality chart */}
              {qualityData.some(d => d.count > 0) && (
                <div className="mt-4">
                  <h3 className="font-semibold text-sm mb-3">Quality Distribution</h3>
                  <div className="h-40">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={qualityData}>
                        <XAxis dataKey="range" tick={{ fontSize: 12 }} />
                        <YAxis tick={{ fontSize: 12 }} />
                        <Tooltip />
                        <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'results' && records && (
          <div>
            <div className="mb-4 flex items-center justify-between">
              <h3 className="font-semibold">{records.length} Records</h3>
            </div>
            <div className="overflow-auto rounded-xl border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/50">
                    {records[0] && Object.keys(records[0].data).filter(k => !k.startsWith('_')).slice(0, 6).map(col => (
                      <th key={col} className="px-4 py-3 text-left font-medium text-xs uppercase text-muted-foreground">{col}</th>
                    ))}
                    <th className="px-4 py-3 text-left font-medium text-xs uppercase text-muted-foreground">Quality</th>
                    <th className="px-4 py-3 text-left font-medium text-xs uppercase text-muted-foreground">Sources</th>
                  </tr>
                </thead>
                <tbody>
                  {records.map(rec => (
                    <tr
                      key={rec.id}
                      className="border-b hover:bg-muted/30 cursor-pointer"
                      onClick={() => setSelectedRecord(rec)}
                    >
                      {Object.keys(rec.data).filter(k => !k.startsWith('_')).slice(0, 6).map(col => (
                        <td key={col} className="px-4 py-3 text-xs max-w-xs truncate">
                          {String(rec.data[col] ?? '—')}
                        </td>
                      ))}
                      <td className="px-4 py-3">
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${qualityBadge(rec.quality_score)}`}>
                          {Math.round(rec.quality_score)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-muted-foreground">
                        {rec.corroboration_count > 1 ? `${rec.corroboration_count} sources` : '1 source'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Record detail drawer */}
            <AnimatePresence>
              {selectedRecord && (
                <motion.div
                  initial={{ x: '100%' }}
                  animate={{ x: 0 }}
                  exit={{ x: '100%' }}
                  className="fixed top-0 right-0 w-96 h-full bg-card border-l shadow-xl z-50 overflow-auto p-6"
                >
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold">Record Detail</h3>
                    <button onClick={() => setSelectedRecord(null)} className="p-1 hover:bg-muted rounded">
                      <X className="h-4 w-4" />
                    </button>
                  </div>

                  <div className="space-y-4">
                    {selectedRecord.field_values.map(fv => (
                      <div key={fv.field_name} className="border rounded-lg p-3">
                        <div className="flex items-start justify-between mb-2">
                          <span className="text-xs font-medium uppercase text-muted-foreground">{fv.field_name}</span>
                          <span className={`text-xs px-1.5 py-0.5 rounded ${fv.verified ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' : 'bg-red-100 text-red-700'}`}>
                            {fv.verified ? '✓ verified' : '⚠ unverified'}
                          </span>
                        </div>
                        <p className="text-sm font-medium mb-2">{fv.value_text || '—'}</p>
                        {fv.evidence_snippet && (
                          <div className="bg-muted rounded p-2 text-xs text-muted-foreground italic">
                            "{fv.evidence_snippet}"
                          </div>
                        )}
                        {fv.source_url && (
                          <a href={fv.source_url} target="_blank" rel="noopener noreferrer"
                            className="text-xs text-primary hover:underline mt-2 block truncate">
                            {fv.source_url}
                          </a>
                        )}
                        <div className="mt-2 flex gap-2 text-xs text-muted-foreground">
                          <span>{fv.extraction_method}</span>
                          <span>·</span>
                          <span>confidence: {(fv.confidence * 100).toFixed(0)}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {activeTab === 'sources' && sources && (
          <div className="overflow-auto rounded-xl border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50">
                  {['Domain', 'URL', 'Robots', 'Pages Fetched', 'Records Yielded', 'Errors', 'Skipped Reason'].map(h => (
                    <th key={h} className="px-4 py-3 text-left font-medium text-xs uppercase text-muted-foreground">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sources.map(src => (
                  <tr key={src.id} className="border-b hover:bg-muted/30">
                    <td className="px-4 py-3 text-xs font-medium">{src.domain}</td>
                    <td className="px-4 py-3 text-xs max-w-xs truncate">
                      <a href={src.url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                        {src.url}
                      </a>
                    </td>
                    <td className="px-4 py-3 text-xs">
                      {src.robots_allowed === true ? '✅' : src.robots_allowed === false ? '🚫' : '❓'}
                    </td>
                    <td className="px-4 py-3 text-xs">{src.pages_fetched}</td>
                    <td className="px-4 py-3 text-xs">{src.records_yielded}</td>
                    <td className="px-4 py-3 text-xs text-destructive">{src.error_count}</td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">{src.skipped_reason || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'compliance' && (
          <div className="max-w-2xl">
            <h3 className="font-semibold mb-4">Compliance Report</h3>
            {run?.compliance_report ? (
              <div className="space-y-3">
                {Object.entries(run.compliance_report).map(([key, val]) => (
                  <div key={key} className="flex justify-between p-3 bg-card border rounded-lg text-sm">
                    <span className="text-muted-foreground capitalize">{key.replace(/_/g, ' ')}</span>
                    <span className="font-medium">{String(val)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground">Compliance report will be available after the run completes.</p>
            )}
          </div>
        )}

        {activeTab === 'chat' && (
          <div className="max-w-2xl">
            <h3 className="font-semibold mb-2">Ask Your Dataset</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Ask questions in plain English. ScoutIQ generates a read-only SQL query and returns the answer.
            </p>
            <div className="flex gap-2 mb-4">
              <input
                type="text"
                value={chatQ}
                onChange={e => setChatQ(e.target.value)}
                placeholder="e.g. What are the top 5 companies by quality score?"
                className="flex-1 px-3 py-2 rounded-lg border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                onKeyDown={e => e.key === 'Enter' && handleChat()}
              />
              <button
                onClick={handleChat}
                disabled={chatLoading || !chatQ.trim()}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm disabled:opacity-50"
              >
                {chatLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Ask'}
              </button>
            </div>
            {chatAnswer && (
              <div className="space-y-3">
                <div className="bg-card border rounded-xl p-4">
                  <p className="text-sm font-medium mb-2">Answer</p>
                  <p className="text-sm">{chatAnswer.answer}</p>
                </div>
                {chatAnswer.sql && (
                  <div className="bg-muted rounded-xl p-4">
                    <p className="text-xs font-medium text-muted-foreground mb-1">SQL Generated</p>
                    <code className="text-xs">{chatAnswer.sql}</code>
                  </div>
                )}
                {chatAnswer.rows.length > 0 && (
                  <div className="overflow-auto rounded-xl border">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b bg-muted/50">
                          {Object.keys(chatAnswer.rows[0]).map(k => (
                            <th key={k} className="px-3 py-2 text-left font-medium">{k}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {chatAnswer.rows.slice(0, 20).map((row, i) => (
                          <tr key={i} className="border-b">
                            {Object.values(row).map((v, j) => (
                              <td key={j} className="px-3 py-2">{String(v)}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
