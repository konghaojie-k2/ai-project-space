import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { User, Session, AuthError } from '@supabase/supabase-js'
import { supabase } from '@/lib/supabase/client'
import { AuthUser, AuthSession } from '@/types/database'

/**
 * Supabase认证状态Hook
 */
export function useSupabaseAuth() {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [session, setSession] = useState<AuthSession | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  // 初始化认证状态
  useEffect(() => {
    // 获取初始会话
    const getInitialSession = async () => {
      try {
        const { data: { session }, error } = await supabase.auth.getSession()

        if (error) {
          console.error('获取会话失败:', error)
          setError(error.message)
        } else {
          setSession(session as AuthSession)
          setUser(session?.user as AuthUser || null)
        }
      } catch (err) {
        console.error('认证初始化错误:', err)
        setError('认证初始化失败')
      } finally {
        setLoading(false)
      }
    }

    getInitialSession()

    // 监听认证状态变化
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        console.log('认证状态变化:', event, session?.user?.email)

        setSession(session as AuthSession)
        setUser(session?.user as AuthUser || null)
        setLoading(false)
        setError(null)

        // 根据事件类型处理路由
        if (event === 'SIGNED_IN') {
          router.refresh()
        } else if (event === 'SIGNED_OUT') {
          router.push('/login')
          router.refresh()
        }
      }
    )

    return () => subscription.unsubscribe()
  }, [router])

  // 登录
  const signIn = useCallback(async (email: string, password: string) => {
    try {
      setLoading(true)
      setError(null)

      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      })

      if (error) {
        throw error
      }

      return data as AuthSession
    } catch (err) {
      const authError = err as AuthError
      const errorMessage = authError.message || '登录失败'
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  // 注册
  const signUp = useCallback(async (email: string, password: string, options?: {
    username?: string
    fullName?: string
  }) => {
    try {
      setLoading(true)
      setError(null)

      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            username: options?.username,
            full_name: options?.fullName,
          },
        },
      })

      if (error) {
        throw error
      }

      return data
    } catch (err) {
      const authError = err as AuthError
      const errorMessage = authError.message || '注册失败'
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  // 登出
  const signOut = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const { error } = await supabase.auth.signOut()

      if (error) {
        throw error
      }
    } catch (err) {
      const authError = err as AuthError
      const errorMessage = authError.message || '登出失败'
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  // 重置密码
  const resetPassword = useCallback(async (email: string) => {
    try {
      setLoading(true)
      setError(null)

      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/auth/reset-password`,
      })

      if (error) {
        throw error
      }
    } catch (err) {
      const authError = err as AuthError
      const errorMessage = authError.message || '密码重置失败'
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  // 更新密码
  const updatePassword = useCallback(async (newPassword: string) => {
    try {
      setLoading(true)
      setError(null)

      const { error } = await supabase.auth.updateUser({
        password: newPassword,
      })

      if (error) {
        throw error
      }
    } catch (err) {
      const authError = err as AuthError
      const errorMessage = authError.message || '密码更新失败'
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  // 更新用户资料
  const updateProfile = useCallback(async (updates: {
    username?: string
    full_name?: string
    avatar_url?: string
    bio?: string
    phone?: string
    department?: string
    position?: string
  }) => {
    try {
      setLoading(true)
      setError(null)

      const { data, error } = await supabase.auth.updateUser({
        data: updates,
      })

      if (error) {
        throw error
      }

      // 同时更新profiles表
      if (user) {
        const { error: profileError } = await supabase
          .from('profiles')
          .update(updates)
          .eq('id', user.id)

        if (profileError) {
          throw profileError
        }
      }

      return data
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '更新资料失败'
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [user])

  // 刷新token
  const refreshSession = useCallback(async () => {
    try {
      setError(null)

      const { data, error } = await supabase.auth.refreshSession()

      if (error) {
        throw error
      }

      return data as AuthSession
    } catch (err) {
      const authError = err as AuthError
      const errorMessage = authError.message || '刷新会话失败'
      setError(errorMessage)
      throw new Error(errorMessage)
    }
  }, [])

  // 检查用户是否已认证
  const isAuthenticated = useCallback(() => {
    return !!user && !!session
  }, [user, session])

  // 检查是否为超级管理员
  const isSuperUser = useCallback(() => {
    return user?.app_metadata?.is_superuser || user?.user_metadata?.is_superuser || false
  }, [user])

  // 获取用户显示名称
  const getDisplayName = useCallback(() => {
    if (!user) return null

    return user.user_metadata?.full_name ||
           user.user_metadata?.name ||
           user.email?.split('@')[0] ||
           'Unknown User'
  }, [user])

  // 获取用户头像
  const getAvatarUrl = useCallback(() => {
    return user?.user_metadata?.avatar_url ||
           user?.user_metadata?.picture ||
           null
  }, [user])

  // 清除错误
  const clearError = useCallback(() => {
    setError(null)
  }, [])

  return {
    // 状态
    user,
    session,
    loading,
    error,
    isAuthenticated: isAuthenticated(),
    isSuperUser: isSuperUser(),

    // 用户信息
    displayName: getDisplayName(),
    avatarUrl: getAvatarUrl(),

    // 方法
    signIn,
    signUp,
    signOut,
    resetPassword,
    updatePassword,
    updateProfile,
    refreshSession,
    clearError,
  }
}

/**
 * 受保护的组件Hook
 * 检查用户是否已认证，未认证则跳转到登录页
 */
export function useRequireAuth() {
  const { user, loading } = useSupabaseAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading && !user) {
      router.push('/login')
    }
  }, [user, loading, router])

  return { user, loading }
}

/**
 * 超级管理员权限Hook
 * 检查用户是否有超级管理员权限
 */
export function useRequireSuperUser() {
  const { user, loading, isSuperUser } = useSupabaseAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading && (!user || !isSuperUser)) {
      router.push('/unauthorized')
    }
  }, [user, isSuperUser, loading, router])

  return { user, loading, isSuperUser }
}