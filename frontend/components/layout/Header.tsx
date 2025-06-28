'use client'

import { useState } from 'react'
import Link from 'next/link'
import { 
  Bars3Icon, 
  BellIcon, 
  UserCircleIcon,
  MagnifyingGlassIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon
} from '@heroicons/react/24/outline'
import { Menu, Transition } from '@headlessui/react'
import { Fragment } from 'react'
import { cn } from '@/lib/utils'

interface HeaderProps {
  onMenuClick: () => void
  user?: {
    name: string
    email: string
    avatar?: string
  }
}

const Header: React.FC<HeaderProps> = ({ onMenuClick, user }) => {
  const [searchQuery, setSearchQuery] = useState('')

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    // TODO: 实现搜索功能
    console.log('搜索:', searchQuery)
  }

  const handleLogout = () => {
    // TODO: 实现登出功能
    console.log('登出')
    window.location.href = '/auth/login'
  }

  return (
    <header className="bg-white shadow-sm border-b border-secondary-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* 左侧：菜单按钮和Logo */}
          <div className="flex items-center">
            <button
              type="button"
              className="p-2 rounded-md text-secondary-400 hover:text-secondary-600 hover:bg-secondary-100 focus:outline-none focus:ring-2 focus:ring-primary-500 lg:hidden"
              onClick={onMenuClick}
            >
              <span className="sr-only">打开菜单</span>
              <Bars3Icon className="h-6 w-6" aria-hidden="true" />
            </button>
            
            <Link href="/dashboard" className="flex items-center ml-4 lg:ml-0">
              <div className="text-2xl font-bold text-primary-600">🚀</div>
              <span className="ml-2 text-xl font-semibold text-secondary-900 hidden sm:block">
                AI项目管理
              </span>
            </Link>
          </div>

          {/* 中间：搜索框 */}
          <div className="flex-1 max-w-lg mx-8 hidden md:block">
            <form onSubmit={handleSearch} className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <MagnifyingGlassIcon className="h-5 w-5 text-secondary-400" aria-hidden="true" />
              </div>
              <input
                type="search"
                placeholder="搜索项目、文件、对话..."
                className="block w-full pl-10 pr-3 py-2 border border-secondary-300 rounded-lg leading-5 bg-white placeholder-secondary-500 focus:outline-none focus:placeholder-secondary-400 focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </form>
          </div>

          {/* 右侧：通知和用户菜单 */}
          <div className="flex items-center space-x-4">
            {/* 通知按钮 */}
            <button
              type="button"
              className="p-2 rounded-md text-secondary-400 hover:text-secondary-600 hover:bg-secondary-100 focus:outline-none focus:ring-2 focus:ring-primary-500 relative"
            >
              <span className="sr-only">查看通知</span>
              <BellIcon className="h-6 w-6" aria-hidden="true" />
              {/* 通知小红点 */}
              <span className="absolute top-1 right-1 block h-2 w-2 rounded-full bg-red-400 ring-2 ring-white"></span>
            </button>

            {/* 用户菜单 */}
            <Menu as="div" className="relative">
              <div>
                <Menu.Button className="flex items-center text-sm rounded-full focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2">
                  <span className="sr-only">打开用户菜单</span>
                  {user?.avatar ? (
                    <img
                      className="h-8 w-8 rounded-full"
                      src={user.avatar}
                      alt={user.name}
                    />
                  ) : (
                    <UserCircleIcon className="h-8 w-8 text-secondary-400" />
                  )}
                  <span className="ml-2 text-sm font-medium text-secondary-700 hidden lg:block">
                    {user?.name || '用户'}
                  </span>
                </Menu.Button>
              </div>
              
              <Transition
                as={Fragment}
                enter="transition ease-out duration-100"
                enterFrom="transform opacity-0 scale-95"
                enterTo="transform opacity-100 scale-100"
                leave="transition ease-in duration-75"
                leaveFrom="transform opacity-100 scale-100"
                leaveTo="transform opacity-0 scale-95"
              >
                <Menu.Panel className="absolute right-0 z-10 mt-2 w-56 origin-top-right bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
                  <div className="py-1">
                    {/* 用户信息 */}
                    <div className="px-4 py-3 border-b border-secondary-100">
                      <p className="text-sm font-medium text-secondary-900">
                        {user?.name || '用户'}
                      </p>
                      <p className="text-sm text-secondary-500">
                        {user?.email || 'user@example.com'}
                      </p>
                    </div>
                    
                    {/* 菜单项 */}
                    <Menu.Item>
                      {({ active }) => (
                        <Link
                          href="/profile"
                          className={cn(
                            'flex items-center px-4 py-2 text-sm',
                            active ? 'bg-secondary-100 text-secondary-900' : 'text-secondary-700'
                          )}
                        >
                          <UserCircleIcon className="mr-3 h-5 w-5" aria-hidden="true" />
                          个人资料
                        </Link>
                      )}
                    </Menu.Item>
                    
                    <Menu.Item>
                      {({ active }) => (
                        <Link
                          href="/settings"
                          className={cn(
                            'flex items-center px-4 py-2 text-sm',
                            active ? 'bg-secondary-100 text-secondary-900' : 'text-secondary-700'
                          )}
                        >
                          <Cog6ToothIcon className="mr-3 h-5 w-5" aria-hidden="true" />
                          系统设置
                        </Link>
                      )}
                    </Menu.Item>
                    
                    <div className="border-t border-secondary-100"></div>
                    
                    <Menu.Item>
                      {({ active }) => (
                        <button
                          onClick={handleLogout}
                          className={cn(
                            'flex w-full items-center px-4 py-2 text-sm text-left',
                            active ? 'bg-secondary-100 text-secondary-900' : 'text-secondary-700'
                          )}
                        >
                          <ArrowRightOnRectangleIcon className="mr-3 h-5 w-5" aria-hidden="true" />
                          退出登录
                        </button>
                      )}
                    </Menu.Item>
                  </div>
                </Menu.Panel>
              </Transition>
            </Menu>
          </div>
        </div>
      </div>
    </header>
  )
}

export default Header 