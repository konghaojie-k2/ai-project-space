'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { 
  MagnifyingGlassIcon, 
  FunnelIcon, 
  DocumentIcon,
  PhotoIcon,
  VideoCameraIcon,
  SpeakerWaveIcon,
  EllipsisVerticalIcon,
  EyeIcon,
  ArrowDownTrayIcon,
  TrashIcon,
  PencilIcon,
  TagIcon,
  DocumentTextIcon,
  TableCellsIcon,
  PresentationChartBarIcon,
  UserIcon,
  CodeBracketIcon
} from '@heroicons/react/24/outline'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import Modal from '@/components/ui/Modal'
import { FilePreview } from '@/components/features/FilePreview'
import TagManager from '@/components/features/TagManager'
import DashboardPageHeader from '@/components/layout/DashboardPageHeader'
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
  projectId?: string
  projectName?: string
}

// 获取项目信息缓存
const projectCache: Map<string, string> = new Map();

// 获取项目名称
const fetchProjectName = async (projectId: string | null | undefined): Promise<string | null> => {
  if (!projectId) {
    return null;
  }
  
  // 检查缓存
  if (projectCache.has(projectId)) {
    return projectCache.get(projectId) || null;
  }
  
  try {
    const { apiGet } = await import('@/lib/api');
    const response = await apiGet(`/api/v1/projects/${projectId}`);
    if (response.ok) {
      const project = await response.json();
      const projectName = project.name || '未知项目';
      projectCache.set(projectId, projectName);
      return projectName;
    } else if (response.status === 403) {
      // 403表示无权限访问，缓存为"无权限访问"而不是null
      const noAccessText = '无权限访问';
      projectCache.set(projectId, noAccessText);
      return noAccessText;
    } else if (response.status === 404) {
      // 404表示项目不存在
      const notFoundText = '项目不存在';
      projectCache.set(projectId, notFoundText);
      return notFoundText;
    }
  } catch (error) {
    console.error(`获取项目信息失败 (${projectId}):`, error);
  }
  
  // 如果获取失败，返回null，在显示时会显示"未知项目"
  return null;
};

// 从后端API获取所有文件列表
const fetchAllFiles = async (): Promise<FileItem[]> => {
  try {
    const { apiGet } = await import('@/lib/api');
    const response = await apiGet('/api/v1/files/');
    if (response.ok) {
      const files = await response.json();
      
      // 收集所有唯一的项目ID
      const projectIds = new Set<string>();
      files.forEach((file: any) => {
        if (file.project_id) {
          projectIds.add(file.project_id);
        }
      });
      
      // 批量获取项目名称
      const projectNamePromises = Array.from(projectIds).map(async (projectId) => {
        const name = await fetchProjectName(projectId);
        return { projectId, name };
      });
      const projectNames = await Promise.all(projectNamePromises);
      const projectNameMap = new Map<string, string>();
      projectNames.forEach(({ projectId, name }) => {
        if (name) {
          projectNameMap.set(projectId, name);
        }
      });
      
      return files.map((file: any) => ({
        id: file.id,
        name: file.original_name,
        type: file.file_type,
        size: file.file_size,
        uploadedAt: file.created_at,
        uploadedBy: file.uploaded_by || '未知用户',
        stage: file.stage || '待分类',
        tags: file.tags || [],
        url: `/api/v1/files/${file.id}/download`,
        projectId: file.project_id || null,
        projectName: file.project_id ? (projectNameMap.get(file.project_id) || '未知项目') : null
      }));
    } else {
      console.error('获取文件列表失败:', response.statusText);
      return [];
    }
  } catch (error) {
    console.error('获取文件列表出错:', error);
    return [];
  }
};

// 获取所有标签（预定义 + 自定义）
const getAllTags = () => {
  let customTags: any[] = [];
  if (typeof window !== 'undefined') {
    try {
      const stored = localStorage.getItem('custom-tags');
      if (stored) {
        customTags = JSON.parse(stored);
      }
    } catch (error) {
      console.error('加载自定义标签失败:', error);
    }
  }
  return [...PREDEFINED_TAGS, ...customTags];
};

// 根据tag ID获取tag信息
const getTagInfo = (tagId: string) => {
  const allTags = getAllTags();
  return allTags.find(tag => tag.id === tagId);
};

const stages = ['全部', ...PROJECT_STAGES.map(stage => stage.name)]
const fileTypes = ['全部', 'PDF', 'Word', 'Excel', '图片', '视频', '音频', '其他']

export default function FilesPage() {
  const [files, setFiles] = useState<FileItem[]>([])
  const [filteredFiles, setFilteredFiles] = useState<FileItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedStage, setSelectedStage] = useState('全部')
  const [selectedType, setSelectedType] = useState('全部')
  const [selectedProject, setSelectedProject] = useState<string>('全部')
  const [showPreviewModal, setShowPreviewModal] = useState(false)
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null)
  const [showFilters, setShowFilters] = useState(false)
  const [showTagManager, setShowTagManager] = useState(false)
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  const [fileToTag, setFileToTag] = useState<FileItem | null>(null)
  const [projects, setProjects] = useState<Array<{id: string, name: string}>>([]);

  // 加载文件数据
  useEffect(() => {
    const loadFiles = async () => {
      setIsLoading(true);
      try {
        const apiFiles = await fetchAllFiles();
        setFiles(apiFiles);
        setFilteredFiles(apiFiles);
      } catch (error) {
        console.error('加载文件失败:', error);
        setFiles([]);
        setFilteredFiles([]);
      } finally {
        setIsLoading(false);
      }
    };
    
    loadFiles();
  }, []);

  // 加载项目列表（用于筛选）
  useEffect(() => {
    const loadProjects = async () => {
      try {
        const { apiGet } = await import('@/lib/api');
        const response = await apiGet('/api/v1/projects/');
        if (response.ok) {
          const projectList = await response.json();
          setProjects(projectList.map((p: any) => ({ id: p.id, name: p.name })));
        }
      } catch (error) {
        console.error('加载项目列表失败:', error);
      }
    };
    loadProjects();
  }, []);

  // 过滤文件
  useEffect(() => {
    let filtered = files

    // 搜索过滤
    if (searchQuery) {
      filtered = filtered.filter(file => 
        file.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (file.projectName && file.projectName.toLowerCase().includes(searchQuery.toLowerCase())) ||
        file.tags.some(tag => {
          const tagInfo = getTagInfo(tag);
          return tagInfo && tagInfo.name.toLowerCase().includes(searchQuery.toLowerCase());
        })
      )
    }

    // 项目过滤
    if (selectedProject !== '全部') {
      filtered = filtered.filter(file => file.projectId === selectedProject)
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
  }, [files, searchQuery, selectedStage, selectedType, selectedProject])

  // 改进的文件图标函数，使用更直观的图标
  const getFileIcon = (type: string, fileName: string) => {
    // 先检查文件扩展名以支持Markdown
    const extension = fileName.split('.').pop()?.toLowerCase();
    
    if (extension === 'md' || extension === 'markdown') {
      return (
        <div className="h-8 w-8 bg-purple-600 rounded flex items-center justify-center">
          <CodeBracketIcon className="h-5 w-5 text-white" />
        </div>
      )
    } else if (type.startsWith('image/')) {
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


  const handlePreview = (file: FileItem) => {
    setSelectedFile(file)
    setShowPreviewModal(true)
  }

  // 添加下载功能
  const handleDownload = (file: FileItem) => {
    if (file.url) {
      // 使用后端API下载文件
      window.open(file.url, '_blank');
    } else {
      console.error('文件下载URL不存在:', file.name);
    }
  }

  // 添加编辑功能
  const handleEdit = (file: FileItem) => {
    // 根据文件类型打开相应的编辑器
    if (file.type.includes('word')) {
      // 打开Word编辑器
      console.log('编辑Word文档:', file.name)
    } else if (file.type.includes('excel')) {
      // 打开Excel编辑器
      console.log('编辑Excel文档:', file.name)
    } else if (file.type === 'application/pdf') {
      // PDF通常不能直接编辑，可以转换或标注
      console.log('PDF文档不支持直接编辑:', file.name)
    } else {
      // 其他文件类型
      console.log('编辑文件:', file.name)
    }
    // 这里应该集成在线编辑器或调用外部编辑器
  }

  const handleDelete = async (fileId: string) => {
    if (confirm('确定要删除这个文件吗？')) {
      try {
        const { apiDelete } = await import('@/lib/api');
        const response = await apiDelete(`/api/v1/files/${fileId}`);
        if (response.ok) {
          // 删除成功后重新加载文件列表
          const apiFiles = await fetchAllFiles();
          setFiles(apiFiles);
          setFilteredFiles(apiFiles);
        } else {
          const errorData = await response.json();
          alert(`删除失败: ${errorData.detail || errorData.message || response.statusText}`);
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

  const handleTagsUpdate = async (tags: string[]) => {
    if (!fileToTag) {
      return;
    }

    try {
      const { apiPut } = await import('@/lib/api');
      const response = await apiPut(`/api/v1/files/${fileToTag.id}`, {
        tags: tags
      });

      if (response.ok) {
        // 更新成功后重新加载文件列表
        const apiFiles = await fetchAllFiles();
        setFiles(apiFiles);
        setFilteredFiles(apiFiles);
      } else {
        const errorData = await response.json();
        alert(`标签更新失败: ${errorData.detail || errorData.message || response.statusText}`);
      }
    } catch (error) {
      console.error('标签更新失败:', error);
      alert('标签更新失败，请稍后重试');
    }
    
    setShowTagManager(false);
    setFileToTag(null);
    setSelectedTags([]);
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 页面头部 */}
      <DashboardPageHeader
        title="文件管理"
        description="管理项目文件，支持多种格式预览和组织"
        showBackButton={false}
      />

      <div className="space-y-6 p-6">
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

      </div>

      {/* 筛选器 */}
      {showFilters && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                项目
              </label>
              <select
                value={selectedProject}
                onChange={(e) => setSelectedProject(e.target.value)}
                className="w-full rounded-md border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                <option value="全部">全部</option>
                {projects.map(project => (
                  <option key={project.id} value={project.id}>{project.name}</option>
                ))}
              </select>
            </div>
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
          {(searchQuery || selectedProject !== '全部' || selectedStage !== '全部' || selectedType !== '全部') && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setSearchQuery('')
                setSelectedProject('全部')
                setSelectedStage('全部')
                setSelectedType('全部')
              }}
            >
              清除筛选
            </Button>
          )}
        </div>
      </div>

      {/* 文件列表视图 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    文件名
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    项目
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
                          {getFileIcon(file.type, file.name)}
                        </div>
                        <div>
                          <div className="text-sm font-medium text-gray-900 dark:text-white">
                            {file.name}
                          </div>
                          {file.tags.length > 0 && (() => {
                            // 过滤掉不存在的tag（已删除的自定义tag或无效tag）
                            const validTags = file.tags.filter(tagId => getTagInfo(tagId) !== undefined);
                            if (validTags.length === 0) return null;
                            
                            return (
                              <div className="flex items-center flex-wrap gap-1 mt-1">
                                {validTags.slice(0, 2).map((tagId) => {
                                  const tagInfo = getTagInfo(tagId);
                                  if (!tagInfo) return null; // 双重检查
                                  return (
                                    <span
                                      key={tagId}
                                      className={`px-1.5 py-0.5 rounded text-xs font-medium ${tagInfo.color} border border-opacity-20`}
                                      title={tagInfo.name}
                                    >
                                      {tagInfo.name}
                                    </span>
                                  );
                                })}
                                {validTags.length > 2 && (
                                  <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400">
                                    +{validTags.length - 2}
                                  </span>
                                )}
                              </div>
                            );
                          })()}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {file.projectId ? (
                        file.projectName === '无权限访问' || file.projectName === '项目不存在' ? (
                          <span className="text-sm text-gray-500 dark:text-gray-400" title="无法访问该项目">
                            {file.projectName}
                          </span>
                        ) : (
                          <Link 
                            href={`/dashboard/projects/${file.projectId}`}
                            className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline"
                          >
                            {file.projectName || '未知项目'}
                          </Link>
                        )
                      ) : (
                        <span className="text-sm text-gray-400 dark:text-gray-500">未分配</span>
                      )}
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
                          title="预览"
                        >
                          <EyeIcon className="h-4 w-4" />
                        </button>
                        <button 
                          onClick={() => handleDownload(file)}
                          className="text-green-600 hover:text-green-900 dark:text-green-400 dark:hover:text-green-300"
                          title="下载"
                        >
                          <ArrowDownTrayIcon className="h-4 w-4" />
                        </button>
                        <button 
                          onClick={() => handleEdit(file)}
                          className="text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-300"
                          title="编辑"
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

      {/* 加载状态 */}
      {isLoading && (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-500 dark:text-gray-400">加载文件中...</p>
        </div>
      )}

      {/* 空状态 */}
      {!isLoading && filteredFiles.length === 0 && (
        <div className="text-center py-12">
          <DocumentIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            {searchQuery || selectedProject !== '全部' || selectedStage !== '全部' || selectedType !== '全部' 
              ? '没有找到匹配的文件' 
              : '暂无文件'
            }
          </h3>
          <p className="text-gray-500 dark:text-gray-400 mb-4">
            {searchQuery || selectedProject !== '全部' || selectedStage !== '全部' || selectedType !== '全部' 
              ? '尝试调整筛选条件或搜索关键词' 
              : '文件需要在项目管理页面中上传'
            }
          </p>
        </div>
      )}

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
    </div>
  )
} 