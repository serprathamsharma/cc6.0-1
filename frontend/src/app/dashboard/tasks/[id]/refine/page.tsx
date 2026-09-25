'use client'
import { useParams, useRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { tasksApi } from '@/lib/api'
import { useState } from 'react'
import { ChevronRight } from 'lucide-react'

export default function RefinePage() {
  const { id } = useParams()
  const router = useRouter()
  const qc = useQueryClient()
  const [refinement, setRefinement] = useState('')
  const [error, setError] = useState('')

  const { data: task } = useQuery({ queryKey: ['task', id], queryFn: () => tasksApi.get(id as string) })

  const refineMutation = useMutation({
    mutationFn: () => tasksApi.refine(id as string, refinement),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['workflows', id] })
      router.push(`/dashboard/tasks/${id}/plan`)
    },
    onError: (err: Error) => setError(err.message),
  })

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-2">Refine Workflow</h1>
      <p className="text-muted-foreground text-sm mb-6">Original: {task?.prompt}</p>

      <div className="space-y-4">
        <textarea
          value={refinement}
          onChange={e => setRefinement(e.target.value)}
          placeholder="e.g. Only remote roles in India, minimum stipend ₹15,000/month"
          rows={4}
          className="w-full px-4 py-3 rounded-xl border bg-card text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary"
        />
        {error && <p className="text-destructive text-sm">{error}</p>}
        <button
          onClick={() => refineMutation.mutate()}
          disabled={!refinement.trim() || refineMutation.isPending}
          className="flex items-center gap-2 px-6 py-3 bg-primary text-primary-foreground rounded-xl font-medium hover:bg-primary/90 disabled:opacity-50"
        >
          Regenerate Plan <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
