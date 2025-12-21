'use client'

import { useState, useEffect } from 'react'
import {
  FolderIcon,
  DocumentTextIcon,
  ChatBubbleLeftRightIcon,
  UserGroupIcon,
  ArrowTrendingUpIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ChartBarIcon,
  PlusIcon
} from '@heroicons/react/24/outline'
import { cn, formatFileSize } from '@/lib/utils'
import { projectSync } from '@/lib/services/project-sync'
import { useUserStore } from '@/lib/stores/userStore'

interface Project {
  id: string
  name: string
  description: string
  stage: string
  createdAt: string
  updatedAt: string
  memberCount: number
  fileCount: number
  totalSize: number
  status: 'active' | 'archived' | 'completed'
  color: string
}

interface DashboardStats {
  activeProjects: number
  totalFiles: number
  totalSize: number
  totalMembers: number
  aiChats: number
}

// 获取全局文件统计（添加错误处理和超时）
const fetchGlobalFileStats = async (): Promise<{ totalFiles: number; totalSize: number }> => {
  try {
    const { apiGet } = await import('@/lib/api');

    // 添加5秒超时
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 5000)

    const response = await apiGet('/api/v1/files/stats/summary', {
      signal: controller.signal
    })

    clearTimeout(timeoutId)

    if (response.ok) {
      const stats = await response.json()
      return {
        totalFiles: stats.data?.total_files || 0,
        totalSize: stats.data?.total_size || 0
      }
    } else {
      console.warn('获取文件统计失败，HTTP状态:', response.status)
    }
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      console.warn('获取文件统计超时，使用默认值')
    } else {
      console.error('获取文件统计失败:', error)
    }
  }
  return { totalFiles: 0, totalSize: 0 }
}

// 获取AI对话统计（添加错误处理和超时）
const fetchChatStats = async (): Promise<{ aiChats: number }> => {
  try {
    const { apiGet } = await import('@/lib/api');

    // 添加5秒超时
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 5000)

    const response = await apiGet('/api/v1/chat/stats', {
      signal: controller.signal
    })

    clearTimeout(timeoutId)

    if (response.ok) {
      const stats = await response.json()
      console.log('AI对话统计数据:', stats)
      return {
        aiChats: stats.data?.total_conversations || 0
      }
    } else {
      console.warn('获取AI对话统计失败，HTTP状态:', response.status)
    }
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      console.warn('获取AI对话统计超时，使用默认值')
    } else {
      console.error('获取AI对话统计失败:', error)
    }
  }
  return { aiChats: 0 }
}

export default function DashboardPage() {
  const { user } = useUserStore()
  const [isLoaded, setIsLoaded] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [hasError, setHasError] = useState(false)
  const [retryCount, setRetryCount] = useState(0)
  const [stats, setStats] = useState<DashboardStats>({
    activeProjects: 0,
    totalFiles: 0,
    totalSize: 0,
    totalMembers: 0,
    aiChats: 0
  })

  // 判断是否为管理员
  const isAdmin = user?.is_superuser || false

  // 手动重试函数
  const handleRetry = () => {
    setRetryCount(prev => prev + 1)
    setHasError(false)
    setIsLoaded(false)
  }

  useEffect(() => {
    let isMounted = true
    let isRequesting = false

    const loadDashboardData = async () => {
      // 防止重复请求
      if (isRequesting) {
        console.log('⏳ Dashboard数据正在加载中，跳过重复请求')
        return
      }

      isRequesting = true
      setIsLoading(true)

      try {
        // 使用同步服务获取项目统计（同步操作，不需要等待）
        const globalStats = projectSync.getGlobalStats()

        // 添加超时控制的并行API请求
        const timeoutPromise = new Promise((_, reject) => {
          setTimeout(() => reject(new Error('Dashboard数据加载超时')), 8000)
        })

        const apiPromise = Promise.all([
          fetchGlobalFileStats(),
          fetchChatStats()
        ])

        // 使用Promise.race实现超时控制
        const [fileStats, chatStats] = await Promise.race([apiPromise, timeoutPromise]) as [
          { totalFiles: number; totalSize: number },
          { aiChats: number }
        ]

        // 只在组件仍然挂载时更新状态
        if (isMounted) {
          setStats({
            activeProjects: globalStats.activeProjects,
            totalFiles: fileStats.totalFiles,
            totalSize: fileStats.totalSize,
            totalMembers: globalStats.totalMembers,
            aiChats: chatStats.aiChats
          })

          setIsLoaded(true)
          setHasError(false)
        }
      } catch (error) {
        console.error('❌ 加载Dashboard数据失败:', error)
        if (isMounted) {
          setHasError(true)
          setIsLoaded(true) // 即使出错也要显示页面
        }
      } finally {
        isRequesting = false
        if (isMounted) {
          setIsLoading(false)
        }
      }
    }

    loadDashboardData()

    // 订阅项目数据变化，实时更新统计（延迟执行，避免立即触发）
    const unsubscribe = projectSync.subscribe(() => {
      // 使用 setTimeout 避免立即触发，给组件时间完成初始加载
      setTimeout(() => {
        if (isMounted && !isRequesting) {
          loadDashboardData()
        }
      }, 100)
    })

    return () => {
      isMounted = false
      unsubscribe()
    }
  }, [])

  // 根据用户权限显示不同的统计卡片
  const statsCards = [
    {
      name: isAdmin ? '活跃项目' : '我的项目',
      value: stats.activeProjects.toString(),
      change: '+0', // TODO: 计算变化
      changeType: 'increase',
      icon: FolderIcon,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50'
    },
    {
      name: isAdmin ? '文件总数' : '我的文件',
      value: stats.totalFiles.toString(),
      change: '+0', // TODO: 计算变化
      changeType: 'increase',
      icon: DocumentTextIcon,
      color: 'text-green-600',
      bgColor: 'bg-green-50'
    },
    {
      name: 'AI对话',
      value: stats.aiChats.toString(),
      change: '+0', // TODO: 计算变化
      changeType: 'increase',
      icon: ChatBubbleLeftRightIcon,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50'
    }
  ]

  // 管理员可以看到额外的统计信息
  if (isAdmin) {
    statsCards.push({
      name: '团队成员',
      value: stats.totalMembers.toString(),
      change: '+0', // TODO: 计算变化
      changeType: 'increase',
      icon: UserGroupIcon,
      color: 'text-orange-600',
      bgColor: 'bg-orange-50'
    })
  } else {
    statsCards.push({
      name: '存储空间',
      value: formatFileSize(stats.totalSize),
      change: '+0', // TODO: 计算变化
      changeType: 'increase',
      icon: ArrowTrendingUpIcon,
      color: 'text-orange-600',
      bgColor: 'bg-orange-50'
    })
  }

  return (
    <div className={cn(
      'bg-gray-50 min-h-full transition-opacity duration-1000',
      isLoaded ? 'opacity-100' : 'opacity-0'
    )}>
      {/* 页面标题区域 - 简化版，因为Header已在Layout中 */}
      <div className="px-6 py-6 border-b border-gray-200 bg-white">
        <div>
          <h1 className="text-3xl font-bold text-secondary-900">
            {isAdmin ? '系统概览' : '我的工作台'}
          </h1>
          <p className="mt-2 text-lg text-secondary-600">
            {isAdmin
              ? '欢迎回来，管理员！这里是系统管理概览。'
              : `欢迎回来，${user?.username || '用户'}！这里是您的工作概览。`
            }
          </p>
          </div>
      </div>

      {/* 内容区域 */}
      <div className="px-6 py-8 max-w-7xl mx-auto">
        {/* 统计卡片 */}
        <div className="mb-8">
          <h2 className="text-lg font-medium text-secondary-900 mb-6">数据概览</h2>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {statsCards.map((item, index) => (
              <div
                key={item.name}
                className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-all duration-300 animate-scale-in"
                style={{ animationDelay: `${index * 100}ms` }}
              >
                <div className="flex items-center">
                  <div className={cn('p-3 rounded-lg', item.bgColor)}>
                    <item.icon className={cn('h-6 w-6', item.color)} aria-hidden="true" />
                  </div>
                  <div className="ml-4 flex-1">
                    <p className="text-sm font-medium text-secondary-600">{item.name}</p>
                    <div className="flex items-baseline">
                      <p className="text-2xl font-semibold text-secondary-900">{item.value}</p>
                      <p className={cn(
                        'ml-2 text-sm font-medium',
                        item.changeType === 'increase' ? 'text-green-600' : 'text-red-600'
                      )}>
                        {item.change}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 快速操作 */}
        <div className="mb-8">
          <h2 className="text-lg font-medium text-secondary-900 mb-6">
            {isAdmin ? '系统管理' : '我的工作'}
          </h2>
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <a
                href="/dashboard/projects"
                className="flex items-center p-5 bg-primary-50 rounded-xl hover:bg-primary-100 transition-colors group border border-primary-100"
              >
                <FolderIcon className="h-8 w-8 text-primary-600 group-hover:text-primary-700" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-primary-900">
                    {isAdmin ? '项目管理' : '我的项目'}
                  </p>
                  <p className="text-xs text-primary-600 mt-1">
                    {isAdmin ? '管理系统项目' : '查看和管理项目'}
                  </p>
                </div>
              </a>

              <a
                href="/dashboard/files"
                className="flex items-center p-5 bg-green-50 rounded-xl hover:bg-green-100 transition-colors group border border-green-100"
              >
                <DocumentTextIcon className="h-8 w-8 text-green-600 group-hover:text-green-700" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-green-900">
                    {isAdmin ? '文件管理' : '我的文件'}
                  </p>
                  <p className="text-xs text-green-600 mt-1">
                    {isAdmin ? '管理系统文件' : '上传和管理文件'}
                  </p>
                </div>
              </a>

              <a
                href="/dashboard/chat"
                className="flex items-center p-5 bg-purple-50 rounded-xl hover:bg-purple-100 transition-colors group border border-purple-100"
              >
                <ChatBubbleLeftRightIcon className="h-8 w-8 text-purple-600 group-hover:text-purple-700" />
                <div className="ml-4">
                  <p className="text-sm font-medium text-purple-900">AI问答</p>
                  <p className="text-xs text-purple-600 mt-1">智能助手对话</p>
                </div>
              </a>

              {isAdmin ? (
                <a
                  href="/dashboard/team"
                  className="flex items-center p-5 bg-orange-50 rounded-xl hover:bg-orange-100 transition-colors group border border-orange-100"
                >
                  <UserGroupIcon className="h-8 w-8 text-orange-600 group-hover:text-orange-700" />
                  <div className="ml-4">
                    <p className="text-sm font-medium text-orange-900">团队管理</p>
                    <p className="text-xs text-orange-600 mt-1">管理团队成员</p>
                  </div>
                </a>
              ) : (
                <a
                  href="/dashboard/projects"
                  className="flex items-center p-5 bg-orange-50 rounded-xl hover:bg-orange-100 transition-colors group border border-orange-100"
                >
                  <PlusIcon className="h-8 w-8 text-orange-600 group-hover:text-orange-700" />
                  <div className="ml-4">
                    <p className="text-sm font-medium text-orange-900">创建项目</p>
                    <p className="text-xs text-orange-600 mt-1">开始新的项目</p>
                  </div>
                </a>
              )}
            </div>
          </div>
        </div>

        {/* 功能介绍 */}
        <div className="mb-8">
          <h2 className="text-lg font-medium text-secondary-900 mb-6">系统功能</h2>
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="space-y-6">
                <div className="flex items-start space-x-4">
                  <CheckCircleIcon className="h-6 w-6 text-green-500 mt-1 flex-shrink-0" />
                  <div>
                    <h3 className="text-base font-medium text-secondary-900 mb-2">项目阶段管理</h3>
                    <p className="text-sm text-secondary-600">按售前、调研、开发、部署等阶段组织项目</p>
                  </div>
                </div>
                <div className="flex items-start space-x-4">
                  <CheckCircleIcon className="h-6 w-6 text-green-500 mt-1 flex-shrink-0" />
                  <div>
                    <h3 className="text-base font-medium text-secondary-900 mb-2">多模态文件支持</h3>
                    <p className="text-sm text-secondary-600">支持PDF、Word、图片、视频等多种格式</p>
                  </div>
                </div>
                <div className="flex items-start space-x-4">
                  <CheckCircleIcon className="h-6 w-6 text-green-500 mt-1 flex-shrink-0" />
                  <div>
                    <h3 className="text-base font-medium text-secondary-900 mb-2">智能问答系统</h3>
                    <p className="text-sm text-secondary-600">基于项目内容的AI智能问答</p>
                  </div>
                </div>
              </div>
              <div className="space-y-6">
                <div className="flex items-start space-x-4">
                  <CheckCircleIcon className="h-6 w-6 text-green-500 mt-1 flex-shrink-0" />
                  <div>
                    <h3 className="text-base font-medium text-secondary-900 mb-2">团队协作</h3>
                    <p className="text-sm text-secondary-600">多用户协作，权限管理，实时同步</p>
                  </div>
                </div>
                <div className="flex items-start space-x-4">
                  <CheckCircleIcon className="h-6 w-6 text-green-500 mt-1 flex-shrink-0" />
                  <div>
                    <h3 className="text-base font-medium text-secondary-900 mb-2">知识沉淀</h3>
                    <p className="text-sm text-secondary-600">优质问答自动保存为项目知识库</p>
                  </div>
                </div>
                <div className="flex items-start space-x-4">
                  <CheckCircleIcon className="h-6 w-6 text-green-500 mt-1 flex-shrink-0" />
                  <div>
                    <h3 className="text-base font-medium text-secondary-900 mb-2">智能文档</h3>
                    <p className="text-sm text-secondary-600">项目进度统计，使用智能文档</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}