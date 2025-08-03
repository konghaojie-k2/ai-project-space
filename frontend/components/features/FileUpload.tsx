'use client'

import React, { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { CloudArrowUpIcon, DocumentIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { CheckCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/24/solid'
import Button from '@/components/ui/Button'
import { formatFileSize } from '@/lib/utils'

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
  status?: 'uploading' | 'success' | 'error'
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
  const [uploadedFiles, setUploadedFiles] = useState<UploadFile[]>([])
  const [isDragActive, setIsDragActive] = useState(false)

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
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

    // 处理接受的文件
    if (acceptedFiles.length > 0) {
      const newFiles: UploadFile[] = acceptedFiles.map((file) => ({
        id: `${file.name}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        originalFile: file,  // 保存原始File对象
        name: file.name,
        size: file.size,
        type: file.type,
        progress: 0,
        status: 'uploading',
      }))

      setUploadedFiles(prev => [...prev, ...newFiles])
      
      // 真实上传到后端
      newFiles.forEach((file, index) => {
        uploadToBackend(file, index * 200)
      })

      onUpload?.(acceptedFiles)
    }
  }, [maxSize, maxFiles, onUpload])

  // 替换模拟上传为真实的后端上传
  const uploadToBackend = async (file: UploadFile, delay: number = 0) => {
    try {
      // 延迟上传以避免并发过多
      if (delay > 0) {
        await new Promise(resolve => setTimeout(resolve, delay))
      }

      const formData = new FormData()
      // 使用保存的原始File对象
      formData.append('files', file.originalFile)
      formData.append('project_id', projectId || '') // 添加项目ID
      if (stage) {
        formData.append('stage', stage) // 只有当stage存在时才添加
      } else {
        formData.append('stage', '待分类') // 默认状态为待分类
      }
      formData.append('description', `上传文件: ${file.name}`)

      // 模拟上传进度
      const progressInterval = setInterval(() => {
        setUploadedFiles(prev => 
          prev.map(f => {
            if (f.id === file.id && f.status === 'uploading') {
              const newProgress = Math.min((f.progress || 0) + Math.random() * 20, 90)
              return { ...f, progress: newProgress }
            }
            return f
          })
        )
      }, 300)

      // 调用后端API
      const response = await fetch('/api/v1/files/upload', {
        method: 'POST',
        body: formData,
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
        
        // 触发文档嵌入处理
        if (result && result.length > 0) {
          await processDocumentEmbedding(result[0].id, result[0].file_path)
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
    onDrop,
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
                        <span className="text-xs text-green-600 dark:text-green-400">
                          上传成功
                        </span>
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