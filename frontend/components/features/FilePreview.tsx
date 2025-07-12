'use client'

import React, { useState } from 'react'
import { XMarkIcon, ArrowsPointingOutIcon } from '@heroicons/react/24/outline'
import { DocumentIcon, PhotoIcon, VideoCameraIcon, SpeakerWaveIcon } from '@heroicons/react/24/solid'
import Button from '@/components/ui/Button'
import Modal from '@/components/ui/Modal'

interface FilePreviewProps {
  file: File | null
  fileUrl?: string
  onClose: () => void
  className?: string
}

export function FilePreview({ file, fileUrl, onClose, className = '' }: FilePreviewProps) {
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [imageError, setImageError] = useState(false)

  if (!file && !fileUrl) {
    return null
  }

  const fileName = file?.name || 'Unknown File'
  const fileType = file?.type || ''
  const fileSize = file?.size || 0
  const displayUrl = fileUrl || (file ? URL.createObjectURL(file) : '')

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const getFileIcon = () => {
    if (fileType.startsWith('image/')) {
      return <PhotoIcon className="h-8 w-8 text-blue-500" />
    } else if (fileType === 'application/pdf') {
      return <DocumentIcon className="h-8 w-8 text-red-500" />
    } else if (fileType.includes('word')) {
      return <DocumentIcon className="h-8 w-8 text-blue-600" />
    } else if (fileType.includes('excel') || fileType.includes('sheet')) {
      return <DocumentIcon className="h-8 w-8 text-green-600" />
    } else if (fileType.startsWith('video/')) {
      return <VideoCameraIcon className="h-8 w-8 text-purple-500" />
    } else if (fileType.startsWith('audio/')) {
      return <SpeakerWaveIcon className="h-8 w-8 text-orange-500" />
    }
    return <DocumentIcon className="h-8 w-8 text-gray-500" />
  }

  const renderPreview = () => {
    if (fileType.startsWith('image/')) {
      return (
        <div className="relative">
          {!imageError ? (
            <img
              src={displayUrl}
              alt={fileName}
              className="max-w-full max-h-96 object-contain rounded-lg shadow-lg"
              onError={() => setImageError(true)}
            />
          ) : (
            <div className="flex flex-col items-center justify-center p-8 bg-gray-100 dark:bg-gray-800 rounded-lg">
              <PhotoIcon className="h-16 w-16 text-gray-400 mb-4" />
              <p className="text-sm text-gray-500 dark:text-gray-400">图片预览失败</p>
            </div>
          )}
          <button
            onClick={() => setIsFullscreen(true)}
            className="absolute top-2 right-2 p-2 bg-black bg-opacity-50 text-white rounded-full hover:bg-opacity-70 transition-all"
          >
            <ArrowsPointingOutIcon className="h-4 w-4" />
          </button>
        </div>
      )
    } else if (fileType === 'application/pdf') {
      return (
        <div className="w-full">
          <iframe
            src={displayUrl}
            className="w-full h-96 border rounded-lg"
            title={fileName}
          />
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 text-center">
            PDF预览 - 如果无法显示，请下载文件查看
          </p>
        </div>
      )
    } else if (fileType.startsWith('video/')) {
      return (
        <video
          src={displayUrl}
          controls
          className="max-w-full max-h-96 rounded-lg shadow-lg"
        >
          您的浏览器不支持视频播放
        </video>
      )
    } else if (fileType.startsWith('audio/')) {
      return (
        <div className="w-full">
          <audio
            src={displayUrl}
            controls
            className="w-full"
          >
            您的浏览器不支持音频播放
          </audio>
        </div>
      )
    } else if (fileType.startsWith('text/')) {
      return (
        <div className="w-full">
          <iframe
            src={displayUrl}
            className="w-full h-96 border rounded-lg"
            title={fileName}
          />
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 text-center">
            文本文件预览
          </p>
        </div>
      )
    } else {
      return (
        <div className="flex flex-col items-center justify-center p-8 bg-gray-100 dark:bg-gray-800 rounded-lg">
          {getFileIcon()}
          <p className="text-sm text-gray-900 dark:text-white mt-4 font-medium">
            {fileName}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {formatFileSize(fileSize)}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-2 text-center">
            此文件类型不支持预览，请下载查看
          </p>
          <Button
            variant="outline"
            size="sm"
            className="mt-4"
            onClick={() => {
              const link = document.createElement('a')
              link.href = displayUrl
              link.download = fileName
              link.click()
            }}
          >
            下载文件
          </Button>
        </div>
      )
    }
  }

  return (
    <>
      <div className={`bg-white dark:bg-gray-900 rounded-lg shadow-lg p-6 ${className}`}>
        {/* 头部 */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            {getFileIcon()}
            <div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                {fileName}
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {formatFileSize(fileSize)} • {fileType || '未知类型'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        {/* 预览内容 */}
        <div className="flex justify-center">
          {renderPreview()}
        </div>

        {/* 操作按钮 */}
        <div className="flex justify-center space-x-3 mt-6">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              const link = document.createElement('a')
              link.href = displayUrl
              link.download = fileName
              link.click()
            }}
          >
            下载
          </Button>
          {fileType.startsWith('image/') && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsFullscreen(true)}
            >
              全屏查看
            </Button>
          )}
        </div>
      </div>

      {/* 全屏模态框 */}
      {isFullscreen && fileType.startsWith('image/') && (
        <Modal
          isOpen={isFullscreen}
          onClose={() => setIsFullscreen(false)}
          size="full"
        >
          <div className="relative w-full h-full flex items-center justify-center bg-black">
            <img
              src={displayUrl}
              alt={fileName}
              className="max-w-full max-h-full object-contain"
            />
            <button
              onClick={() => setIsFullscreen(false)}
              className="absolute top-4 right-4 p-2 bg-black bg-opacity-50 text-white rounded-full hover:bg-opacity-70 transition-all"
            >
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>
        </Modal>
      )}
    </>
  )
} 