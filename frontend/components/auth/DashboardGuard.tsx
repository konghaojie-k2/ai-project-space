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
    // 只在客户端执行
    if (typeof window === 'undefined') {
      return;
    }

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
    // 只在第一次检查时尝试恢复，避免重复调用
    // 注意：如果用户刚刚登录，userStore可能还在更新中，给一个短暂的延迟
    if (authToken && !user && !initialCheckDone) {
      console.log('🔄 DashboardGuard: 有token但无用户信息，等待用户状态更新...');
      setInitialCheckDone(true);
      
      // 先等待一小段时间，让userStore完成状态更新（登录后立即跳转时）
      setTimeout(() => {
        const currentUser = useUserStore.getState().user;
        if (currentUser) {
          console.log('✅ DashboardGuard: 用户状态已更新，无需恢复');
          return;
        }
        
        // 如果仍然没有用户信息，才尝试恢复
        console.log('🔄 DashboardGuard: 用户状态未更新，尝试恢复状态...');
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
          }).catch((error) => {
            console.error('❌ DashboardGuard: 状态恢复出错:', error);
            setTimeout(() => {
              router.replace('/login');
            }, 1000);
          });
        });
      }, 300); // 等待300ms，给userStore时间更新
      
      return;
    }

    // 未登录，跳转到登录页
    if (!user) {
      console.warn('🚪 DashboardGuard: 用户未登录，准备跳转到登录页:', {
        currentPath: typeof window !== 'undefined' ? window.location.pathname : 'unknown',
        hasAuthToken: !!authToken,
        timestamp: new Date().toISOString()
      });
      console.trace('🔍 DashboardGuard跳转调用栈:');
      router.replace('/login')
      return
    }

    // 移除管理员权限限制，允许所有用户访问dashboard
    // 权限控制在各个组件内部处理
    console.log('✅ DashboardGuard: 用户权限验证通过，允许访问:', {
      userEmail: user.email,
      isSuperuser: user.is_superuser,
      currentPath: typeof window !== 'undefined' ? window.location.pathname : 'unknown',
      timestamp: new Date().toISOString()
    });
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

  // 只有未登录才返回null，所有登录用户都可以访问
  if (!user) {
    return null
  }

  // 有权限，显示内容
  return <>{children}</>
}
