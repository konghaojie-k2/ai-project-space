'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useUserStore } from '@/lib/stores/userStore'

interface DashboardGuardProps {
  children: React.ReactNode
}

/**
 * Dashboard访问权限保护组件
 * 只允许管理员访问Dashboard页面
 */
export default function DashboardGuard({ children }: DashboardGuardProps) {
  const router = useRouter()
  const { user, loading } = useUserStore()

  useEffect(() => {
    // 等待用户状态加载完成
    if (loading) return

    // 未登录，跳转到登录页
    if (!user) {
      router.replace('/login')
      return
    }

    // 非管理员用户，跳转到无权限页面
    if (!user.is_superuser) {
      router.replace('/unauthorized')
      return
    }
  }, [user, loading, router])

  // 加载中显示
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">验证权限中...</p>
        </div>
      </div>
    )
  }

  // 未登录或无权限
  if (!user || !user.is_superuser) {
    return null
  }

  // 有权限，显示内容
  return <>{children}</>
}
