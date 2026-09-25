'use client'
import { useQuery } from '@tanstack/react-query'
import { tasksApi } from '@/lib/api'
import { formatDate, statusBg } from '@/lib/utils'
import { useRouter } from 'next/navigation'

export default function HistoryPage() {
  const router = useRouter()
  const { data: tasks } = useQuery({ queryKey: ['tasks'], queryFn: () => tasksApi.list() })

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-6">History</h1>
      <div className="space-y-4">
        {tasks?.map(task => (
          <div
            key={task.id}
            className="bg-card border rounded-xl p-5 cursor-pointer hover:border-primary/50"
            onClick={() => router.push(`/dashboard/tasks/${task.id}`)}
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="font-medium">{task.title}</p>
                <p className="text-xs text-muted-foreground mt-1">{formatDate(task.created_at)}</p>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusBg(task.status)}`}>
                {task.status}
              </span>
            </div>
            <p className="text-sm text-muted-foreground mt-2 line-clamp-2">{task.prompt}</p>
          </div>
        ))}
        {tasks?.length === 0 && (
          <p className="text-muted-foreground text-center py-12">No workflow history yet.</p>
        )}
      </div>
    </div>
  )
}
