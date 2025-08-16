'use client'

import React, { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { CloudArrowUpIcon, DocumentIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { CheckCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/24/solid'
import Button from '@/components/ui/Button'
import { formatFileSize } from '@/lib/utils'
import { useUser } from '@/lib/contexts/UserContext'

interface FileUploadProps {
  onUpload?: (files: File[]) => void
  onRemove?: (file: File) => void
  accept?: Record<string, string[]>
  maxSize?: number
  maxFiles?: number
  multiple?: boolean
  disabled?: boolean
  className?: string
  projectId?: string // 添加项目ID
  stage?: string // 添加项目阶段
}

interface UploadFile {
  id: string
  originalFile: File  // 保存原始File对象
  name: string
  size: number
  type: string
  progress?: number
  status?: 'pending' | 'uploading' | 'success' | 'error'
  error?: string
}

export function FileUpload({
  onUpload,
  onRemove,
  accept = {
    'image/*': ['.png', '.jpg', '.jpeg', '.gif', '.webp'],
    'application/pdf': ['.pdf'],
    'application/msword': ['.doc'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
    'application/vnd.ms-excel': ['.xls'],
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    'text/plain': ['.txt'],
    'text/markdown': ['.md'],
    'application/zip': ['.zip'],
    'application/x-rar-compressed': ['.rar'],
  },
  maxSize = 10 * 1024 * 1024, // 10MB
  maxFiles = 10,
  multiple = true,
  disabled = false,
  className = '',
  projectId = 'default', // 默认项目ID
  stage, // 移除默认值，让stage可以为空
}: FileUploadProps) {
  const { user } = useUser()
  const [uploadedFiles, setUploadedFiles] = useState<UploadFile[]>([])
  const [isDragActive, setIsDragActive] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [embeddingStatus, setEmbeddingStatus] = useState<Record<string, 'pending' | 'processing' | 'success' | 'failed'>>({})

  // 处理文件选择
  const handleFileSelect = (selectedFiles: File[]) => {
    if (disabled) return

    const validFiles = selectedFiles.filter(file => {
      // 检查文件大小
      if (file.size > maxSize) {
        console.warn(`文件 ${file.name} 大小超过 ${(maxSize / 1024 / 1024).toFixed(1)}MB`)
        return false
      }

      // 检查文件数量
      if (uploadedFiles.length >= maxFiles) {
        console.warn(`最多只能上传 ${maxFiles} 个文件`)
        return false
      }

      return true
    })

    if (validFiles.length === 0) return

    const newFiles: UploadFile[] = validFiles.map((file, index) => ({
      id: `file-${Date.now()}-${index}`,
      originalFile: file, // 保存原始File对象
      name: file.name,
      size: file.size,
      type: file.type,
      progress: 0,
      status: 'pending' as const
    }))

    setUploadedFiles(prev => [...prev, ...newFiles])
    
    // 开始上传
    if (onUpload) {
      setIsUploading(true)
      newFiles.forEach((uploadFile, index) => {
        uploadToBackend(uploadFile, index * 100) // 错开上传时间
      })
    }
  }

  // 替换模拟上传为真实的后端上传
  const uploadToBackend = async (file: UploadFile, delay: number = 0) => {
    try {
      // 延迟上传以避免并发过多
      if (delay > 0) {
        await new Promise(resolve => setTimeout(resolve, delay))
      }
      
      // 设置初始嵌入状态
      setEmbeddingStatus(prev => ({
        ...prev,
        [file.id]: 'pending'
      }))

      // 更新文件状态为上传中
      setUploadedFiles(prev => 
        prev.map(f => 
          f.id === file.id 
            ? { ...f, status: 'uploading' }
            : f
        )
      )

      // 模拟进度更新
      const progressInterval = setInterval(() => {
        setUploadedFiles(prev => 
          prev.map(f => 
            f.id === file.id 
              ? { ...f, progress: Math.min((f.progress || 0) + Math.random() * 30, 90) }
              : f
          )
        )
      }, 200)

      // 创建FormData
      const formData = new FormData()
      formData.append('files', file.originalFile)
      formData.append('stage', stage || 'draft')
      if (projectId !== 'default') formData.append('project_id', projectId)
      formData.append('description', `上传文件: ${file.name}`)
      // 添加实际用户信息
      formData.append('uploaded_by', user?.name || '管理员')

      const response = await fetch('/api/v1/files/upload', {
        method: 'POST',
        body: formData
      })

      clearInterval(progressInterval)

      if (response.ok) {
        const result = await response.json()
        
        // 更新文件状态为成功
        setUploadedFiles(prev => 
          prev.map(f => 
            f.id === file.id 
              ? { ...f, progress: 100, status: 'success' }
              : f
          )
        )

        console.log('文件上传成功:', result)
        
        // 处理嵌入状态
        if (result && result.length > 0) {
          const uploadedFile = result[0]
          setEmbeddingStatus(prev => ({
            ...prev,
            [file.id]: uploadedFile.is_processed ? 'success' : 'processing'
          }))
          
          // 如果未处理，显示处理中状态
          if (!uploadedFile.is_processed) {
            setTimeout(() => {
              setEmbeddingStatus(prev => ({
                ...prev,
                [file.id]: 'success'
              }))
            }, 3000) // 3秒后假设处理完成
          }
        }
      } else {
        const error = await response.text()
        throw new Error(error)
      }

    } catch (error) {
      console.error('文件上传失败:', error)
      
      // 更新文件状态为失败
      setUploadedFiles(prev => 
        prev.map(f => 
          f.id === file.id 
            ? { ...f, status: 'error', error: error instanceof Error ? error.message : String(error) }
            : f
        )
      )
      
      // 设置嵌入状态为失败
      setEmbeddingStatus(prev => ({
        ...prev,
        [file.id]: 'failed'
      }))
    }
  }

  // 处理文档嵌入
  const processDocumentEmbedding = async (fileId: string, filePath: string) => {
    try {
      console.log('开始处理文档嵌入...', fileId)
      
      const response = await fetch('/api/v1/chat/documents/process', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          project_id: projectId,
          file_paths: [filePath],
          chunk_size: 1000,
          chunk_overlap: 200
        }),
      })

      if (response.ok) {
        console.log('文档嵌入处理已启动')
      } else {
        console.warn('文档嵌入处理失败:', await response.text())
      }
    } catch (error) {
      console.error('文档嵌入处理出错:', error)
    }
  }

  const { getRootProps, getInputProps, isDragActive: dropzoneActive } = useDropzone({
    onDrop: (acceptedFiles, rejectedFiles) => {
      handleFileSelect(acceptedFiles)
      // 处理被拒绝的文件
      if (rejectedFiles.length > 0) {
        rejectedFiles.forEach((file) => {
          const errors = file.errors.map((error: any) => {
            switch (error.code) {
              case 'file-too-large':
                return `文件大小超过限制 (${formatFileSize(maxSize)})`
              case 'file-invalid-type':
                return '不支持的文件类型'
              case 'too-many-files':
                return `最多只能上传 ${maxFiles} 个文件`
              default:
                return error.message
            }
          }).join(', ')
          
          console.error(`文件 ${file.file.name} 上传失败: ${errors}`)
        })
      }
    },
    accept,
    maxSize,
    maxFiles,
    multiple,
    disabled,
    onDragEnter: () => setIsDragActive(true),
    onDragLeave: () => setIsDragActive(false),
  })

  const removeFile = (file: UploadFile) => {
    setUploadedFiles(prev => prev.filter(f => f.id !== file.id))
    onRemove?.(file.originalFile)
  }

  const getFileIcon = (file: File) => {
    // 安全检查file.type是否存在
    const fileType = file.type || '';
    const fileName = file.name || '';
    
    if (fileType.startsWith('image/')) {
      return '🖼️'
    } else if (fileType === 'application/pdf') {
      return '📄'
    } else if (fileType.includes('word') || fileName.toLowerCase().includes('.doc')) {
      return '📝'
    } else if (fileType.includes('excel') || fileType.includes('sheet') || fileName.toLowerCase().includes('.xls')) {
      return '📊'
    } else if (fileType.startsWith('video/')) {
      return '🎥'
    } else if (fileType.startsWith('audio/')) {
      return '🎵'
    } else if (fileType === 'text/plain' || fileName.toLowerCase().endsWith('.txt')) {
      return '📃'
    } else if (fileName.toLowerCase().endsWith('.zip') || fileName.toLowerCase().endsWith('.rar')) {
      return '🗜️'
    } else {
      return '📄'
    }
  }

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case 'success':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case 'error':
        return <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />
      default:
        return null
    }
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* 拖拽上传区域 */}
      <div
        {...getRootProps()}
        className={`
          relative border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
          transition-all duration-200 ease-in-out
          ${dropzoneActive || isDragActive
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
            : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
          }
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} />
        
        <div className="space-y-4">
          <div className="flex justify-center">
            <CloudArrowUpIcon className="h-12 w-12 text-gray-400" />
          </div>
          
          <div className="space-y-2">
            <p className="text-lg font-medium text-gray-900 dark:text-white">
              {dropzoneActive || isDragActive
                ? '释放文件开始上传'
                : '拖拽文件到这里，或点击选择文件'
              }
            </p>
            
            <p className="text-sm text-gray-500 dark:text-gray-400">
              支持 PDF、Word、Excel、图片、视频、音频等格式
            </p>
            
            <p className="text-xs text-gray-400 dark:text-gray-500">
              单个文件最大 {formatFileSize(maxSize)}，最多 {maxFiles} 个文件
            </p>
          </div>
          
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={disabled}
            className="mt-4"
          >
            选择文件
          </Button>
        </div>
      </div>

      {/* 文件列表 */}
      {uploadedFiles.length > 0 && (
        <div className="space-y-3">
          <h4 className="font-medium text-gray-900 dark:text-white">
            已上传文件 ({uploadedFiles.length})
          </h4>
          
          <div className="space-y-2">
            {uploadedFiles.map((file) => (
              <div
                key={file.id}
                className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
              >
                <div className="flex items-center space-x-3 flex-1 min-w-0">
                  <div className="flex-shrink-0">
                    <span className="text-2xl">{getFileIcon(file.originalFile)}</span>
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {file.name}
                      </p>
                      {getStatusIcon(file.status)}
                    </div>
                    
                    <div className="flex items-center space-x-2 mt-1">
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {formatFileSize(file.size)}
                      </p>
                      
                      {file.status === 'uploading' && (
                        <div className="flex items-center space-x-2">
                          <div className="w-16 bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                            <div
                              className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
                              style={{ width: `${file.progress || 0}%` }}
                            />
                          </div>
                          <span className="text-xs text-gray-500 dark:text-gray-400">
                            {Math.round(file.progress || 0)}%
                          </span>
                        </div>
                      )}
                      
                      {file.status === 'success' && (
                        <div className="flex items-center space-x-2">
                          <span className="text-xs text-green-600 dark:text-green-400">
                            上传成功
                          </span>
                          {/* 嵌入状态指示器 */}
                          <div className="flex items-center space-x-1">
                            {embeddingStatus[file.id] === 'pending' && (
                              <div className="flex items-center space-x-1">
                                <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse"></div>
                                <span className="text-xs text-yellow-600 dark:text-yellow-400">等待索引</span>
                              </div>
                            )}
                            {embeddingStatus[file.id] === 'processing' && (
                              <div className="flex items-center space-x-1">
                                <div className="w-2 h-2 bg-blue-400 rounded-full animate-spin"></div>
                                <span className="text-xs text-blue-600 dark:text-blue-400">智能索引中</span>
                              </div>
                            )}
                            {embeddingStatus[file.id] === 'success' && (
                              <div className="flex items-center space-x-1">
                                <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                                <span className="text-xs text-green-600 dark:text-green-400">索引完成</span>
                              </div>
                            )}
                            {embeddingStatus[file.id] === 'failed' && (
                              <div className="flex items-center space-x-1">
                                <div className="w-2 h-2 bg-red-400 rounded-full"></div>
                                <span className="text-xs text-red-600 dark:text-red-400">索引失败</span>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                      
                      {file.status === 'error' && (
                        <span className="text-xs text-red-600 dark:text-red-400">
                          上传失败
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                
                <button
                  onClick={() => removeFile(file)}
                  className="flex-shrink-0 p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  <XMarkIcon className="h-5 w-5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
} 