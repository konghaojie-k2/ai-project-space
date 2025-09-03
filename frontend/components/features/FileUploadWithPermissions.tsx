'use client'

import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import Button from '@/components/ui/Button'
import { useUserStore } from '@/lib/stores/userStore'

interface FileUploadProps {
  onUploadSuccess?: (files: any[]) => void
  projectId?: string
  stage: string
}

interface FileWithPermissions extends File {
  id: string
  tags: string[]
  description: string
  accessLevel: string
}

/**
 * 文件上传组件 - 支持访问权限选择
 */
export default function FileUploadWithPermissions({ 
  onUploadSuccess, 
  projectId,
  stage = 'data-understanding'
}: FileUploadProps) {
  const { user } = useUserStore()
  const [files, setFiles] = useState<FileWithPermissions[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<{[key: string]: number}>({})

  // 访问级别选项
  const accessLevelOptions = [
    { value: 'all_users', label: '🌍 全员可见', description: '所有团队成员都可以查看' },
    { value: 'admins_only', label: '👑 仅管理员', description: '只有管理员可以查看' },
    { value: 'owner_only', label: '🔒 仅自己', description: '只有上传者可以查看' }
  ]

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.map(file => ({
      ...file,
      id: Math.random().toString(36).substr(2, 9),
      tags: [],
      description: '',
      accessLevel: 'all_users' // 默认全员可见
    }))
    setFiles(prev => [...prev, ...newFiles])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
      'image/*': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    }
  })

  // 更新文件属性
  const updateFile = (fileId: string, field: string, value: any) => {
    setFiles(prev => prev.map(file => 
      file.id === fileId ? { ...file, [field]: value } : file
    ))
  }

  // 添加标签
  const addTag = (fileId: string, tag: string) => {
    if (!tag.trim()) return
    updateFile(fileId, 'tags', [
      ...files.find(f => f.id === fileId)?.tags || [],
      tag.trim()
    ])
  }

  // 移除标签
  const removeTag = (fileId: string, tagIndex: number) => {
    const file = files.find(f => f.id === fileId)
    if (file) {
      const newTags = [...file.tags]
      newTags.splice(tagIndex, 1)
      updateFile(fileId, 'tags', newTags)
    }
  }

  // 移除文件
  const removeFile = (fileId: string) => {
    setFiles(prev => prev.filter(f => f.id !== fileId))
  }

  // 上传文件
  const uploadFiles = async () => {
    if (files.length === 0) return

    setIsUploading(true)
    const uploadedFiles = []

    try {
      for (const file of files) {
        const formData = new FormData()
        formData.append('files', file)
        formData.append('stage', stage)
        formData.append('access_level', file.accessLevel)
        
        if (projectId) {
          formData.append('project_id', projectId)
        }
        if (file.description) {
          formData.append('description', file.description)
        }
        if (file.tags.length > 0) {
          formData.append('tags', file.tags.join(','))
        }

        const token = localStorage.getItem('auth-token')
        
        setUploadProgress(prev => ({ ...prev, [file.id]: 0 }))

        const response = await fetch('http://localhost:8000/api/v1/files/upload', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          },
          body: formData
        })

        if (response.ok) {
          const result = await response.json()
          uploadedFiles.push(...result)
          setUploadProgress(prev => ({ ...prev, [file.id]: 100 }))
        } else {
          throw new Error(`上传失败: ${response.status}`)
        }
      }

      // 上传成功
      setFiles([])
      setUploadProgress({})
      onUploadSuccess?.(uploadedFiles)
      
    } catch (error) {
      console.error('文件上传失败:', error)
      alert('文件上传失败，请重试')
    } finally {
      setIsUploading(false)
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

  return (
    <div className="space-y-6">
      {/* 拖拽上传区域 */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
          isDragActive 
            ? 'border-blue-500 bg-blue-50' 
            : 'border-gray-300 hover:border-gray-400'
        }`}
      >
        <input {...getInputProps()} />
        <div className="text-4xl mb-4">📁</div>
        <div className="text-lg font-medium text-gray-900 mb-2">
          {isDragActive ? '释放文件开始上传' : '拖拽文件到此处或点击选择'}
        </div>
        <div className="text-sm text-gray-600">
          支持 PDF, Word, Excel, 图片, 文本等格式
        </div>
      </div>

      {/* 文件列表 */}
      {files.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-medium text-gray-900">待上传文件</h3>
          
          {files.map((file) => (
            <div key={file.id} className="bg-white border rounded-lg p-4">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <div className="font-medium text-gray-900">{file.name}</div>
                  <div className="text-sm text-gray-500">
                    {formatFileSize(file.size)} • {file.type}
                  </div>
                </div>
                <Button
                  onClick={() => removeFile(file.id)}
                  className="bg-red-100 text-red-700 hover:bg-red-200 text-sm"
                >
                  移除
                </Button>
              </div>

              {/* 文件描述 */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  文件描述
                </label>
                <textarea
                  value={file.description}
                  onChange={(e) => updateFile(file.id, 'description', e.target.value)}
                  placeholder="请输入文件描述（可选）"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={2}
                />
              </div>

              {/* 访问权限选择 */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  📋 访问权限
                </label>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {accessLevelOptions.map((option) => (
                    <label
                      key={option.value}
                      className={`flex items-center p-3 border rounded-lg cursor-pointer transition-colors ${
                        file.accessLevel === option.value
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-300 hover:border-gray-400'
                      }`}
                    >
                      <input
                        type="radio"
                        name={`access-${file.id}`}
                        value={option.value}
                        checked={file.accessLevel === option.value}
                        onChange={(e) => updateFile(file.id, 'accessLevel', e.target.value)}
                        className="sr-only"
                      />
                      <div>
                        <div className="font-medium text-sm">{option.label}</div>
                        <div className="text-xs text-gray-600">{option.description}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* 标签管理 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  标签
                </label>
                <div className="flex flex-wrap gap-2 mb-2">
                  {file.tags.map((tag, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded-full"
                    >
                      {tag}
                      <button
                        onClick={() => removeTag(file.id, index)}
                        className="ml-1 text-blue-600 hover:text-blue-800"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
                <input
                  type="text"
                  placeholder="输入标签后按回车"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      addTag(file.id, e.currentTarget.value)
                      e.currentTarget.value = ''
                    }
                  }}
                />
              </div>

              {/* 上传进度 */}
              {uploadProgress[file.id] !== undefined && (
                <div className="mt-4">
                  <div className="flex justify-between text-sm text-gray-600 mb-1">
                    <span>上传进度</span>
                    <span>{uploadProgress[file.id]}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${uploadProgress[file.id]}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          ))}

          {/* 上传按钮 */}
          <div className="flex justify-end space-x-3">
            <Button
              onClick={() => setFiles([])}
              className="bg-gray-100 text-gray-700 hover:bg-gray-200"
              disabled={isUploading}
            >
              清空列表
            </Button>
            <Button
              onClick={uploadFiles}
              className="bg-blue-600 hover:bg-blue-700 text-white"
              disabled={isUploading || files.length === 0}
            >
              {isUploading ? '上传中...' : `上传 ${files.length} 个文件`}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
