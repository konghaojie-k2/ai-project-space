'use client'

import { useEffect, useState } from 'react'
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
  const { user, isLoading } = useUserStore()
  const hasHydrated = (useUserStore as any).persist?.hasHydrated?.() ?? true
  const [initialCheckDone, setInitialCheckDone] = useState(false)

  useEffect(() => {
    console.log('🛡️ DashboardGuard 权限检查:', {
      hasHydrated,
      isLoading,
      hasUser: !!user,
      userEmail: user?.email,
      isSuperuser: user?.is_superuser,
      currentPath: window.location.pathname,
      initialCheckDone,
      timestamp: new Date().toISOString()
    });

    // 等待用户状态加载完成
    if (!hasHydrated || isLoading) {
      console.log('⏳ DashboardGuard 等待状态加载:', { hasHydrated, isLoading });
      return;
    }

    // 检查 localStorage 中是否有认证信息
    const authToken = localStorage.getItem('auth-token');
    const userStorage = localStorage.getItem('user-storage');
    
    console.log('🔍 DashboardGuard 检查本地存储:', {
      hasAuthToken: !!authToken,
      hasUserStorage: !!userStorage,
      userFromStorage: userStorage ? JSON.parse(userStorage) : null
    });

    // 如果有 token 但没有用户信息，可能是状态恢复问题
    if (authToken && !user && !initialCheckDone) {
      console.log('🔄 DashboardGuard: 有token但无用户信息，尝试恢复状态...');
      setInitialCheckDone(true);
      
      // 尝试恢复认证状态
      import('@/lib/utils/auth-recovery').then(({ authRecovery }) => {
        authRecovery.attemptRecovery().then((recovered) => {
          if (!recovered) {
            console.log('❌ DashboardGuard: 状态恢复失败，将跳转到登录页');
            setTimeout(() => {
              router.replace('/login');
            }, 1000);
          } else {
            console.log('✅ DashboardGuard: 状态恢复成功');
          }
        });
      });
      
      return;
    }

    // 未登录，跳转到登录页
    if (!user) {
      console.warn('🚪 DashboardGuard: 用户未登录，准备跳转到登录页:', {
        currentPath: window.location.pathname,
        hasAuthToken: !!authToken,
        timestamp: new Date().toISOString()
      });
      console.trace('🔍 DashboardGuard跳转调用栈:');
      router.replace('/login')
      return
    }

    // 非管理员用户，跳转到无权限页面
    if (!user.is_superuser) {
      console.warn('🚫 DashboardGuard: 用户无管理员权限，跳转到未授权页面:', {
        userEmail: user.email,
        isSuperuser: user.is_superuser,
        currentPath: window.location.pathname,
        timestamp: new Date().toISOString()
      });
      router.replace('/unauthorized')
      return
    }

    console.log('✅ DashboardGuard: 权限验证通过，允许访问');
  }, [user, isLoading, hasHydrated, router, initialCheckDone])

  // 加载中显示
  if (!hasHydrated || isLoading) {
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
