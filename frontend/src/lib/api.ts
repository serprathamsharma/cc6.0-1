/**
 * API client for ScoutIQ backend.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

let authToken: string | null = null

export function setToken(token: string) {
  authToken = token
  if (typeof window !== 'undefined') {
    localStorage.setItem('scoutiq_token', token)
    document.cookie = `scoutiq_token=${encodeURIComponent(token)}; path=/; max-age=604800; SameSite=Lax`
  }
}

export function getToken(): string | null {
  if (authToken) return authToken
  if (typeof window !== 'undefined') {
    return localStorage.getItem('scoutiq_token')
  }
  return null
}

export function clearToken() {
  authToken = null
  if (typeof window !== 'undefined') {
    localStorage.removeItem('scoutiq_token')
    localStorage.removeItem('scoutiq_user')
    document.cookie = 'scoutiq_token=; path=/; max-age=0'
  }
}

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }

  return res.json()
}

// Auth
export const authApi = {
  register: (data: { name: string; email: string; password: string; workspace_name: string }) =>
    apiFetch<{ access_token: string; user_id: string; workspace_id: string; name: string; email: string }>(
      '/api/v1/auth/register', { method: 'POST', body: JSON.stringify(data) }
    ),
  login: (data: { email: string; password: string }) =>
    apiFetch<{ access_token: string; user_id: string; workspace_id: string; name: string; email: string }>(
      '/api/v1/auth/login', { method: 'POST', body: JSON.stringify(data) }
    ),
}

// Health
export const healthApi = {
  get: () => apiFetch<{ status: string; demo_mode: boolean; model_planner: string }>('/health'),
}

// Tasks
export const tasksApi = {
  list: (archived = false) => apiFetch<Task[]>(`/api/v1/tasks?archived=${archived}`),
  create: (prompt: string) => apiFetch<Task>('/api/v1/tasks', { method: 'POST', body: JSON.stringify({ prompt }) }),
  get: (id: string) => apiFetch<Task>(`/api/v1/tasks/${id}`),
  plan: (id: string) => apiFetch<Workflow>(`/api/v1/tasks/${id}/plan`, { method: 'POST' }),
  approve: (taskId: string, workflowId: string, autoRun = true) =>
    apiFetch<Run>(`/api/v1/tasks/${taskId}/workflows/${workflowId}/approve`, {
      method: 'POST', body: JSON.stringify({ auto_run: autoRun })
    }),
  listWorkflows: (taskId: string) => apiFetch<Workflow[]>(`/api/v1/tasks/${taskId}/workflows`),
  listRuns: (taskId: string) => apiFetch<Run[]>(`/api/v1/tasks/${taskId}/runs`),
  getRun: (taskId: string, runId: string) => apiFetch<Run>(`/api/v1/tasks/${taskId}/runs/${runId}`),
  getRecords: (taskId: string, runId: string, params?: { search?: string; quarantined?: boolean; limit?: number; offset?: number }) => {
    const q = new URLSearchParams()
    if (params?.search) q.set('search', params.search)
    if (params?.quarantined !== undefined) q.set('quarantined', String(params.quarantined))
    if (params?.limit) q.set('limit', String(params.limit))
    if (params?.offset) q.set('offset', String(params.offset))
    return apiFetch<RecordOut[]>(`/api/v1/tasks/${taskId}/runs/${runId}/records?${q}`)
  },
  getSources: (taskId: string, runId: string) =>
    apiFetch<SourceOut[]>(`/api/v1/tasks/${taskId}/runs/${runId}/sources`),
  export: (taskId: string, runId: string, format: string, includeProvenance = true) =>
    fetch(`${API_URL}/api/v1/tasks/${taskId}/runs/${runId}/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}` },
      body: JSON.stringify({ format, include_provenance: includeProvenance }),
    }),
  refine: (taskId: string, refinement: string) =>
    apiFetch<Workflow>(`/api/v1/tasks/${taskId}/refine`, { method: 'POST', body: JSON.stringify({ refinement }) }),
  chat: (taskId: string, runId: string, question: string) =>
    apiFetch<{ answer: string; sql: string | null; rows: Record<string, unknown>[] }>(
      `/api/v1/tasks/${taskId}/runs/${runId}/chat`,
      { method: 'POST', body: JSON.stringify({ question }) }
    ),
  versions: (taskId: string) => apiFetch<DatasetVersion[]>(`/api/v1/tasks/${taskId}/versions`),
  getVersionDiff: (taskId: string, versionId: string) =>
    apiFetch<VersionDiff>(`/api/v1/tasks/${taskId}/versions/${versionId}/diff`),
  getInsights: (taskId: string, runId: string) =>
    apiFetch<DatasetInsights>(`/api/v1/tasks/${taskId}/runs/${runId}/insights`),
  enrichRun: (taskId: string, runId: string) =>
    apiFetch<{ enriched_records: number; fields_filled: number; message: string }>(
      `/api/v1/tasks/${taskId}/runs/${runId}/enrich`,
      { method: 'POST' }
    ),
  adjudicateField: (taskId: string, recordId: string, fieldName: string, data: { verified?: boolean; value?: string }) =>
    apiFetch<{ ok: boolean }>(
      `/api/v1/tasks/${taskId}/records/${recordId}/fields/${fieldName}`,
      { method: 'PATCH', body: JSON.stringify(data) }
    ),
  archive: (taskId: string) => apiFetch<void>(`/api/v1/tasks/${taskId}/archive`, { method: 'PATCH' }),
  delete: (taskId: string) => apiFetch<void>(`/api/v1/tasks/${taskId}`, { method: 'DELETE' }),
  clone: (taskId: string) => apiFetch<Task>(`/api/v1/tasks/${taskId}/clone`, { method: 'POST' }),
  cancelRun: (taskId: string, runId: string) =>
    apiFetch<void>(`/api/v1/tasks/${taskId}/runs/${runId}/cancel`, { method: 'PATCH' }),
  kpis: () => apiFetch<{ total_tasks: number; total_runs: number; total_records: number; demo_mode: boolean }>('/api/v1/tasks/kpis/summary'),
}

// SSE
export function streamRunEvents(
  taskId: string,
  runId: string,
  onEvent: (event: RunEvent) => void,
  onDone: () => void,
): () => void {
  const token = getToken()
  const url = `${API_URL}/api/v1/tasks/${taskId}/runs/${runId}/events`
  const es = new EventSource(url + (token ? `?token=${token}` : ''))
  es.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data)
      if (data.type === 'done') {
        onDone()
        es.close()
      } else {
        onEvent(data as RunEvent)
      }
    } catch {}
  }
  es.onerror = () => { onDone(); es.close() }
  return () => es.close()
}

// Types
export interface Task {
  id: string
  title: string
  prompt: string
  status: string
  created_at: string
  updated_at: string
  latest_run_id: string | null
  latest_dataset_version_id: string | null
}

export interface DAGNode {
  id: string
  tool: string
  label: string
  config: Record<string, unknown>
  depends_on: string[]
  estimated_time_s: number
  estimated_cost_usd: number
}

export interface Workflow {
  id: string
  task_id: string
  version: number
  requirement_spec: Record<string, unknown>
  dag: { nodes: DAGNode[]; title: string; description: string }
  assumptions: string[]
  estimated_time_s: number | null
  estimated_cost_usd: number | null
  approved: boolean
  created_at: string
}

export interface Run {
  id: string
  task_id: string
  workflow_id: string
  status: string
  node_states: Record<string, string>
  started_at: string | null
  finished_at: string | null
  pages_fetched: number
  records_found: number
  records_validated: number
  records_deduped: number
  error_count: number
  total_cost_usd: number
  compliance_report: Record<string, unknown> | null
  demo_mode: boolean
  created_at: string
}

export interface RunEvent {
  id: string
  type: string
  node_id: string | null
  message: string
  level: string
  data: Record<string, unknown> | null
  occurred_at: string
}

export interface FieldValue {
  field_name: string
  value_text: string | null
  source_url: string | null
  evidence_snippet: string | null
  extraction_method: string
  confidence: number
  verified: boolean
}

export interface RecordOut {
  id: string
  data: Record<string, unknown>
  quality_score: number
  quality_flags: string[]
  is_quarantined: boolean
  quarantine_reasons: string[]
  corroboration_count: number
  pii_flagged: boolean
  entity_type: string
  field_values: FieldValue[]
}

export interface SourceOut {
  id: string
  domain: string
  url: string
  robots_allowed: boolean | null
  pages_fetched: number
  records_yielded: number
  error_count: number
  skipped_reason: string | null
}

export interface DatasetVersion {
  id: string
  version_number: number
  run_id: string
  record_count: number
  diff_summary: Record<string, unknown> | null
  created_at: string
}

export interface DatasetInsights {
  record_count: number
  average_quality_score: number
  executive_summary: string
  key_takeaways: string[]
  anomalies_detected: string[]
  distributions: Record<string, unknown>
  charts: { id: string; title: string; type: string; data: { name: string; value: number }[] }[]
  recommended_questions: string[]
  analyzed_at: string
}

export interface VersionDiff {
  current_version: number
  previous_version: number | null
  summary: string
  added_count: number
  removed_count: number
  modified_count: number
  unchanged_count: number
  quality_delta: number
  changes: Array<{
    type: 'added' | 'removed' | 'modified'
    record_id: string
    key?: string
    preview?: Record<string, unknown>
    field_diffs?: Record<string, { old: unknown; new: unknown }>
  }>
}

