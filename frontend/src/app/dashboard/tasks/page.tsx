'use client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { tasksApi } from '@/lib/api'
import { useState } from 'react'
import { formatDate, statusBg } from '@/lib/utils'
import { Archive, Trash2, Copy, Play, ExternalLink } from 'lucide-react'

export default function TasksPage() {
  const router = useRouter()
  const qc = useQueryClient()
  const [archived, setArchived] = useState(false)
  const { data: tasks, isLoading } = useQuery({
    queryKey: ['tasks', archived],
    queryFn: () => tasksApi.list(archived),
  })

  const archiveMutation = useMutation({
    mutationFn: tasksApi.archive,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tasks'] }),
  })
  const deleteMutation = useMutation({
    mutationFn: tasksApi.delete,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tasks'] }),
  })
  const cloneMutation = useMutation({
    mutationFn: tasksApi.clone,
    onSuccess: (task) => router.push(`/dashboard/tasks/${task.id}/plan`),
  })

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Task Manager</h1>
        <div className="flex gap-2">
          <button
            onClick={() => setArchived(false)}
            className={`px-3 py-1.5 rounded-lg text-sm ${!archived ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}
          >Active</button>
          <button
            onClick={() => setArchived(true)}
            className={`px-3 py-1.5 rounded-lg text-sm ${archived ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}
          >Archived</button>
        </div>
      </div>

      {isLoading && <p className="text-muted-foreground">Loading...</p>}

      <div className="space-y-3">
        {tasks?.map(task => (
          <div key={task.id} className="bg-card border rounded-xl p-4 flex items-center gap-4">
            <div className="flex-1 min-w-0">
              <p className="font-medium truncate">{task.title}</p>
              <p className="text-xs text-muted-foreground">{formatDate(task.created_at)}</p>
            </div>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusBg(task.status)}`}>
              {task.status}
            </span>
            <div className="flex gap-2">
              <button onClick={() => router.push(`/dashboard/tasks/${task.id}`)} className="p-1.5 hover:bg-muted rounded">
                <ExternalLink className="h-4 w-4" />
              </button>
              {task.latest_run_id && (
                <button onClick={() => router.push(`/dashboard/tasks/${task.id}/plan`)} className="p-1.5 hover:bg-muted rounded">
                  <Play className="h-4 w-4" />
                </button>
              )}
              <button onClick={() => cloneMutation.mutate(task.id)} className="p-1.5 hover:bg-muted rounded">
                <Copy className="h-4 w-4" />
              </button>
              <button onClick={() => archiveMutation.mutate(task.id)} className="p-1.5 hover:bg-muted rounded">
                <Archive className="h-4 w-4" />
              </button>
              <button onClick={() => deleteMutation.mutate(task.id)} className="p-1.5 hover:bg-muted rounded text-destructive">
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>
        ))}
        {tasks?.length === 0 && (
          <p className="text-muted-foreground text-center py-12">No tasks yet. Create one from the Command Center.</p>
        )}
      </div>
    </div>
  )
}
