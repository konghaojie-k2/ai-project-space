'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { 
  Bars3Icon, 
  XMarkIcon,
  UserCircleIcon,
  ArrowRightOnRectangleIcon,
  Cog6ToothIcon
} from '@heroicons/react/24/outline'
import { useUserStore } from '@/lib/stores/userStore'

export default function MainNavbar() {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false)
  const { user, isAuthenticated, logout } = useUserStore()
  const router = useRouter()

  const handleLogout = () => {
    logout()
    setIsUserMenuOpen(false)
    router.push('/')
  }

  const handleLogin = () => {
    router.push('/login')
  }

  const handleRegister = () => {
    router.push('/register')
  }

  // 点击外部关闭用户菜单
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Element
      if (!target.closest('.user-menu-container')) {
        setIsUserMenuOpen(false)
      }
    }

    if (isUserMenuOpen) {
      document.addEventListener('click', handleClickOutside)
      return () => document.removeEventListener('click', handleClickOutside)
    }
  }, [isUserMenuOpen])

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex items-center">
            <Link href="/" className="flex items-center">
              <span className="text-2xl font-bold text-primary-600">
                🚀 AI项目管理
              </span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-8">
            <Link 
              href="/features" 
              className="text-gray-600 hover:text-primary-600 transition-colors"
            >
              功能特性
            </Link>
            <Link 
              href="/pricing" 
              className="text-gray-600 hover:text-primary-600 transition-colors"
            >
              价格方案
            </Link>
            <Link 
              href="/demo" 
              className="text-gray-600 hover:text-primary-600 transition-colors"
            >
              产品演示
            </Link>
            <Link 
              href="/help" 
              className="text-gray-600 hover:text-primary-600 transition-colors"
            >
              帮助中心
            </Link>

            {/* 用户状态区域 */}
            {isAuthenticated ? (
              <div className="relative user-menu-container">
                <button
                  onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                  className="flex items-center space-x-2 text-gray-600 hover:text-primary-600 transition-colors"
                >
                  <UserCircleIcon className="w-6 h-6" />
                  <span className="text-sm font-medium">
                    {user?.username || user?.email || '用户'}
                  </span>
                </button>

                {/* 用户下拉菜单 */}
                {isUserMenuOpen && (
                  <div className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg border border-gray-200 py-1 z-10">
                    <Link
                      href="/dashboard"
                      className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                      onClick={() => setIsUserMenuOpen(false)}
                    >
                      <UserCircleIcon className="w-4 h-4 inline mr-2" />
                      控制面板
                    </Link>
                    <Link
                      href="/settings"
                      className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                      onClick={() => setIsUserMenuOpen(false)}
                    >
                      <Cog6ToothIcon className="w-4 h-4 inline mr-2" />
                      设置
                    </Link>
                    <hr className="my-1" />
                    <button
                      onClick={handleLogout}
                      className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors"
                    >
                      <ArrowRightOnRectangleIcon className="w-4 h-4 inline mr-2" />
                      退出登录
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center space-x-4">
                <button
                  onClick={handleLogin}
                  className="text-gray-600 hover:text-primary-600 transition-colors font-medium"
                >
                  登录
                </button>
                <button
                  onClick={handleRegister}
                  className="bg-primary-600 text-white px-4 py-2 rounded-md hover:bg-primary-700 transition-colors font-medium"
                >
                  免费注册
                </button>
              </div>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden">
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="text-gray-600 hover:text-primary-600 transition-colors"
            >
              {isMenuOpen ? (
                <XMarkIcon className="w-6 h-6" />
              ) : (
                <Bars3Icon className="w-6 h-6" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {isMenuOpen && (
          <div className="md:hidden border-t border-gray-200 py-4">
            <div className="space-y-4">
              <Link 
                href="/features" 
                className="block text-gray-600 hover:text-primary-600 transition-colors"
                onClick={() => setIsMenuOpen(false)}
              >
                功能特性
              </Link>
              <Link 
                href="/pricing" 
                className="block text-gray-600 hover:text-primary-600 transition-colors"
                onClick={() => setIsMenuOpen(false)}
              >
                价格方案
              </Link>
              <Link 
                href="/demo" 
                className="block text-gray-600 hover:text-primary-600 transition-colors"
                onClick={() => setIsMenuOpen(false)}
              >
                产品演示
              </Link>
              <Link 
                href="/help" 
                className="block text-gray-600 hover:text-primary-600 transition-colors"
                onClick={() => setIsMenuOpen(false)}
              >
                帮助中心
              </Link>

              {/* 移动端用户状态 */}
              <hr className="border-gray-200" />
              {isAuthenticated ? (
                <div className="space-y-2">
                  <div className="text-sm text-gray-500 font-medium">
                    欢迎，{user?.username || user?.email || '用户'}
                  </div>
                  <Link
                    href="/dashboard"
                    className="block text-gray-600 hover:text-primary-600 transition-colors"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    控制面板
                  </Link>
                  <Link
                    href="/settings"
                    className="block text-gray-600 hover:text-primary-600 transition-colors"
                    onClick={() => setIsMenuOpen(false)}
                  >
                    设置
                  </Link>
                  <button
                    onClick={() => {
                      handleLogout()
                      setIsMenuOpen(false)
                    }}
                    className="block w-full text-left text-gray-600 hover:text-primary-600 transition-colors"
                  >
                    退出登录
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  <button
                    onClick={() => {
                      handleLogin()
                      setIsMenuOpen(false)
                    }}
                    className="block w-full text-left text-gray-600 hover:text-primary-600 transition-colors font-medium"
                  >
                    登录
                  </button>
                  <button
                    onClick={() => {
                      handleRegister()
                      setIsMenuOpen(false)
                    }}
                    className="block w-full text-left bg-primary-600 text-white px-4 py-2 rounded-md hover:bg-primary-700 transition-colors font-medium"
                  >
                    免费注册
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </nav>
  )
} 