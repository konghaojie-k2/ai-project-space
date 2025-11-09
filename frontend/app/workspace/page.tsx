'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useUserStore } from '@/lib/stores/userStore'
import Button from '@/components/ui/Button'

interface UserFile {
  id: string
  original_name: string
  file_size: number
  file_type: string
  stage: string
  created_at: string
  description?: string
  tags: string[]
}

/**
 * 普通用户工作空间页面
 * 只显示用户自己的文件和基本功能
 */
export default function WorkspacePage() {
  const router = useRouter()
  const { user, loading } = useUserStore()
  const [files, setFiles] = useState<UserFile[]>([])
  const [loadingFiles, setLoadingFiles] = useState(true)

  // 权限检查
  useEffect(() => {
    if (loading) return

    if (!user) {
      router.replace('/login')
      return
    }

    // 管理员重定向到dashboard
    if (user.is_superuser) {
      router.replace('/dashboard')
      return
    }

    // 普通用户加载自己的文件
    loadUserFiles()
  }, [user, loading, router])

  // 加载用户文件
  const loadUserFiles = async () => {
    try {
      setLoadingFiles(true)
      const token = localStorage.getItem('auth-token')
      
      const { apiGet } = await import('@/lib/api');
      const response = await apiGet('/api/v1/files/')

      if (response.ok) {
        const data = await response.json()
        setFiles(data)
      } else {
        console.error('加载文件失败:', response.status)
      }
    } catch (error) {
      console.error('加载文件失败:', error)
    } finally {
      setLoadingFiles(false)
    }
  }

  // 格式化文件大小
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  // 格式化日期
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN')
  }

  if (loading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">加载中...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 顶部导航 */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <div className="text-2xl font-bold text-blue-600">🚀</div>
              <h1 className="ml-3 text-xl font-semibold text-gray-900">
                我的工作空间
              </h1>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-600">
                欢迎，<span className="font-medium">{user.username}</span>
              </div>
              <Button
                onClick={() => {
                  localStorage.removeItem('auth-token')
                  router.push('/login')
                }}
                className="bg-gray-600 hover:bg-gray-700 text-white text-sm"
              >
                退出登录
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* 主要内容 */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 用户权限说明 */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <div className="flex items-center space-x-2 mb-2">
            <span className="text-blue-600">👤</span>
            <h3 className="text-sm font-medium text-blue-900">团队成员权限</h3>
          </div>
          <div className="text-xs text-blue-800 space-y-1">
            <div>• ✅ 文件上传：可以上传和管理自己的文件</div>
            <div>• ✅ 文件访问：可以查看自己上传的文件和公开文件</div>
            <div>• ✅ AI聊天：可以与AI助手进行对话</div>
            <div>• ❌ 系统管理：无法访问用户管理和系统统计功能</div>
          </div>
        </div>

        {/* 快速操作 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white p-6 rounded-lg shadow border">
            <div className="text-center">
              <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">📤</span>
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">上传文件</h3>
              <p className="text-sm text-gray-600 mb-4">上传文档、图片等文件进行管理</p>
              <Button 
                onClick={() => router.push('/dashboard/files')}
                className="bg-green-600 hover:bg-green-700 text-white w-full"
              >
                开始上传
              </Button>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow border">
            <div className="text-center">
              <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">💬</span>
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">AI助手</h3>
              <p className="text-sm text-gray-600 mb-4">与AI助手对话，获取帮助</p>
              <Button 
                onClick={() => router.push('/dashboard/chat')}
                className="bg-blue-600 hover:bg-blue-700 text-white w-full"
              >
                开始对话
              </Button>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow border">
            <div className="text-center">
              <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">📋</span>
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">项目协作</h3>
              <p className="text-sm text-gray-600 mb-4">参与团队项目和协作</p>
              <Button 
                onClick={() => router.push('/dashboard/projects')}
                className="bg-purple-600 hover:bg-purple-700 text-white w-full"
              >
                查看项目
              </Button>
            </div>
          </div>
        </div>

        {/* 我的文件 */}
        <div className="bg-white rounded-lg shadow border">
          <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
            <h2 className="text-lg font-medium text-gray-900">📁 我的文件</h2>
            <Button
              onClick={loadUserFiles}
              className="bg-blue-600 hover:bg-blue-700 text-white text-sm"
            >
              刷新
            </Button>
          </div>

          <div className="p-6">
            {loadingFiles ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                <p className="mt-4 text-gray-600">加载文件中...</p>
              </div>
            ) : files.length === 0 ? (
              <div className="text-center py-8">
                <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl">📂</span>
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">暂无文件</h3>
                <p className="text-gray-600 mb-4">您还没有上传任何文件</p>
                <Button 
                  onClick={() => router.push('/dashboard/files')}
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                >
                  立即上传
                </Button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        文件名
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        大小
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        类型
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        阶段
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        上传时间
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        操作
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {files.map((file) => (
                      <tr key={file.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <div className="text-sm font-medium text-gray-900">
                              {file.original_name}
                            </div>
                          </div>
                          {file.description && (
                            <div className="text-sm text-gray-500 mt-1">
                              {file.description}
                            </div>
                          )}
                          {file.tags.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-1">
                              {file.tags.map((tag, index) => (
                                <span
                                  key={index}
                                  className="inline-flex px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full"
                                >
                                  {tag}
                                </span>
                              ))}
                            </div>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatFileSize(file.file_size)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {file.file_type}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                            {file.stage}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatDate(file.created_at)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          <div className="flex space-x-2">
                            <a
                              href={`${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8001/api/v1'}/files/${file.id}/download`}
                              className="text-blue-600 hover:text-blue-900"
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              下载
                            </a>
                            <button
                              onClick={() => router.push(`/dashboard/files/${file.id}`)}
                              className="text-green-600 hover:text-green-900"
                            >
                              查看
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
