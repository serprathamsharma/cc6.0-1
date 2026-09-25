'use client'
import { useParams, useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { tasksApi } from '@/lib/api'
import { formatDate, statusBg } from '@/lib/utils'
import { Play, History, ExternalLink } from 'lucide-react'

export default function TaskDetailPage() {
  const { id } = useParams()
  const router = useRouter()

  const { data: task } = useQuery({ queryKey: ['task', id], queryFn: () => tasksApi.get(id as string) })
  const { data: runs } = useQuery({ queryKey: ['runs', id], queryFn: () => tasksApi.listRuns(id as string) })
  const { data: versions } = useQuery({ queryKey: ['versions', id], queryFn: () => tasksApi.versions(id as string) })

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-1">{task?.title}</h1>
        <p className="text-muted-foreground text-sm">{task?.prompt}</p>
      </div>

      <div className="flex gap-3 mb-8">
        <button
          onClick={() => router.push(`/dashboard/tasks/${id}/plan`)}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm"
        >
          <Play className="h-4 w-4" /> New Run
        </button>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Runs */}
        <div>
          <h2 className="font-semibold mb-3 flex items-center gap-2">
            <Play className="h-4 w-4" /> Runs
          </h2>
          <div className="space-y-2">
            {runs?.map(run => (
              <div
                key={run.id}
                className="p-3 bg-card border rounded-xl cursor-pointer hover:border-primary/50 flex items-center justify-between"
                onClick={() => router.push(`/dashboard/tasks/${id}/runs/${run.id}`)}
              >
                <div>
                  <p className="text-xs font-mono text-muted-foreground">{run.id.slice(0, 8)}...</p>
                  <p className="text-xs text-muted-foreground">{formatDate(run.created_at)}</p>
                  <p className="text-xs mt-1">{run.records_deduped} records{run.demo_mode ? ' [DEMO]' : ''}</p>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full ${statusBg(run.status)}`}>{run.status}</span>
              </div>
            ))}
            {runs?.length === 0 && <p className="text-muted-foreground text-sm">No runs yet.</p>}
          </div>
        </div>

        {/* Dataset Versions */}
        <div>
          <h2 className="font-semibold mb-3 flex items-center gap-2">
            <History className="h-4 w-4" /> Dataset Versions
          </h2>
          <div className="space-y-2">
            {versions?.map(v => (
              <div key={v.id} className="p-3 bg-card border rounded-xl">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">v{v.version_number}</span>
                  <span className="text-xs text-muted-foreground">{v.record_count} records</span>
                </div>
                <p className="text-xs text-muted-foreground">{formatDate(v.created_at)}</p>
                {v.diff_summary && (
                  <div className="mt-1 text-xs text-muted-foreground">
                    +{(v.diff_summary as any).added || 0} / -{(v.diff_summary as any).removed || 0} / ~{(v.diff_summary as any).changed || 0}
                  </div>
                )}
              </div>
            ))}
            {versions?.length === 0 && <p className="text-muted-foreground text-sm">No versions yet.</p>}
          </div>
        </div>
      </div>
    </div>
  )
}
