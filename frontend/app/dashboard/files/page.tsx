'use client'

import React, { useState, useEffect } from 'react'
import { 
  MagnifyingGlassIcon, 
  FunnelIcon, 
  Squares2X2Icon, 
  ListBulletIcon,
  CloudArrowUpIcon,
  DocumentIcon,
  PhotoIcon,
  VideoCameraIcon,
  SpeakerWaveIcon,
  EllipsisVerticalIcon,
  EyeIcon,
  ArrowDownTrayIcon,
  TrashIcon,
  PencilIcon,
  ShareIcon,
  TagIcon
} from '@heroicons/react/24/outline'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import Modal from '@/components/ui/Modal'
import { FileUpload } from '@/components/features/FileUpload'
import { FilePreview } from '@/components/features/FilePreview'
import TagManager from '@/components/features/TagManager'
import { formatFileSize, cn } from '@/lib/utils'
import { PROJECT_STAGES, getStageById, getStageColor as getProjectStageColor, getStageIcon } from '@/lib/constants/project-stages'
import { PREDEFINED_TAGS, getTagById, getTagColor } from '@/lib/constants/file-tags'

interface FileItem {
  id: string
  name: string
  type: string
  size: number
  uploadedAt: string
  uploadedBy: string
  stage: string
  tags: string[]
  url?: string
  thumbnail?: string
}

// 模拟数据
const mockFiles: FileItem[] = [
  {
    id: '1',
    name: '项目需求文档.pdf',
    type: 'application/pdf',
    size: 2048000,
    uploadedAt: '2024-12-28T10:30:00Z',
    uploadedBy: '张三',
    stage: '售前',
    tags: ['需求', '重要']
  },
  {
    id: '2',
    name: '用户调研报告.docx',
    type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    size: 1536000,
    uploadedAt: '2024-12-27T14:20:00Z',
    uploadedBy: '李四',
    stage: '业务调研',
    tags: ['调研', '用户']
  },
  {
    id: '3',
    name: '数据分析图表.png',
    type: 'image/png',
    size: 512000,
    uploadedAt: '2024-12-26T09:15:00Z',
    uploadedBy: '王五',
    stage: '数据理解',
    tags: ['图表', '分析']
  }
]

const stages = ['全部', ...PROJECT_STAGES.map(stage => stage.name)]
const fileTypes = ['全部', 'PDF', 'Word', 'Excel', '图片', '视频', '音频', '其他']

export default function FilesPage() {
  const [files, setFiles] = useState<FileItem[]>(mockFiles)
  const [filteredFiles, setFilteredFiles] = useState<FileItem[]>(mockFiles)
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedStage, setSelectedStage] = useState('全部')
  const [selectedType, setSelectedType] = useState('全部')
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [showPreviewModal, setShowPreviewModal] = useState(false)
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null)
  const [showFilters, setShowFilters] = useState(false)
  const [showTagManager, setShowTagManager] = useState(false)
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  const [fileToTag, setFileToTag] = useState<FileItem | null>(null)

  // 过滤文件
  useEffect(() => {
    let filtered = files

    // 搜索过滤
    if (searchQuery) {
      filtered = filtered.filter(file => 
        file.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        file.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
      )
    }

    // 阶段过滤
    if (selectedStage !== '全部') {
      filtered = filtered.filter(file => file.stage === selectedStage)
    }

    // 类型过滤
    if (selectedType !== '全部') {
      filtered = filtered.filter(file => {
        switch (selectedType) {
          case 'PDF':
            return file.type === 'application/pdf'
          case 'Word':
            return file.type.includes('word')
          case 'Excel':
            return file.type.includes('excel') || file.type.includes('sheet')
          case '图片':
            return file.type.startsWith('image/')
          case '视频':
            return file.type.startsWith('video/')
          case '音频':
            return file.type.startsWith('audio/')
          default:
            return true
        }
      })
    }

    setFilteredFiles(filtered)
  }, [files, searchQuery, selectedStage, selectedType])

  const getFileIcon = (type: string) => {
    if (type.startsWith('image/')) {
      return <PhotoIcon className="h-8 w-8 text-blue-500" />
    } else if (type === 'application/pdf') {
      return <DocumentIcon className="h-8 w-8 text-red-500" />
    } else if (type.includes('word')) {
      return <DocumentIcon className="h-8 w-8 text-blue-600" />
    } else if (type.includes('excel') || type.includes('sheet')) {
      return <DocumentIcon className="h-8 w-8 text-green-600" />
    } else if (type.startsWith('video/')) {
      return <VideoCameraIcon className="h-8 w-8 text-purple-500" />
    } else if (type.startsWith('audio/')) {
      return <SpeakerWaveIcon className="h-8 w-8 text-orange-500" />
    }
    return <DocumentIcon className="h-8 w-8 text-gray-500" />
  }

  const getStageColorClass = (stage: string) => {
    const stageData = PROJECT_STAGES.find(s => s.name === stage)
    if (stageData) {
      // 将背景色转换为对应的文本颜色类
      const colorMap = {
        'bg-blue-500': 'bg-blue-100 text-blue-800',
        'bg-green-500': 'bg-green-100 text-green-800',
        'bg-purple-500': 'bg-purple-100 text-purple-800',
        'bg-orange-500': 'bg-orange-100 text-orange-800',
        'bg-red-500': 'bg-red-100 text-red-800',
        'bg-indigo-500': 'bg-indigo-100 text-indigo-800',
      }
      return colorMap[stageData.color as keyof typeof colorMap] || 'bg-gray-100 text-gray-800'
    }
    return 'bg-gray-100 text-gray-800'
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

  const handleFileUpload = (uploadedFiles: File[]) => {
    const newFiles: FileItem[] = uploadedFiles.map(file => ({
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      name: file.name,
      type: file.type,
      size: file.size,
      uploadedAt: new Date().toISOString(),
      uploadedBy: '当前用户',
      stage: '售前',
      tags: [],
      url: URL.createObjectURL(file)
    }))
    
    setFiles(prev => [...newFiles, ...prev])
    setShowUploadModal(false)
  }

  const handlePreview = (file: FileItem) => {
    setSelectedFile(file)
    setShowPreviewModal(true)
  }

  const handleDelete = (fileId: string) => {
    setFiles(prev => prev.filter(f => f.id !== fileId))
  }

  const handleTagFile = (file: FileItem) => {
    setFileToTag(file)
    setSelectedTags(file.tags)
    setShowTagManager(true)
  }

  const handleTagsUpdate = (tags: string[]) => {
    if (fileToTag) {
      setFiles(prev => prev.map(f => 
        f.id === fileToTag.id 
          ? { ...f, tags }
          : f
      ))
    }
    setShowTagManager(false)
    setFileToTag(null)
    setSelectedTags([])
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            文件管理
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            管理项目文件，支持多种格式预览和组织
          </p>
        </div>
        <Button onClick={() => setShowUploadModal(true)}>
          <CloudArrowUpIcon className="h-5 w-5 mr-2" />
          上传文件
        </Button>
      </div>

      {/* 工具栏 */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0">
        {/* 搜索和筛选 */}
        <div className="flex items-center space-x-4">
          <div className="relative">
            <MagnifyingGlassIcon className="h-5 w-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <Input
              type="text"
              placeholder="搜索文件..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 w-64"
            />
          </div>
          <Button
            variant="outline"
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center space-x-2"
          >
            <FunnelIcon className="h-4 w-4" />
            <span>筛选</span>
          </Button>
        </div>

        {/* 视图切换 */}
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setViewMode('grid')}
            className={cn(
              'p-2 rounded-md',
              viewMode === 'grid'
                ? 'bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-400'
                : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'
            )}
          >
            <Squares2X2Icon className="h-5 w-5" />
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={cn(
              'p-2 rounded-md',
              viewMode === 'list'
                ? 'bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-400'
                : 'text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'
            )}
          >
            <ListBulletIcon className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* 筛选器 */}
      {showFilters && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                项目阶段
              </label>
              <select
                value={selectedStage}
                onChange={(e) => setSelectedStage(e.target.value)}
                className="w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                {stages.map(stage => (
                  <option key={stage} value={stage}>{stage}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                文件类型
              </label>
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                {fileTypes.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}

      {/* 文件统计 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-500 dark:text-gray-400">
              共 {filteredFiles.length} 个文件
            </span>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              总大小 {formatFileSize(filteredFiles.reduce((sum, file) => sum + file.size, 0))}
            </span>
          </div>
          {(searchQuery || selectedStage !== '全部' || selectedType !== '全部') && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setSearchQuery('')
                setSelectedStage('全部')
                setSelectedType('全部')
              }}
            >
              清除筛选
            </Button>
          )}
        </div>
      </div>

      {/* 文件网格视图 */}
      {viewMode === 'grid' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filteredFiles.map((file) => (
            <div
              key={file.id}
              className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow duration-200 group"
            >
              {/* 文件预览 */}
              <div className="relative aspect-[4/3] bg-gray-50 dark:bg-gray-700 rounded-t-lg overflow-hidden">
                <div className="flex items-center justify-center h-full">
                  {getFileIcon(file.type)}
                </div>
                
                {/* 操作按钮 */}
                <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <div className="flex space-x-1">
                    <button
                      onClick={() => handlePreview(file)}
                      className="p-1.5 bg-white dark:bg-gray-800 rounded-full shadow-sm hover:shadow-md"
                    >
                      <EyeIcon className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                    </button>
                    <button 
                      onClick={() => handleTagFile(file)}
                      className="p-1.5 bg-white dark:bg-gray-800 rounded-full shadow-sm hover:shadow-md"
                    >
                      <TagIcon className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                    </button>
                  </div>
                </div>
              </div>

              {/* 文件信息 */}
              <div className="p-4">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="text-sm font-medium text-gray-900 dark:text-white truncate flex-1">
                    {file.name}
                  </h3>
                </div>
                
                <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-2">
                  <span>{formatFileSize(file.size)}</span>
                  <span>{formatDate(file.uploadedAt)}</span>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className={cn(
                    'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
                    getStageColorClass(file.stage)
                  )}>
                    {file.stage}
                  </span>
                  
                  {file.tags.length > 0 && (
                    <div className="flex items-center space-x-1">
                      <TagIcon className="h-3 w-3 text-gray-400" />
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {file.tags[0]}
                        {file.tags.length > 1 && ` +${file.tags.length - 1}`}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 文件列表视图 */}
      {viewMode === 'list' && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    文件名
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    大小
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    阶段
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    上传者
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    上传时间
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {filteredFiles.map((file) => (
                  <tr key={file.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 mr-3">
                          {getFileIcon(file.type)}
                        </div>
                        <div>
                          <div className="text-sm font-medium text-gray-900 dark:text-white">
                            {file.name}
                          </div>
                          {file.tags.length > 0 && (
                            <div className="flex items-center space-x-1 mt-1">
                              {file.tags.map((tag, index) => (
                                <span
                                  key={index}
                                  className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200"
                                >
                                  {tag}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {formatFileSize(file.size)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={cn(
                        'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
                        getStageColorClass(file.stage)
                      )}>
                        {file.stage}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {file.uploadedBy}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {formatDate(file.uploadedAt)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => handlePreview(file)}
                          className="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300"
                        >
                          <EyeIcon className="h-4 w-4" />
                        </button>
                        <button className="text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-300">
                          <ArrowDownTrayIcon className="h-4 w-4" />
                        </button>
                        <button className="text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-300">
                          <PencilIcon className="h-4 w-4" />
                        </button>
                        <button className="text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-300">
                          <ShareIcon className="h-4 w-4" />
                        </button>
                        <button 
                          onClick={() => handleTagFile(file)}
                          className="text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-300"
                        >
                          <TagIcon className="h-4 w-4" />
                        </button>
                        <button 
                          onClick={() => handleDelete(file.id)}
                          className="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300"
                        >
                          <TrashIcon className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 空状态 */}
      {filteredFiles.length === 0 && (
        <div className="text-center py-12">
          <DocumentIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            {searchQuery || selectedStage !== '全部' || selectedType !== '全部' 
              ? '没有找到匹配的文件' 
              : '暂无文件'
            }
          </h3>
          <p className="text-gray-500 dark:text-gray-400 mb-4">
            {searchQuery || selectedStage !== '全部' || selectedType !== '全部' 
              ? '尝试调整筛选条件或搜索关键词' 
              : '开始上传您的第一个文件'
            }
          </p>
          <Button onClick={() => setShowUploadModal(true)}>
            <CloudArrowUpIcon className="h-5 w-5 mr-2" />
            上传文件
          </Button>
        </div>
      )}

      {/* 上传模态框 */}
      <Modal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        title="上传文件"
        size="lg"
      >
        <FileUpload
          onUpload={handleFileUpload}
          multiple={true}
          maxFiles={10}
          maxSize={50 * 1024 * 1024} // 50MB
        />
      </Modal>

      {/* 预览模态框 */}
      <Modal
        isOpen={showPreviewModal}
        onClose={() => setShowPreviewModal(false)}
        size="xl"
      >
        {selectedFile && (
          <FilePreview
            file={null}
            fileUrl={selectedFile.url}
            onClose={() => setShowPreviewModal(false)}
          />
        )}
      </Modal>

      {/* 标签管理器 */}
      {showTagManager && (
        <TagManager
          selectedTags={selectedTags}
          onTagsChange={handleTagsUpdate}
          onClose={() => setShowTagManager(false)}
        />
      )}
    </div>
  )
} 