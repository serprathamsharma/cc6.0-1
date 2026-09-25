'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { tasksApi, healthApi } from '@/lib/api'
import { motion } from 'framer-motion'
import { Sparkles, TrendingUp, Database, Play, ArrowRight, AlertCircle } from 'lucide-react'
import { statusBg, formatDate } from '@/lib/utils'

const EXAMPLES = [
  { label: '🎓 AI/ML Internships India', prompt: 'Find AI/ML internships in India posted in the last 30 days at product companies, with apply link, stipend, and skills.' },
  { label: '🏆 Hackathon Sponsors Delhi/NCR', prompt: 'Find companies that sponsored tech hackathons or developer events in Delhi/NCR, with sponsorship tier and a contact page.' },
  { label: '💰 SaaS Pricing Plans', prompt: 'Collect pricing plans of the top 20 project-management SaaS tools.' },
  { label: '🚀 Sales Leads B2B SaaS', prompt: 'Find B2B SaaS companies in India that raised Series A in 2024, with company size and contact page.' },
]

export default function DashboardPage() {
  const router = useRouter()
  const qc = useQueryClient()
  const [prompt, setPrompt] = useState('')
  const [error, setError] = useState('')

  const { data: health } = useQuery({ queryKey: ['health'], queryFn: healthApi.get })
  const { data: kpis } = useQuery({ queryKey: ['kpis'], queryFn: tasksApi.kpis })
  const { data: tasks } = useQuery({ queryKey: ['tasks'], queryFn: () => tasksApi.list() })

  const createMutation = useMutation({
    mutationFn: tasksApi.create,
    onSuccess: (task) => {
      qc.invalidateQueries({ queryKey: ['tasks'] })
      router.push(`/dashboard/tasks/${task.id}/plan`)
    },
    onError: (err: Error) => setError(err.message),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!prompt.trim()) return
    setError('')
    createMutation.mutate(prompt.trim())
  }

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* Demo mode banner */}
      {health?.demo_mode && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6 flex items-center gap-2 px-4 py-3 bg-yellow-100 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-800 rounded-lg text-yellow-800 dark:text-yellow-200 text-sm"
        >
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          <span><strong>DEMO MODE</strong> — No API keys detected. Running with pre-recorded fixture data. Every record still traces to a source URL and evidence snippet.</span>
        </motion.div>
      )}

      {/* Hero */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
        <h1 className="text-3xl font-bold mb-2 flex items-center gap-3">
          <Sparkles className="h-8 w-8 text-primary" />
          What data do you need?
        </h1>
        <p className="text-muted-foreground">Describe your data need in plain English. ScoutIQ turns it into a clean, source-backed dataset.</p>
      </motion.div>

      {/* Prompt box */}
      <form onSubmit={handleSubmit} className="mb-8">
        <div className="relative">
          <textarea
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            placeholder="e.g. Find AI/ML internships in India posted in the last 30 days at product companies, with apply link, stipend, and skills."
            rows={4}
            className="w-full px-4 py-4 rounded-xl border bg-card text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary shadow-sm"
            onKeyDown={e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit(e as any) }}
          />
          <div className="absolute bottom-4 right-4">
            <button
              type="submit"
              disabled={!prompt.trim() || createMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              <Play className="h-4 w-4" />
              {createMutation.isPending ? 'Starting...' : 'Scout It'}
            </button>
          </div>
        </div>
        {error && <p className="mt-2 text-destructive text-sm">{error}</p>}
        <p className="mt-2 text-xs text-muted-foreground">Tip: Cmd+Enter to submit</p>
      </form>

      {/* Example chips */}
      <div className="mb-10">
        <p className="text-sm font-medium text-muted-foreground mb-3">Try an example:</p>
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map(ex => (
            <button
              key={ex.label}
              onClick={() => setPrompt(ex.prompt)}
              className="px-3 py-1.5 rounded-lg border text-sm hover:bg-muted transition-colors"
            >
              {ex.label}
            </button>
          ))}
        </div>
      </div>

      {/* KPIs */}
      {kpis && (
        <div className="grid grid-cols-3 gap-4 mb-10">
          {[
            { label: 'Total Tasks', value: kpis.total_tasks, icon: Database },
            { label: 'Total Runs', value: kpis.total_runs, icon: Play },
            { label: 'Records Collected', value: kpis.total_records.toLocaleString(), icon: TrendingUp },
          ].map(({ label, value, icon: Icon }) => (
            <div key={label} className="bg-card border rounded-xl p-5">
              <div className="flex items-center gap-2 text-muted-foreground text-sm mb-1">
                <Icon className="h-4 w-4" />{label}
              </div>
              <div className="text-2xl font-bold">{value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Recent tasks */}
      {tasks && tasks.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Recent Workflows</h2>
          <div className="space-y-3">
            {tasks.slice(0, 5).map(task => (
              <motion.div
                key={task.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center justify-between p-4 bg-card border rounded-xl hover:border-primary/50 transition-colors cursor-pointer"
                onClick={() => router.push(`/dashboard/tasks/${task.id}`)}
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{task.title}</p>
                  <p className="text-xs text-muted-foreground">{formatDate(task.created_at)}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusBg(task.status)}`}>
                    {task.status}
                  </span>
                  <ArrowRight className="h-4 w-4 text-muted-foreground" />
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
