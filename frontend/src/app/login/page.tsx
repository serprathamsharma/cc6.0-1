'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowRight, Zap } from 'lucide-react'

export default function LoginPage() {
  const router = useRouter()

  useEffect(() => {
    router.replace('/dashboard')
  }, [router])

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="text-center max-w-md bg-card border rounded-2xl p-8 shadow-xl">
        <div className="h-12 w-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center mx-auto mb-4">
          <Zap className="h-6 w-6" />
        </div>
        <h1 className="text-2xl font-bold mb-2">Welcome to ScoutIQ</h1>
        <p className="text-sm text-muted-foreground mb-6">
          Sign-in is currently bypassed for demo mode. Entering dashboard directly...
        </p>
        <Link
          href="/dashboard"
          className="inline-flex items-center justify-center gap-2 w-full py-2.5 px-4 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors"
        >
          Enter Dashboard <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </div>
  )
}
