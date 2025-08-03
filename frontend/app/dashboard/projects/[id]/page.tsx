'use client'

import React, { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { 
  ArrowLeftIcon,
  CloudArrowUpIcon,
  DocumentIcon,
  PhotoIcon,
  VideoCameraIcon,
  SpeakerWaveIcon,
  ArrowDownTrayIcon,
  TrashIcon,
  PencilIcon,
  TagIcon,
  DocumentTextIcon,
  TableCellsIcon,
  PresentationChartBarIcon,
  FunnelIcon,
  MagnifyingGlassIcon,
  Squares2X2Icon,
  ListBulletIcon,
  UserGroupIcon,
  CalendarIcon,
  FolderIcon,
  ArchiveBoxIcon,
  UserIcon,
  CpuChipIcon,
  ChatBubbleLeftRightIcon,
  HomeIcon
} from '@heroicons/react/24/outline'
import Link from 'next/link'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import Modal from '@/components/ui/Modal'
import { FileUpload } from '@/components/features/FileUpload'
import TagManager from '@/components/features/TagManager'
import { formatFileSize, cn } from '@/lib/utils'
import { PROJECT_STAGES } from '@/lib/constants/project-stages'
import { projectSync } from '@/lib/services/project-sync'

interface Project {
  id: string
  name: string
  description: string
  stage: string
  createdAt: string
  updatedAt: string
  memberCount: number
  status: 'active' | 'archived' | 'completed'
  color: string
}

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
  source: 'user' | 'ai' | 'system' | 'api' // 文件来源：用户上传、AI生成、系统自动、API
}

// 移除所有模拟数据
// const mockProjects: Record<string, Project> = {
//   '1': {
//     id: '1',
//     name: 'AI智能客服系统',
//     description: '基于大语言模型的智能客服解决方案，提升客户服务效率',
//     stage: '工程开发',
//     createdAt: '2024-01-15T10:00:00Z',
//     updatedAt: '2024-12-28T15:30:00Z',
//     memberCount: 8,
//     status: 'active',
//     color: 'bg-blue-500'
//   },
//   '2': {
//     id: '2',
//     name: '数据分析平台',
//     description: '企业级数据分析和可视化平台，支持多数据源集成',
//     stage: '数据理解',
//     createdAt: '2024-02-01T09:00:00Z',
//     updatedAt: '2024-12-27T11:20:00Z',
//     memberCount: 6,
//     status: 'active',
//     color: 'bg-green-500'
//   },
//   '3': {
//     id: '3',
//     name: '推荐系统优化',
//     description: '电商推荐算法优化项目，提升用户体验和转化率',
//     stage: '实施部署',
//     createdAt: '2024-03-10T14:00:00Z',
//     updatedAt: '2024-12-26T16:45:00Z',
//     memberCount: 5,
//     status: 'completed',
//     color: 'bg-purple-500'
//   },
//   '4': {
//     id: '4',
//     name: '图像识别模型',
//     description: '医疗影像AI诊断辅助系统，提高诊断准确率',
//     stage: '业务调研',
//     createdAt: '2024-04-05T11:00:00Z',
//     updatedAt: '2024-12-25T09:15:00Z',
//     memberCount: 4,
//     status: 'active',
//     color: 'bg-orange-500'
//   }
// }

// 移除所有模拟数据
// const mockProjectFiles: Record<string, FileItem[]> = {
//   '1': [
//     {
//       id: '1',
//       name: '项目需求文档.pdf',
//       type: 'application/pdf',
//       size: 2048000,
//       uploadedAt: '2024-12-28T10:30:00Z',
//       uploadedBy: '张三',
//       stage: '售前',
//       tags: ['需求', '重要'],
//       source: 'user'
//     },
//     {
//       id: '2',
//       name: '用户调研报告.docx',
//       type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
//       size: 1536000,
//       uploadedAt: '2024-12-27T14:20:00Z',
//       uploadedBy: '李四',
//       stage: '业务调研',
//       tags: ['调研', '用户'],
//       source: 'user'
//     },
//     {
//       id: '3',
//       name: 'AI生成的数据分析报告.pdf',
//       type: 'application/pdf',
//       size: 512000,
//       uploadedAt: '2024-12-26T09:15:00Z',
//       uploadedBy: 'Claude-3.5',
//       stage: '数据理解',
//       tags: ['AI生成', '分析'],
//       source: 'ai'
//     },
//     {
//       id: '4',
//       name: '系统架构设计.pptx',
//       type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
//       size: 3072000,
//       uploadedAt: '2024-12-25T16:45:00Z',
//       uploadedBy: '赵六',
//       stage: '工程开发',
//       tags: ['架构', '设计'],
//       source: 'user'
//     },
//     {
//       id: '5',
//       name: 'AI优化建议文档.docx',
//       type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
//       size: 1024000,
//       uploadedAt: '2024-12-24T11:30:00Z',
//       uploadedBy: 'GPT-4',
//       stage: '数据探索',
//       tags: ['AI生成', '优化'],
//       source: 'ai'
//     },
//     {
//       id: '6',
//       name: '测试数据集.xlsx',
//       type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
//       size: 5120000,
//       uploadedAt: '2024-12-23T11:30:00Z',
//       uploadedBy: '钱七',
//       stage: '数据探索',
//       tags: ['数据', '测试'],
//       source: 'user'
//     }
//   ],
//   '2': [
//     {
//       id: '6',
//       name: '数据源接入方案.pdf',
//       type: 'application/pdf',
//       size: 1800000,
//       uploadedAt: '2024-12-27T14:20:00Z',
//       uploadedBy: '李四',
//       stage: '数据理解',
//       tags: ['数据源', '方案'],
//       source: 'user'
//     },
//     {
//       id: '7',
//       name: 'AI生成的可视化建议.pdf',
//       type: 'application/pdf',
//       size: 3200000,
//       uploadedAt: '2024-12-26T10:15:00Z',
//       uploadedBy: 'Gemini-Pro',
//       stage: '数据理解',
//       tags: ['AI生成', '可视化'],
//       source: 'ai'
//     },
//     {
//       id: '8',
//       name: '数据字典.xlsx',
//       type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
//       size: 890000,
//       uploadedAt: '2024-12-25T16:30:00Z',
//       uploadedBy: '赵六',
//       stage: '数据理解',
//       tags: ['数据字典', '文档'],
//       source: 'user'
//     }
//   ],
//   '3': [
//     {
//       id: '9',
//       name: '推荐算法优化报告.pdf',
//       type: 'application/pdf',
//       size: 2400000,
//       uploadedAt: '2024-12-26T11:45:00Z',
//       uploadedBy: '钱七',
//       stage: '实施部署',
//       tags: ['算法', '优化'],
//       source: 'user'
//     },
//     {
//       id: '10',
//       name: 'AI生成的A/B测试分析.pdf',
//       type: 'application/pdf',
//       size: 1600000,
//       uploadedAt: '2024-12-25T09:20:00Z',
//       uploadedBy: 'Claude-3.5',
//       stage: '实施部署',
//       tags: ['AI生成', '测试'],
//       source: 'ai'
//     }
//   ],
//   '4': [
//     {
//       id: '11',
//       name: '医疗影像标注指南.pdf',
//       type: 'application/pdf',
//       size: 3100000,
//       uploadedAt: '2024-12-25T13:30:00Z',
//       uploadedBy: '周九',
//       stage: '业务调研',
//       tags: ['标注', '指南'],
//       source: 'user'
//     },
//     {
//       id: '12',
//       name: 'AI诊断模型建议.pdf',
//       type: 'application/pdf',
//       size: 2800000,
//       uploadedAt: '2024-12-24T16:45:00Z',
//       uploadedBy: 'GPT-4',
//       stage: '业务调研',
//       tags: ['AI生成', '模型'],
//       source: 'ai'
//     }
//   ]
// }

const stages = ['全部', ...PROJECT_STAGES.map(stage => stage.name)]
const fileTypes = ['全部', 'PDF', 'Word', 'Excel', 'PPT', '图片', '视频', '音频', '其他']

// 在组件外部添加一个函数来处理项目数据持久化存储
const getStoredProjects = (): Record<string, Project> => {
  if (typeof window !== 'undefined') {
    try {
      const stored = localStorage.getItem('ai-projects')
      if (stored) {
        const projectArray = JSON.parse(stored)
        // 将数组转换为对象格式
        const projectMap: Record<string, Project> = {}
        projectArray.forEach((project: Project) => {
          projectMap[project.id] = project
        })
        return projectMap
      }
    } catch (error) {
      console.error('读取项目数据失败:', error)
    }
  }
  return {} // 移除模拟数据，返回空对象
}

// 从后端API获取文件列表
const fetchProjectFiles = async (projectId: string): Promise<FileItem[]> => {
  try {
    const response = await fetch(`/api/v1/files?project_id=${projectId}`)
    if (response.ok) {
      const files = await response.json()
      return files.map((file: any) => ({
        id: file.id,
        name: file.original_name,
        type: file.file_type,
        size: file.file_size,
        uploadedAt: file.created_at,
        uploadedBy: '当前用户', // 可以从用户信息获取
        stage: file.stage,
        tags: [], // 可以从file.tags获取
        url: `/api/v1/files/${file.id}/download`, // 下载链接
        source: 'api' as const
      }))
    } else {
      console.error('获取文件列表失败:', response.statusText)
      return []
    }
  } catch (error) {
    console.error('获取文件列表出错:', error)
    return []
  }
}

const getStoredFiles = (projectId: string): FileItem[] => {
  // 保留作为后备，但优先使用API数据
  if (typeof window !== 'undefined') {
    const stored = localStorage.getItem(`project_${projectId}_files`)
    if (stored) {
      try {
        return JSON.parse(stored)
      } catch (error) {
        console.error('解析存储的文件数据失败:', error)
      }
    }
  }
  return [] // 移除模拟数据，返回空数组
}

const saveFilesToStorage = (projectId: string, files: FileItem[]) => {
  if (typeof window !== 'undefined') {
    localStorage.setItem(`project_${projectId}_files`, JSON.stringify(files))
  }
}

// 添加API调用函数
const fetchProjectInfo = async (projectId: string): Promise<Project | null> => {
  try {
    // 这里应该调用真实的项目API，暂时返回基础信息
    // 在实际应用中，应该有 /api/v1/projects/{id} 端点
    const mockProject: Project = {
      id: projectId,
      name: `项目 ${projectId}`,
      description: '从API获取的项目描述',
      stage: '工程开发',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      memberCount: 1,
      status: 'active',
      color: 'bg-blue-500'
    }
    return mockProject
  } catch (error) {
    console.error('获取项目信息失败:', error)
    return null
  }
}

const fetchProjectStats = async (projectId: string) => {
  try {
    const response = await fetch(`/api/v1/files?project_id=${projectId}`)
    if (response.ok) {
      const files = await response.json()
      return {
        fileCount: files.length,
        totalSize: files.reduce((sum: number, file: any) => sum + (file.file_size || 0), 0)
      }
    }
    return { fileCount: 0, totalSize: 0 }
  } catch (error) {
    console.error('获取项目统计失败:', error)
    return { fileCount: 0, totalSize: 0 }
  }
}

export default function ProjectDetailPage() {
  const params = useParams()
  const projectId = params.id as string

  // 初始化项目数据
  const [storedProjects, setStoredProjects] = useState<Record<string, Project>>(getStoredProjects())
  const currentProject = storedProjects[projectId] || null
  
  // 初始时使用原始数据，避免SSR水合错误
  const initialFiles = getStoredFiles(projectId)

  const [project, setProject] = useState<Project | null>(currentProject)
  const [files, setFiles] = useState<FileItem[]>(initialFiles)
  const [filteredFiles, setFilteredFiles] = useState<FileItem[]>(initialFiles)
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedStage, setSelectedStage] = useState('全部')
  const [selectedType, setSelectedType] = useState('全部')
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [showTagManager, setShowTagManager] = useState(false)
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  const [fileToTag, setFileToTag] = useState<FileItem | null>(null)
  const [isHydrated, setIsHydrated] = useState(false)
  
  // 编辑文件状态
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingFile, setEditingFile] = useState<FileItem | null>(null)
  const [editName, setEditName] = useState('')
  const [editStage, setEditStage] = useState('')

  // 项目统计状态
  const [projectStats, setProjectStats] = useState({ fileCount: 0, totalSize: 0 })
  const [isLoading, setIsLoading] = useState(true)

  // 客户端水合完成后再加载数据
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true)
      
      // 从同步服务获取项目信息
      const projectInfo = projectSync.getProjectById(projectId)
      if (projectInfo) {
        setProject(projectInfo)
      }
      
      // 加载文件数据和统计信息
      try {
        const [apiFiles, stats] = await Promise.all([
          fetchProjectFiles(projectId),
          fetchProjectStats(projectId)
        ])
        
        setFiles(apiFiles)
        setFilteredFiles(apiFiles)
        setProjectStats(stats)
        
        // 同步更新项目统计到同步服务
        await projectSync.updateProjectFileStats(projectId)
        
      } catch (error) {
        console.error('加载数据失败:', error)
        // 如果API失败，显示空状态
        setFiles([])
        setFilteredFiles([])
        setProjectStats({ fileCount: 0, totalSize: 0 })
      } finally {
        setIsHydrated(true)
        setIsLoading(false)
      }
    }
    
    loadData()

    // 订阅项目数据变化
    const unsubscribe = projectSync.subscribe(() => {
      const updatedProject = projectSync.getProjectById(projectId)
      if (updatedProject) {
        setProject(updatedProject)
      }
    })
    
    return unsubscribe
  }, [projectId])

  // 当项目数据更新时，更新当前项目
  useEffect(() => {
    const updatedProject = storedProjects[projectId] || null
    setProject(updatedProject)
  }, [storedProjects, projectId])

  // 渲染已归档项目的提示页面
  const renderArchivedProject = () => (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="max-w-md w-full bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8 text-center">
        <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-gray-100 dark:bg-gray-700 mb-4">
          <ArchiveBoxIcon className="h-6 w-6 text-gray-600 dark:text-gray-400" />
        </div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
          项目已归档
        </h3>
        <p className="text-gray-500 dark:text-gray-400 mb-6">
          "{project?.name}" 项目已被归档，无法访问项目详情。
        </p>
        <div className="space-y-3">
          <Link href="/dashboard/projects">
            <Button className="w-full">
              返回项目列表
            </Button>
          </Link>
          <p className="text-sm text-gray-400 dark:text-gray-500">
            如需恢复项目，请在项目列表中点击恢复按钮
          </p>
        </div>
      </div>
    </div>
  )

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
          case 'PPT':
            return file.type.includes('powerpoint') || file.type.includes('presentation')
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

  // 改进的文件图标函数
  const getFileIcon = (type: string) => {
    if (type.startsWith('image/')) {
      return <PhotoIcon className="h-8 w-8 text-blue-500" />
    } else if (type === 'application/pdf') {
      return (
        <div className="h-8 w-8 bg-red-500 rounded flex items-center justify-center">
          <span className="text-white text-xs font-bold">PDF</span>
        </div>
      )
    } else if (type.includes('word')) {
      return (
        <div className="h-8 w-8 bg-blue-600 rounded flex items-center justify-center">
          <DocumentTextIcon className="h-5 w-5 text-white" />
        </div>
      )
    } else if (type.includes('excel') || type.includes('sheet')) {
      return (
        <div className="h-8 w-8 bg-green-600 rounded flex items-center justify-center">
          <TableCellsIcon className="h-5 w-5 text-white" />
        </div>
      )
    } else if (type.includes('powerpoint') || type.includes('presentation')) {
      return (
        <div className="h-8 w-8 bg-orange-600 rounded flex items-center justify-center">
          <PresentationChartBarIcon className="h-5 w-5 text-white" />
        </div>
      )
    } else if (type.startsWith('video/')) {
      return <VideoCameraIcon className="h-8 w-8 text-purple-500" />
    } else if (type.startsWith('audio/')) {
      return <SpeakerWaveIcon className="h-8 w-8 text-orange-500" />
    }
    return <DocumentIcon className="h-8 w-8 text-gray-500" />
  }

  // 获取上传者头像
  const getUploaderAvatar = (uploadedBy: string, source: 'user' | 'ai' | 'system') => {
    if (source === 'ai') {
      // AI生成的文件显示AI头像
      return (
        <div className="absolute -top-1 -left-1 h-6 w-6 bg-purple-500 rounded-full flex items-center justify-center border-2 border-white">
          <CpuChipIcon className="h-4 w-4 text-white" />
        </div>
      )
    } else {
      // 用户上传的文件显示用户头像
      const initials = uploadedBy.length > 0 ? uploadedBy.charAt(0).toUpperCase() : 'U'
      return (
        <div className="absolute -top-1 -left-1 h-6 w-6 bg-blue-500 rounded-full flex items-center justify-center border-2 border-white">
          <span className="text-white text-xs font-medium">{initials}</span>
        </div>
      )
    }
  }

  const getStageColorClass = (stage: string) => {
    const stageData = PROJECT_STAGES.find(s => s.name === stage)
    if (stageData) {
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

  // 封装文件操作后的数据同步
  const syncAfterFileOperation = async () => {
    try {
      const [apiFiles, stats] = await Promise.all([
        fetchProjectFiles(projectId),
        fetchProjectStats(projectId)
      ])
      setFiles(apiFiles)
      setFilteredFiles(apiFiles)
      setProjectStats(stats)
      
      // 同步更新到项目服务
      await projectSync.updateProjectFileStats(projectId)
    } catch (error) {
      console.error('同步数据失败:', error)
    }
  }

  const handleFileUpload = async (uploadedFiles: File[]) => {
    // 文件上传会通过FileUpload组件自动处理
    // 上传成功后重新获取文件列表和统计信息
    await syncAfterFileOperation()
    setShowUploadModal(false)
  }

  const handleRename = async (file: FileItem) => {
    // 设置编辑状态
    setEditingFile(file)
    setEditName(file.name)
    setEditStage(file.stage)
    setShowEditModal(true)
  }

  // 处理文件编辑提交
  const handleEditSubmit = async () => {
    if (!editingFile || !editName.trim()) {
      alert('文件名不能为空')
      return
    }

    try {
      const response = await fetch(`/api/v1/files/${editingFile.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          original_name: editName.trim(),
          stage: editStage
        }),
      });

      if (response.ok) {
        // 重新获取文件列表以确保数据同步
        await syncAfterFileOperation()
        setShowEditModal(false)
        setEditingFile(null)
        setEditName('')
        setEditStage('')
        alert('文件信息已更新')
      } else {
        const errorData = await response.json();
        console.error('编辑失败详情:', errorData);
        alert(`编辑失败: ${errorData.detail || errorData.message || response.statusText}`);
      }
    } catch (error) {
      console.error('编辑失败:', error)
      alert('编辑失败，请稍后重试')
    }
  }

  const handleDownload = async (file: FileItem) => {
    try {
      // 调用后端下载API
      const response = await fetch(`/api/v1/files/${file.id}/download`);
      
      if (response.ok) {
        // 获取文件内容
        const blob = await response.blob();
        
        // 创建下载链接
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = file.name;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // 清理URL对象
        URL.revokeObjectURL(url);
        
        console.log('文件下载成功:', file.name);
      } else {
        const errorData = await response.json();
        alert(`下载失败: ${errorData.message || response.statusText}`);
      }
    } catch (error) {
      console.error('下载失败:', error);
      alert('下载失败，请稍后重试');
    }
  }



  const handleDelete = async (fileId: string) => {
    if (confirm('确定要删除这个文件吗？')) {
      try {
        const response = await fetch(`/api/v1/files/${fileId}`, {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (response.ok) {
          await syncAfterFileOperation()
          alert('文件删除成功！');
        } else {
          const errorData = await response.json();
          alert(`文件删除失败: ${errorData.message || response.statusText}`);
        }
      } catch (error) {
        console.error('删除文件失败:', error);
        alert('删除文件失败，请稍后重试');
      }
    }
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



  const handleOpenAIChat = () => {
    // 直接跳转到AI对话页面，并传递项目ID作为参数
    window.location.href = `/dashboard/chat?project=${projectId}&name=${encodeURIComponent(project?.name || '')}`
  }

  // 如果项目已归档，显示无法访问的提示
  if (isHydrated && project?.status === 'archived') {
    return renderArchivedProject()
  }

  // 显示加载状态
  if (isLoading || !isHydrated) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">加载项目数据中...</p>
        </div>
      </div>
    )
  }

  // 如果项目不存在
  if (!project) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">项目不存在</h1>
          <p className="text-gray-600 dark:text-gray-400 mb-6">无法找到ID为 {projectId} 的项目</p>
          <Link href="/dashboard/projects">
            <Button>返回项目列表</Button>
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 面包屑导航 */}
      <div className="flex items-center space-x-2 text-sm text-gray-500 dark:text-gray-400">
        <Link href="/dashboard" className="hover:text-gray-700 dark:hover:text-gray-300 flex items-center">
          <HomeIcon className="h-4 w-4 mr-1" />
          Dashboard
        </Link>
        <span>/</span>
        <Link href="/dashboard/projects" className="hover:text-gray-700 dark:hover:text-gray-300">
          项目管理
        </Link>
        <span>/</span>
        <span className="text-gray-900 dark:text-white">{project?.name}</span>
      </div>

      {/* 项目信息头部 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-4">
            <Link href="/dashboard/projects">
              <button className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700">
                <ArrowLeftIcon className="h-5 w-5" />
              </button>
            </Link>
            <div>
              <div className="flex items-center space-x-3 mb-2">
                <div className={cn('w-4 h-4 rounded-full', project?.color)} />
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                  {project?.name}
                </h1>
              </div>
              <p className="text-gray-600 dark:text-gray-300 mb-4">
                {project?.description}
              </p>
              <div className="flex items-center space-x-6 text-sm text-gray-500 dark:text-gray-400">
                <div className="flex items-center space-x-1">
                  <CalendarIcon className="h-4 w-4" />
                  <span>当前阶段: {project?.stage}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <UserGroupIcon className="h-4 w-4" />
                  <span>{project?.memberCount} 名成员</span>
                </div>
                <div className="flex items-center space-x-1">
                  <FolderIcon className="h-4 w-4" />
                  <span>{projectStats.fileCount} 个文件</span>
                </div>
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <Button
              variant="outline"
              onClick={handleOpenAIChat}
              className="flex items-center"
            >
              <ChatBubbleLeftRightIcon className="h-5 w-5 mr-2" />
              AI助手
            </Button>
            <Button onClick={() => setShowUploadModal(true)}>
              <CloudArrowUpIcon className="h-5 w-5 mr-2" />
              上传文件
            </Button>
          </div>
        </div>
      </div>

      {/* 文件管理区域 */}
      <div className="space-y-4">
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
                        onClick={() => handleDownload(file)}
                        className="p-1.5 bg-white dark:bg-gray-800 rounded-full shadow-sm hover:shadow-md transition-shadow"
                        title="下载"
                      >
                        <ArrowDownTrayIcon className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                      </button>
                      <button 
                        onClick={() => handleRename(file)}
                        className="p-1.5 bg-white dark:bg-gray-800 rounded-full shadow-sm hover:shadow-md transition-shadow"
                        title="重命名"
                      >
                        <PencilIcon className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                      </button>
                      <button 
                        onClick={() => handleTagFile(file)}
                        className="p-1.5 bg-white dark:bg-gray-800 rounded-full shadow-sm hover:shadow-md transition-shadow"
                        title="标签"
                      >
                        <TagIcon className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                      </button>
                      <button 
                        onClick={() => handleDelete(file.id)}
                        className="p-1.5 bg-white dark:bg-gray-800 rounded-full shadow-sm hover:shadow-md transition-shadow"
                        title="删除"
                      >
                        <TrashIcon className="h-4 w-4 text-gray-600 dark:text-gray-400" />
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
                    
                    {/* 上传者信息 - 移到右侧 */}
                    <div className="flex items-center text-xs text-gray-500 dark:text-gray-400">
                      <UserIcon className="h-3 w-3 mr-1" />
                      <span>{file.uploadedBy}</span>
                    </div>
                  </div>
                  
                  {/* 标签信息 */}
                  {file.tags.length > 0 && (
                    <div className="flex items-center space-x-1 mt-2">
                      <TagIcon className="h-3 w-3 text-gray-400" />
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {file.tags[0]}
                        {file.tags.length > 1 && ` +${file.tags.length - 1}`}
                      </span>
                    </div>
                  )}
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
                            onClick={() => handleDownload(file)}
                            className="text-green-600 hover:text-green-900 dark:text-green-400 dark:hover:text-green-300"
                            title="下载"
                          >
                            <ArrowDownTrayIcon className="h-4 w-4" />
                          </button>
                          <button 
                            onClick={() => handleRename(file)}
                            className="text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-300"
                            title="重命名"
                          >
                            <PencilIcon className="h-4 w-4" />
                          </button>
                          <button 
                            onClick={() => handleTagFile(file)}
                            className="text-purple-600 hover:text-purple-900 dark:text-purple-400 dark:hover:text-purple-300"
                            title="标签"
                          >
                            <TagIcon className="h-4 w-4" />
                          </button>
                          <button 
                            onClick={() => handleDelete(file.id)}
                            className="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300"
                            title="删除"
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
                : '为这个项目上传第一个文件'
              }
            </p>
            <Button onClick={() => setShowUploadModal(true)}>
              <CloudArrowUpIcon className="h-5 w-5 mr-2" />
              上传文件
            </Button>
          </div>
        )}
      </div>

      {/* 上传模态框 */}
      <Modal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        title={`上传文件到 ${project?.name}`}
        size="lg"
      >
        <FileUpload
          onUpload={handleFileUpload}
          multiple={true}
          maxFiles={10}
          maxSize={50 * 1024 * 1024} // 50MB
          projectId={projectId}
        />
      </Modal>

      {/* 编辑文件模态框 */}
      <Modal
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        title={`编辑文件: ${editingFile?.name}`}
        size="sm"
      >
        <div className="space-y-4">
          <div>
            <label htmlFor="edit-name" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              文件名
            </label>
            <Input
              id="edit-name"
              type="text"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              className="mt-1"
            />
          </div>
          <div>
            <label htmlFor="edit-stage" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              文件阶段
            </label>
            <select
              id="edit-stage"
              value={editStage}
              onChange={(e) => setEditStage(e.target.value)}
              className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            >
              <option value="待分类">待分类</option>
              {PROJECT_STAGES.map(stage => (
                <option key={stage.name} value={stage.name}>{stage.name}</option>
              ))}
            </select>
          </div>
          <div className="flex justify-end space-x-2">
            <Button variant="outline" onClick={() => setShowEditModal(false)}>
              取消
            </Button>
            <Button onClick={handleEditSubmit}>
              保存
            </Button>
          </div>
        </div>
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