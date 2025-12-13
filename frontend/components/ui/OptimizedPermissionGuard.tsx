#!/usr/bin/env tsx
/**
 * 优化的权限保护组件
 *
 * 特性：
 * 1. 使用缓存权限Hook
 * 2. React.memo优化渲染
 * 3. 批量权限检查
 * 4. 智能权限预热
 * 5. 减少不必要的重渲染
 */

import React, { memo, useMemo, useCallback, useEffect } from 'react'
import { Shield, Lock, AlertCircle, Loader2 } from 'lucide-react'
import { useCachedPermissions } from '@/hooks/useCachedPermissions'

export interface OptimizedPermissionGuardProps {
  // 权限配置
  resourceType: 'project' | 'file' | 'system'
  resourceId?: string
  permission?: string
  permissions?: string[]  // 支持多个权限检查
  requireAll?: boolean     // 是否需要所有权限都通过

  // 项目特定的便捷配置
  projectId?: string
  projectRole?: 'owner' | 'admin' | 'member' | 'viewer'

  // 渲染配置
  children: React.ReactNode
  fallback?: React.ReactNode
  loadingFallback?: React.ReactNode
  errorFallback?: React.ReactNode

  // 优化配置
  preload?: boolean        // 是否预加载权限
  cacheKey?: string        // 自定义缓存键
  debug?: boolean          // 调试模式
}

interface PermissionCheck {
  resourceType: string
  resourceId: string
  permission: string
}

// 加载组件
const LoadingFallback = memo(() => (
  <div className="flex items-center justify-center min-h-[100px] p-4">
    <Loader2 className="h-6 w-6 animate-spin text-blue-500 mr-2" />
    <span className="text-sm text-gray-600">正在验证权限...</span>
  </div>
))

LoadingFallback.displayName = 'LoadingFallback'

// 无权限组件
const AccessDenied = memo(({ reason }: { reason?: string }) => (
  <div className="flex items-center justify-center min-h-[100px] p-4 text-gray-500">
    <Lock className="h-6 w-6 mr-2" />
    <span className="text-sm">权限不足{reason ? `: ${reason}` : ''}</span>
  </div>
))

AccessDenied.displayName = 'AccessDenied'

// 错误组件
const ErrorFallback = memo(({ error }: { error: string }) => (
  <div className="flex items-center justify-center min-h-[100px] p-4">
    <AlertCircle className="h-6 w-6 text-red-500 mr-2" />
    <span className="text-sm text-red-600">权限验证失败: {error}</span>
  </div>
))

ErrorFallback.displayName = 'ErrorFallback'

/**
 * 优化的权限保护组件
 */
export const OptimizedPermissionGuard = memo<OptimizedPermissionGuardProps>(({
  resourceType,
  resourceId,
  permission,
  permissions = [],
  requireAll = true,
  projectId,
  projectRole,
  children,
  fallback,
  loadingFallback = <LoadingFallback />,
  errorFallback,
  preload = false,
  cacheKey,
  debug = false
}) => {
  const {
    checkPermission,
    batchCheckPermissions,
    warmUpPermissions,
    loading,
    error
  } = useCachedPermissions()

  // 生成权限检查列表
  const permissionChecks = useMemo(() => {
    const checks: PermissionCheck[] = []

    // 如果指定了项目ID，优先使用
    const effectiveResourceId = projectId || resourceId

    if (!effectiveResourceId) {
      debug && console.warn('OptimizedPermissionGuard: 缺少resourceId或projectId')
      return checks
    }

    // 单个权限检查
    if (permission) {
      checks.push({
        resourceType,
        resourceId: effectiveResourceId,
        permission
      })
    }

    // 多个权限检查
    if (permissions.length > 0) {
      permissions.forEach(perm => {
        checks.push({
          resourceType,
          resourceId: effectiveResourceId,
          permission: perm
        })
      })
    }

    // 项目角色映射到权限
    if (projectRole && resourceType === 'project') {
      const rolePermissions = getRolePermissions(projectRole)
      rolePermissions.forEach(perm => {
        checks.push({
          resourceType,
          resourceId: effectiveResourceId,
          permission: perm
        })
      })
    }

    return checks
  }, [
    resourceType,
    resourceId,
    projectId,
    permission,
    permissions,
    projectRole,
    debug
  ])

  // 生成缓存键
  const effectiveCacheKey = useMemo(() => {
    if (cacheKey) return cacheKey

    const parts = [
      'permission-guard',
      resourceType,
      projectId || resourceId,
      permission,
      permissions.join(','),
      projectRole,
      requireAll.toString()
    ].filter(Boolean)

    return parts.join(':')
  }, [
    cacheKey,
    resourceType,
    projectId,
    resourceId,
    permission,
    permissions,
    projectRole,
    requireAll
  ])

  // 执行权限检查
  const { hasPermission, isLoading, hasError, errorReason } = usePermissionCheck(
    permissionChecks,
    requireAll,
    batchCheckPermissions,
    effectiveCacheKey
  )

  // 权限预热
  useEffect(() => {
    if (preload && permissionChecks.length > 0) {
      warmUpPermissions(projectId ? [projectId] : undefined)
    }
  }, [preload, permissionChecks.length, projectId, warmUpPermissions])

  // 调试日志
  useEffect(() => {
    if (debug) {
      console.log('OptimizedPermissionGuard:', {
        resourceType,
        resourceId,
        projectId,
        permission,
        permissions,
        hasPermission,
        isLoading,
        hasError,
        cacheKey: effectiveCacheKey
      })
    }
  }, [
    debug,
    resourceType,
    resourceId,
    projectId,
    permission,
    permissions,
    hasPermission,
    isLoading,
    hasError,
    effectiveCacheKey
  ])

  // 加载状态
  if (isLoading || loading) {
    return <>{loadingFallback}</>
  }

  // 错误状态
  if (hasError || error) {
    if (errorFallback) {
      return <>{errorFallback}</>
    }
    return <ErrorFallback error={error || '未知错误'} />
  }

  // 权限检查失败
  if (!hasPermission) {
    if (fallback) {
      return <>{fallback}</>
    }
    return <AccessDenied reason={errorReason} />
  }

  // 权限检查通过，渲染子组件
  return <>{children}</>
})

OptimizedPermissionGuard.displayName = 'OptimizedPermissionGuard'

/**
 * 权限检查Hook
 * 批量检查权限并缓存结果
 */
function usePermissionCheck(
  checks: PermissionCheck[],
  requireAll: boolean,
  batchCheckPermissions: (
    requests: Array<{ resourceType: string; resourceId: string; permissions: string[] }>
  ) => Promise<Record<string, any>>,
  cacheKey: string
) {
  const [state, setState] = React.useState<{
    hasPermission: boolean
    isLoading: boolean
    hasError: boolean
    errorReason?: string
    results: Record<string, boolean>
  }>({
    hasPermission: false,
    isLoading: checks.length > 0,
    hasError: false,
    results: {}
  })

  // 执行权限检查
  React.useEffect(() => {
    if (checks.length === 0) {
      setState({
        hasPermission: true, // 没有权限要求时默认通过
        isLoading: false,
        hasError: false,
        results: {}
      })
      return
    }

    let isMounted = true

    const performPermissionCheck = async () => {
      try {
        // 按资源ID分组权限检查
        const resourceGroups: Record<string, PermissionCheck[]> = {}
        checks.forEach(check => {
          const key = `${check.resourceType}:${check.resourceId}`
          if (!resourceGroups[key]) {
            resourceGroups[key] = []
          }
          resourceGroups[key].push(check)
        })

        // 转换为批量检查格式
        const batchRequests = Object.values(resourceGroups).map(group => ({
          resourceType: group[0].resourceType,
          resourceId: group[0].resourceId,
          permissions: group.map(check => check.permission)
        }))

        // 执行批量检查
        const batchResults = await batchCheckPermissions(batchRequests)

        // 解析结果
        const results: Record<string, boolean> = {}
        let allGranted = true
        let anyGranted = false

        checks.forEach((check, index) => {
          const key = `${index}:${check.resourceId}:${check.permission}`
          const granted = batchResults[key]?.granted ?? false
          results[check.permission] = granted

          if (!granted) {
            allGranted = false
          } else {
            anyGranted = true
          }
        })

        // 根据requireAll决定最终结果
        const finalHasPermission = requireAll ? allGranted : anyGranted

        if (isMounted) {
          setState({
            hasPermission: finalHasPermission,
            isLoading: false,
            hasError: false,
            results
          })
        }

      } catch (err) {
        console.error('权限检查失败:', err)
        if (isMounted) {
          setState({
            hasPermission: false,
            isLoading: false,
            hasError: true,
            errorReason: err instanceof Error ? err.message : '权限检查失败',
            results: {}
          })
        }
      }
    }

    performPermissionCheck()

    return () => {
      isMounted = false
    }
  }, [checks, requireAll, batchCheckPermissions, cacheKey])

  return state
}

/**
 * 获取角色对应的权限列表
 */
function getRolePermissions(role: string): string[] {
  const rolePermissionMap: Record<string, string[]> = {
    owner: ['read', 'write', 'delete', 'manage_members', 'manage_settings'],
    admin: ['read', 'write', 'delete', 'manage_members'],
    member: ['read', 'write'],
    viewer: ['read']
  }

  return rolePermissionMap[role] || []
}

// 便捷组件
export const ProjectPermissionGuard = memo<{
  projectId: string
  permission?: string
  permissions?: string[]
  requireAll?: boolean
  children: React.ReactNode
  fallback?: React.ReactNode
}>((props) => (
  <OptimizedPermissionGuard
    resourceType="project"
    projectId={props.projectId}
    permission={props.permission}
    permissions={props.permissions}
    requireAll={props.requireAll}
    fallback={props.fallback}
  >
    {props.children}
  </OptimizedPermissionGuard>
))

ProjectPermissionGuard.displayName = 'ProjectPermissionGuard'

export const SystemPermissionGuard = memo<{
  permission?: string
  permissions?: string[]
  requireAll?: boolean
  children: React.ReactNode
  fallback?: React.ReactNode
}>((props) => (
  <OptimizedPermissionGuard
    resourceType="system"
    resourceId="global"
    permission={props.permission}
    permissions={props.permissions}
    requireAll={props.requireAll}
    fallback={props.fallback}
  >
    {props.children}
  </OptimizedPermissionGuard>
))

SystemPermissionGuard.displayName = 'SystemPermissionGuard'

export default OptimizedPermissionGuard