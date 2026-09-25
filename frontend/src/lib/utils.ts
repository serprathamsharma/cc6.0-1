import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleString()
}

export function formatCost(usd: number): string {
  return `$${usd.toFixed(4)}`
}

export function formatDuration(seconds: number | null): string {
  if (!seconds) return '—'
  if (seconds < 60) return `${Math.round(seconds)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}m ${s}s`
}

export function statusColor(status: string): string {
  const map: Record<string, string> = {
    completed: 'text-green-600 dark:text-green-400',
    running: 'text-blue-600 dark:text-blue-400',
    queued: 'text-yellow-600 dark:text-yellow-400',
    failed: 'text-red-600 dark:text-red-400',
    cancelled: 'text-gray-500',
    paused: 'text-orange-500',
    done: 'text-green-600 dark:text-green-400',
    pending: 'text-yellow-600 dark:text-yellow-400',
  }
  return map[status] || 'text-gray-400'
}

export function statusBg(status: string): string {
  const map: Record<string, string> = {
    completed: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    running: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    queued: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    failed: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    cancelled: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
    paused: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
    draft: 'bg-gray-100 text-gray-600',
    pending: 'bg-yellow-100 text-yellow-800',
  }
  return map[status] || 'bg-gray-100 text-gray-600'
}

export function qualityColor(score: number): string {
  if (score >= 80) return 'text-green-600 dark:text-green-400'
  if (score >= 60) return 'text-yellow-600 dark:text-yellow-400'
  return 'text-red-600 dark:text-red-400'
}

export function qualityBadge(score: number): string {
  if (score >= 80) return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
  if (score >= 60) return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
  return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
}
