'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  HomeIcon,
  FolderIcon,
  DocumentTextIcon,
  ChatBubbleLeftRightIcon,
  BookOpenIcon,
  ChartBarIcon,
  UsersIcon,
  Cog6ToothIcon,
  ChevronDownIcon,
  ChevronRightIcon
} from '@heroicons/react/24/outline'
import { cn } from '@/lib/utils'
import { useUserStore } from '@/lib/stores/userStore'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
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
    icon: FolderIcon,
    current: false,
    children: [
      { name: '我的项目', href: '/dashboard/projects' },
      { name: '项目模板', href: '/dashboard/templates' },
      { name: '项目统计', href: '/dashboard/analytics' }
    ]
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

const bottomNavigation = [
  {
    name: '系统设置',
    href: '/dashboard/settings',
    icon: Cog6ToothIcon
  }
]

const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const { user } = useUserStore()
  const pathname = usePathname()
  const [expandedItems, setExpandedItems] = useState<string[]>(['项目管理', '团队管理'])

  const toggleExpanded = (itemName: string) => {
    setExpandedItems(prev => 
      prev.includes(itemName)
        ? prev.filter(name => name !== itemName)
        : [...prev, itemName]
    )
  }

  const isActiveLink = (href: string) => {
    return pathname === href || pathname.startsWith(href + '/')
  }

  const NavigationItem = ({ item, level = 0 }: { item: any; level?: number }) => {
    const hasChildren = item.children && item.children.length > 0
    const isExpanded = expandedItems.includes(item.name)
    const isActive = item.href ? isActiveLink(item.href) : false

    if (hasChildren) {
      return (
        <div>
          <button
            onClick={() => toggleExpanded(item.name)}
            className={cn(
              'group flex w-full items-center rounded-md py-2 px-3 text-sm font-medium transition-colors duration-200',
              'hover:bg-secondary-100 hover:text-secondary-900',
              'focus:outline-none focus:ring-2 focus:ring-primary-500',
              level > 0 && 'ml-4',
              isActive ? 'bg-primary-50 text-primary-700' : 'text-secondary-600'
            )}
          >
            <item.icon
              className={cn(
                'mr-3 h-5 w-5 flex-shrink-0',
                isActive ? 'text-primary-500' : 'text-secondary-400 group-hover:text-secondary-500'
              )}
              aria-hidden="true"
            />
            <span className="flex-1 text-left">{item.name}</span>
            {isExpanded ? (
              <ChevronDownIcon className="ml-2 h-4 w-4" />
            ) : (
              <ChevronRightIcon className="ml-2 h-4 w-4" />
            )}
          </button>
          
          {isExpanded && (
            <div className="mt-1 space-y-1">
              {item.children.map((child: any) => (
                <NavigationItem key={child.name} item={child} level={level + 1} />
              ))}
            </div>
          )}
        </div>
      )
    }

    return (
      <Link
        href={item.href}
        onClick={onClose}
        className={cn(
          'group flex items-center rounded-md py-2 px-3 text-sm font-medium transition-colors duration-200',
          'hover:bg-secondary-100 hover:text-secondary-900',
          'focus:outline-none focus:ring-2 focus:ring-primary-500',
          level > 0 && 'ml-8',
          isActive 
            ? 'bg-primary-50 text-primary-700 border-r-2 border-primary-500' 
            : 'text-secondary-600'
        )}
      >
        {item.icon && (
          <item.icon
            className={cn(
              'mr-3 h-5 w-5 flex-shrink-0',
              isActive ? 'text-primary-500' : 'text-secondary-400 group-hover:text-secondary-500'
            )}
            aria-hidden="true"
          />
        )}
        {item.name}
      </Link>
    )
  }

  return (
    <>
      {/* 移动端遮罩 */}
      {isOpen && (
        <div 
          className="fixed inset-0 z-20 bg-black bg-opacity-50 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* 侧边栏 */}
      <div
        className={cn(
          'fixed inset-y-0 left-0 z-30 w-64 bg-white shadow-lg transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex flex-col h-full">
          {/* Logo区域 */}
          <div className="flex items-center h-16 px-4 border-b border-secondary-200">
            <Link href="/dashboard" className="flex items-center" onClick={onClose}>
              <div className="text-2xl font-bold text-primary-600">🚀</div>
              <span className="ml-2 text-lg font-semibold text-secondary-900">
                AI项目管理
              </span>
            </Link>
          </div>

          {/* 当前用户状态 */}
          {user && (
            <div className={`px-4 py-3 border-b border-secondary-200 ${
              user.is_superuser 
                ? 'bg-gradient-to-r from-purple-50 to-blue-50' 
                : 'bg-gradient-to-r from-gray-50 to-blue-50'
            }`}>
              <div className="flex items-center space-x-2">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  user.is_superuser ? 'bg-purple-600' : 'bg-blue-600'
                }`}>
                  <span className="text-white text-sm font-bold">
                    {user.is_superuser ? '👑' : '👤'}
                  </span>
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-900">
                    {user.username}
                  </div>
                  <div className="text-xs text-gray-600">
                    {user.is_superuser ? '🔧 系统管理员' : '📁 团队成员'}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 导航菜单 */}
          <nav className="flex-1 px-4 py-4 space-y-1 overflow-y-auto">
            {navigation.map((item) => (
              <NavigationItem key={item.name} item={item} />
            ))}
          </nav>

          {/* 底部菜单 */}
          <div className="px-4 py-4 border-t border-secondary-200">
            {bottomNavigation.map((item) => (
              <NavigationItem key={item.name} item={item} />
            ))}
          </div>

          {/* 版本信息 */}
          <div className="px-4 py-2 text-xs text-secondary-500 border-t border-secondary-200">
            <p>版本 v0.1.0</p>
            <p>© 2024 AI项目管理系统</p>
          </div>
        </div>
      </div>
    </>
  )
}

export default Sidebar 