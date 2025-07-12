'use client'

import React, { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { 
  ArrowLeftIcon,
  DocumentIcon,
  PhotoIcon,
  VideoCameraIcon,
  SpeakerWaveIcon,
  ShareIcon,
  ArrowDownTrayIcon,
  PencilIcon,
  TrashIcon,
  ClockIcon,
  UserIcon,
  TagIcon,
  ChatBubbleLeftIcon,
  EyeIcon,
  HeartIcon,
  StarIcon
} from '@heroicons/react/24/outline'
import { HeartIcon as HeartIconSolid, StarIcon as StarIconSolid } from '@heroicons/react/24/solid'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import Modal from '@/components/ui/Modal'
import { FilePreview } from '@/components/features/FilePreview'
import { formatFileSize, cn } from '@/lib/utils'

interface FileDetail {
  id: string
  name: string
  type: string
  size: number
  uploadedAt: string
  uploadedBy: string
  stage: string
  tags: string[]
  description: string
  url: string
  thumbnail?: string
  downloads: number
  views: number
  likes: number
  isLiked: boolean
  isFavorited: boolean
  versions: FileVersion[]
  comments: FileComment[]
}

interface FileVersion {
  id: string
  version: string
  uploadedAt: string
  uploadedBy: string
  size: number
  changes: string
  url: string
}

interface FileComment {
  id: string
  content: string
  author: string
  createdAt: string
  replies: FileComment[]
}

// 模拟数据
const mockFileDetail: FileDetail = {
  id: '1',
  name: '项目需求文档.pdf',
  type: 'application/pdf',
  size: 2048000,
  uploadedAt: '2024-12-28T10:30:00Z',
  uploadedBy: '张三',
  stage: '售前',
  tags: ['需求', '重要', '客户'],
  description: '这是项目的核心需求文档，包含了所有功能需求和非功能需求的详细说明。',
  url: '/api/files/1/download',
  downloads: 45,
  views: 128,
  likes: 12,
  isLiked: false,
  isFavorited: true,
  versions: [
    {
      id: '1-3',
      version: 'v1.3',
      uploadedAt: '2024-12-28T10:30:00Z',
      uploadedBy: '张三',
      size: 2048000,
      changes: '更新了用户界面设计要求',
      url: '/api/files/1/versions/3'
    },
    {
      id: '1-2',
      version: 'v1.2',
      uploadedAt: '2024-12-27T14:20:00Z',
      uploadedBy: '李四',
      size: 1998000,
      changes: '添加了性能要求章节',
      url: '/api/files/1/versions/2'
    },
    {
      id: '1-1',
      version: 'v1.1',
      uploadedAt: '2024-12-26T09:15:00Z',
      uploadedBy: '张三',
      size: 1945000,
      changes: '初始版本',
      url: '/api/files/1/versions/1'
    }
  ],
  comments: [
    {
      id: '1',
      content: '这个需求文档写得很详细，对开发很有帮助。',
      author: '王五',
      createdAt: '2024-12-28T11:00:00Z',
      replies: [
        {
          id: '1-1',
          content: '同意，特别是用户界面部分的描述很清楚。',
          author: '赵六',
          createdAt: '2024-12-28T11:30:00Z',
          replies: []
        }
      ]
    },
    {
      id: '2',
      content: '建议在下个版本中添加更多的用例图。',
      author: '孙七',
      createdAt: '2024-12-28T12:00:00Z',
      replies: []
    }
  ]
}

export default function FileDetailPage() {
  const params = useParams()
  const router = useRouter()
  const [file, setFile] = useState<FileDetail>(mockFileDetail)
  const [showPreviewModal, setShowPreviewModal] = useState(false)
  const [showShareModal, setShowShareModal] = useState(false)
  const [activeTab, setActiveTab] = useState<'info' | 'versions' | 'comments'>('info')
  const [newComment, setNewComment] = useState('')
  const [replyTo, setReplyTo] = useState<string | null>(null)
  const [replyContent, setReplyContent] = useState('')

  const getFileIcon = (type: string) => {
    if (type.startsWith('image/')) {
      return <PhotoIcon className="h-12 w-12 text-blue-500" />
    } else if (type === 'application/pdf') {
      return <DocumentIcon className="h-12 w-12 text-red-500" />
    } else if (type.includes('word')) {
      return <DocumentIcon className="h-12 w-12 text-blue-600" />
    } else if (type.includes('excel') || type.includes('sheet')) {
      return <DocumentIcon className="h-12 w-12 text-green-600" />
    } else if (type.startsWith('video/')) {
      return <VideoCameraIcon className="h-12 w-12 text-purple-500" />
    } else if (type.startsWith('audio/')) {
      return <SpeakerWaveIcon className="h-12 w-12 text-orange-500" />
    }
    return <DocumentIcon className="h-12 w-12 text-gray-500" />
  }

  const getStageColor = (stage: string) => {
    const colors = {
      '售前': 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      '业务调研': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      '数据理解': 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
      '数据探索': 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
      '工程开发': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
      '实施部署': 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
    }
    return colors[stage as keyof typeof colors] || 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200'
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const handleLike = () => {
    setFile(prev => ({
      ...prev,
      isLiked: !prev.isLiked,
      likes: prev.isLiked ? prev.likes - 1 : prev.likes + 1
    }))
  }

  const handleFavorite = () => {
    setFile(prev => ({
      ...prev,
      isFavorited: !prev.isFavorited
    }))
  }

  const handleAddComment = () => {
    if (!newComment.trim()) return

    const comment: FileComment = {
      id: Date.now().toString(),
      content: newComment,
      author: '当前用户',
      createdAt: new Date().toISOString(),
      replies: []
    }

    setFile(prev => ({
      ...prev,
      comments: [comment, ...prev.comments]
    }))
    setNewComment('')
  }

  const handleReply = (commentId: string) => {
    if (!replyContent.trim()) return

    const reply: FileComment = {
      id: Date.now().toString(),
      content: replyContent,
      author: '当前用户',
      createdAt: new Date().toISOString(),
      replies: []
    }

    setFile(prev => ({
      ...prev,
      comments: prev.comments.map(comment => 
        comment.id === commentId 
          ? { ...comment, replies: [...comment.replies, reply] }
          : comment
      )
    }))
    setReplyContent('')
    setReplyTo(null)
  }

  const renderInfoTab = () => (
    <div className="space-y-6">
      {/* 基本信息 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          基本信息
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              文件名
            </label>
            <p className="text-sm text-gray-900 dark:text-white">{file.name}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              文件大小
            </label>
            <p className="text-sm text-gray-900 dark:text-white">{formatFileSize(file.size)}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              上传者
            </label>
            <p className="text-sm text-gray-900 dark:text-white">{file.uploadedBy}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              上传时间
            </label>
            <p className="text-sm text-gray-900 dark:text-white">{formatDate(file.uploadedAt)}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              项目阶段
            </label>
            <span className={cn(
              'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
              getStageColor(file.stage)
            )}>
              {file.stage}
            </span>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              文件类型
            </label>
            <p className="text-sm text-gray-900 dark:text-white">{file.type}</p>
          </div>
        </div>
      </div>

      {/* 描述 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          文件描述
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
          {file.description}
        </p>
      </div>

      {/* 标签 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          标签
        </h3>
        <div className="flex flex-wrap gap-2">
          {file.tags.map((tag, index) => (
            <span
              key={index}
              className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200"
            >
              <TagIcon className="h-4 w-4 mr-1" />
              {tag}
            </span>
          ))}
        </div>
      </div>

      {/* 统计信息 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          统计信息
        </h3>
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {file.views}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              查看次数
            </div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {file.downloads}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              下载次数
            </div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {file.likes}
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">
              点赞数
            </div>
          </div>
        </div>
      </div>
    </div>
  )

  const renderVersionsTab = () => (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white">
          版本历史
        </h3>
      </div>
      <div className="divide-y divide-gray-200 dark:divide-gray-700">
        {file.versions.map((version, index) => (
          <div key={version.id} className="px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium',
                  index === 0 
                    ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                    : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
                )}>
                  {version.version}
                </div>
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {version.changes}
                    </span>
                    {index === 0 && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                        当前版本
                      </span>
                    )}
                  </div>
                  <div className="flex items-center space-x-4 text-xs text-gray-500 dark:text-gray-400 mt-1">
                    <span className="flex items-center">
                      <UserIcon className="h-3 w-3 mr-1" />
                      {version.uploadedBy}
                    </span>
                    <span className="flex items-center">
                      <ClockIcon className="h-3 w-3 mr-1" />
                      {formatDate(version.uploadedAt)}
                    </span>
                    <span>{formatFileSize(version.size)}</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <Button variant="outline" size="sm">
                  <ArrowDownTrayIcon className="h-4 w-4 mr-1" />
                  下载
                </Button>
                {index !== 0 && (
                  <Button variant="outline" size="sm">
                    恢复
                  </Button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )

  const renderCommentsTab = () => (
    <div className="space-y-6">
      {/* 添加评论 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          添加评论
        </h3>
        <div className="space-y-4">
          <textarea
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            placeholder="写下你的评论..."
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
            rows={3}
          />
          <div className="flex justify-end">
            <Button onClick={handleAddComment} disabled={!newComment.trim()}>
              发表评论
            </Button>
          </div>
        </div>
      </div>

      {/* 评论列表 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            评论 ({file.comments.length})
          </h3>
        </div>
        <div className="divide-y divide-gray-200 dark:divide-gray-700">
          {file.comments.map((comment) => (
            <div key={comment.id} className="px-6 py-4">
              <div className="flex items-start space-x-3">
                <div className="w-8 h-8 bg-gray-300 dark:bg-gray-600 rounded-full flex items-center justify-center">
                  <UserIcon className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-1">
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {comment.author}
                    </span>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {formatDate(comment.createdAt)}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                    {comment.content}
                  </p>
                  <button
                    onClick={() => setReplyTo(comment.id)}
                    className="text-xs text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                  >
                    回复
                  </button>
                  
                  {/* 回复表单 */}
                  {replyTo === comment.id && (
                    <div className="mt-3 space-y-2">
                      <textarea
                        value={replyContent}
                        onChange={(e) => setReplyContent(e.target.value)}
                        placeholder="写下你的回复..."
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                        rows={2}
                      />
                      <div className="flex justify-end space-x-2">
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => {
                            setReplyTo(null)
                            setReplyContent('')
                          }}
                        >
                          取消
                        </Button>
                        <Button 
                          size="sm"
                          onClick={() => handleReply(comment.id)}
                          disabled={!replyContent.trim()}
                        >
                          回复
                        </Button>
                      </div>
                    </div>
                  )}
                  
                  {/* 回复列表 */}
                  {comment.replies.length > 0 && (
                    <div className="mt-3 space-y-3">
                      {comment.replies.map((reply) => (
                        <div key={reply.id} className="flex items-start space-x-3 pl-4 border-l-2 border-gray-200 dark:border-gray-600">
                          <div className="w-6 h-6 bg-gray-300 dark:bg-gray-600 rounded-full flex items-center justify-center">
                            <UserIcon className="h-3 w-3 text-gray-600 dark:text-gray-400" />
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center space-x-2 mb-1">
                              <span className="text-sm font-medium text-gray-900 dark:text-white">
                                {reply.author}
                              </span>
                              <span className="text-xs text-gray-500 dark:text-gray-400">
                                {formatDate(reply.createdAt)}
                              </span>
                            </div>
                            <p className="text-sm text-gray-600 dark:text-gray-400">
                              {reply.content}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      {/* 返回按钮 */}
      <div className="flex items-center">
        <Button
          variant="ghost"
          onClick={() => router.back()}
          className="flex items-center space-x-2"
        >
          <ArrowLeftIcon className="h-4 w-4" />
          <span>返回</span>
        </Button>
      </div>

      {/* 文件头部 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-4">
            <div className="flex-shrink-0">
              {getFileIcon(file.type)}
            </div>
            <div className="flex-1 min-w-0">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                {file.name}
              </h1>
              <div className="flex items-center space-x-4 text-sm text-gray-500 dark:text-gray-400">
                <span className="flex items-center">
                  <UserIcon className="h-4 w-4 mr-1" />
                  {file.uploadedBy}
                </span>
                <span className="flex items-center">
                  <ClockIcon className="h-4 w-4 mr-1" />
                  {formatDate(file.uploadedAt)}
                </span>
                <span>{formatFileSize(file.size)}</span>
                <span className="flex items-center">
                  <EyeIcon className="h-4 w-4 mr-1" />
                  {file.views} 次查看
                </span>
              </div>
            </div>
          </div>
          
          {/* 操作按钮 */}
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleLike}
              className="flex items-center space-x-1"
            >
              {file.isLiked ? (
                <HeartIconSolid className="h-4 w-4 text-red-500" />
              ) : (
                <HeartIcon className="h-4 w-4" />
              )}
              <span>{file.likes}</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleFavorite}
              className="flex items-center space-x-1"
            >
              {file.isFavorited ? (
                <StarIconSolid className="h-4 w-4 text-yellow-500" />
              ) : (
                <StarIcon className="h-4 w-4" />
              )}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowPreviewModal(true)}
              className="flex items-center space-x-1"
            >
              <EyeIcon className="h-4 w-4" />
              <span>预览</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowShareModal(true)}
              className="flex items-center space-x-1"
            >
              <ShareIcon className="h-4 w-4" />
              <span>分享</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="flex items-center space-x-1"
            >
              <ArrowDownTrayIcon className="h-4 w-4" />
              <span>下载</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="flex items-center space-x-1"
            >
              <PencilIcon className="h-4 w-4" />
              <span>编辑</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="flex items-center space-x-1 text-red-600 hover:text-red-700"
            >
              <TrashIcon className="h-4 w-4" />
              <span>删除</span>
            </Button>
          </div>
        </div>
      </div>

      {/* 标签页 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="flex space-x-8 px-6">
            <button
              onClick={() => setActiveTab('info')}
              className={cn(
                'py-4 px-1 border-b-2 font-medium text-sm',
                activeTab === 'info'
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
              )}
            >
              基本信息
            </button>
            <button
              onClick={() => setActiveTab('versions')}
              className={cn(
                'py-4 px-1 border-b-2 font-medium text-sm',
                activeTab === 'versions'
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
              )}
            >
              版本历史 ({file.versions.length})
            </button>
            <button
              onClick={() => setActiveTab('comments')}
              className={cn(
                'py-4 px-1 border-b-2 font-medium text-sm',
                activeTab === 'comments'
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
              )}
            >
              评论 ({file.comments.length})
            </button>
          </nav>
        </div>
        
        <div className="p-6">
          {activeTab === 'info' && renderInfoTab()}
          {activeTab === 'versions' && renderVersionsTab()}
          {activeTab === 'comments' && renderCommentsTab()}
        </div>
      </div>

      {/* 预览模态框 */}
      <Modal
        isOpen={showPreviewModal}
        onClose={() => setShowPreviewModal(false)}
        size="xl"
      >
        <FilePreview
          file={null}
          fileUrl={file.url}
          onClose={() => setShowPreviewModal(false)}
        />
      </Modal>

      {/* 分享模态框 */}
      <Modal
        isOpen={showShareModal}
        onClose={() => setShowShareModal(false)}
        title="分享文件"
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              分享链接
            </label>
            <div className="flex">
              <Input
                type="text"
                value={`${window.location.origin}/files/${file.id}`}
                readOnly
                className="flex-1"
              />
              <Button
                variant="outline"
                className="ml-2"
                onClick={() => {
                  navigator.clipboard.writeText(`${window.location.origin}/files/${file.id}`)
                }}
              >
                复制
              </Button>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              访问权限
            </label>
            <select className="w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white">
              <option>仅团队成员可访问</option>
              <option>获得链接的任何人都可查看</option>
              <option>公开访问</option>
            </select>
          </div>
        </div>
      </Modal>
    </div>
  )
} 