import { useState, useCallback } from 'react'
import { supabase } from '@/lib/supabase/client'

// 文件上传响应类型
interface FileUploadResponse {
  success: boolean
  message: string
  file_id?: string
  url?: string
  size?: number
  content_type?: string
}

// 文件详细信息类型
interface FileDetailResponse {
  id: string
  filename: string
  original_filename: string
  content_type: string
  size: number
  description?: string
  tags?: string[]
  uploaded_by: string
  uploader_name?: string
  project_id?: string
  project_name?: string
  access_level: 'all_users' | 'project_members' | 'admins_only' | 'owner_only'
  created_at: string
  updated_at: string
  shares?: Array<{
    id: string
    user_id: string
    username: string
    can_view: boolean
    can_download: boolean
    can_edit: boolean
    created_at: string
  }>
  is_favorited?: boolean
  preview_available?: boolean
}

// 文件统计类型
interface FileStatsResponse {
  total_files: number
  total_size: number
  by_type: Record<string, number>
  by_project: Record<string, number>
}

// 文件分享请求类型
interface FileShareRequest {
  user_email: string
  can_view: boolean
  can_download: boolean
  can_edit: boolean
  expires_at?: string
}

// 文件搜索请求类型
interface FileSearchRequest {
  query: string
  project_id?: string
  file_type?: string
  limit?: number
}

// 文件元数据更新类型
interface FileMetadataUpdate {
  description?: string
  tags?: string[]
  custom_fields?: Record<string, any>
}

/**
 * 增强文件管理Hook
 * 提供基于Supabase权限系统的文件操作功能
 */
export function useEnhancedFiles() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 清除错误状态
  const clearError = useCallback(() => {
    setError(null)
  }, [])

  // 处理API错误
  const handleApiError = useCallback((err: any) => {
    const errorMessage = err?.detail || err?.message || '操作失败'
    setError(errorMessage)
    console.error('文件API错误:', err)
  }, [])

  // 上传文件
  const uploadFile = useCallback(async (
    file: File,
    options: {
      project_id?: string
      title?: string
      description?: string
      tags?: string[]
      access_level?: 'all_users' | 'project_members' | 'admins_only' | 'owner_only'
      is_public?: boolean
      allow_ai?: boolean
    } = {}
  ): Promise<FileUploadResponse | null> => {
    setLoading(true)
    clearError()

    try {
      const formData = new FormData()
      formData.append('file', file)

      if (options.project_id) formData.append('project_id', options.project_id)
      if (options.title) formData.append('title', options.title)
      if (options.description) formData.append('description', options.description)
      if (options.tags?.length) formData.append('tags', options.tags.join(','))
      if (options.access_level) formData.append('access_level', options.access_level)
      if (options.is_public !== undefined) formData.append('is_public', options.is_public.toString())
      if (options.allow_ai !== undefined) formData.append('allow_ai', options.allow_ai.toString())

      const { data, error } = await supabase.functions.invoke('files-enhanced-upload', {
        body: formData,
        method: 'POST'
      })

      if (error) {
        handleApiError(error)
        return null
      }

      return data as FileUploadResponse
    } catch (err) {
      handleApiError(err)
      return null
    } finally {
      setLoading(false)
    }
  }, [clearError, handleApiError])

  // 获取文件列表
  const getFiles = useCallback(async (options: {
    project_id?: string
    limit?: number
  } = {}): Promise<FileDetailResponse[]> => {
    setLoading(true)
    clearError()

    try {
      const params = new URLSearchParams()
      if (options.project_id) params.append('project_id', options.project_id)
      if (options.limit) params.append('limit', options.limit.toString())

      const { data, error } = await supabase
        .functions.invoke('files-enhanced', {
          method: 'GET',
          query: params.toString()
        })

      if (error) {
        handleApiError(error)
        return []
      }

      return data || []
    } catch (err) {
      handleApiError(err)
      return []
    } finally {
      setLoading(false)
    }
  }, [clearError, handleApiError])

  // 获取文件详细信息
  const getFileDetail = useCallback(async (
    fileId: string
  ): Promise<FileDetailResponse | null> => {
    setLoading(true)
    clearError()

    try {
      const { data, error } = await supabase
        .functions.invoke(`files-enhanced/${fileId}`, {
          method: 'GET'
        })

      if (error) {
        handleApiError(error)
        return null
      }

      return data as FileDetailResponse
    } catch (err) {
      handleApiError(err)
      return null
    } finally {
      setLoading(false)
    }
  }, [clearError, handleApiError])

  // 搜索文件
  const searchFiles = useCallback(async (
    searchRequest: FileSearchRequest
  ): Promise<FileDetailResponse[]> => {
    setLoading(true)
    clearError()

    try {
      const { data, error } = await supabase
        .functions.invoke('files-enhanced/search', {
          method: 'POST',
          body: searchRequest
        })

      if (error) {
        handleApiError(error)
        return []
      }

      return data?.results || []
    } catch (err) {
      handleApiError(err)
      return []
    } finally {
      setLoading(false)
    }
  }, [clearError, handleApiError])

  // 分享文件
  const shareFile = useCallback(async (
    fileId: string,
    shareRequest: FileShareRequest
  ): Promise<boolean> => {
    setLoading(true)
    clearError()

    try {
      const { error } = await supabase
        .functions.invoke(`files-enhanced/${fileId}/share`, {
          method: 'POST',
          body: shareRequest
        })

      if (error) {
        handleApiError(error)
        return false
      }

      return true
    } catch (err) {
      handleApiError(err)
      return false
    } finally {
      setLoading(false)
    }
  }, [clearError, handleApiError])

  // 更新文件元数据
  const updateFileMetadata = useCallback(async (
    fileId: string,
    metadataUpdate: FileMetadataUpdate
  ): Promise<boolean> => {
    setLoading(true)
    clearError()

    try {
      const { error } = await supabase
        .functions.invoke(`files-enhanced/${fileId}/metadata`, {
          method: 'PUT',
          body: metadataUpdate
        })

      if (error) {
        handleApiError(error)
        return false
      }

      return true
    } catch (err) {
      handleApiError(err)
      return false
    } finally {
      setLoading(false)
    }
  }, [clearError, handleApiError])

  // 删除文件
  const deleteFile = useCallback(async (fileId: string): Promise<boolean> => {
    setLoading(true)
    clearError()

    try {
      const { error } = await supabase
        .functions.invoke(`files-enhanced/${fileId}`, {
          method: 'DELETE'
        })

      if (error) {
        handleApiError(error)
        return false
      }

      return true
    } catch (err) {
      handleApiError(err)
      return false
    } finally {
      setLoading(false)
    }
  }, [clearError, handleApiError])

  // 获取文件下载链接
  const getDownloadUrl = useCallback(async (
    fileId: string
  ): Promise<string | null> => {
    setLoading(true)
    clearError()

    try {
      const { data, error } = await supabase
        .functions.invoke(`files-enhanced/${fileId}/download`, {
          method: 'GET'
        })

      if (error) {
        handleApiError(error)
        return null
      }

      return data?.download_url || null
    } catch (err) {
      handleApiError(err)
      return null
    } finally {
      setLoading(false)
    }
  }, [clearError, handleApiError])

  // 预览文件
  const previewFile = useCallback(async (
    fileId: string,
    options: {
      max_width?: number
      max_height?: number
      page?: number
      quality?: number
    } = {}
  ): Promise<string | null> => {
    setLoading(true)
    clearError()

    try {
      const { data, error } = await supabase
        .functions.invoke(`files-enhanced/${fileId}/preview`, {
          method: 'POST',
          body: options
        })

      if (error) {
        handleApiError(error)
        return null
      }

      return data?.preview_url || null
    } catch (err) {
      handleApiError(err)
      return null
    } finally {
      setLoading(false)
    }
  }, [clearError, handleApiError])

  // 获取文件统计
  const getFileStats = useCallback(async (
    projectId?: string
  ): Promise<FileStatsResponse | null> => {
    setLoading(true)
    clearError()

    try {
      const url = projectId
        ? `files-enhanced/stats/user?project_id=${projectId}`
        : 'files-enhanced/stats/user'

      const { data, error } = await supabase.functions.invoke(url, {
        method: 'GET'
      })

      if (error) {
        handleApiError(error)
        return null
      }

      return data as FileStatsResponse
    } catch (err) {
      handleApiError(err)
      return null
    } finally {
      setLoading(false)
    }
  }, [clearError, handleApiError])

  // 获取最近文件活动
  const getRecentActivity = useCallback(async (
    options: {
      limit?: number
      file_id?: string
    } = {}
  ): Promise<any[]> => {
    setLoading(true)
    clearError()

    try {
      const params = new URLSearchParams()
      if (options.limit) params.append('limit', options.limit.toString())
      if (options.file_id) params.append('file_id', options.file_id)

      const { data, error } = await supabase
        .functions.invoke(`files-enhanced/activity/recent?${params}`, {
          method: 'GET'
        })

      if (error) {
        handleApiError(error)
        return []
      }

      return data?.activities || []
    } catch (err) {
      handleApiError(err)
      return []
    } finally {
      setLoading(false)
    }
  }, [clearError, handleApiError])

  return {
    // 状态
    loading,
    error,

    // 操作方法
    uploadFile,
    getFiles,
    getFileDetail,
    searchFiles,
    shareFile,
    updateFileMetadata,
    deleteFile,
    getDownloadUrl,
    previewFile,
    getFileStats,
    getRecentActivity,

    // 工具方法
    clearError
  }
}