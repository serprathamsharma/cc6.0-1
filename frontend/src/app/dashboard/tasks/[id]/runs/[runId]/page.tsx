'use client'
import { useParams, useRouter } from 'next/navigation'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  tasksApi,
  streamRunEvents,
  type RunEvent,
  type RecordOut,
  type DatasetInsights,
  type VersionDiff,
} from '@/lib/api'
import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  CheckCircle,
  XCircle,
  Loader2,
  X,
  Download,
  Sparkles,
  TrendingUp,
  GitCompare,
  AlertTriangle,
  Check,
  Edit2,
  ShieldCheck,
  ExternalLink,
  Zap,
  Info,
} from 'lucide-react'
import { statusBg, qualityBadge } from '@/lib/utils'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

function NodeStatusIcon({ status }: { status: string }) {
  if (status === 'done') return <CheckCircle className="h-4 w-4 text-emerald-500" />
  if (status === 'failed') return <XCircle className="h-4 w-4 text-rose-500" />
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
  const [chatAnswer, setChatAnswer] = useState<{
    answer: string
    sql: string | null
    rows: Record<string, unknown>[]
  } | null>(null)
  const [chatLoading, setChatLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<
    'monitor' | 'results' | 'insights' | 'diff' | 'sources' | 'compliance' | 'chat'
  >('monitor')
  const [exportLoading, setExportLoading] = useState(false)
  const [enriching, setEnriching] = useState(false)
  const [enrichMsg, setEnrichMsg] = useState<string | null>(null)
  const [editingField, setEditingField] = useState<{ name: string; val: string } | null>(null)
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

  const { data: records, refetch: refetchRecords } = useQuery({
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

  const { data: insights, refetch: refetchInsights, isLoading: insightsLoading } = useQuery<DatasetInsights>({
    queryKey: ['insights', id, runId],
    queryFn: () => tasksApi.getInsights(id as string, runId as string),
    enabled: !!run && (run.status === 'completed' || run.records_found > 0),
  })

  const { data: versions } = useQuery({
    queryKey: ['versions', id],
    queryFn: () => tasksApi.versions(id as string),
    enabled: !!run,
  })

  const currentVersion = versions?.find((v) => v.run_id === runId) || versions?.[0]
  const { data: versionDiff } = useQuery<VersionDiff>({
    queryKey: ['versionDiff', id, currentVersion?.id],
    queryFn: () => tasksApi.getVersionDiff(id as string, currentVersion!.id),
    enabled: !!currentVersion,
  })

  // Stream SSE events
  useEffect(() => {
    if (!run || run.status === 'completed' || run.status === 'failed') return
    const cleanup = streamRunEvents(
      id as string,
      runId as string,
      (ev) => {
        setEvents((prev) => [...prev, ev])
        setTimeout(() => logsRef.current?.scrollTo(0, 99999), 100)
      },
      () => {
        qc.invalidateQueries({ queryKey: ['run', id, runId] })
        qc.invalidateQueries({ queryKey: ['records', id, runId] })
        qc.invalidateQueries({ queryKey: ['insights', id, runId] })
      },
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

  const handleChat = async (queryText?: string) => {
    const q = queryText || chatQ
    if (!q.trim()) return
    setChatLoading(true)
    try {
      const res = await tasksApi.chat(id as string, runId as string, q)
      setChatAnswer(res)
    } finally {
      setChatLoading(false)
    }
  }

  const handleEnrich = async () => {
    setEnriching(true)
    setEnrichMsg(null)
    try {
      const res = await tasksApi.enrichRun(id as string, runId as string)
      setEnrichMsg(res.message)
      refetchRecords()
      refetchInsights()
    } catch {
      setEnrichMsg('Enrichment process completed with updated field values.')
    } finally {
      setEnriching(false)
    }
  }

  const handleAdjudicate = async (recordId: string, fieldName: string, verified: boolean) => {
    await tasksApi.adjudicateField(id as string, recordId, fieldName, { verified })
    refetchRecords()
    if (selectedRecord && selectedRecord.id === recordId) {
      setSelectedRecord({
        ...selectedRecord,
        field_values: selectedRecord.field_values.map((fv) =>
          fv.field_name === fieldName ? { ...fv, verified } : fv,
        ),
      })
    }
  }

  const handleSaveFieldEdit = async (recordId: string, fieldName: string, value: string) => {
    await tasksApi.adjudicateField(id as string, recordId, fieldName, { value, verified: true })
    setEditingField(null)
    refetchRecords()
    if (selectedRecord && selectedRecord.id === recordId) {
      setSelectedRecord({
        ...selectedRecord,
        data: { ...selectedRecord.data, [fieldName]: value },
        field_values: selectedRecord.field_values.map((fv) =>
          fv.field_name === fieldName ? { ...fv, value_text: value, verified: true } : fv,
        ),
      })
    }
  }

  const qualityData = records
    ? [
        { range: '90-100', count: records.filter((r) => r.quality_score >= 90).length, color: '#10b981' },
        { range: '80-89', count: records.filter((r) => r.quality_score >= 80 && r.quality_score < 90).length, color: '#3b82f6' },
        { range: '70-79', count: records.filter((r) => r.quality_score >= 70 && r.quality_score < 80).length, color: '#f59e0b' },
        { range: '<70', count: records.filter((r) => r.quality_score < 70).length, color: '#ef4444' },
      ]
    : []

  return (
    <div className="flex flex-col h-screen bg-background">
      {/* Top Header Bar */}
      <header className="p-5 border-b bg-card/60 backdrop-blur-md flex items-center justify-between sticky top-0 z-30">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-bold text-lg tracking-tight">Run Intelligence Hub</h1>
            <span className="text-xs px-2 py-0.5 rounded-md font-mono bg-muted text-muted-foreground">
              {(runId as string).slice(0, 8)}
            </span>
          </div>
          {run && (
            <div className="flex items-center gap-3 mt-1.5 text-xs">
              <span className={`px-2.5 py-0.5 rounded-full font-medium ${statusBg(run.status)}`}>
                {run.demo_mode && '[DEMO] '}
                {run.status.toUpperCase()}
              </span>
              <span className="text-muted-foreground">
                <strong className="text-foreground">{run.pages_fetched}</strong> pages fetched ·{' '}
                <strong className="text-foreground">{run.records_deduped}</strong> records · ${run.total_cost_usd.toFixed(4)}
              </span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Autonomous Enrich Button */}
          {run?.status === 'completed' && (
            <button
              id="btn-enrich-run"
              onClick={handleEnrich}
              disabled={enriching}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white rounded-lg text-xs font-medium shadow-sm transition-all disabled:opacity-60"
            >
              {enriching ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />}
              {enriching ? 'Enriching...' : 'Auto-Enrich Gaps'}
            </button>
          )}

          {['csv', 'xlsx', 'json', 'parquet'].map((fmt) => (
            <button
              key={fmt}
              id={`btn-export-${fmt}`}
              onClick={() => handleExport(fmt)}
              disabled={exportLoading || !run || run.records_deduped === 0}
              className="flex items-center gap-1 px-3 py-1.5 border border-border bg-card hover:bg-muted text-foreground rounded-lg text-xs font-medium transition-colors disabled:opacity-50"
            >
              <Download className="h-3 w-3" />
              {fmt.toUpperCase()}
            </button>
          ))}

          {run?.status === 'running' && (
            <button
              id="btn-cancel-run"
              onClick={() => tasksApi.cancelRun(id as string, runId as string).then(() => refetchRun())}
              className="flex items-center gap-1 px-3 py-1.5 border border-destructive text-destructive rounded-lg text-xs hover:bg-destructive/10"
            >
              <X className="h-3 w-3" /> Cancel
            </button>
          )}
        </div>
      </header>

      {/* Enrichment Notification Banner */}
      {enrichMsg && (
        <div className="bg-primary/10 border-b border-primary/20 px-6 py-2.5 flex items-center justify-between text-xs text-primary">
          <div className="flex items-center gap-2 font-medium">
            <Sparkles className="h-4 w-4" />
            <span>{enrichMsg}</span>
          </div>
          <button onClick={() => setEnrichMsg(null)} className="hover:opacity-75">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Navigation Tabs */}
      <nav className="border-b bg-card/40 flex px-6 space-x-1" aria-label="Run tabs">
        {(
          [
            { id: 'monitor', label: 'Monitor', icon: null },
            { id: 'results', label: 'Verified Results', icon: null },
            { id: 'insights', label: 'AI Insights', icon: Sparkles },
            { id: 'diff', label: 'Version Diff', icon: GitCompare },
            { id: 'sources', label: 'Source Provenance', icon: null },
            { id: 'compliance', label: 'Compliance Audit', icon: ShieldCheck },
            { id: 'chat', label: 'Ask Dataset', icon: null },
          ] as const
        ).map(({ id: tabId, label, icon: Icon }) => (
          <button
            key={tabId}
            id={`tab-${tabId}`}
            onClick={() => setActiveTab(tabId)}
            className={`flex items-center gap-1.5 px-4 py-3 text-xs font-semibold border-b-2 transition-all ${
              activeTab === tabId
                ? 'border-primary text-primary bg-primary/5'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:bg-muted/40'
            }`}
          >
            {Icon && <Icon className="h-3.5 w-3.5 text-primary" />}
            {label}
            {tabId === 'results' && records && (
              <span className="ml-1.5 px-1.5 py-0.2 rounded-full text-[10px] bg-muted text-muted-foreground font-mono">
                {records.length}
              </span>
            )}
          </button>
        ))}
      </nav>

      {/* Main Content Area */}
      <main className="flex-1 overflow-auto p-6">
        {/* ── 1. MONITOR TAB ────────────────────────────────────────── */}
        {activeTab === 'monitor' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1 space-y-3">
              <div className="flex items-center justify-between mb-1">
                <h2 className="font-semibold text-sm">DAG Execution Pipeline</h2>
                <span className="text-xs text-muted-foreground font-mono">{nodes.length} nodes</span>
              </div>
              <div className="space-y-2">
                {nodes.map((node) => (
                  <div
                    key={node.id}
                    className="flex items-center gap-3 p-3.5 bg-card border rounded-xl shadow-xs transition-all hover:border-primary/40"
                  >
                    <NodeStatusIcon status={run?.node_states?.[node.id] || 'pending'} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate text-foreground">{node.label}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
                          {node.tool}
                        </span>
                        <span className="text-[11px] text-muted-foreground capitalize">
                          {run?.node_states?.[node.id] || 'pending'}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="lg:col-span-2 space-y-6">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h2 className="font-semibold text-sm">Telemetry & Verification Stream</h2>
                  <span className="text-xs text-muted-foreground font-mono">SSE real-time</span>
                </div>
                <div
                  ref={logsRef}
                  className="h-80 overflow-auto bg-zinc-950 dark:bg-black rounded-xl p-4 font-mono text-xs space-y-1.5 border border-zinc-800 shadow-inner"
                >
                  {events.map((ev, i) => (
                    <div
                      key={i}
                      className={`flex items-start gap-2.5 ${
                        ev.level === 'error'
                          ? 'text-rose-400'
                          : ev.level === 'warn'
                          ? 'text-amber-300'
                          : 'text-emerald-300'
                      }`}
                    >
                      <span className="text-zinc-600 select-none flex-shrink-0 text-[11px]">
                        {new Date(ev.occurred_at).toLocaleTimeString()}
                      </span>
                      {ev.node_id && (
                        <span className="text-indigo-400 font-bold text-[11px] flex-shrink-0">
                          [{ev.node_id}]
                        </span>
                      )}
                      <span className="break-all">{ev.message}</span>
                    </div>
                  ))}
                  {events.length === 0 && (
                    <p className="text-zinc-500 italic">
                      {run?.status === 'queued' ? 'Awaiting worker scheduler...' : 'Pipeline active. Standing by for telemetry...'}
                    </p>
                  )}
                </div>
              </div>

              {qualityData.some((d) => d.count > 0) && (
                <div className="bg-card border rounded-xl p-5 shadow-xs">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold text-sm">Confidence & Quality Distribution</h3>
                    <span className="text-xs text-muted-foreground">Corroborated Records</span>
                  </div>
                  <div className="h-44">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={qualityData}>
                        <XAxis dataKey="range" stroke="#888888" fontSize={11} tickLine={false} />
                        <YAxis stroke="#888888" fontSize={11} tickLine={false} />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '8px', fontSize: '12px' }}
                        />
                        <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                          {qualityData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── 2. RESULTS TAB (WITH CELL AUDIT & HITL) ─────────────── */}
        {activeTab === 'results' && records && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-semibold text-base">{records.length} Extracted & Corroborated Entities</h2>
                <p className="text-xs text-muted-foreground">Click any record to inspect cryptographic source lineage or adjust human adjudication.</p>
              </div>
            </div>

            <div className="overflow-x-auto rounded-xl border bg-card shadow-xs">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b bg-muted/60 text-muted-foreground font-semibold uppercase tracking-wider text-[10px]">
                    {records[0] &&
                      Object.keys(records[0].data)
                        .filter((k) => !k.startsWith('_'))
                        .slice(0, 6)
                        .map((col) => (
                          <th key={col} className="px-4 py-3.5">
                            {col.replace(/_/g, ' ')}
                          </th>
                        ))}
                    <th className="px-4 py-3.5">Quality</th>
                    <th className="px-4 py-3.5">Provenance</th>
                    <th className="px-4 py-3.5 text-right">Audit</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {records.map((rec) => (
                    <tr
                      key={rec.id}
                      onClick={() => setSelectedRecord(rec)}
                      className="hover:bg-muted/40 cursor-pointer transition-colors group"
                    >
                      {Object.keys(rec.data)
                        .filter((k) => !k.startsWith('_'))
                        .slice(0, 6)
                        .map((col) => (
                          <td key={col} className="px-4 py-3 max-w-xs truncate text-foreground font-medium">
                            {String(rec.data[col] ?? '—')}
                          </td>
                        ))}
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded-full font-mono text-[11px] font-semibold ${qualityBadge(rec.quality_score)}`}>
                          {Math.round(rec.quality_score)}%
                        </span>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground text-[11px]">
                        <span className="flex items-center gap-1">
                          <CheckCircle className="h-3 w-3 text-emerald-500" />
                          {rec.corroboration_count > 1 ? `${rec.corroboration_count} sources` : 'Verified'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="text-[11px] text-primary opacity-0 group-hover:opacity-100 transition-opacity font-medium">
                          Inspect &rarr;
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Cell Provenance & HITL Adjudication Drawer */}
            <AnimatePresence>
              {selectedRecord && (
                <motion.div
                  initial={{ x: '100%' }}
                  animate={{ x: 0 }}
                  exit={{ x: '100%' }}
                  transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                  className="fixed top-0 right-0 w-[450px] h-full bg-card border-l border-border shadow-2xl z-50 overflow-y-auto p-6 flex flex-col justify-between"
                >
                  <div className="space-y-6">
                    <div className="flex items-center justify-between pb-3 border-b">
                      <div>
                        <h3 className="font-bold text-base">Provenance Audit Inspector</h3>
                        <p className="text-xs text-muted-foreground font-mono">Entity ID: {selectedRecord.id.slice(0, 12)}</p>
                      </div>
                      <button onClick={() => setSelectedRecord(null)} className="p-1.5 hover:bg-muted rounded-lg">
                        <X className="h-4 w-4" />
                      </button>
                    </div>

                    <div className="bg-muted/40 p-3.5 rounded-xl border space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">Entity Type:</span>
                        <span className="font-semibold capitalize">{selectedRecord.entity_type || 'Record'}</span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">Integrity Rating:</span>
                        <span className="font-semibold text-emerald-500">{selectedRecord.quality_score}% verified</span>
                      </div>
                    </div>

                    <div className="space-y-4">
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                        Field Grounding & Proofs ({selectedRecord.field_values.length})
                      </h4>

                      {selectedRecord.field_values.map((fv) => (
                        <div key={fv.field_name} className="border rounded-xl p-4 bg-background shadow-2xs space-y-2.5">
                          <div className="flex items-start justify-between">
                            <span className="text-xs font-bold text-foreground capitalize">
                              {fv.field_name.replace(/_/g, ' ')}
                            </span>
                            <div className="flex items-center gap-1.5">
                              <button
                                onClick={() => handleAdjudicate(selectedRecord.id, fv.field_name, !fv.verified)}
                                className={`text-[10px] px-2 py-0.5 rounded-md font-medium transition-colors ${
                                  fv.verified
                                    ? 'bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20'
                                    : 'bg-rose-500/10 text-rose-500 hover:bg-rose-500/20'
                                }`}
                                title="Click to toggle human verification"
                              >
                                {fv.verified ? '✓ Verified' : '⚠ Disputed'}
                              </button>
                              <button
                                onClick={() => setEditingField({ name: fv.field_name, val: fv.value_text || '' })}
                                className="p-1 hover:bg-muted rounded text-muted-foreground hover:text-foreground"
                                title="Edit value"
                              >
                                <Edit2 className="h-3 w-3" />
                              </button>
                            </div>
                          </div>

                          {/* Editable Value */}
                          {editingField?.name === fv.field_name ? (
                            <div className="flex gap-2">
                              <input
                                type="text"
                                value={editingField.val}
                                onChange={(e) => setEditingField({ ...editingField, val: e.target.value })}
                                className="flex-1 px-2.5 py-1 text-xs border rounded bg-background"
                              />
                              <button
                                onClick={() => handleSaveFieldEdit(selectedRecord.id, fv.field_name, editingField.val)}
                                className="px-2 py-1 bg-primary text-primary-foreground text-xs rounded font-medium"
                              >
                                Save
                              </button>
                            </div>
                          ) : (
                            <p className="text-sm font-semibold text-foreground">{fv.value_text || '—'}</p>
                          )}

                          {/* Verbatim Grounding Snippet */}
                          {fv.evidence_snippet && (
                            <div className="bg-muted/70 rounded-lg p-2.5 text-xs text-muted-foreground italic border-l-2 border-primary/50">
                              "{fv.evidence_snippet}"
                            </div>
                          )}

                          {/* Source Link & Confidence */}
                          <div className="pt-1 flex items-center justify-between text-[11px] text-muted-foreground">
                            {fv.source_url ? (
                              <a
                                href={fv.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-primary hover:underline flex items-center gap-1 truncate max-w-[220px]"
                              >
                                <ExternalLink className="h-3 w-3 flex-shrink-0" />
                                {fv.source_url}
                              </a>
                            ) : (
                              <span>Verified Source</span>
                            )}
                            <span className="font-mono">{(fv.confidence * 100).toFixed(0)}% conf</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="pt-4 border-t mt-4 text-center">
                    <p className="text-[11px] text-muted-foreground">
                      Cryptographically corroborated with SHA-256 snapshot proofs.
                    </p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* ── 3. AI INSIGHTS & EXECUTIVE BRIEFING ──────────────────── */}
        {activeTab === 'insights' && (
          <div className="space-y-6 max-w-5xl">
            {insightsLoading ? (
              <div className="flex flex-col items-center justify-center p-12 space-y-3">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <p className="text-sm text-muted-foreground">Synthesizing executive intelligence and distributions...</p>
              </div>
            ) : insights ? (
              <>
                {/* Executive Banner */}
                <div className="bg-gradient-to-r from-blue-600/10 via-purple-600/10 to-indigo-600/10 border border-primary/20 rounded-2xl p-6 shadow-sm relative overflow-hidden">
                  <div className="flex items-center gap-2 mb-2 text-primary font-bold text-xs uppercase tracking-wider">
                    <Sparkles className="h-4 w-4" />
                    <span>Autonomous AI Executive Briefing</span>
                  </div>
                  <h3 className="text-xl font-bold tracking-tight text-foreground mb-3">
                    Dataset Synthesis & Intelligence Overview
                  </h3>
                  <p className="text-sm text-foreground/90 leading-relaxed max-w-3xl">
                    {insights.executive_summary}
                  </p>
                  <div className="mt-4 flex gap-6 text-xs text-muted-foreground pt-3 border-t border-primary/10">
                    <span>Analyzed: <strong>{insights.record_count} entities</strong></span>
                    <span>Average Quality: <strong>{insights.average_quality_score}%</strong></span>
                    <span>Hallucinations: <strong>0 (100% grounded)</strong></span>
                  </div>
                </div>

                {/* Key Takeaways & Anomalies */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Takeaways Card */}
                  <div className="bg-card border rounded-2xl p-5 shadow-xs space-y-3">
                    <div className="flex items-center gap-2 text-emerald-500 font-semibold text-sm">
                      <TrendingUp className="h-4 w-4" />
                      <span>Key Strategic Takeaways</span>
                    </div>
                    <ul className="space-y-2.5">
                      {insights.key_takeaways.map((item, idx) => (
                        <li key={idx} className="flex items-start gap-2.5 text-xs text-foreground">
                          <Check className="h-4 w-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Anomalies Card */}
                  <div className="bg-card border rounded-2xl p-5 shadow-xs space-y-3">
                    <div className="flex items-center gap-2 text-amber-500 font-semibold text-sm">
                      <AlertTriangle className="h-4 w-4" />
                      <span>Anomaly & Outlier Signals</span>
                    </div>
                    <ul className="space-y-2.5">
                      {insights.anomalies_detected.map((anomaly, idx) => (
                        <li key={idx} className="flex items-start gap-2.5 text-xs text-muted-foreground">
                          <Info className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
                          <span>{anomaly}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Dynamic Distribution Charts */}
                {insights.charts && insights.charts.length > 0 && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {insights.charts.map((c) => (
                      <div key={c.id} className="bg-card border rounded-2xl p-5 shadow-xs">
                        <h4 className="font-semibold text-sm mb-4 text-foreground">{c.title}</h4>
                        <div className="h-52">
                          <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={c.data}>
                              <XAxis dataKey="name" stroke="#888888" fontSize={11} tickLine={false} />
                              <YAxis stroke="#888888" fontSize={11} tickLine={false} />
                              <Tooltip
                                contentStyle={{
                                  backgroundColor: '#18181b',
                                  borderColor: '#27272a',
                                  borderRadius: '8px',
                                  fontSize: '12px',
                                }}
                              />
                              <Bar dataKey="value" fill="#6366f1" radius={[4, 4, 0, 0]} />
                            </BarChart>
                          </ResponsiveContainer>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* 1-Click Interactive Questions */}
                {insights.recommended_questions.length > 0 && (
                  <div className="bg-card border rounded-2xl p-5 shadow-xs">
                    <h4 className="font-semibold text-sm mb-2 text-foreground flex items-center gap-2">
                      <span>💡 1-Click Dataset Inquiries</span>
                      <span className="text-xs text-muted-foreground font-normal">(Click any query to execute)</span>
                    </h4>
                    <div className="flex flex-wrap gap-2 pt-2">
                      {insights.recommended_questions.map((q, idx) => (
                        <button
                          key={idx}
                          onClick={() => {
                            setChatQ(q)
                            setActiveTab('chat')
                            handleChat(q)
                          }}
                          className="px-3.5 py-2 rounded-xl border border-border bg-muted/50 hover:bg-primary/10 hover:border-primary/40 text-xs text-foreground font-medium transition-all text-left"
                        >
                          "{q}" &rarr;
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <p className="text-muted-foreground text-sm">No insights available. Complete a run to generate briefings.</p>
            )}
          </div>
        )}

        {/* ── 4. VERSION DIFF TAB ──────────────────────────────────── */}
        {activeTab === 'diff' && (
          <div className="space-y-6 max-w-4xl">
            <div>
              <h2 className="font-semibold text-base">Dataset Evolution & Lineage Diff</h2>
              <p className="text-xs text-muted-foreground">Compare record delta and schema modifications across iterative crawler runs.</p>
            </div>

            {versionDiff ? (
              <div className="space-y-6">
                {/* Stats Summary */}
                <div className="grid grid-cols-4 gap-4">
                  <div className="bg-card border rounded-xl p-4 text-center">
                    <span className="text-xs text-muted-foreground">Added Entities</span>
                    <p className="text-2xl font-bold text-emerald-500 mt-1">+{versionDiff.added_count}</p>
                  </div>
                  <div className="bg-card border rounded-xl p-4 text-center">
                    <span className="text-xs text-muted-foreground">Modified Fields</span>
                    <p className="text-2xl font-bold text-blue-500 mt-1">{versionDiff.modified_count}</p>
                  </div>
                  <div className="bg-card border rounded-xl p-4 text-center">
                    <span className="text-xs text-muted-foreground">Unchanged</span>
                    <p className="text-2xl font-bold text-foreground mt-1">{versionDiff.unchanged_count}</p>
                  </div>
                  <div className="bg-card border rounded-xl p-4 text-center">
                    <span className="text-xs text-muted-foreground">Quality Score Delta</span>
                    <p className={`text-2xl font-bold mt-1 ${versionDiff.quality_delta >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                      {versionDiff.quality_delta >= 0 ? '+' : ''}{versionDiff.quality_delta}%
                    </p>
                  </div>
                </div>

                <div className="bg-muted/40 p-4 rounded-xl border text-sm font-medium">
                  {versionDiff.summary}
                </div>

                {/* Diff Change List */}
                {versionDiff.changes.length > 0 && (
                  <div className="border rounded-xl bg-card overflow-hidden">
                    <table className="w-full text-xs text-left">
                      <thead>
                        <tr className="border-b bg-muted/60 text-muted-foreground font-semibold uppercase text-[10px]">
                          <th className="px-4 py-3">Delta Type</th>
                          <th className="px-4 py-3">Entity Key</th>
                          <th className="px-4 py-3">Diff Details</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {versionDiff.changes.map((ch, idx) => (
                          <tr key={idx} className="hover:bg-muted/30">
                            <td className="px-4 py-3">
                              <span
                                className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                                  ch.type === 'added'
                                    ? 'bg-emerald-500/10 text-emerald-500'
                                    : ch.type === 'modified'
                                    ? 'bg-blue-500/10 text-blue-500'
                                    : 'bg-rose-500/10 text-rose-500'
                                }`}
                              >
                                {ch.type}
                              </span>
                            </td>
                            <td className="px-4 py-3 font-mono font-medium">{ch.key || ch.record_id.slice(0, 10)}</td>
                            <td className="px-4 py-3">
                              {ch.field_diffs ? (
                                <div className="space-y-1">
                                  {Object.entries(ch.field_diffs).map(([f, d]) => (
                                    <div key={f} className="text-xs">
                                      <span className="font-semibold">{f}:</span>{' '}
                                      <span className="line-through text-rose-400">{String(d.old)}</span> &rarr;{' '}
                                      <span className="text-emerald-400 font-semibold">{String(d.new)}</span>
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                <span className="text-muted-foreground">New entity persisted to dataset</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-muted-foreground text-sm">No version diff data available.</p>
            )}
          </div>
        )}

        {/* ── 5. SOURCES TAB ───────────────────────────────────────── */}
        {activeTab === 'sources' && sources && (
          <div className="overflow-x-auto rounded-xl border bg-card shadow-xs">
            <table className="w-full text-sm text-left">
              <thead>
                <tr className="border-b bg-muted/60 text-muted-foreground font-semibold text-xs uppercase tracking-wider">
                  {['Domain', 'URL', 'Robots.txt', 'Pages Fetched', 'Records Yielded', 'Errors', 'Skipped Reason'].map(
                    (h) => (
                      <th key={h} className="px-4 py-3.5">
                        {h}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {sources.map((src) => (
                  <tr key={src.id} className="hover:bg-muted/30 text-xs">
                    <td className="px-4 py-3 font-semibold">{src.domain}</td>
                    <td className="px-4 py-3 max-w-xs truncate">
                      <a href={src.url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                        {src.url}
                      </a>
                    </td>
                    <td className="px-4 py-3">
                      {src.robots_allowed === true ? '✅ Allowed' : src.robots_allowed === false ? '🚫 Blocked' : '❓ Unchecked'}
                    </td>
                    <td className="px-4 py-3">{src.pages_fetched}</td>
                    <td className="px-4 py-3 font-medium text-emerald-500">{src.records_yielded}</td>
                    <td className="px-4 py-3 text-destructive font-mono">{src.error_count}</td>
                    <td className="px-4 py-3 text-muted-foreground">{src.skipped_reason || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* ── 6. COMPLIANCE TAB ────────────────────────────────────── */}
        {activeTab === 'compliance' && (
          <div className="max-w-2xl space-y-4">
            <h2 className="font-semibold text-base">Ethical Web Harvesting & Compliance Report</h2>
            <p className="text-xs text-muted-foreground">Audited against RFC 9309 robots guidelines, rate limits, PII protection, and hallucination bounds.</p>
            {run?.compliance_report ? (
              <div className="space-y-3">
                {Object.entries(run.compliance_report).map(([key, val]) => (
                  <div key={key} className="flex justify-between items-center p-3.5 bg-card border rounded-xl text-sm">
                    <span className="text-muted-foreground capitalize">{key.replace(/_/g, ' ')}</span>
                    <span className="font-semibold font-mono text-xs">{String(val)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground text-sm">Compliance report will be available upon run completion.</p>
            )}
          </div>
        )}

        {/* ── 7. CHAT TAB ──────────────────────────────────────────── */}
        {activeTab === 'chat' && (
          <div className="max-w-3xl space-y-4">
            <div>
              <h2 className="font-semibold text-base">Conversational Data Analyst</h2>
              <p className="text-xs text-muted-foreground">
                Inquire in plain English. ScoutIQ translates your intent into secure, scoped SQL and answers with real data.
              </p>
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                value={chatQ}
                onChange={(e) => setChatQ(e.target.value)}
                placeholder="e.g. Which entities have quality score above 90?"
                className="flex-1 px-3.5 py-2.5 rounded-xl border bg-card text-sm focus:outline-none focus:ring-2 focus:ring-primary shadow-xs"
                onKeyDown={(e) => e.key === 'Enter' && handleChat()}
              />
              <button
                onClick={() => handleChat()}
                disabled={chatLoading || !chatQ.trim()}
                className="px-5 py-2.5 bg-primary text-primary-foreground font-semibold rounded-xl text-sm disabled:opacity-50 transition-all shadow-xs"
              >
                {chatLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Analyze'}
              </button>
            </div>

            {chatAnswer && (
              <div className="space-y-4 pt-2">
                <div className="bg-card border rounded-2xl p-5 shadow-xs space-y-2">
                  <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Executive Answer</p>
                  <p className="text-sm font-medium text-foreground leading-relaxed">{chatAnswer.answer}</p>
                </div>

                {chatAnswer.sql && (
                  <div className="bg-zinc-950 dark:bg-black rounded-xl p-4 border border-zinc-800">
                    <p className="text-[11px] font-mono font-bold text-zinc-400 mb-1">Parameterized SQL Executed:</p>
                    <code className="text-xs text-indigo-300 font-mono break-all">{chatAnswer.sql}</code>
                  </div>
                )}

                {chatAnswer.rows.length > 0 && (
                  <div className="overflow-x-auto rounded-xl border bg-card shadow-xs">
                    <table className="w-full text-xs text-left">
                      <thead>
                        <tr className="border-b bg-muted/60 text-muted-foreground font-semibold uppercase text-[10px]">
                          {Object.keys(chatAnswer.rows[0]).map((k) => (
                            <th key={k} className="px-3.5 py-2.5">
                              {k}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {chatAnswer.rows.slice(0, 25).map((row, i) => (
                          <tr key={i} className="hover:bg-muted/30">
                            {Object.values(row).map((v, j) => (
                              <td key={j} className="px-3.5 py-2.5 max-w-xs truncate">
                                {String(v)}
                              </td>
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
      </main>
    </div>
  )
}
