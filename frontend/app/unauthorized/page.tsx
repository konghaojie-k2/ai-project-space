'use client'

import Link from 'next/link'
import Button from '@/components/ui/Button'

/**
 * 无权限访问页面
 * 当普通用户尝试访问管理员功能时显示
 */
export default function UnauthorizedPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
        {/* 图标 */}
        <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
          <svg className="w-10 h-10 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m0 0v2m0-2h2m-2 0H10m2-9V6m0 0V4m0 2h2m-2 0H10" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>

        {/* 标题 */}
        <h1 className="text-2xl font-bold text-gray-900 mb-4">
          🚫 访问受限
        </h1>

        {/* 说明文本 */}
        <div className="text-gray-600 mb-6 space-y-2">
          <p className="text-lg">抱歉，您没有权限访问此页面</p>
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-sm">
            <div className="font-medium text-yellow-800 mb-2">👤 当前权限级别：普通用户</div>
            <div className="text-yellow-700 text-left space-y-1">
              <div>• ✅ 基本功能：聊天、文件上传</div>
              <div>• ✅ 个人文件：查看和管理</div>
              <div>• ✅ 共享文件：参与协作</div>
              <div>• ❌ 系统管理：需要管理员权限</div>
            </div>
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="space-y-3">
          <Link href="/">
            <Button className="w-full bg-blue-600 hover:bg-blue-700 text-white">
              🏠 返回首页
            </Button>
          </Link>
          
          <div className="text-sm text-gray-500">
            如需管理员权限，请联系系统管理员
          </div>
        </div>

        {/* 联系信息 */}
        <div className="mt-6 pt-6 border-t border-gray-200">
          <p className="text-xs text-gray-400">
            如有疑问，请联系技术支持
          </p>
        </div>
      </div>
    </div>
  )
}
