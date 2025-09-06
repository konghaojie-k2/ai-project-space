'use client';

import React, { useState, useEffect } from 'react';
import { useUserStore } from '@/lib/stores/userStore';
import { 
  UserIcon, 
  CheckCircleIcon, 
  XCircleIcon, 
  ClockIcon,
  ShieldCheckIcon,
  KeyIcon,
  EyeIcon,
  EyeSlashIcon
} from '@heroicons/react/24/outline';

/**
 * 用户状态指示器组件
 * 实时显示用户登录状态和认证信息
 */
export default function UserStatusIndicator() {
  const { user, isAuthenticated, isLoading } = useUserStore();
  const [isExpanded, setIsExpanded] = useState(false);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [userStorage, setUserStorage] = useState<any>(null);

  // 实时监控本地存储
  useEffect(() => {
    const updateTokens = () => {
      setAuthToken(localStorage.getItem('auth-token'));
      setRefreshToken(localStorage.getItem('refresh-token'));
      
      const userStorageData = localStorage.getItem('user-storage');
      if (userStorageData) {
        try {
          setUserStorage(JSON.parse(userStorageData));
        } catch (error) {
          setUserStorage(null);
        }
      } else {
        setUserStorage(null);
      }
    };

    // 初始加载
    updateTokens();

    // 监听存储变化
    const handleStorageChange = () => {
      updateTokens();
    };

    window.addEventListener('storage', handleStorageChange);
    
    // 定期检查（因为同页面的localStorage变化不会触发storage事件）
    const interval = setInterval(updateTokens, 1000);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
      clearInterval(interval);
    };
  }, []);

  const getStatusColor = () => {
    if (isLoading) return 'bg-yellow-500';
    if (isAuthenticated && user) return 'bg-green-500';
    if (authToken) return 'bg-orange-500'; // 有token但状态不一致
    return 'bg-red-500';
  };

  const getStatusText = () => {
    if (isLoading) return '加载中...';
    if (isAuthenticated && user) return '已登录';
    if (authToken) return '状态异常';
    return '未登录';
  };

  return (
    <div className="fixed top-4 right-4 z-50">
      {/* 状态指示器 */}
      <div 
        className={`flex items-center space-x-2 px-3 py-2 rounded-lg shadow-lg cursor-pointer transition-all ${
          isExpanded ? 'bg-white border' : 'bg-white/90 backdrop-blur-sm'
        }`}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className={`w-3 h-3 rounded-full ${getStatusColor()}`}></div>
        <span className="text-sm font-medium text-gray-700">
          {getStatusText()}
        </span>
        {isExpanded ? (
          <EyeSlashIcon className="w-4 h-4 text-gray-500" />
        ) : (
          <EyeIcon className="w-4 h-4 text-gray-500" />
        )}
      </div>

      {/* 详细信息面板 */}
      {isExpanded && (
        <div className="mt-2 bg-white border rounded-lg shadow-lg p-4 w-80 max-h-96 overflow-y-auto">
          <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
            <UserIcon className="w-5 h-5 mr-2" />
            用户状态详情
          </h3>

          {/* Zustand 状态 */}
          <div className="mb-4">
            <h4 className="text-sm font-medium text-gray-700 mb-2">🏪 Zustand 状态</h4>
            <div className="space-y-1 text-xs">
              <div className="flex items-center justify-between">
                <span>isAuthenticated:</span>
                <span className={`px-2 py-1 rounded ${isAuthenticated ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                  {isAuthenticated ? '✅ true' : '❌ false'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>isLoading:</span>
                <span className={`px-2 py-1 rounded ${isLoading ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-800'}`}>
                  {isLoading ? '⏳ true' : '✅ false'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>hasUser:</span>
                <span className={`px-2 py-1 rounded ${user ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                  {user ? '✅ true' : '❌ false'}
                </span>
              </div>
            </div>
          </div>

          {/* 用户信息 */}
          {user && (
            <div className="mb-4">
              <h4 className="text-sm font-medium text-gray-700 mb-2">👤 用户信息</h4>
              <div className="space-y-1 text-xs">
                <div><strong>用户名:</strong> {user.username}</div>
                <div><strong>邮箱:</strong> {user.email}</div>
                <div className="flex items-center">
                  <strong>权限:</strong>
                  <span className={`ml-2 px-2 py-1 rounded ${user.is_superuser ? 'bg-purple-100 text-purple-800' : 'bg-gray-100 text-gray-800'}`}>
                    {user.is_superuser ? (
                      <>
                        <ShieldCheckIcon className="w-3 h-3 inline mr-1" />
                        管理员
                      </>
                    ) : (
                      <>
                        <UserIcon className="w-3 h-3 inline mr-1" />
                        普通用户
                      </>
                    )}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Token 状态 */}
          <div className="mb-4">
            <h4 className="text-sm font-medium text-gray-700 mb-2">🔑 Token 状态</h4>
            <div className="space-y-1 text-xs">
              <div className="flex items-center justify-between">
                <span>Auth Token:</span>
                <span className={`px-2 py-1 rounded ${authToken ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                  {authToken ? `✅ ${authToken.substring(0, 10)}...` : '❌ 无'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Refresh Token:</span>
                <span className={`px-2 py-1 rounded ${refreshToken ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                  {refreshToken ? `✅ ${refreshToken.substring(0, 10)}...` : '❌ 无'}
                </span>
              </div>
            </div>
          </div>

          {/* 本地存储状态 */}
          <div className="mb-4">
            <h4 className="text-sm font-medium text-gray-700 mb-2">💾 本地存储</h4>
            <div className="space-y-1 text-xs">
              <div className="flex items-center justify-between">
                <span>User Storage:</span>
                <span className={`px-2 py-1 rounded ${userStorage ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                  {userStorage ? '✅ 存在' : '❌ 无'}
                </span>
              </div>
              {userStorage && (
                <div className="mt-2 p-2 bg-gray-50 rounded text-xs">
                  <pre className="whitespace-pre-wrap">
                    {JSON.stringify(userStorage, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => {
                console.log('🔄 手动触发状态检查');
                useUserStore.getState().checkAuthStatus?.();
              }}
              className="px-3 py-1 bg-blue-100 text-blue-800 rounded text-xs hover:bg-blue-200"
            >
              检查状态
            </button>
            <button
              onClick={async () => {
                console.log('🔄 强制恢复认证状态');
                const { authRecovery } = await import('@/lib/utils/auth-recovery');
                const result = await authRecovery.forceRecovery();
                console.log('🔄 强制恢复结果:', result);
              }}
              className="px-3 py-1 bg-green-100 text-green-800 rounded text-xs hover:bg-green-200"
            >
              强制恢复
            </button>
            <button
              onClick={() => {
                console.log('🧹 清除所有认证数据');
                localStorage.removeItem('auth-token');
                localStorage.removeItem('refresh-token');
                localStorage.removeItem('user-storage');
                useUserStore.setState({
                  user: null,
                  isAuthenticated: false,
                  isLoading: false
                });
              }}
              className="px-3 py-1 bg-red-100 text-red-800 rounded text-xs hover:bg-red-200"
            >
              清除状态
            </button>
            <button
              onClick={async () => {
                console.log('📊 获取恢复状态报告');
                const { authRecovery } = await import('@/lib/utils/auth-recovery');
                const status = authRecovery.getRecoveryStatus();
                console.log('📊 恢复状态报告:', status);
              }}
              className="px-3 py-1 bg-purple-100 text-purple-800 rounded text-xs hover:bg-purple-200"
            >
              状态报告
            </button>
          </div>

          {/* 时间戳 */}
          <div className="mt-3 pt-3 border-t text-xs text-gray-500 flex items-center">
            <ClockIcon className="w-3 h-3 mr-1" />
            {new Date().toLocaleTimeString()}
          </div>
        </div>
      )}
    </div>
  );
}
