import type { Metadata, Viewport } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import ToastProvider from '@/components/providers/ToastProvider'
import { UserProvider } from '@/lib/contexts/UserContext'
// UserStatusIndicator功能已集成到Sidebar中
import '@/lib/debug/auth-monitor' // 引入认证监控工具
import '@/lib/debug/redirect-tracker' // 引入重定向追踪器
import '@/lib/utils/auth-sync' // 引入认证状态同步工具

// 配置Inter字体
const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'AI项目管理系统',
  description: '基于AI的智能项目管理平台，支持多模态内容处理和智能问答',
  keywords: ['AI', '项目管理', '智能问答', '文件管理', '团队协作'],
  authors: [{ name: 'AI项目管理系统团队' }],
  icons: {
    icon: [
      { url: '/favicon.ico', sizes: 'any' },
      { url: '/favicon.png', type: 'image/png', sizes: '32x32' },
    ],
    shortcut: '/favicon.ico',
    apple: '/favicon.png',
  },
  openGraph: {
    title: 'AI项目管理系统',
    description: '基于AI的智能项目管理平台',
    type: 'website',
    locale: 'zh_CN',
  },
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN">
      <body className={inter.className}>
        {/* 全局加载状态 */}
        <div id="loading" className="hidden fixed inset-0 bg-white bg-opacity-75 z-50 flex items-center justify-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary-600"></div>
        </div>
        
        {/* 主要内容 */}
        <UserProvider>
          <main className="min-h-screen bg-secondary-50">
            {children}
          </main>
          
          {/* Toast通知提供者 */}
          <ToastProvider />
          
          {/* 用户状态指示器功能已集成到Sidebar中 */}
        </UserProvider>
      </body>
    </html>
  )
} 