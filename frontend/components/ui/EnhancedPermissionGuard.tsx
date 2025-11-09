import React, { useEffect, useState } from 'react'
import { useSystemPermissions, useProjectPermissions } from '@/hooks/usePermissions'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase/client'
import { AlertCircle, Lock, Shield } from 'lucide-react'

interface EnhancedPermissionGuardProps {
  children: React.ReactNode
  permission?: string
  projectId?: string
  projectPermission?: 'read' | 'write' | 'delete' | 'manage_members' | 'manage_settings'
  fallback?: React.ReactNode
  requireAuth?: boolean
}

/**
 * 增强权限保护组件
 *
 * 支持多种权限检查模式：
 * 1. 系统权限检查 (permission prop)
 * 2. 项目权限检查 (projectId + projectPermission props)
 * 3. 基础认证检查 (requireAuth prop)
 */
export function EnhancedPermissionGuard({
  children,
  permission,
  projectId,
  projectPermission,
  fallback,
  requireAuth = false
}: EnhancedPermissionGuardProps) {
  const router = useRouter()
  const [checking, setChecking] = useState(true)
  const [hasAccess, setHasAccess] = useState(false)

  const { hasPermission: hasSystemPermission, loading: systemLoading } = useSystemPermissions()
  const { hasProjectPermission: checkProjectPermission, loading: projectLoading } = useProjectPermissions()

  useEffect(() => {
    const checkPermissions = async () => {
      try {
        setChecking(true)

        // 如果只需要认证检查
        if (requireAuth && !permission && !projectId) {
          const { data: { user } } = await supabase.auth.getUser()
          setHasAccess(!!user)
          return
        }

        // 系统权限检查
        if (permission) {
          const hasPermit = await hasSystemPermission(permission)
          setHasAccess(hasPermit)
          return
        }

        // 项目权限检查
        if (projectId && projectPermission) {
          const hasPermit = await checkProjectPermission(projectId, projectPermission)
          setHasAccess(hasPermit)
          return
        }

        // 如果没有指定权限要求，默认允许访问
        setHasAccess(true)

      } catch (error) {
        console.error('权限检查失败:', error)
        setHasAccess(false)
      } finally {
        setChecking(false)
      }
    }

    checkPermissions()
  }, [permission, projectId, projectPermission, requireAuth, hasSystemPermission, checkProjectPermission])

  // 显示加载状态
  if (checking || systemLoading || projectLoading) {
    return (
      <div className="flex items-center justify-center min-h-[200px]">
        <div className="flex flex-col items-center space-y-4 text-gray-500">
          <Shield className="h-8 w-8 animate-pulse" />
          <p>正在验证权限...</p>
        </div>
      </div>
    )
  }

  // 权限验证失败
  if (!hasAccess) {
    // 如果提供了自定义fallback组件，使用它
    if (fallback) {
      return <>{fallback}</>
    }

    // 默认的无权限访问提示
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center max-w-md mx-auto p-6">
          <div className="mb-4">
            <Lock className="h-16 w-16 text-gray-400 mx-auto" />
          </div>

          <div className="mb-4">
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              访问受限
            </h3>

            {permission && (
              <p className="text-sm text-gray-600">
                您需要 <span className="font-medium">"{permission}"</span> 权限才能访问此页面。
              </p>
            )}

            {projectId && projectPermission && (
              <p className="text-sm text-gray-600">
                您需要项目的 <span className="font-medium">"{projectPermission}"</span> 权限才能执行此操作。
              </p>
            )}

            {requireAuth && (
              <p className="text-sm text-gray-600">
                请登录后访问此页面。
              </p>
            )}
          </div>

          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <button
              onClick={() => router.back()}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              返回上页
            </button>

            {requireAuth && (
              <button
                onClick={() => router.push('/login')}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                去登录
              </button>
            )}
          </div>

          <div className="mt-6 p-4 bg-yellow-50 rounded-lg">
            <div className="flex">
              <div className="flex-shrink-0">
                <AlertCircle className="h-5 w-5 text-yellow-400" />
              </div>
              <div className="ml-3">
                <p className="text-sm text-yellow-800">
                  如果您认为这是一个错误，请联系系统管理员获取相应权限。
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // 权限验证通过，显示子组件
  return <>{children}</>
}

/**
 * 系统权限保护组件的便捷版本
 */
export function SystemPermissionGuard({
  permission,
  children,
  fallback
}: {
  permission: string
  children: React.ReactNode
  fallback?: React.ReactNode
}) {
  return (
    <EnhancedPermissionGuard
      permission={permission}
      fallback={fallback}
    >
      {children}
    </EnhancedPermissionGuard>
  )
}

/**
 * 项目权限保护组件的便捷版本
 */
export function ProjectPermissionGuard({
  projectId,
  permission,
  children,
  fallback
}: {
  projectId: string
  permission: 'read' | 'write' | 'delete' | 'manage_members' | 'manage_settings'
  children: React.ReactNode
  fallback?: React.ReactNode
}) {
  return (
    <EnhancedPermissionGuard
      projectId={projectId}
      projectPermission={permission}
      fallback={fallback}
    >
      {children}
    </EnhancedPermissionGuard>
  )
}

/**
 * 认证保护组件的便捷版本
 */
export function AuthGuard({
  children,
  fallback
}: {
  children: React.ReactNode
  fallback?: React.ReactNode
}) {
  return (
    <EnhancedPermissionGuard
      requireAuth={true}
      fallback={fallback}
    >
      {children}
    </EnhancedPermissionGuard>
  )
}

/**
 * 管理员权限保护组件
 */
export function AdminGuard({
  children,
  fallback
}: {
  children: React.ReactNode
  fallback?: React.ReactNode
}) {
  return (
    <SystemPermissionGuard
      permission="admin_access"
      fallback={fallback || (
        <div className="text-center py-8">
          <Lock className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">需要管理员权限</h3>
          <p className="text-gray-600">此功能仅限管理员访问</p>
        </div>
      )}
    >
      {children}
    </SystemPermissionGuard>
  )
}

/**
 * 超级管理员权限保护组件
 */
export function SuperAdminGuard({
  children,
  fallback
}: {
  children: React.ReactNode
  fallback?: React.ReactNode
}) {
  return (
    <SystemPermissionGuard
      permission="manage_system"
      fallback={fallback || (
        <div className="text-center py-8">
          <Lock className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">需要超级管理员权限</h3>
          <p className="text-gray-600">此功能仅限超级管理员访问</p>
        </div>
      )}
    >
      {children}
    </SystemPermissionGuard>
  )
}