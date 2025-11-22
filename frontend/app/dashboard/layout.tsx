'use client'

import { useState } from 'react'
import { usePathname } from 'next/navigation'
import { useUserStore } from '@/lib/stores/userStore'
import DashboardGuard from '@/components/auth/DashboardGuard'
import Header from '@/components/layout/Header'

interface DashboardLayoutProps {
  children: React.ReactNode
}

/**
 * Dashboard布局组件
 * 统一使用顶部横向导航，不再使用侧边栏
 */
export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const { user } = useUserStore()
  const pathname = usePathname()

  // 判断是否为项目详情页面（路径格式：/dashboard/projects/[id]）
  const isProjectDetailPage = /^\/dashboard\/projects\/[^\/]+$/.test(pathname)

  // 判断是否为dashboard首页
  const isDashboardHome = pathname === '/dashboard'

  // 决定是否显示导航菜单（项目详情页面不显示）
  const shouldShowNavigation = !isProjectDetailPage

  return (
    <DashboardGuard>
      <div className="h-screen flex flex-col">
        {/* 顶部导航栏 - 根据页面类型决定是否显示导航 */}
        <Header
          onMenuClick={() => setMobileMenuOpen(true)}
          showTitle={shouldShowNavigation}
        />

        {/* 页面内容 */}
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
    </DashboardGuard>
  )
}
