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
  ChartBarIcon
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'

// 统计卡片数据
const stats = [
  {
    name: '活跃项目',
    value: '12',
    change: '+2',
    changeType: 'increase',
    icon: FolderIcon,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50'
  },
  {
    name: '文件总数',
    value: '1,234',
    change: '+89',
    changeType: 'increase',
    icon: DocumentTextIcon,
    color: 'text-green-600',
    bgColor: 'bg-green-50'
  },
  {
    name: 'AI对话',
    value: '456',
    change: '+23',
    changeType: 'increase',
    icon: ChatBubbleLeftRightIcon,
    color: 'text-purple-600',
    bgColor: 'bg-purple-50'
  },
  {
    name: '团队成员',
    value: '8',
    change: '+1',
    changeType: 'increase',
    icon: UserGroupIcon,
    color: 'text-orange-600',
    bgColor: 'bg-orange-50'
  }
]

export default function DashboardPage() {
  const [isLoaded, setIsLoaded] = useState(false)

  useEffect(() => {
    setIsLoaded(true)
  }, [])

  return (
    <div className={cn('space-y-6 transition-opacity duration-1000', isLoaded ? 'opacity-100' : 'opacity-0')}>
      {/* 页面标题 */}
      <div>
        <h1 className="text-2xl font-bold text-secondary-900">概览</h1>
        <p className="mt-1 text-sm text-secondary-600">
          欢迎回来！这里是您的项目管理概览。
        </p>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((item, index) => (
          <div 
            key={item.name}
            className="card hover:shadow-md transition-all duration-300 animate-scale-in"
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

      {/* 快速操作 */}
      <div className="card">
        <h2 className="text-lg font-medium text-secondary-900 mb-4">快速操作</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <a
            href="/dashboard/projects"
            className="flex items-center p-4 bg-primary-50 rounded-lg hover:bg-primary-100 transition-colors group"
          >
            <FolderIcon className="h-8 w-8 text-primary-600 group-hover:text-primary-700" />
            <div className="ml-3">
              <p className="text-sm font-medium text-primary-900">创建项目</p>
              <p className="text-xs text-primary-600">开始新的项目</p>
            </div>
          </a>
          
          <a
            href="/dashboard/analytics"
            className="flex items-center p-4 bg-green-50 rounded-lg hover:bg-green-100 transition-colors group"
          >
            <ChartBarIcon className="h-8 w-8 text-green-600 group-hover:text-green-700" />
            <div className="ml-3">
              <p className="text-sm font-medium text-green-900">项目分析</p>
              <p className="text-xs text-green-600">数据统计分析</p>
            </div>
          </a>
          
          <a
            href="/dashboard/chat"
            className="flex items-center p-4 bg-purple-50 rounded-lg hover:bg-purple-100 transition-colors group"
          >
            <ChatBubbleLeftRightIcon className="h-8 w-8 text-purple-600 group-hover:text-purple-700" />
            <div className="ml-3">
              <p className="text-sm font-medium text-purple-900">AI问答</p>
              <p className="text-xs text-purple-600">智能助手对话</p>
            </div>
          </a>
          
          <a
            href="/dashboard/team"
            className="flex items-center p-4 bg-orange-50 rounded-lg hover:bg-orange-100 transition-colors group"
          >
            <UserGroupIcon className="h-8 w-8 text-orange-600 group-hover:text-orange-700" />
            <div className="ml-3">
              <p className="text-sm font-medium text-orange-900">团队协作</p>
              <p className="text-xs text-orange-600">管理团队成员</p>
            </div>
          </a>
        </div>
      </div>

      {/* 功能介绍 */}
      <div className="card">
        <h2 className="text-lg font-medium text-secondary-900 mb-4">系统功能</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div className="flex items-start space-x-3">
              <CheckCircleIcon className="h-6 w-6 text-green-500 mt-1" />
              <div>
                <h3 className="text-sm font-medium text-secondary-900">项目阶段管理</h3>
                <p className="text-sm text-secondary-600">按售前、调研、开发、部署等阶段组织项目</p>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <CheckCircleIcon className="h-6 w-6 text-green-500 mt-1" />
              <div>
                <h3 className="text-sm font-medium text-secondary-900">多模态文件支持</h3>
                <p className="text-sm text-secondary-600">支持PDF、Word、图片、视频等多种格式</p>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <CheckCircleIcon className="h-6 w-6 text-green-500 mt-1" />
              <div>
                <h3 className="text-sm font-medium text-secondary-900">智能问答系统</h3>
                <p className="text-sm text-secondary-600">基于项目内容的AI智能问答</p>
              </div>
            </div>
          </div>
          <div className="space-y-4">
            <div className="flex items-start space-x-3">
              <CheckCircleIcon className="h-6 w-6 text-green-500 mt-1" />
              <div>
                <h3 className="text-sm font-medium text-secondary-900">团队协作</h3>
                <p className="text-sm text-secondary-600">多用户协作，权限管理，实时同步</p>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <CheckCircleIcon className="h-6 w-6 text-green-500 mt-1" />
              <div>
                <h3 className="text-sm font-medium text-secondary-900">知识沉淀</h3>
                <p className="text-sm text-secondary-600">优质问答自动保存为项目知识库</p>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <CheckCircleIcon className="h-6 w-6 text-green-500 mt-1" />
              <div>
                <h3 className="text-sm font-medium text-secondary-900">数据分析</h3>
                <p className="text-sm text-secondary-600">项目进度统计，使用数据分析</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
} 