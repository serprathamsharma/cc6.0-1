'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore, type AuthStore } from '@/store/auth'
import { authApi } from '@/lib/api'
import { motion } from 'framer-motion'

export default function LoginPage() {
  const router = useRouter()
  const setAuth = useAuthStore((s: AuthStore) => s.setAuth)
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [form, setForm] = useState({ name: '', email: '', password: '', workspace_name: 'My Workspace' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = mode === 'login'
        ? await authApi.login({ email: form.email, password: form.password })
        : await authApi.register(form)
      setAuth({ user_id: res.user_id, workspace_id: res.workspace_id, name: res.name, email: res.email }, res.access_token)
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.message || 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md"
      >
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-primary mb-2">ScoutIQ</h1>
          <p className="text-muted-foreground">AI Data Intelligence Platform</p>
        </div>

        <div className="bg-card rounded-xl border p-8 shadow-lg">
          <div className="flex gap-2 mb-6">
            {(['login', 'register'] as const).map(m => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                  mode === m ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-muted/80'
                }`}
              >
                {m === 'login' ? 'Sign In' : 'Register'}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'register' && (
              <>
                <input
                  type="text" placeholder="Full name"
                  value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  required
                />
                <input
                  type="text" placeholder="Workspace name"
                  value={form.workspace_name} onChange={e => setForm(f => ({ ...f, workspace_name: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </>
            )}
            <input
              type="email" placeholder="Email address"
              value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
              className="w-full px-3 py-2 rounded-lg border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              required
            />
            <input
              type="password" placeholder="Password"
              value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
              className="w-full px-3 py-2 rounded-lg border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              required
            />
            {error && <p className="text-destructive text-sm">{error}</p>}
            <button
              type="submit" disabled={loading}
              className="w-full py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {loading ? 'Please wait...' : mode === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>

          <div className="mt-4 p-3 bg-muted rounded-lg text-xs text-muted-foreground">
            <strong>Demo:</strong> Register with any email/password. No real keys needed — runs in DEMO MODE with fixture data.
          </div>
        </div>
      </motion.div>
    </div>
  )
}
