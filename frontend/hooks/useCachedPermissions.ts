#!/usr/bin/env tsx
/**
 * 缓存权限管理Hook
 * 提供高性能的权限检查和缓存机制
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { supabase } from '@/lib/supabase/client'

// 权限缓存接口
interface PermissionCacheEntry {
  permissions: Record<string, boolean>
  timestamp: number
  ttl: number
  hitCount: number
}

interface BatchPermissionRequest {
  resourceType: 'project' | 'file' | 'system'
  resourceId: string
  permissions: string[]
}

interface PermissionCheckResult {
  granted: boolean
  reason?: string
  cacheHit: boolean
  source: 'cache' | 'api'
}

// 缓存配置
const CACHE_CONFIG = {
  DEFAULT_TTL: 5 * 60 * 1000, // 5分钟
  MAX_CACHE_SIZE: 1000,
  CLEANUP_INTERVAL: 30 * 1000, // 30秒清理一次
  BATCH_SIZE: 50, // 批量检查大小限制
}

// 内存缓存存储
class PermissionCacheManager {
  private cache: Map<string, PermissionCacheEntry> = new Map()
  private cleanupTimer: NodeJS.Timeout | null = null

  constructor() {
    this.startCleanupTimer()
  }

  private startCleanupTimer() {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer)
    }
    this.cleanupTimer = setInterval(() => {
      this.cleanup()
    }, CACHE_CONFIG.CLEANUP_INTERVAL)
  }

  private generateCacheKey(
    resourceType: string,
    resourceId: string,
    permission: string
  ): string {
    return `${resourceType}:${resourceId}:${permission}`
  }

  get(resourceType: string, resourceId: string, permission: string): boolean | null {
    const key = this.generateCacheKey(resourceType, resourceId, permission)
    const entry = this.cache.get(key)

    if (!entry) {
      return null
    }

    // 检查是否过期
    if (Date.now() - entry.timestamp > entry.ttl) {
      this.cache.delete(key)
      return null
    }

    // 更新命中次数
    entry.hitCount++
    return entry.permissions[permission] ?? false
  }

  set(
    resourceType: string,
    resourceId: string,
    permission: string,
    granted: boolean,
    ttl: number = CACHE_CONFIG.DEFAULT_TTL
  ): void {
    const key = this.generateCacheKey(resourceType, resourceId, permission)

    // 检查缓存大小限制
    if (this.cache.size >= CACHE_CONFIG.MAX_CACHE_SIZE) {
      this.evictLRU()
    }

    this.cache.set(key, {
      permissions: { [permission]: granted },
      timestamp: Date.now(),
      ttl,
      hitCount: 0
    })
  }

  batchSet(
    entries: Array<{
      resourceType: string
      resourceId: string
      permission: string
      granted: boolean
    }>,
    ttl: number = CACHE_CONFIG.DEFAULT_TTL
  ): void {
    entries.forEach(entry => {
      this.set(
        entry.resourceType,
        entry.resourceId,
        entry.permission,
        entry.granted,
        ttl
      )
    })
  }

  invalidate(pattern?: string): number {
    let deletedCount = 0

    if (pattern) {
      for (const [key] of this.cache.entries()) {
        if (key.includes(pattern)) {
          this.cache.delete(key)
          deletedCount++
        }
      }
    } else {
      deletedCount = this.cache.size
      this.cache.clear()
    }

    return deletedCount
  }

  invalidateUserCache(userId: string): number {
    const pattern = `user:${userId}`
    return this.invalidate(pattern)
  }

  private evictLRU(): void {
    let oldestKey = ''
    let oldestTime = Date.now()

    for (const [key, entry] of this.cache.entries()) {
      if (entry.timestamp < oldestTime) {
        oldestTime = entry.timestamp
        oldestKey = key
      }
    }

    if (oldestKey) {
      this.cache.delete(oldestKey)
    }
  }

  private cleanup(): void {
    const now = Date.now()
    const keysToDelete: string[] = []

    for (const [key, entry] of this.cache.entries()) {
      if (now - entry.timestamp > entry.ttl) {
        keysToDelete.push(key)
      }
    }

    keysToDelete.forEach(key => this.cache.delete(key))

    if (keysToDelete.length > 0) {
      console.log(`清理了 ${keysToDelete.length} 个过期权限缓存`)
    }
  }

  getStats() {
    const now = Date.now()
    let validEntries = 0
    let expiredEntries = 0
    let totalHits = 0

    for (const entry of this.cache.values()) {
      if (now - entry.timestamp > entry.ttl) {
        expiredEntries++
      } else {
        validEntries++
      }
      totalHits += entry.hitCount
    }

    return {
      size: this.cache.size,
      validEntries,
      expiredEntries,
      totalHits,
      hitRate: totalHits > 0 ? totalHits / (totalHits + this.cache.size) : 0
    }
  }

  destroy() {
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer)
    }
    this.cache.clear()
  }
}

// 全局缓存管理器实例
const permissionCache = new PermissionCacheManager()

/**
 * 缓存权限管理Hook
 */
export function useCachedPermissions() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const userRef = useRef<any>(null)

  // 获取当前用户信息
  const getCurrentUser = useCallback(async () => {
    if (userRef.current) {
      return userRef.current
    }

    try {
      const { data: { user } } = await supabase.auth.getUser()
      userRef.current = user
      return user
    } catch (err) {
      console.error('获取用户信息失败:', err)
      return null
    }
  }, [])

  // 检查单个权限（带缓存）
  const checkPermission = useCallback(async (
    resourceType: 'project' | 'file' | 'system',
    resourceId: string,
    permission: string
  ): Promise<PermissionCheckResult> => {
    try {
      // 1. 尝试从缓存获取
      const cachedResult = permissionCache.get(resourceType, resourceId, permission)
      if (cachedResult !== null) {
        return {
          granted: cachedResult,
          cacheHit: true,
          source: 'cache'
        }
      }

      // 2. 从API获取
      const user = await getCurrentUser()
      if (!user) {
        throw new Error('用户未认证')
      }

      const response = await fetch('/api/v1/permissions/check', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.session?.access_token}`
        },
        body: JSON.stringify({
          resource_type: resourceType,
          resource_id: resourceId,
          permission
        })
      })

      if (!response.ok) {
        throw new Error(`权限检查失败: ${response.statusText}`)
      }

      const result = await response.json()

      // 3. 缓存结果
      permissionCache.set(resourceType, resourceId, permission, result.granted)

      return {
        granted: result.granted,
        reason: result.reason,
        cacheHit: false,
        source: 'api'
      }

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '权限检查失败'
      console.error('权限检查错误:', err)
      return {
        granted: false,
        reason: errorMessage,
        cacheHit: false,
        source: 'api'
      }
    }
  }, [getCurrentUser])

  // 批量权限检查
  const batchCheckPermissions = useCallback(async (
    requests: BatchPermissionRequest[]
  ): Promise<Record<string, PermissionCheckResult>> => {
    try {
      setLoading(true)
      setError(null)

      const user = await getCurrentUser()
      if (!user) {
        throw new Error('用户未认证')
      }

      // 1. 先从缓存获取已有的权限
      const results: Record<string, PermissionCheckResult> = {}
      const uncachedRequests: Array<{
        index: number
        request: BatchPermissionRequest
      }> = []

      requests.forEach((request, index) => {
        request.permissions.forEach(permission => {
          const key = `${index}:${request.resourceId}:${permission}`
          const cachedResult = permissionCache.get(
            request.resourceType,
            request.resourceId,
            permission
          )

          if (cachedResult !== null) {
            results[key] = {
              granted: cachedResult,
              cacheHit: true,
              source: 'cache'
            }
          } else {
            uncachedRequests.push({ index, request })
          }
        })
      })

      // 2. 批量检查未缓存的权限
      if (uncachedRequests.length > 0) {
        // 将请求分组，每批最多 CACHE_CONFIG.BATCH_SIZE 个
        const batches = []
        for (let i = 0; i < uncachedRequests.length; i += CACHE_CONFIG.BATCH_SIZE) {
          batches.push(uncachedRequests.slice(i, i + CACHE_CONFIG.BATCH_SIZE))
        }

        for (const batch of batches) {
          const apiRequests = batch.flatMap(({ request }) =>
            request.permissions.map(permission => ({
              resource_type: request.resourceType,
              resource_id: request.resourceId,
              permission
            }))
          )

          const response = await fetch('/api/v1/permissions/batch-check', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${user.session?.access_token}`
            },
            body: JSON.stringify({
              checks: apiRequests
            })
          })

          if (!response.ok) {
            throw new Error(`批量权限检查失败: ${response.statusText}`)
          }

          const batchResults = await response.json()

          // 处理批量结果
          let apiIndex = 0
          batch.forEach(({ index, request }) => {
            request.permissions.forEach(permission => {
              const key = `${index}:${request.resourceId}:${permission}`
              const apiResult = batchResults.results[apiIndex]

              if (apiResult) {
                results[key] = {
                  granted: apiResult.granted,
                  reason: apiResult.reason,
                  cacheHit: false,
                  source: 'api'
                }

                // 缓存结果
                permissionCache.set(
                  request.resourceType,
                  request.resourceId,
                  permission,
                  apiResult.granted
                )
              }

              apiIndex++
            })
          })
        }
      }

      return results

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '批量权限检查失败'
      setError(errorMessage)
      console.error('批量权限检查错误:', err)

      // 返回所有权限都为false的结果
      const errorResults: Record<string, PermissionCheckResult> = {}
      requests.forEach((request, index) => {
        request.permissions.forEach(permission => {
          const key = `${index}:${request.resourceId}:${permission}`
          errorResults[key] = {
            granted: false,
            reason: errorMessage,
            cacheHit: false,
            source: 'api'
          }
        })
      })

      return errorResults

    } finally {
      setLoading(false)
    }
  }, [getCurrentUser])

  // 预热权限缓存
  const warmUpPermissions = useCallback(async (projectIds?: string[]) => {
    try {
      const user = await getCurrentUser()
      if (!user) {
        return
      }

      const response = await fetch('/api/v1/permissions/cache/warm-up', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.session?.access_token}`
        },
        body: JSON.stringify({
          project_ids: projectIds
        })
      })

      if (!response.ok) {
        throw new Error(`权限预热失败: ${response.statusText}`)
      }

      const result = await response.json()
      console.log(`权限预热完成: ${result.message}`)

    } catch (err) {
      console.error('权限预热失败:', err)
    }
  }, [getCurrentUser])

  // 清除缓存
  const invalidateCache = useCallback((pattern?: string) => {
    return permissionCache.invalidate(pattern)
  }, [])

  // 清除用户缓存
  const invalidateUserCache = useCallback(async () => {
    try {
      const user = await getCurrentUser()
      if (!user) {
        return
      }

      // 清除本地缓存
      const deletedCount = permissionCache.invalidateUserCache(user.id)

      // 通知服务器清除缓存
      const response = await fetch('/api/v1/permissions/cache/invalidate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.session?.access_token}`
        },
        body: JSON.stringify({
          user_id: user.id
        })
      })

      if (response.ok) {
        const result = await response.json()
        console.log(`缓存清除完成: 本地${deletedCount}项, 服务器${result.deleted_count}项`)
      }

    } catch (err) {
      console.error('清除用户缓存失败:', err)
    }
  }, [getCurrentUser])

  // 获取缓存统计信息
  const getCacheStats = useCallback(() => {
    return permissionCache.getStats()
  }, [])

  // 便捷方法：检查项目权限
  const checkProjectPermission = useCallback((
    projectId: string,
    permission: string
  ) => {
    return checkPermission('project', projectId, permission)
  }, [checkPermission])

  // 便捷方法：批量检查项目权限
  const batchCheckProjectPermissions = useCallback((
    checks: Array<{ projectId: string; permissions: string[] }>
  ) => {
    const requests: BatchPermissionRequest[] = checks.map(check => ({
      resourceType: 'project' as const,
      resourceId: check.projectId,
      permissions: check.permissions
    }))

    return batchCheckPermissions(requests)
  }, [batchCheckPermissions])

  return {
    loading,
    error,
    checkPermission,
    checkProjectPermission,
    batchCheckPermissions,
    batchCheckProjectPermissions,
    warmUpPermissions,
    invalidateCache,
    invalidateUserCache,
    getCacheStats
  }
}

/**
 * 权限预加载Hook
 * 在用户登录后自动预热常用权限
 */
export function usePermissionPreload() {
  const { warmUpPermissions } = useCachedPermissions()

  const preloadUserPermissions = useCallback(async () => {
    try {
      // 预热用户的项目权限
      await warmUpPermissions()

      console.log('用户权限预加载完成')
    } catch (err) {
      console.error('权限预加载失败:', err)
    }
  }, [warmUpPermissions])

  return {
    preloadUserPermissions
  }
}

// 导出缓存管理器实例（用于调试）
export { permissionCache }

// 组件卸载时清理缓存
export function usePermissionCleanup() {
  useEffect(() => {
    return () => {
      // 组件卸载时可以选择是否清理缓存
      // permissionCache.destroy()
    }
  }, [])
}