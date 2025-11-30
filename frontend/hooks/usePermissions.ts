import { useState, useEffect, useCallback } from 'react'
import { supabase } from '@/lib/supabase/client'
import { ProjectRole, FileAccessLevel, SystemRole } from '@/types/database'

// 权限绕过模式检查
const PERMISSION_BYPASS_MODE = process.env.NEXT_PUBLIC_PERMISSION_BYPASS === 'true'

// 详细日志检查
const LOG_PERMISSION_BYPASS = process.env.NEXT_PUBLIC_LOG_PERMISSION_BYPASS === 'true'

/**
 * 增强项目权限管理Hook (基于新的权限模型)
 */
export function useProjectPermissions() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 获取用户在项目中的有效权限
  const getEffectiveProjectPermissions = useCallback(async (projectId: string) => {
    try {
      setLoading(true)
      setError(null)

      const { data: { user } } = await supabase.auth.getUser()
      if (!user) {
        throw new Error('用户未认证')
      }

      // 使用新的权限检查函数
      const { data, error } = await supabase.rpc(
        'get_effective_project_permissions',
        {
          project_uuid: projectId,
          user_uuid: user.id
        }
      )

      if (error) throw error

      return data || {}
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '获取项目权限失败'
      setError(errorMessage)
      return {}
    } finally {
      setLoading(false)
    }
  }, [])

  // 检查用户是否有特定项目权限 (使用新的权限系统)
  const hasProjectPermission = useCallback(async (
    projectId: string,
    requiredPermission: 'read' | 'write' | 'delete' | 'manage_members' | 'manage_settings'
  ): Promise<boolean> => {
    try {
      setLoading(true)
      setError(null)

      // 权限绕过模式：所有项目权限检查都返回true
      if (PERMISSION_BYPASS_MODE) {
        if (process.env.NEXT_PUBLIC_LOG_PERMISSION_BYPASS === 'true') {
          console.log('权限绕过模式：项目权限检查通过', { projectId, requiredPermission })
        }
        return true
      }

      const { data: { user } } = await supabase.auth.getUser()
      if (!user) {
        return false
      }

      // 使用新的权限检查函数
      const { data, error } = await supabase.rpc(
        'has_project_permission',
        {
          project_uuid: projectId,
          user_uuid: user.id,
          required_permission: requiredPermission
        }
      )

      if (error) throw error

      return data === true
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '权限检查失败'
      setError(errorMessage)
      return false
    } finally {
      setLoading(false)
    }
  }, [])

  // 检查用户在项目中的角色 (兼容旧版本)
  const checkProjectRole = async (projectId: string): Promise<ProjectRole | null> => {
    try {
      const permissions = await getEffectiveProjectPermissions(projectId)

      // 根据权限推断角色
      if (permissions.manage_settings) return 'owner'
      if (permissions.manage_members) return 'admin'
      if (permissions.write) return 'member'
      if (permissions.read) return 'viewer'

      return null
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '角色检查失败'
      setError(errorMessage)
      return null
    }
  }

  // 兼容旧版本的角色权限检查
  const hasProjectRolePermission = async (
    projectId: string,
    requiredRole: ProjectRole
  ): Promise<boolean> => {
    const userRole = await checkProjectRole(projectId)
    if (!userRole) return false

    // 角色权限层级
    const roleHierarchy: Record<ProjectRole, number> = {
      viewer: 1,
      member: 2,
      admin: 3,
      owner: 4,
    }

    return roleHierarchy[userRole] >= roleHierarchy[requiredRole]
  }

  // 获取用户可访问的项目 (使用权限视图)
  const getUserProjects = async () => {
    try {
      setLoading(true)
      setError(null)

      // 使用新的用户可访问项目视图
      const { data, error } = await supabase
        .from('user_accessible_projects')
        .select('*')
        .order('updated_at', { ascending: false })

      if (error) throw error

      return data || []
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '获取项目失败'
      setError(errorMessage)
      return []
    } finally {
      setLoading(false)
    }
  }

  // 添加项目成员 (增强版本)
  const addProjectMember = async (
    projectId: string,
    userEmail: string,
    role: ProjectRole
  ) => {
    try {
      setLoading(true)
      setError(null)

      // 根据邮箱获取用户ID
      const { data: userProfile, error: userError } = await supabase
        .from('profiles')
        .select('id, username, full_name')
        .eq('email', userEmail)
        .single()

      if (userError || !userProfile) {
        throw new Error('用户不存在')
      }

      // 检查当前用户是否有权限添加成员
      const canAddMembers = await hasProjectPermission(projectId, 'manage_members')
      if (!canAddMembers) {
        throw new Error('没有权限添加项目成员')
      }

      // 获取当前用户ID作为邀请人
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) {
        throw new Error('用户未认证')
      }

      // 添加成员 (使用增强版本)
      const { error } = await supabase
        .from('project_members')
        .insert({
          project_id: projectId,
          user_id: userProfile.id,
          role,
          invited_by: user.id,
          is_active: true,
          permissions: '{}',
        })

      if (error) throw error

      return true
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '添加成员失败'
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  // 更新项目成员角色
  const updateProjectMemberRole = async (
    projectId: string,
    userId: string,
    newRole: ProjectRole
  ) => {
    try {
      setLoading(true)
      setError(null)

      // 检查当前用户是否有权限管理成员
      const canManageMembers = await hasProjectPermission(projectId, 'manage_members')
      if (!canManageMembers) {
        throw new Error('没有权限管理项目成员')
      }

      const { error } = await supabase
        .from('project_members')
        .update({
          role: newRole,
          updated_at: new Date().toISOString()
        })
        .eq('project_id', projectId)
        .eq('user_id', userId)
        .eq('is_active', true)

      if (error) throw error

      return true
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '更新角色失败'
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  // 移除项目成员
  const removeProjectMember = async (projectId: string, userId: string) => {
    try {
      setLoading(true)
      setError(null)

      // 检查当前用户是否有权限管理成员
      const canManageMembers = await hasProjectPermission(projectId, 'manage_members')
      if (!canManageMembers) {
        throw new Error('没有权限移除项目成员')
      }

      // 不能移除自己
      const { data: { user } } = await supabase.auth.getUser()
      if (user && user.id === userId) {
        throw new Error('不能移除自己')
      }

      const { error } = await supabase
        .from('project_members')
        .delete()
        .eq('project_id', projectId)
        .eq('user_id', userId)

      if (error) throw error

      return true
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '移除成员失败'
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  // 获取项目成员列表 (增强版本，包含更多信息)
  const getProjectMembers = async (projectId: string) => {
    try {
      setLoading(true)
      setError(null)

      const { data, error } = await supabase
        .from('project_members')
        .select(`
          *,
          profiles!project_members_user_id_fkey (
            id,
            username,
            full_name,
            avatar_url,
            email,
            system_role,
            is_active
          )
        `)
        .eq('project_id', projectId)
        .eq('is_active', true)
        .order('joined_at', { ascending: true })

      if (error) throw error

      return data || []
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '获取成员列表失败'
      setError(errorMessage)
      return []
    } finally {
      setLoading(false)
    }
  }

  // 获取权限审计日志
  const getPermissionAuditLog = async (
    projectId?: string,
    limit: number = 50
  ) => {
    try {
      setLoading(true)
      setError(null)

      let query = supabase
        .from('permission_audit_log')
        .select(`
          *,
          performed_by_profile:profiles!permission_audit_log_performed_by_fkey (
            username, full_name, avatar_url
          ),
          target_user_profile:profiles!permission_audit_log_target_user_id_fkey (
            username, full_name, avatar_url
          )
        `)
        .order('created_at', { ascending: false })
        .limit(limit)

      if (projectId) {
        query = query.eq('entity_id', projectId).eq('entity_type', 'project')
      }

      const { data, error } = await query

      if (error) throw error

      return data || []
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '获取审计日志失败'
      setError(errorMessage)
      return []
    } finally {
      setLoading(false)
    }
  }

  return {
    loading,
    error,
    // 新的权限方法
    getEffectiveProjectPermissions,
    hasProjectPermission,
    // 兼容旧版本的方法
    checkProjectRole,
    hasProjectRolePermission,
    getUserProjects,
    // 增强的成员管理方法
    addProjectMember,
    updateProjectMemberRole,
    removeProjectMember,
    getProjectMembers,
    // 新增的审计功能
    getPermissionAuditLog,
  }
}

/**
 * 文件权限管理Hook
 */
export function useFilePermissions() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 检查文件访问权限
  const checkFileAccess = async (fileId: string): Promise<boolean> => {
    try {
      setLoading(true)
      setError(null)

      const { data: { user } } = await supabase.auth.getUser()
      if (!user) {
        return false
      }

      // 获取文件信息
      const { data: file, error } = await supabase
        .from('files')
        .select(`
          access_level,
          uploaded_by,
          project_id
        `)
        .eq('id', fileId)
        .single()

      if (error || !file) {
        return false
      }

      // 检查访问权限
      const { access_level, uploaded_by, project_id } = file
      const userId = user.id
      const isSuperUser = user.user_metadata?.is_superuser || user.app_metadata?.is_superuser

      // 超级管理员有所有权限
      if (isSuperUser) {
        return true
      }

      // 文件上传者有所有权限
      if (uploaded_by === userId) {
        return true
      }

      // 根据访问级别检查
      switch (access_level) {
        case 'all_users':
          return true

        case 'project_members':
          if (!project_id) return false
          return await checkProjectMembership(project_id, userId)

        case 'admins_only':
          return isSuperUser

        case 'owner_only':
          return uploaded_by === userId

        default:
          return false
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '文件权限检查失败'
      setError(errorMessage)
      return false
    } finally {
      setLoading(false)
    }
  }

  // 检查项目成员身份
  const checkProjectMembership = async (projectId: string, userId: string) => {
    const { data, error } = await supabase
      .from('project_members')
      .select('id')
      .eq('project_id', projectId)
      .eq('user_id', userId)
      .single()

    return !error && !!data
  }

  // 获取用户可访问的文件
  const getAccessibleFiles = async (projectId?: string) => {
    try {
      setLoading(true)
      setError(null)

      const { data: { user } } = await supabase.auth.getUser()
      if (!user) {
        return []
      }

      let query = supabase
        .from('files')
        .select(`
          *,
          project:projects (id, name),
          uploader:profiles (id, username, full_name)
        `)

      if (projectId) {
        query = query.eq('project_id', projectId)
      }

      // 由于RLS策略，这里会自动过滤用户有权限访问的文件
      const { data, error } = await query.order('created_at', { ascending: false })

      if (error) throw error

      return data || []
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '获取文件列表失败'
      setError(errorMessage)
      return []
    } finally {
      setLoading(false)
    }
  }

  // 更新文件访问权限
  const updateFileAccessLevel = async (
    fileId: string,
    accessLevel: FileAccessLevel
  ) => {
    try {
      setLoading(true)
      setError(null)

      const { error } = await supabase
        .from('files')
        .update({ access_level })
        .eq('id', fileId)

      if (error) throw error

      return true
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '更新文件权限失败'
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  return {
    loading,
    error,
    checkFileAccess,
    getAccessibleFiles,
    updateFileAccessLevel,
  }
}

/**
 * 增强系统权限Hook (基于新的权限模型)
 */
export function useSystemPermissions() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 获取用户权限汇总信息
  const getUserPermissionSummary = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const { data: { user } } = await supabase.auth.getUser()
      if (!user) {
        return null
      }

      // 使用新的用户权限汇总视图
      const { data, error } = await supabase
        .from('user_permission_summary')
        .select('*')
        .eq('user_id', user.id)
        .single()

      if (error) throw error

      return data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '获取权限汇总失败'
      setError(errorMessage)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  // 检查用户是否为超级管理员
  const isSuperUser = useCallback(async () => {
    try {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) return false

      // 权限绕过模式：所有用户都是超级用户
      if (PERMISSION_BYPASS_MODE) {
        if (process.env.NEXT_PUBLIC_LOG_PERMISSION_BYPASS === 'true') {
          console.log('权限绕过模式：超级用户权限检查通过')
        }
        return true
      }

      // 检查用户档案中的超级管理员状态
      const { data: profile, error } = await supabase
        .from('profiles')
        .select('is_superuser, system_role')
        .eq('id', user.id)
        .single()

      if (error || !profile) return false

      return profile.is_superuser === true || profile.system_role === 'super_admin'
    } catch (err) {
      console.error('检查超级用户权限失败:', err)
      return false
    }
  }, [])

  // 获取用户权限列表 (基于新的权限模型)
  const getUserPermissions = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const permissionSummary = await getUserPermissionSummary()

      if (!permissionSummary) {
        return []
      }

      const overallPermissionLevel = permissionSummary.overall_permission_level

      // 基于整体权限级别返回权限
      const levelPermissions = {
        'system_admin': [
          'read', 'write', 'delete', 'manage_users', 'manage_projects',
          'view_all_projects', 'manage_system', 'admin_access', 'view_audit_log'
        ],
        'admin': ['read', 'write', 'delete', 'manage_users', 'manage_projects', 'view_audit_log'],
        'manager': ['read', 'write', 'delete', 'manage_projects'],
        'user': ['read', 'write']
      }

      return levelPermissions[overallPermissionLevel as keyof typeof levelPermissions] || ['read']
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '获取权限失败'
      setError(errorMessage)
      return []
    } finally {
      setLoading(false)
    }
  }, [getUserPermissionSummary])

  // 检查特定权限
  const hasPermission = useCallback(async (permission: string) => {
    // 权限绕过模式：只绕过业务权限，保留数据查询权限
    if (PERMISSION_BYPASS_MODE) {
      // 只绕过业务相关的权限，保留数据访问权限
      const businessPermissions = ['manage_users', 'manage_projects', 'delete_project', 'system_admin']
      const isBusinessPermission = businessPermissions.includes(permission)

      if (LOG_PERMISSION_BYPASS && isBusinessPermission) {
        console.log('权限绕过模式：业务权限检查通过', permission)
      }

      // 对于数据查询相关的权限，仍然进行检查
      const dataPermissions = ['read', 'access_dashboard', 'view_projects']
      if (dataPermissions.includes(permission)) {
        return false // 数据权限不绕过，让正常逻辑处理
      }

      return isBusinessPermission // 只绕过业务权限
    }

    const permissions = await getUserPermissions()
    return permissions.includes(permission)
  }, [getUserPermissions])

  // 获取用户系统角色
  const getUserSystemRole = useCallback(async () => {
    try {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) return 'user'

      const { data: profile, error } = await supabase
        .from('profiles')
        .select('system_role, is_superuser')
        .eq('id', user.id)
        .single()

      if (error || !profile) return 'user'

      if (profile.is_superuser || profile.system_role === 'super_admin') {
        return 'super_admin'
      }

      return profile.system_role || 'user'
    } catch (err) {
      console.error('获取系统角色失败:', err)
      return 'user'
    }
  }, [])

  return {
    loading,
    error,
    // 新的权限方法
    getUserPermissionSummary,
    getUserSystemRole,
    // 兼容旧版本的方法
    isSuperUser,
    getUserPermissions,
    hasPermission,
  }
}

/**
 * 权限保护组件Hook
 */
export function useRequirePermission(permission: string) {
  const { hasPermission, loading } = useSystemPermissions()
  const [hasAccess, setHasAccess] = useState(false)

  useEffect(() => {
    const checkAccess = async () => {
      const access = await hasPermission(permission)
      setHasAccess(access)
    }

    if (!loading) {
      checkAccess()
    }
  }, [permission, loading, hasPermission])

  return { hasAccess, loading }
}