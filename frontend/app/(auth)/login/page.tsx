'use client'

import { useState } from 'react'
import Link from 'next/link'
import { EyeIcon, EyeSlashIcon, EnvelopeIcon, LockClosedIcon } from '@heroicons/react/24/outline'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'

export default function LoginPage() {
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  })
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
    // 清除对应字段的错误
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }))
    }
  }

  const validateForm = () => {
    const newErrors: Record<string, string> = {}
    
    if (!formData.email) {
      newErrors.email = '请输入邮箱地址'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = '邮箱格式不正确'
    }
    
    if (!formData.password) {
      newErrors.password = '请输入密码'
    } else if (formData.password.length < 6) {
      newErrors.password = '密码至少6位'
    }
    
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) return
    
    setIsLoading(true)
    
    try {
      // 模拟登录请求
      await new Promise(resolve => setTimeout(resolve, 2000))
      
      // TODO: 实际登录逻辑
      console.log('登录数据:', formData)
      
      // 登录成功后跳转
      window.location.href = '/dashboard'
    } catch (error) {
      console.error('登录失败:', error)
      setErrors({ general: '登录失败，请检查用户名和密码' })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-secondary-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Logo和标题 */}
        <div className="text-center">
          <div className="text-4xl font-bold text-primary-600 mb-2">🚀</div>
          <h2 className="text-3xl font-bold text-secondary-900">
            登录账户
          </h2>
          <p className="mt-2 text-sm text-secondary-600">
            欢迎回到AI项目管理系统
          </p>
        </div>

        {/* 登录表单 */}
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {/* 通用错误信息 */}
          {errors.general && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              {errors.general}
            </div>
          )}

          <div className="space-y-4">
            {/* 邮箱输入 */}
            <Input
              name="email"
              type="email"
              label="邮箱地址"
              placeholder="请输入邮箱地址"
              value={formData.email}
              onChange={handleInputChange}
              error={errors.email}
              leftIcon={<EnvelopeIcon />}
              required
            />

            {/* 密码输入 */}
            <Input
              name="password"
              type={showPassword ? 'text' : 'password'}
              label="密码"
              placeholder="请输入密码"
              value={formData.password}
              onChange={handleInputChange}
              error={errors.password}
              leftIcon={<LockClosedIcon />}
              rightIcon={
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="text-secondary-400 hover:text-secondary-600"
                >
                  {showPassword ? <EyeSlashIcon /> : <EyeIcon />}
                </button>
              }
              required
            />
          </div>

          {/* 记住我和忘记密码 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <input
                id="remember-me"
                name="remember-me"
                type="checkbox"
                className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-secondary-300 rounded"
              />
              <label htmlFor="remember-me" className="ml-2 block text-sm text-secondary-700">
                记住我
              </label>
            </div>

            <div className="text-sm">
              <Link 
                href="/auth/forgot-password" 
                className="font-medium text-primary-600 hover:text-primary-500 transition-colors"
              >
                忘记密码？
              </Link>
            </div>
          </div>

          {/* 登录按钮 */}
          <Button
            type="submit"
            variant="primary"
            size="lg"
            loading={isLoading}
            className="w-full"
          >
            {isLoading ? '登录中...' : '登录'}
          </Button>

          {/* 注册链接 */}
          <div className="text-center">
            <span className="text-sm text-secondary-600">
              还没有账户？{' '}
              <Link 
                href="/auth/register" 
                className="font-medium text-primary-600 hover:text-primary-500 transition-colors"
              >
                立即注册
              </Link>
            </span>
          </div>
        </form>

        {/* 分割线 */}
        <div className="mt-6">
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-secondary-300" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-secondary-50 text-secondary-500">或者</span>
            </div>
          </div>
        </div>

        {/* 第三方登录 */}
        <div className="mt-6 space-y-3">
          <Button
            variant="outline"
            size="lg"
            className="w-full"
            onClick={() => {
              // TODO: 实现第三方登录
              console.log('第三方登录')
            }}
          >
            <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
              <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            使用 Google 登录
          </Button>
        </div>
      </div>
    </div>
  )
} 