'use client';

import React, { useState, useEffect } from 'react';
import { 
  getUsers, 
  getUserStats, 
  updateUserStatus, 
  updateUserAdminStatus,
  User,
  UserStats 
} from '@/lib/api/users';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';

/**
 * 团队管理页面组件
 * 提供管理员查看和管理团队成员的功能
 */
export default function TeamPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [stats, setStats] = useState<UserStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedUser, setSelectedUser] = useState<User | null>(null);

  // 加载用户数据
  const loadUsers = async () => {
    try {
      setLoading(true);
      
      const token = localStorage.getItem('auth-token');
      if (!token) {
        console.error('未找到认证token');
        return;
      }

      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      };

      // 直接使用fetch API调用
      const [usersResponse, statsResponse] = await Promise.all([
        fetch('http://localhost:8000/api/v1/auth/users', {
          method: 'GET',
          headers
        }),
        fetch('http://localhost:8000/api/v1/auth/users/stats/summary', {
          method: 'GET',
          headers
        })
      ]);

      if (!usersResponse.ok) {
        throw new Error(`用户API调用失败: ${usersResponse.status}`);
      }
      
      if (!statsResponse.ok) {
        throw new Error(`统计API调用失败: ${statsResponse.status}`);
      }

      const usersData = await usersResponse.json();
      const statsData = await statsResponse.json();

      setUsers(usersData);
      setStats(statsData);
      
      console.log('团队数据加载成功:', { users: usersData.length, stats: statsData });
      
    } catch (error) {
      console.error('加载用户数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 搜索用户
  const handleSearch = async () => {
    await loadUsers();
  };

  // 切换用户状态
  const toggleUserStatus = async (user: User) => {
    try {
      await updateUserStatus(user.id, !user.is_active);
      await loadUsers(); // 重新加载数据
    } catch (error) {
      console.error('更新用户状态失败:', error);
    }
  };

  // 切换管理员权限
  const toggleAdminStatus = async (user: User) => {
    try {
      const token = localStorage.getItem('auth-token');
      const response = await fetch(`http://localhost:8000/api/v1/auth/users/${user.id}/admin?is_superuser=${!user.is_superuser}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error(`更新管理员权限失败: ${response.status}`);
      }
      
      await loadUsers(); // 重新加载数据
    } catch (error) {
      console.error('更新管理员权限失败:', error);
    }
  };



  // 格式化日期
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN');
  };

  // 页面初始化
  useEffect(() => {
    loadUsers();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-gray-600">加载中...</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">团队管理</h1>
          <p className="text-sm text-gray-600 mt-1">管理团队成员权限和状态</p>
        </div>
        <Button
          onClick={loadUsers}
          className="bg-blue-600 hover:bg-blue-700 text-white"
        >
          刷新数据
        </Button>
      </div>

      {/* 权限说明 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="text-sm font-medium text-blue-900 mb-2">📋 权限级别说明</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-blue-800">
          <div>
            <div className="font-medium mb-1">👑 管理员权限：</div>
            <div>• 用户管理：创建、禁用、设置权限</div>
            <div>• 系统统计：查看所有数据统计</div>
            <div>• 文件管理：访问所有用户文件</div>
            <div>• Dashboard：完整访问权限</div>
          </div>
          <div>
            <div className="font-medium mb-1">👤 普通成员权限：</div>
            <div>• 基本功能：聊天、文件上传</div>
            <div>• 文件访问：仅限个人和共享文件</div>
            <div>• 项目参与：仅限被邀请的项目</div>
            <div>• 无Dashboard访问权限</div>
          </div>
        </div>
      </div>

      {/* 统计信息卡片 */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-lg shadow border">
            <div className="text-2xl font-bold text-blue-600">{stats.total_users}</div>
            <div className="text-sm text-gray-600">团队成员总数</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow border">
            <div className="text-2xl font-bold text-green-600">{stats.active_users}</div>
            <div className="text-sm text-gray-600">活跃成员</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow border">
            <div className="text-2xl font-bold text-yellow-600">{stats.verified_users}</div>
            <div className="text-sm text-gray-600">已验证成员</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow border">
            <div className="text-2xl font-bold text-purple-600">{stats.admin_users}</div>
            <div className="text-sm text-gray-600">管理员</div>
          </div>
        </div>
      )}

      {/* 搜索栏 */}
      <div className="bg-white p-4 rounded-lg shadow border">
        <div className="flex items-center space-x-4">
          <div className="flex-1">
            <Input
              type="text"
              placeholder="搜索团队成员..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              className="w-full"
            />
          </div>
          <Button
            onClick={handleSearch}
            className="bg-gray-600 hover:bg-gray-700 text-white px-6"
          >
            搜索
          </Button>
        </div>
      </div>

      {/* 用户列表 */}
      <div className="bg-white rounded-lg shadow border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  成员信息
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  联系方式
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  状态
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  权限
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  创建时间
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  操作
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {users.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className="flex-shrink-0 h-10 w-10">
                        {user.avatar_url ? (
                          <img 
                            className="h-10 w-10 rounded-full object-cover" 
                            src={user.avatar_url} 
                            alt={user.username}
                          />
                        ) : (
                          <div className="h-10 w-10 rounded-full bg-gray-300 flex items-center justify-center">
                            <span className="text-sm font-medium text-gray-700">
                              {user.username.charAt(0).toUpperCase()}
                            </span>
                          </div>
                        )}
                      </div>
                      <div className="ml-4">
                        <div className="text-sm font-medium text-gray-900">
                          {user.username}
                        </div>
                        <div className="text-sm text-gray-500">
                          ID: {user.id}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{user.email}</div>
                    {user.phone && (
                      <div className="text-sm text-gray-500">{user.phone}</div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      user.is_active 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {user.is_active ? '✅ 活跃' : '❌ 禁用'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex flex-col space-y-1">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        user.is_superuser 
                          ? 'bg-purple-100 text-purple-800 border border-purple-300' 
                          : 'bg-gray-100 text-gray-800'
                      }`} title={user.is_superuser ? '管理员：可以管理所有用户、查看系统统计、访问管理功能' : '普通成员：只能访问基本功能'}>
                        {user.is_superuser ? '👑 管理员' : '👤 团队成员'}
                      </span>
                      {user.is_superuser && (
                        <span className="text-xs text-purple-600 font-medium">
                          🔧 系统管理权限
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {formatDate(user.created_at)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-y-1">
                    <div className="flex flex-col space-y-1">
                      <Button
                        onClick={() => toggleUserStatus(user)}
                        className={`text-xs px-2 py-1 ${
                          user.is_active 
                            ? 'bg-red-100 text-red-700 hover:bg-red-200' 
                            : 'bg-green-100 text-green-700 hover:bg-green-200'
                        }`}
                      >
                        {user.is_active ? '❌ 禁用' : '✅ 启用'}
                      </Button>
                      <Button
                        onClick={() => toggleAdminStatus(user)}
                        className={`text-xs px-2 py-1 ${
                          user.is_superuser 
                            ? 'bg-orange-100 text-orange-700 hover:bg-orange-200' 
                            : 'bg-purple-100 text-purple-700 hover:bg-purple-200'
                        }`}
                      >
                        {user.is_superuser ? '👑 取消管理员' : '👑 设为管理员'}
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 空状态 */}
      {users.length === 0 && !loading && (
        <div className="text-center py-12">
          <div className="text-gray-500 text-lg">
            {searchTerm ? '未找到匹配的团队成员' : '暂无团队成员数据'}
          </div>
        </div>
      )}
    </div>
  );
}
