'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { 
  EyeIcon, 
  EyeSlashIcon, 
  EnvelopeIcon, 
  LockClosedIcon, 
  UserIcon,
  CheckIcon,
  XMarkIcon
} from '@heroicons/react/24/outline'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { useUserActions, useUserLoading, useUserError } from '@/lib/stores/userStore'
import { useNotify } from '@/lib/stores/appStore'

interface FormData {
  username: string
  email: string
  password: string
  confirmPassword: string
  agreeToTerms: boolean
}

interface PasswordStrength {
  score: number
  feedback: string[]
  color: string
}

export default function RegisterPage() {
  const router = useRouter()
  const notify = useNotify()
  
  // Zustand状态
  const { register, clearError } = useUserActions()
  const isLoading = useUserLoading()
  const error = useUserError()
  
  // 本地状态
  const [formData, setFormData] = useState<FormData>({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    agreeToTerms: false
  })
  
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [formErrors, setFormErrors] = useState<Record<string, string>>({})

  // 清除错误信息
  useEffect(() => {
    return () => {
      clearError()
    }
  }, [clearError])

  // 密码强度检查
  const checkPasswordStrength = (password: string): PasswordStrength => {
    let score = 0
    const feedback: string[] = []
    
    if (password.length >= 8) {
      score += 1
    } else {
      feedback.push('至少8个字符')
    }
    
    if (/[a-z]/.test(password)) {
      score += 1
    } else {
      feedback.push('包含小写字母')
    }
    
    if (/[A-Z]/.test(password)) {
      score += 1
    } else {
      feedback.push('包含大写字母')
    }
    
    if (/\d/.test(password)) {
      score += 1
    } else {
      feedback.push('包含数字')
    }
    
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
      score += 1
    } else {
      feedback.push('包含特殊字符')
    }
    
    let color = 'bg-red-500'
    if (score >= 4) color = 'bg-green-500'
    else if (score >= 3) color = 'bg-yellow-500'
    else if (score >= 2) color = 'bg-orange-500'
    
    return { score, feedback, color }
  }

  const passwordStrength = checkPasswordStrength(formData.password)

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }))
    
    // 清除对应字段的错误
    if (formErrors[name]) {
      setFormErrors(prev => ({
        ...prev,
        [name]: ''
      }))
    }
    
    // 清除全局错误
    if (error) {
      clearError()
    }
  }

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {}
    
    // 用户名验证
    if (!formData.username.trim()) {
      newErrors.username = '请输入用户名'
    } else if (formData.username.length < 3) {
      newErrors.username = '用户名至少3个字符'
    } else if (formData.username.length > 20) {
      newErrors.username = '用户名不能超过20个字符'
    } else if (!/^[a-zA-Z0-9_\u4e00-\u9fa5]+$/.test(formData.username)) {
      newErrors.username = '用户名只能包含字母、数字、下划线和中文'
    }
    
    // 邮箱验证
    if (!formData.email) {
      newErrors.email = '请输入邮箱地址'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = '邮箱格式不正确'
    }
    
    // 密码验证
    if (!formData.password) {
      newErrors.password = '请输入密码'
    } else if (passwordStrength.score < 3) {
      newErrors.password = '密码强度不够，请参考密码要求'
    }
    
    // 确认密码验证
    if (!formData.confirmPassword) {
      newErrors.confirmPassword = '请确认密码'
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = '两次输入的密码不一致'
    }
    
    // 用户协议验证
    if (!formData.agreeToTerms) {
      newErrors.agreeToTerms = '请同意用户协议和隐私政策'
    }
    
    setFormErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) return
    
    try {
      await register({
        username: formData.username,
        email: formData.email,
        password: formData.password
      })

      // 注册成功，显示通知并跳转到登录页面
      notify.success('注册成功', '请检查邮箱进行验证后登录')
      router.push('/login')

    } catch (error) {
      // 错误已经在store中处理，这里可以添加额外的错误处理
      console.error('注册失败:', error)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-secondary-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Logo和标题 */}
        <div className="text-center">
          <div className="text-4xl font-bold text-primary-600 mb-2">🚀</div>
          <h2 className="text-3xl font-bold text-secondary-900">
            创建账户
          </h2>
          <p className="mt-2 text-sm text-secondary-600">
            加入AI项目管理系统，开启高效工作之旅
          </p>
        </div>

        {/* 注册表单 */}
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {/* 全局错误信息 */}
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              {error}
            </div>
          )}

          <div className="space-y-4">
            {/* 用户名输入 */}
            <Input
              name="username"
              type="text"
              label="用户名"
              placeholder="请输入用户名"
              value={formData.username}
              onChange={handleInputChange}
              error={formErrors.username}
              leftIcon={<UserIcon />}
              helperText="3-20个字符，支持字母、数字、下划线和中文"
              required
            />

            {/* 邮箱输入 */}
            <Input
              name="email"
              type="email"
              label="邮箱地址"
              placeholder="请输入邮箱地址"
              value={formData.email}
              onChange={handleInputChange}
              error={formErrors.email}
              leftIcon={<EnvelopeIcon />}
              helperText="用于接收重要通知和密码重置"
              required
            />

            {/* 密码输入 */}
            <div>
              <Input
                name="password"
                type={showPassword ? 'text' : 'password'}
                label="密码"
                placeholder="请输入密码"
                value={formData.password}
                onChange={handleInputChange}
                error={formErrors.password}
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
              
              {/* 密码强度指示器 */}
              {formData.password && (
                <div className="mt-2 space-y-2">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm text-secondary-600">密码强度:</span>
                    <div className="flex-1 bg-secondary-200 rounded-full h-2">
                      <div 
                        className={`h-2 rounded-full transition-all duration-300 ${passwordStrength.color}`}
                        style={{ width: `${(passwordStrength.score / 5) * 100}%` }}
                      />
                    </div>
                    <span className="text-sm font-medium">
                      {passwordStrength.score <= 2 ? '弱' : passwordStrength.score <= 3 ? '中' : '强'}
                    </span>
                  </div>
                  
                  {/* 密码要求列表 */}
                  <div className="grid grid-cols-1 gap-1 text-xs">
                    {[
                      { check: formData.password.length >= 8, text: '至少8个字符' },
                      { check: /[a-z]/.test(formData.password), text: '包含小写字母' },
                      { check: /[A-Z]/.test(formData.password), text: '包含大写字母' },
                      { check: /\d/.test(formData.password), text: '包含数字' },
                      { check: /[!@#$%^&*(),.?":{}|<>]/.test(formData.password), text: '包含特殊字符' }
                    ].map((requirement, index) => (
                      <div key={index} className="flex items-center space-x-2">
                        {requirement.check ? (
                          <CheckIcon className="h-3 w-3 text-green-500" />
                        ) : (
                          <XMarkIcon className="h-3 w-3 text-red-500" />
                        )}
                        <span className={requirement.check ? 'text-green-600' : 'text-red-600'}>
                          {requirement.text}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* 确认密码输入 */}
            <Input
              name="confirmPassword"
              type={showConfirmPassword ? 'text' : 'password'}
              label="确认密码"
              placeholder="请再次输入密码"
              value={formData.confirmPassword}
              onChange={handleInputChange}
              error={formErrors.confirmPassword}
              leftIcon={<LockClosedIcon />}
              rightIcon={
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="text-secondary-400 hover:text-secondary-600"
                >
                  {showConfirmPassword ? <EyeSlashIcon /> : <EyeIcon />}
                </button>
              }
              required
            />
          </div>

          {/* 用户协议 */}
          <div className="space-y-2">
            <div className="flex items-start">
              <input
                id="agree-terms"
                name="agreeToTerms"
                type="checkbox"
                checked={formData.agreeToTerms}
                onChange={handleInputChange}
                className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-secondary-300 rounded mt-0.5"
              />
              <label htmlFor="agree-terms" className="ml-2 block text-sm text-secondary-700">
                我已阅读并同意{' '}
                <span className="text-secondary-500 cursor-not-allowed opacity-50" title="功能暂未开放">
                  用户协议
                </span>
                {' '}和{' '}
                <span className="text-secondary-500 cursor-not-allowed opacity-50" title="功能暂未开放">
                  隐私政策
                </span>
              </label>
            </div>
            {formErrors.agreeToTerms && (
              <p className="text-sm text-red-600">{formErrors.agreeToTerms}</p>
            )}
          </div>

          {/* 注册按钮 */}
          <Button
            type="submit"
            variant="primary"
            size="lg"
            loading={isLoading}
            className="w-full"
          >
            {isLoading ? '注册中...' : '创建账户'}
          </Button>

          {/* 登录链接 */}
          <div className="text-center">
            <span className="text-sm text-secondary-600">
              已有账户？{' '}
              <Link 
                href="/login" 
                className="font-medium text-primary-600 hover:text-primary-500 transition-colors"
              >
                立即登录
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

        {/* 第三方注册 */}
        <div className="mt-6 space-y-3">
          <Button
            variant="outline"
            size="lg"
            className="w-full"
            onClick={() => {
              // TODO: 实现第三方注册
              notify.info('功能开发中', '第三方注册功能即将上线')
            }}
          >
            <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
              <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            使用 Google 注册
          </Button>
        </div>
      </div>
    </div>
  )
} 