'use client'
import { useParams, useRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { tasksApi, type DAGNode } from '@/lib/api'
import { useState, useCallback } from 'react'
import ReactFlow, { Node, Edge, Background, Controls, MiniMap, useNodesState, useEdgesState } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { motion } from 'framer-motion'
import { Play, Zap, Clock, DollarSign, CheckCircle, ChevronRight } from 'lucide-react'
import { formatCost, formatDuration } from '@/lib/utils'

const TOOL_COLORS: Record<string, string> = {
  discover_sources: '#3b82f6',
  fetch_static: '#06b6d4',
  fetch_dynamic: '#0891b2',
  extract_structured: '#8b5cf6',
  extract_llm: '#7c3aed',
  paginate: '#64748b',
  normalize: '#10b981',
  validate: '#059669',
  dedupe: '#f59e0b',
  enrich: '#f97316',
  score: '#22c55e',
}

function dagToFlow(nodes: DAGNode[]): { nodes: Node[]; edges: Edge[] } {
  const cols: Record<number, DAGNode[]> = {}
  const depthMap: Record<string, number> = {}
  
  // Topological sort for depth
  const getDepth = (id: string, visited = new Set<string>()): number => {
    if (depthMap[id] !== undefined) return depthMap[id]
    const node = nodes.find(n => n.id === id)
    if (!node || node.depends_on.length === 0) return (depthMap[id] = 0)
    const maxDep = Math.max(...node.depends_on.map(d => getDepth(d, visited)))
    return (depthMap[id] = maxDep + 1)
  }
  nodes.forEach(n => getDepth(n.id))
  nodes.forEach(n => {
    const d = depthMap[n.id] || 0
    ;(cols[d] = cols[d] || []).push(n)
  })

  const flowNodes: Node[] = []
  const flowEdges: Edge[] = []

  Object.entries(cols).forEach(([col, colNodes]) => {
    colNodes.forEach((node, rowIdx) => {
      flowNodes.push({
        id: node.id,
        position: { x: Number(col) * 220, y: rowIdx * 100 },
        data: { label: (
          <div className="text-xs">
            <div className="font-semibold">{node.label}</div>
            <div className="opacity-60">{node.tool}</div>
          </div>
        ) },
        style: {
          background: TOOL_COLORS[node.tool] || '#64748b',
          color: 'white',
          border: 'none',
          borderRadius: 8,
          padding: '8px 12px',
          minWidth: 160,
        },
      })
      node.depends_on.forEach(dep => {
        flowEdges.push({
          id: `${dep}-${node.id}`,
          source: dep,
          target: node.id,
          animated: true,
          style: { stroke: '#94a3b8' },
        })
      })
    })
  })

  return { nodes: flowNodes, edges: flowEdges }
}

export default function PlanPage() {
  const { id } = useParams()
  const router = useRouter()
  const qc = useQueryClient()
  const [autoRun, setAutoRun] = useState(true)

  const { data: task } = useQuery({ queryKey: ['task', id], queryFn: () => tasksApi.get(id as string) })
  const { data: workflows, isLoading: planLoading } = useQuery({
    queryKey: ['workflows', id],
    queryFn: () => tasksApi.listWorkflows(id as string),
  })

  const planMutation = useMutation({
    mutationFn: () => tasksApi.plan(id as string),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['workflows', id] }),
  })

  const approveMutation = useMutation({
    mutationFn: (workflowId: string) => tasksApi.approve(id as string, workflowId, autoRun),
    onSuccess: (run) => router.push(`/dashboard/tasks/${id}/runs/${run.id}`),
  })

  const latestWorkflow = workflows?.[0]
  const { nodes: flowNodes, edges: flowEdges } = latestWorkflow
    ? dagToFlow(latestWorkflow.dag.nodes)
    : { nodes: [], edges: [] }

  const [nodes, , onNodesChange] = useNodesState(flowNodes)
  const [edges, , onEdgesChange] = useEdgesState(flowEdges)

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-1">Plan Review</h1>
        <p className="text-muted-foreground text-sm truncate">{task?.prompt}</p>
      </div>

      {!latestWorkflow ? (
        <div className="text-center py-16">
          <p className="text-muted-foreground mb-4">No workflow plan yet. Generate one to continue.</p>
          <button
            onClick={() => planMutation.mutate()}
            disabled={planMutation.isPending}
            className="px-6 py-3 bg-primary text-primary-foreground rounded-xl font-medium hover:bg-primary/90 disabled:opacity-50"
          >
            {planMutation.isPending ? 'Generating plan...' : 'Generate Workflow Plan'}
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Estimates */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-card border rounded-xl p-4 flex items-center gap-3">
              <Clock className="h-5 w-5 text-primary" />
              <div>
                <p className="text-xs text-muted-foreground">Estimated Time</p>
                <p className="font-semibold">{formatDuration(latestWorkflow.estimated_time_s)}</p>
              </div>
            </div>
            <div className="bg-card border rounded-xl p-4 flex items-center gap-3">
              <DollarSign className="h-5 w-5 text-primary" />
              <div>
                <p className="text-xs text-muted-foreground">Estimated Cost</p>
                <p className="font-semibold">{formatCost(latestWorkflow.estimated_cost_usd || 0)}</p>
              </div>
            </div>
          </div>

          {/* DAG */}
          <div className="bg-card border rounded-xl overflow-hidden" style={{ height: 400 }}>
            <div className="p-3 border-b text-sm font-medium">{latestWorkflow.dag.title}</div>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              fitView
              proOptions={{ hideAttribution: true }}
            >
              <Background />
              <Controls />
              <MiniMap />
            </ReactFlow>
          </div>

          {/* Requirement Spec */}
          <div className="bg-card border rounded-xl p-5">
            <h3 className="font-semibold mb-3">Requirement Spec</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Entity Type:</span>{' '}
                <span className="font-medium">{latestWorkflow.requirement_spec.entity_type as string}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Target Volume:</span>{' '}
                <span className="font-medium">{latestWorkflow.requirement_spec.target_volume as number} records</span>
              </div>
              <div>
                <span className="text-muted-foreground">Freshness:</span>{' '}
                <span className="font-medium">{latestWorkflow.requirement_spec.freshness_days as number} days</span>
              </div>
            </div>
          </div>

          {/* Assumptions */}
          {latestWorkflow.assumptions.length > 0 && (
            <div className="bg-card border rounded-xl p-5">
              <h3 className="font-semibold mb-3">Assumptions</h3>
              <ul className="space-y-1">
                {latestWorkflow.assumptions.map((a: string, i: number) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <CheckCircle className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                    {a}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Auto-run toggle + Approve */}
          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={autoRun}
                onChange={e => setAutoRun(e.target.checked)}
                className="rounded"
              />
              Auto-run after approval
            </label>
            <button
              onClick={() => approveMutation.mutate(latestWorkflow.id)}
              disabled={approveMutation.isPending}
              className="flex items-center gap-2 px-6 py-3 bg-primary text-primary-foreground rounded-xl font-medium hover:bg-primary/90 disabled:opacity-50"
            >
              <Play className="h-4 w-4" />
              {approveMutation.isPending ? 'Starting...' : 'Approve & Run'}
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
