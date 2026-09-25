'use client'
import { useRouter } from 'next/navigation'
import { useEffect } from 'react'
import { useAuthStore, type AuthStore } from '@/store/auth'

export default function RootPage() {
  const router = useRouter()
  const user = useAuthStore((s: AuthStore) => s.user)
  useEffect(() => {
    if (user) router.replace('/dashboard')
    else router.replace('/login')
  }, [user, router])
  return null
}
