'use client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from 'next-themes'
import { useState, useEffect } from 'react'
import { useAuthStore, type AuthStore } from '@/store/auth'

function AuthLoader({ children }: { children: React.ReactNode }) {
  const loadFromStorage = useAuthStore((s: AuthStore) => s.loadFromStorage)
  useEffect(() => { loadFromStorage() }, [loadFromStorage])
  return <>{children}</>
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
  }))
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
        <AuthLoader>{children}</AuthLoader>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
