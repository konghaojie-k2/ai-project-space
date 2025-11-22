'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Bars3Icon,
  HomeIcon,
  FolderIcon,
  DocumentTextIcon,
  ChatBubbleLeftRightIcon,
  BookOpenIcon,
  ChartBarIcon,
  UsersIcon,
  Cog6ToothIcon,
  ChevronDownIcon,
  EyeIcon,
  EyeSlashIcon,
  ClockIcon
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'
import { useUserStore } from '@/lib/stores/userStore'

interface HeaderProps {
  onMenuClick: () => void
  showTitle?: boolean
}

// 导航菜单配置
const navigation = [
  {
    name: '概览',
    href: '/dashboard',
    icon: HomeIcon,
    current: false
  },
  {
    name: '项目管理',
    href: '/dashboard/projects',
    icon: FolderIcon,
    current: false
  },
  {
    name: '文件管理',
    href: '/dashboard/files',
    icon: DocumentTextIcon,
    current: false
  },
  {
    name: 'AI问答',
    href: '/dashboard/chat',
    icon: ChatBubbleLeftRightIcon,
    current: false
  },
  {
    name: '知识笔记',
    href: '/dashboard/notes',
    icon: BookOpenIcon,
    current: false
  },
  {
    name: '数据分析',
    href: '/dashboard/analytics',
    icon: ChartBarIcon,
    current: false
  },
  {
    name: '团队管理',
    href: '/dashboard/team',
    icon: UsersIcon,
    current: false
  }
]

const Header: React.FC<HeaderProps> = ({ onMenuClick, showTitle = true }) => {
  const { user, isAuthenticated, isLoading } = useUserStore()
  const pathname = usePathname()
  const [showDebugInfo, setShowDebugInfo] = useState(false)
  const [authToken, setAuthToken] = useState<string | null>(null)
  const [refreshToken, setRefreshToken] = useState<string | null>(null)
  const [isClient, setIsClient] = useState(false)
  const [currentTime, setCurrentTime] = useState<string>('')

  useEffect(() => {
    setIsClient(true)
  }, [])

  useEffect(() => {
    if (isClient) {
      // 初始化时间
      setCurrentTime(new Date().toLocaleTimeString())

      // 每秒更新时间
      const timeInterval = setInterval(() => {
        setCurrentTime(new Date().toLocaleTimeString())
      }, 1000)

      return () => clearInterval(timeInterval)
    }
  }, [isClient])

  useEffect(() => {
    if (isClient && (process.env.NODE_ENV === 'development' || showDebugInfo)) {
      const updateTokens = () => {
        setAuthToken(localStorage.getItem('auth-token'))
        setRefreshToken(localStorage.getItem('refresh-token'))
      }

      updateTokens()
      const interval = setInterval(updateTokens, 1000)
      return () => clearInterval(interval)
    }
  }, [isClient, showDebugInfo])

  const isActiveLink = (href: string) => {
    return pathname === href || pathname.startsWith(href + '/')
  }

  const handleLogout = () => {
    console.log('登出')
    window.location.href = '/auth/login'
  }

  return (
    <header className="bg-white shadow-sm border-b border-secondary-200">
      <div className="max-w-full px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* 左侧：Logo */}
          <div className="flex items-center">
            <Link href="/dashboard" className="flex items-center group">
              <div className="text-2xl font-bold text-primary-600 group-hover:scale-110 transition-transform duration-200">🚀</div>
              <span className="ml-3 text-lg font-semibold text-secondary-900 hidden xl:block">
                AI项目管理
              </span>
            </Link>
          </div>

          {/* 中间：主导航区域 - 根据showTitle决定是否显示 */}
          {showTitle && (
            <div className="flex-1 flex justify-center px-8">
              <nav className="hidden md:flex items-center space-x-1 bg-gray-50 rounded-lg p-1">
                {navigation.map((item) => (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={cn(
                      'flex items-center px-4 py-2 rounded-md text-sm font-medium transition-all duration-200',
                      'hover:bg-white hover:shadow-sm hover:text-secondary-900',
                      'focus:outline-none focus:ring-2 focus:ring-primary-500',
                      isActiveLink(item.href)
                        ? 'bg-white text-primary-700 shadow-sm border border-primary-200'
                        : 'text-secondary-600'
                    )}
                  >
                    <item.icon className={cn(
                      'h-4 w-4 mr-2',
                      isActiveLink(item.href) ? 'text-primary-500' : 'text-secondary-400'
                    )} />
                    <span className="hidden lg:inline">{item.name}</span>
                  </Link>
                ))}
              </nav>
            </div>
          )}

          {/* 右侧：用户信息和操作 */}
          <div className="flex items-center space-x-3">
            {user ? (
              <>
                {/* 调试按钮 */}
                {isClient && (process.env.NODE_ENV === 'development' || showDebugInfo) && (
                  <button
                    onClick={() => setShowDebugInfo(!showDebugInfo)}
                    className="p-2 rounded-lg hover:bg-gray-100 transition-colors group"
                    title={showDebugInfo ? '隐藏调试信息' : '显示调试信息'}
                  >
                    {showDebugInfo ? (
                      <EyeSlashIcon className="h-4 w-4 text-gray-500 group-hover:text-gray-700" />
                    ) : (
                      <EyeIcon className="h-4 w-4 text-gray-500 group-hover:text-gray-700" />
                    )}
                  </button>
                )}

                {/* 用户信息 */}
                <div className="flex items-center space-x-3 pl-3 border-l border-gray-200">
                  <div className="text-right hidden sm:block">
                    <div className="text-sm font-medium text-gray-900">
                      {user.username || '用户'}
                    </div>
                    {user.is_superuser && (
                      <div className="text-xs text-purple-600 font-medium">
                        🔧 系统管理员
                      </div>
                    )}
                  </div>
                  <div className="relative">
                    <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center ring-2 ring-white shadow-sm hover:shadow-md transition-shadow duration-200">
                      <span className="text-white text-sm font-bold">
                        {user.username?.charAt(0)?.toUpperCase() || 'U'}
                      </span>
                    </div>
                    {/* 在线状态指示器 */}
                    <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-500 border-2 border-white rounded-full"></div>
                  </div>
                </div>

                {/* 移动端菜单按钮 */}
                <button
                  type="button"
                  className="p-2 rounded-lg text-secondary-400 hover:text-secondary-600 hover:bg-secondary-100 focus:outline-none focus:ring-2 focus:ring-primary-500 md:hidden"
                  onClick={onMenuClick}
                >
                  <span className="sr-only">打开菜单</span>
                  <Bars3Icon className="h-6 w-6" aria-hidden="true" />
                </button>
              </>
            ) : (
              /* 未登录状态显示登录按钮 */
              <div className="flex items-center space-x-3">
                <Link
                  href="/auth/login"
                  className="px-4 py-2 text-sm font-medium text-primary-600 hover:text-primary-700 transition-colors"
                >
                  登录
                </Link>
                <button
                  type="button"
                  className="p-2 rounded-lg text-secondary-400 hover:text-secondary-600 hover:bg-secondary-100 focus:outline-none focus:ring-2 focus:ring-primary-500 md:hidden"
                  onClick={onMenuClick}
                >
                  <span className="sr-only">打开菜单</span>
                  <Bars3Icon className="h-6 w-6" aria-hidden="true" />
                </button>
              </div>
            )}
          </div>
        </div>

        {/* 调试信息面板 */}
        {isClient && showDebugInfo && user && (
          <div className="border-t border-gray-200 bg-gradient-to-r from-gray-50 to-gray-100 px-4 py-3">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div className="flex items-center space-x-8 text-xs">
                {/* Zustand 状态 */}
                <div className="flex items-center space-x-3">
                  <span className="font-semibold text-gray-700 flex items-center">
                    <span className="mr-1">🏪</span> 状态:
                  </span>
                  <div className="flex space-x-2">
                    <span className={`px-2 py-1 rounded-full font-medium ${isAuthenticated ? 'bg-green-100 text-green-800 border border-green-200' : 'bg-red-100 text-red-800 border border-red-200'}`}>
                      {isAuthenticated ? '✅ 已认证' : '❌ 未认证'}
                    </span>
                    <span className={`px-2 py-1 rounded-full font-medium ${isLoading ? 'bg-yellow-100 text-yellow-800 border border-yellow-200' : 'bg-gray-100 text-gray-800 border border-gray-200'}`}>
                      {isLoading ? '⏳ 加载中' : '✅ 就绪'}
                    </span>
                  </div>
                </div>

                {/* Token 状态 */}
                <div className="flex items-center space-x-3">
                  <span className="font-semibold text-gray-700 flex items-center">
                    <span className="mr-1">🔑</span> Token:
                  </span>
                  <div className="flex space-x-2">
                    <span className={`px-2 py-1 rounded-full font-medium ${authToken ? 'bg-green-100 text-green-800 border border-green-200' : 'bg-red-100 text-red-800 border border-red-200'}`}>
                      Auth: {authToken ? '✅' : '❌'}
                    </span>
                    <span className={`px-2 py-1 rounded-full font-medium ${refreshToken ? 'bg-green-100 text-green-800 border border-green-200' : 'bg-red-100 text-red-800 border border-red-200'}`}>
                      Refresh: {refreshToken ? '✅' : '❌'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-3 text-xs text-gray-600">
                <div className="flex items-center space-x-1">
                  <ClockIcon className="w-3 h-3" />
                  <span className="font-medium">{isClient ? currentTime : ''}</span>
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={() => {
                      console.log('🔄 手动触发状态检查')
                      console.log('用户状态:', { user, isAuthenticated, isLoading })
                    }}
                    className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full hover:bg-blue-200 font-medium transition-colors"
                  >
                    检查状态
                  </button>
                  <button
                    onClick={() => {
                      console.log('🧹 清除所有认证数据')
                      localStorage.removeItem('auth-token')
                      localStorage.removeItem('refresh-token')
                      localStorage.removeItem('user-storage')
                      window.location.reload()
                    }}
                    className="px-3 py-1 bg-red-100 text-red-800 rounded-full hover:bg-red-200 font-medium transition-colors"
                  >
                    清除数据
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </header>
  )
}

export default Header 