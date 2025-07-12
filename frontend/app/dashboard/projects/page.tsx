'use client'

import React, { useState, useEffect } from 'react'
import { 
  PlusIcon,
  FolderIcon,
  CalendarIcon,
  UserGroupIcon,
  DocumentIcon,
  EllipsisVerticalIcon,
  EyeIcon,
  PencilIcon,
  TrashIcon,
  ArchiveBoxIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline'
import Link from 'next/link'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import Modal from '@/components/ui/Modal'
import { formatFileSize, cn } from '@/lib/utils'

interface Project {
  id: string
  name: string
  description: string
  stage: string
  createdAt: string
  updatedAt: string
  memberCount: number
  fileCount: number
  totalSize: number
  status: 'active' | 'archived' | 'completed'
  color: string
}

// 模拟项目数据
const mockProjects: Project[] = [
  {
    id: '1',
    name: 'AI智能客服系统',
    description: '基于大语言模型的智能客服解决方案，提升客户服务效率',
    stage: '工程开发',
    createdAt: '2024-01-15T10:00:00Z',
    updatedAt: '2024-12-28T15:30:00Z',
    memberCount: 8,
    fileCount: 45,
    totalSize: 128 * 1024 * 1024, // 128MB
    status: 'active',
    color: 'bg-blue-500'
  },
  {
    id: '2',
    name: '数据分析平台',
    description: '企业级数据分析和可视化平台，支持多数据源集成',
    stage: '数据理解',
    createdAt: '2024-02-01T09:00:00Z',
    updatedAt: '2024-12-27T11:20:00Z',
    memberCount: 6,
    fileCount: 32,
    totalSize: 89 * 1024 * 1024, // 89MB
    status: 'active',
    color: 'bg-green-500'
  },
  {
    id: '3',
    name: '推荐系统优化',
    description: '电商推荐算法优化项目，提升用户体验和转化率',
    stage: '实施部署',
    createdAt: '2024-03-10T14:00:00Z',
    updatedAt: '2024-12-26T16:45:00Z',
    memberCount: 5,
    fileCount: 28,
    totalSize: 67 * 1024 * 1024, // 67MB
    status: 'completed',
    color: 'bg-purple-500'
  },
  {
    id: '4',
    name: '图像识别模型',
    description: '医疗影像AI诊断辅助系统，提高诊断准确率',
    stage: '业务调研',
    createdAt: '2024-04-05T11:00:00Z',
    updatedAt: '2024-12-25T09:15:00Z',
    memberCount: 4,
    fileCount: 18,
    totalSize: 156 * 1024 * 1024, // 156MB
    status: 'active',
    color: 'bg-orange-500'
  }
]

// localStorage持久化存储函数
const getStoredProjects = (): Project[] => {
  if (typeof window === 'undefined') return mockProjects
  
  try {
    const stored = localStorage.getItem('ai-projects')
    if (stored) {
      return JSON.parse(stored)
    }
  } catch (error) {
    console.error('读取项目数据失败:', error)
  }
  return mockProjects
}

const saveProjectsToStorage = (projects: Project[]) => {
  if (typeof window === 'undefined') return
  
  try {
    localStorage.setItem('ai-projects', JSON.stringify(projects))
  } catch (error) {
    console.error('保存项目数据失败:', error)
  }
}

const statusConfig = {
  active: { label: '进行中', color: 'bg-green-100 text-green-800' },
  completed: { label: '已完成', color: 'bg-blue-100 text-blue-800' },
  archived: { label: '已归档', color: 'bg-gray-100 text-gray-800' }
}

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>(mockProjects)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedStatus, setSelectedStatus] = useState<string>('all')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingProject, setEditingProject] = useState<Project | null>(null)
  const [editForm, setEditForm] = useState({
    name: '',
    description: '',
    stage: '',
    status: 'active' as 'active' | 'archived' | 'completed'
  })
  const [createForm, setCreateForm] = useState({
    name: '',
    description: '',
    stage: '售前',
    status: 'active' as 'active' | 'archived' | 'completed'
  })
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [isHydrated, setIsHydrated] = useState(false)

  // 客户端水合完成后加载localStorage数据
  useEffect(() => {
    setIsHydrated(true)
    const storedProjects = getStoredProjects()
    setProjects(storedProjects)
  }, [])

  const filteredProjects = projects.filter(project => {
    const matchesSearch = project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         project.description.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = selectedStatus === 'all' || project.status === selectedStatus
    return matchesSearch && matchesStatus
  })

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  }

  const handleDeleteProject = (projectId: string) => {
    if (confirm('确定要删除这个项目吗？此操作不可撤销。')) {
      const updatedProjects = projects.filter(p => p.id !== projectId)
      setProjects(updatedProjects)
      saveProjectsToStorage(updatedProjects)
    }
  }

  const handleArchiveProject = (projectId: string) => {
    const updatedProjects = projects.map(p => 
      p.id === projectId 
        ? { ...p, status: (p.status === 'archived' ? 'active' : 'archived') as 'active' | 'archived' | 'completed' }
        : p
    )
    setProjects(updatedProjects)
    saveProjectsToStorage(updatedProjects)
  }

  const handleCompleteProject = (projectId: string) => {
    const updatedProjects = projects.map(p => 
      p.id === projectId 
        ? { ...p, status: 'completed' as 'active' | 'archived' | 'completed', updatedAt: new Date().toISOString() }
        : p
    )
    setProjects(updatedProjects)
    saveProjectsToStorage(updatedProjects)
  }

  const handleEditProject = (project: Project) => {
    setEditingProject(project)
    setEditForm({
      name: project.name,
      description: project.description,
      stage: project.stage,
      status: project.status
    })
    setShowEditModal(true)
  }

  const handleUpdateProject = () => {
    if (editingProject && editForm.name.trim()) {
      const updatedProjects = projects.map(p => 
        p.id === editingProject.id 
          ? { 
              ...p, 
              name: editForm.name.trim(),
              description: editForm.description.trim(),
              stage: editForm.stage,
              status: editForm.status,
              updatedAt: new Date().toISOString()
            }
          : p
      )
      
      setProjects(updatedProjects)
      saveProjectsToStorage(updatedProjects)
      
      setShowEditModal(false)
      setEditingProject(null)
      setEditForm({ name: '', description: '', stage: '', status: 'active' })
    }
  }

  const handleCancelEdit = () => {
    setShowEditModal(false)
    setEditingProject(null)
    setEditForm({ name: '', description: '', stage: '', status: 'active' })
  }

  const handleCreateProject = () => {
    if (createForm.name.trim()) {
      const newProject: Project = {
        id: `${Date.now()}`,
        name: createForm.name.trim(),
        description: createForm.description.trim(),
        stage: createForm.stage,
        status: createForm.status,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        memberCount: 1, // 默认创建者为成员
        fileCount: 0,
        totalSize: 0,
        color: getRandomProjectColor()
      }
      
      const updatedProjects = [newProject, ...projects]
      setProjects(updatedProjects)
      saveProjectsToStorage(updatedProjects)
      
      // 重置表单和关闭模态框
      setCreateForm({ name: '', description: '', stage: '售前', status: 'active' })
      setShowCreateModal(false)
    }
  }

  const handleCancelCreate = () => {
    setCreateForm({ name: '', description: '', stage: '售前', status: 'active' })
    setShowCreateModal(false)
  }

  // 随机选择项目颜色
  const getRandomProjectColor = () => {
    const colors = ['bg-blue-500', 'bg-green-500', 'bg-purple-500', 'bg-orange-500', 'bg-red-500', 'bg-indigo-500']
    return colors[Math.floor(Math.random() * colors.length)]
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            项目管理
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            管理您的AI项目，按项目组织文件和资源
          </p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          <PlusIcon className="h-5 w-5 mr-2" />
          新建项目
        </Button>
      </div>

      {/* 工具栏 */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0">
        {/* 搜索和筛选 */}
        <div className="flex items-center space-x-4">
          <div className="relative">
            <Input
              type="text"
              placeholder="搜索项目..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-64"
            />
          </div>
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
          >
            <option value="all">全部状态</option>
            <option value="active">进行中</option>
            <option value="completed">已完成</option>
            <option value="archived">已归档</option>
          </select>
        </div>

        {/* 统计信息 */}
        <div className="flex items-center space-x-6 text-sm text-gray-500 dark:text-gray-400">
          <span>共 {filteredProjects.length} 个项目</span>
          <span>活跃项目 {projects.filter(p => p.status === 'active').length} 个</span>
        </div>
      </div>

      {/* 项目网格视图 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredProjects.map((project) => (
          <div
            key={project.id}
            className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow duration-200 group"
          >
            {/* 项目头部 */}
            <div className="p-6 pb-4">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center space-x-3">
                  <div className={cn('w-3 h-3 rounded-full', project.color)} />
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    {project.name}
                  </h3>
                </div>
                <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                  <div className="flex items-center space-x-1">
                    {project.status !== 'archived' ? (
                      <Link href={`/dashboard/projects/${project.id}`}>
                        <button
                          className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700"
                          title="查看项目"
                        >
                          <EyeIcon className="h-4 w-4" />
                        </button>
                      </Link>
                    ) : (
                      <button
                        disabled
                        className="p-1.5 text-gray-300 dark:text-gray-600 rounded-full cursor-not-allowed"
                        title="已归档项目无法预览"
                      >
                        <EyeIcon className="h-4 w-4" />
                      </button>
                    )}
                    <button
                      onClick={() => handleEditProject(project)}
                      className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700"
                      title="编辑项目"
                    >
                      <PencilIcon className="h-4 w-4" />
                    </button>
                    {project.status === 'active' && (
                      <button
                        onClick={() => handleCompleteProject(project.id)}
                        className="p-1.5 text-blue-400 hover:text-blue-600 dark:hover:text-blue-300 rounded-full hover:bg-blue-50 dark:hover:bg-blue-900/20"
                        title="标记为完成"
                      >
                        <CheckCircleIcon className="h-4 w-4" />
                      </button>
                    )}
                    <button
                      onClick={() => handleArchiveProject(project.id)}
                      className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700"
                      title={project.status === 'archived' ? '恢复项目' : '归档项目'}
                    >
                      <ArchiveBoxIcon className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDeleteProject(project.id)}
                      className="p-1.5 text-red-400 hover:text-red-600 dark:hover:text-red-300 rounded-full hover:bg-red-50 dark:hover:bg-red-900/20"
                      title="删除项目"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
              
              <p className="text-gray-600 dark:text-gray-300 text-sm mb-4 line-clamp-2">
                {project.description}
              </p>

              {/* 项目状态和阶段 */}
              <div className="flex items-center justify-between mb-4">
                <span className={cn(
                  'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
                  statusConfig[project.status].color
                )}>
                  {statusConfig[project.status].label}
                </span>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {project.stage}
                </span>
              </div>

              {/* 项目统计 */}
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <div className="flex items-center justify-center mb-1">
                    <UserGroupIcon className="h-4 w-4 text-gray-400 mr-1" />
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {project.memberCount}
                    </span>
                  </div>
                  <span className="text-xs text-gray-500 dark:text-gray-400">成员</span>
                </div>
                <div>
                  <div className="flex items-center justify-center mb-1">
                    <DocumentIcon className="h-4 w-4 text-gray-400 mr-1" />
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {project.fileCount}
                    </span>
                  </div>
                  <span className="text-xs text-gray-500 dark:text-gray-400">文件</span>
                </div>
                <div>
                  <div className="flex items-center justify-center mb-1">
                    <FolderIcon className="h-4 w-4 text-gray-400 mr-1" />
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {formatFileSize(project.totalSize)}
                    </span>
                  </div>
                  <span className="text-xs text-gray-500 dark:text-gray-400">大小</span>
                </div>
              </div>
            </div>

            {/* 项目底部 */}
            <div className="px-6 py-4 bg-gray-50 dark:bg-gray-700/50 rounded-b-lg">
              <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                <span>创建于 {formatDate(project.createdAt)}</span>
                <span>更新于 {formatDate(project.updatedAt)}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* 空状态 */}
      {filteredProjects.length === 0 && (
        <div className="text-center py-12">
          <FolderIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            {searchQuery || selectedStatus !== 'all' 
              ? '没有找到匹配的项目' 
              : '暂无项目'
            }
          </h3>
          <p className="text-gray-500 dark:text-gray-400 mb-4">
            {searchQuery || selectedStatus !== 'all' 
              ? '尝试调整搜索条件或筛选器' 
              : '创建您的第一个AI项目'
            }
          </p>
          <Button onClick={() => setShowCreateModal(true)}>
            <PlusIcon className="h-5 w-5 mr-2" />
            新建项目
          </Button>
        </div>
      )}

      {/* 创建项目模态框 */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="新建项目"
        size="lg"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              项目名称
            </label>
            <Input
              type="text"
              placeholder="输入项目名称"
              value={createForm.name}
              onChange={(e) => setCreateForm(prev => ({ ...prev, name: e.target.value }))}
              className="w-full"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              项目描述
            </label>
            <textarea
              rows={3}
              placeholder="简要描述项目目标和内容"
              value={createForm.description}
              onChange={(e) => setCreateForm(prev => ({ ...prev, description: e.target.value }))}
              className="w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              项目阶段
            </label>
            <select 
              value={createForm.stage}
              onChange={(e) => setCreateForm(prev => ({ ...prev, stage: e.target.value }))}
              className="w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            >
              <option value="售前">售前阶段</option>
              <option value="业务调研">业务调研</option>
              <option value="数据理解">数据理解</option>
              <option value="数据探索">数据探索</option>
              <option value="工程开发">工程开发</option>
              <option value="实施部署">实施部署</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              项目状态
            </label>
            <select 
              value={createForm.status}
              onChange={(e) => setCreateForm(prev => ({ ...prev, status: e.target.value as 'active' | 'archived' | 'completed' }))}
              className="w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            >
              <option value="active">进行中</option>
              <option value="completed">已完成</option>
              <option value="archived">已归档</option>
            </select>
          </div>
          <div className="flex justify-end space-x-3 pt-4">
            <Button variant="outline" onClick={handleCancelCreate}>
              取消
            </Button>
            <Button onClick={handleCreateProject}>
              创建项目
            </Button>
          </div>
        </div>
      </Modal>

      {/* 编辑项目模态框 */}
      <Modal
        isOpen={showEditModal}
        onClose={handleCancelEdit}
        title="编辑项目"
        size="lg"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              项目名称
            </label>
            <Input
              type="text"
              placeholder="输入项目名称"
              value={editForm.name}
              onChange={(e) => setEditForm(prev => ({ ...prev, name: e.target.value }))}
              className="w-full"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              项目描述
            </label>
            <textarea
              rows={3}
              placeholder="简要描述项目目标和内容"
              value={editForm.description}
              onChange={(e) => setEditForm(prev => ({ ...prev, description: e.target.value }))}
              className="w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              项目阶段
            </label>
            <select 
              value={editForm.stage}
              onChange={(e) => setEditForm(prev => ({ ...prev, stage: e.target.value }))}
              className="w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            >
              <option value="售前">售前阶段</option>
              <option value="业务调研">业务调研</option>
              <option value="数据理解">数据理解</option>
              <option value="数据探索">数据探索</option>
              <option value="工程开发">工程开发</option>
              <option value="实施部署">实施部署</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              项目状态
            </label>
            <select 
              value={editForm.status}
              onChange={(e) => setEditForm(prev => ({ ...prev, status: e.target.value as 'active' | 'archived' | 'completed' }))}
              className="w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            >
              <option value="active">进行中</option>
              <option value="completed">已完成</option>
              <option value="archived">已归档</option>
            </select>
          </div>
          <div className="flex justify-end space-x-3 pt-4">
            <Button variant="outline" onClick={handleCancelEdit}>
              取消
            </Button>
            <Button onClick={handleUpdateProject}>
              保存修改
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
} 