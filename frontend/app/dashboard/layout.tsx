// import DashboardGuard from '@/components/auth/DashboardGuard'

interface DashboardLayoutProps {
  children: React.ReactNode
}

/**
 * Dashboard布局组件
 * 临时禁用权限保护进行测试
 */
export default function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <>
      {children}
    </>
  )
}
