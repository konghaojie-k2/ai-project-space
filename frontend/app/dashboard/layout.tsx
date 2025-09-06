import DashboardGuard from '@/components/auth/DashboardGuard'

interface DashboardLayoutProps {
  children: React.ReactNode
}

/**
 * Dashboard布局组件
 * 只允许管理员访问Dashboard页面
 */
export default function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <DashboardGuard>
      {children}
    </DashboardGuard>
  )
}
