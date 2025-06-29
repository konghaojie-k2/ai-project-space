'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { EnvelopeIcon, ArrowLeftIcon, CheckCircleIcon } from '@heroicons/react/24/outline'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { useUserActions, useUserLoading, useUserError } from '@/lib/stores/userStore'
import { useNotify } from '@/lib/stores/appStore'

type Step = 'input' | 'success'

export default function ForgotPasswordPage() {
  const notify = useNotify()
  
  // Zustand状态
  const { forgotPassword, clearError } = useUserActions()
  const isLoading = useUserLoading()
  const error = useUserError()
  
  // 本地状态
  const [step, setStep] = useState<Step>('input')
  const [email, setEmail] = useState('')
  const [formError, setFormError] = useState('')

  // 清除错误信息
  useEffect(() => {
    return () => {
      clearError()
    }
  }, [clearError])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setEmail(e.target.value)
    
    // 清除表单错误信息
    if (formError) {
      setFormError('')
    }
    
    // 清除全局错误
    if (error) {
      clearError()
    }
  }

  const validateEmail = (): boolean => {
    if (!email) {
      setFormError('请输入邮箱地址')
      return false
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setFormError('邮箱格式不正确')
      return false
    }
    return true
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateEmail()) return
    
    try {
      await forgotPassword(email)
      
      // 发送成功，切换到成功页面
      setStep('success')
      notify.success('邮件发送成功', '请检查您的邮箱')
      
    } catch (error) {
      // 错误已经在store中处理，这里可以添加额外的错误处理
      console.error('发送重置邮件失败:', error)
    }
  }

  const handleResend = async () => {
    try {
      await forgotPassword(email)
      notify.success('邮件重新发送成功', '请检查您的邮箱')
    } catch (error) {
      console.error('重新发送失败:', error)
      notify.error('重新发送失败', '请稍后重试')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-secondary-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {step === 'input' ? (
          <>
            {/* Logo和标题 */}
            <div className="text-center">
              <div className="text-4xl font-bold text-primary-600 mb-2">🔐</div>
              <h2 className="text-3xl font-bold text-secondary-900">
                忘记密码
              </h2>
              <p className="mt-2 text-sm text-secondary-600">
                输入您的邮箱地址，我们将发送密码重置链接
              </p>
            </div>

            {/* 重置表单 */}
            <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
              {/* 全局错误信息 */}
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
                  {error}
                </div>
              )}

              <div className="space-y-4">
                {/* 邮箱输入 */}
                <Input
                  name="email"
                  type="email"
                  label="邮箱地址"
                  placeholder="请输入您的邮箱地址"
                  value={email}
                  onChange={handleInputChange}
                  error={formError}
                  leftIcon={<EnvelopeIcon />}
                  required
                />
              </div>

              {/* 发送重置邮件按钮 */}
              <Button
                type="submit"
                variant="primary"
                size="lg"
                loading={isLoading}
                className="w-full"
              >
                {isLoading ? '发送中...' : '发送重置邮件'}
              </Button>

              {/* 返回登录 */}
              <div className="text-center">
                <Link 
                  href="/auth/login" 
                  className="inline-flex items-center text-sm font-medium text-primary-600 hover:text-primary-500 transition-colors"
                >
                  <ArrowLeftIcon className="h-4 w-4 mr-2" />
                  返回登录
                </Link>
              </div>
            </form>

            {/* 帮助信息 */}
            <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <h3 className="text-sm font-medium text-blue-800 mb-2">
                💡 找不到重置邮件？
              </h3>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• 请检查您的垃圾邮件文件夹</li>
                <li>• 确认邮箱地址输入正确</li>
                <li>• 重置邮件可能需要几分钟才能到达</li>
                <li>• 如仍有问题，请联系客服支持</li>
              </ul>
            </div>
          </>
        ) : (
          <>
            {/* 成功页面 */}
            <div className="text-center">
              <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-green-100 mb-4">
                <CheckCircleIcon className="h-8 w-8 text-green-600" />
              </div>
              <h2 className="text-3xl font-bold text-secondary-900">
                邮件已发送
              </h2>
              <p className="mt-2 text-sm text-secondary-600">
                我们已向 <span className="font-medium text-secondary-900">{email}</span> 发送了密码重置链接
              </p>
            </div>

            {/* 操作指引 */}
            <div className="mt-8 space-y-6">
              <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
                <h3 className="text-sm font-medium text-gray-800 mb-2">
                  📧 接下来的步骤：
                </h3>
                <ol className="text-sm text-gray-700 space-y-1 list-decimal list-inside">
                  <li>检查您的邮箱（包括垃圾邮件文件夹）</li>
                  <li>点击邮件中的"重置密码"链接</li>
                  <li>设置您的新密码</li>
                  <li>使用新密码登录系统</li>
                </ol>
              </div>

              {/* 重新发送邮件 */}
              <div className="text-center space-y-4">
                <p className="text-sm text-secondary-600">
                  没有收到邮件？
                </p>
                <Button
                  variant="outline"
                  size="md"
                  loading={isLoading}
                  onClick={handleResend}
                  className="w-full"
                >
                  {isLoading ? '发送中...' : '重新发送邮件'}
                </Button>
              </div>

              {/* 返回登录 */}
              <div className="text-center">
                <Link 
                  href="/auth/login" 
                  className="inline-flex items-center text-sm font-medium text-primary-600 hover:text-primary-500 transition-colors"
                >
                  <ArrowLeftIcon className="h-4 w-4 mr-2" />
                  返回登录
                </Link>
              </div>
            </div>

            {/* 安全提示 */}
            <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <h3 className="text-sm font-medium text-yellow-800 mb-2">
                🔒 安全提示
              </h3>
              <ul className="text-sm text-yellow-700 space-y-1">
                <li>• 重置链接将在24小时后失效</li>
                <li>• 请勿与他人分享重置链接</li>
                <li>• 如果您没有请求重置密码，请忽略此邮件</li>
              </ul>
            </div>
          </>
        )}
      </div>
    </div>
  )
} 