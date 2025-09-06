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
import { 
  UsersIcon,
  MagnifyingGlassIcon,
  UserPlusIcon,
  CogIcon,
  EyeIcon,
  ShieldCheckIcon,
  UserIcon,
  StarIcon,
  FolderIcon,
  PlusIcon,
  TrashIcon,
  ArrowLeftIcon
} from '@heroicons/react/24/outline';
import { apiGet, apiPost, apiPut, apiDelete } from '@/lib/api';
import { requestManager } from '@/lib/utils/request-manager';
import DashboardPageHeader from '@/components/layout/DashboardPageHeader';

// 项目成员相关类型
interface ProjectMember {
  project_id: string;
  user_id: number;
  username: string;
  email: string;
  role: 'owner' | 'admin' | 'member' | 'viewer';
  joined_at: string;
}

interface Project {
  id: string;
  name: string;
  description?: string;
  stage: string;
  status: string;
  created_at: string;
}

/**
 * 团队管理页面组件
 * 提供管理员查看和管理团队成员的功能，包含用户管理和项目团队管理
 */
export default function TeamPage() {
  // 标签页状态
  const [activeTab, setActiveTab] = useState<'users' | 'projects'>('users');
  
  // 用户管理相关状态
  const [users, setUsers] = useState<User[]>([]);
  const [stats, setStats] = useState<UserStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedUser, setSelectedUser] = useState<User | null>(null);

  // 项目团队相关状态
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [projectMembers, setProjectMembers] = useState<ProjectMember[]>([]);
  const [projectLoading, setProjectLoading] = useState(false);
  const [showAddMemberModal, setShowAddMemberModal] = useState(false);
  const [newMemberEmail, setNewMemberEmail] = useState('');
  const [newMemberRole, setNewMemberRole] = useState<'owner' | 'admin' | 'member' | 'viewer'>('member');
  const [showEditMemberModal, setShowEditMemberModal] = useState(false);
  const [editingMember, setEditingMember] = useState<ProjectMember | null>(null);

  // 角色图标映射
  const getRoleIcon = (role: string) => {
    const normalizedRole = role.toLowerCase();
    switch (normalizedRole) {
      case 'owner':
        return <StarIcon className="w-4 h-4 text-yellow-500" />;
      case 'admin':
        return <ShieldCheckIcon className="w-4 h-4 text-blue-500" />;
      case 'member':
        return <UserIcon className="w-4 h-4 text-green-500" />;
      case 'viewer':
        return <EyeIcon className="w-4 h-4 text-gray-500" />;
      default:
        return <UserIcon className="w-4 h-4 text-gray-500" />;
    }
  };

  // 角色名称映射
  const getRoleName = (role: string) => {
    const normalizedRole = role.toLowerCase();
    switch (normalizedRole) {
      case 'owner': return '项目负责人';
      case 'admin': return '管理员';
      case 'member': return '成员';
      case 'viewer': return '观察者';
      default: return '未知';
    }
  };

  // 加载用户数据
  const loadUsers = async () => {
    return requestManager.executeRequest('load-users', async () => {
      console.log('📊 开始加载用户数据...');
      setLoading(true);
      
      try {
        const token = localStorage.getItem('auth-token');
        if (!token) {
          console.error('未找到认证token');
          return;
        }

        const [usersResponse, statsResponse] = await Promise.all([
          apiGet('/api/v1/auth/users'),
          apiGet('/api/v1/auth/users/stats/summary')
        ]);

        if (!usersResponse.ok) {
          throw new Error(`用户API调用失败: ${usersResponse.status}`);
        }

        if (!statsResponse.ok) {
          throw new Error(`统计API调用失败: ${statsResponse.status}`);
        }

        const usersData = await usersResponse.json();
        const statsData = await statsResponse.json();

        console.log('✅ 用户数据加载成功:', { userCount: usersData?.length, stats: statsData });

        setUsers(usersData || []);
        setStats(statsData || null);
      } catch (error) {
        console.error('❌ 加载用户数据失败:', error);
        throw error;
      } finally {
        setLoading(false);
      }
    });
  };

  // 加载项目数据
  const loadProjects = async () => {
    if (projectLoading) {
      console.log('⏳ 项目数据正在加载中，跳过重复请求');
      return;
    }

    try {
      console.log('📁 开始加载项目数据...');
      setProjectLoading(true);
      const projectsResponse = await apiGet('/api/v1/projects/');

      if (projectsResponse.ok) {
        const projectsData = await projectsResponse.json();
        console.log('✅ 项目列表加载成功:', { projectCount: projectsData?.length });
        setProjects(projectsData || []);
      } else {
        console.warn('⚠️ 项目列表加载失败:', projectsResponse.status);
      }
    } catch (error) {
      console.error('❌ 加载项目数据失败:', error);
    } finally {
      setProjectLoading(false);
    }
  };

  // 加载项目成员
  const loadProjectMembers = async (projectId: string) => {
    try {
      const response = await apiGet(`/api/v1/projects/${projectId}/members`);
      if (response.ok) {
        const data = await response.json();
        setProjectMembers(data || []);
      }
    } catch (error) {
      console.error('加载项目成员失败:', error);
    }
  };

  // 搜索处理
  const handleSearch = () => {
    console.log('搜索:', searchTerm);
  };

  // 切换用户状态
  const toggleUserStatus = async (userId: number, currentStatus: boolean) => {
    try {
      const { apiRequest } = await import('@/lib/api');
      const response = await apiRequest(`/api/v1/auth/users/${userId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ is_active: !currentStatus })
      });

      if (!response.ok) {
        throw new Error('更新用户状态失败');
      }

      await loadUsers(); // 重新加载数据
    } catch (error) {
      console.error('更新用户状态失败:', error);
    }
  };

  // 切换管理员权限
  const toggleAdminStatus = async (userId: number, currentStatus: boolean) => {
    try {
      const { apiRequest } = await import('@/lib/api');
      const response = await apiRequest(`/api/v1/auth/users/${userId}/admin`, {
        method: 'PATCH',
        body: JSON.stringify({ is_superuser: !currentStatus })
      });

      if (!response.ok) {
        throw new Error('更新管理员权限失败');
      }

      await loadUsers(); // 重新加载数据
    } catch (error) {
      console.error('更新管理员权限失败:', error);
    }
  };

  // 选择项目
  const handleSelectProject = (project: Project) => {
    setSelectedProject(project);
    loadProjectMembers(project.id);
  };

  // 添加项目成员
  const handleAddMember = async () => {
    if (!selectedProject || !newMemberEmail.trim()) {
      alert('请输入有效的邮箱地址');
      return;
    }

    try {
      console.log('➕ 添加项目成员:', { email: newMemberEmail, role: newMemberRole });
      
      await apiPost(`/api/v1/projects/${selectedProject.id}/members`, {
        email: newMemberEmail,
        role: newMemberRole
      });

      // 重新加载项目成员
      loadProjectMembers(selectedProject.id);
      
      // 重置表单
      setNewMemberEmail('');
      setNewMemberRole('member');
      setShowAddMemberModal(false);
      
      alert('成员添加成功！');
    } catch (error) {
      console.error('❌ 添加成员失败:', error);
      alert('添加成员失败，请检查邮箱是否存在');
    }
  };

  // 编辑成员角色
  const handleEditMember = (member: ProjectMember) => {
    setEditingMember(member);
    setShowEditMemberModal(true);
  };

  // 更新成员角色
  const handleUpdateMemberRole = async (newRole: 'owner' | 'admin' | 'member' | 'viewer') => {
    if (!editingMember || !selectedProject) return;

    try {
      console.log('🔄 更新成员角色:', { memberId: editingMember.user_id, newRole });
      
      await apiPut(`/api/v1/projects/${selectedProject.id}/members/${editingMember.user_id}`, {
        role: newRole
      });

      // 重新加载项目成员
      loadProjectMembers(selectedProject.id);
      
      setShowEditMemberModal(false);
      setEditingMember(null);
      
      alert('成员角色更新成功！');
    } catch (error) {
      console.error('❌ 更新成员角色失败:', error);
      alert('更新成员角色失败');
    }
  };

  // 移除项目成员
  const handleRemoveMember = async (member: ProjectMember) => {
    if (!selectedProject) return;
    
    if (!confirm(`确定要从项目中移除 ${member.username} 吗？`)) {
      return;
    }

    try {
      console.log('🗑️ 移除项目成员:', member.user_id);
      
      await apiDelete(`/api/v1/projects/${selectedProject.id}/members/${member.user_id}`);

      // 重新加载项目成员
      loadProjectMembers(selectedProject.id);
      
      alert('成员移除成功！');
    } catch (error) {
      console.error('❌ 移除成员失败:', error);
      alert('移除成员失败');
    }
  };

  // 格式化日期
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN');
  };

  // 页面初始化
  useEffect(() => {
    console.log('🔄 TeamPage useEffect 触发:', { activeTab });
    loadUsers();
  }, []); // 只在组件挂载时执行一次

  // 单独处理项目数据加载
  useEffect(() => {
    if (activeTab === 'projects') {
      console.log('📁 加载项目数据...');
      loadProjects();
    }
  }, [activeTab]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-gray-600">加载中...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 页面头部 */}
      <DashboardPageHeader
        title="团队管理"
        description="管理团队成员权限和项目团队"
        actions={
          <Button
            onClick={() => activeTab === 'users' ? loadUsers() : loadProjects()}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            刷新数据
          </Button>
        }
      />

      <div className="p-6 space-y-6">

      {/* 标签页导航 */}
      <div className="bg-white rounded-lg shadow border">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8 px-6">
            <button
              onClick={() => setActiveTab('users')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'users'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center space-x-2">
                <UsersIcon className="w-5 h-5" />
                <span>用户管理</span>
              </div>
            </button>
            <button
              onClick={() => setActiveTab('projects')}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'projects'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center space-x-2">
                <FolderIcon className="w-5 h-5" />
                <span>项目团队</span>
              </div>
            </button>
          </nav>
        </div>

        {/* 标签页内容 */}
        <div className="p-6">
          {activeTab === 'users' ? (
            // 用户管理标签页
            <div className="space-y-6">
              {/* 用户状态说明 */}
              <div className="bg-green-50 border border-green-200 rounded-lg p-6">
                <div className="flex items-center mb-4">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
                      <UsersIcon className="w-5 h-5 text-green-600" />
                    </div>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-lg font-semibold text-gray-900">用户状态说明</h3>
                    <p className="text-sm text-gray-600">了解不同用户状态的含义</p>
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* 活跃状态 */}
                  <div className="bg-white rounded-lg p-4 border border-green-200 shadow-sm">
                    <div className="flex items-center mb-3">
                      <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800 mr-3">
                        ✅ 活跃
                      </span>
                      <h4 className="font-semibold text-gray-900">正常用户</h4>
                    </div>
                    <ul className="space-y-2 text-sm text-gray-700">
                      <li className="flex items-start">
                        <span className="text-green-500 mr-2">•</span>
                        <span>可以正常登录系统</span>
                      </li>
                      <li className="flex items-start">
                        <span className="text-green-500 mr-2">•</span>
                        <span>享有完整功能权限</span>
                      </li>
                      <li className="flex items-start">
                        <span className="text-green-500 mr-2">•</span>
                        <span>可以参与项目协作</span>
                      </li>
                    </ul>
                  </div>

                  {/* 禁用状态 */}
                  <div className="bg-white rounded-lg p-4 border border-red-200 shadow-sm">
                    <div className="flex items-center mb-3">
                      <span className="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800 mr-3">
                        ❌ 禁用
                      </span>
                      <h4 className="font-semibold text-gray-900">受限用户</h4>
                    </div>
                    <ul className="space-y-2 text-sm text-gray-700">
                      <li className="flex items-start">
                        <span className="text-red-500 mr-2">•</span>
                        <span>无法登录系统</span>
                      </li>
                      <li className="flex items-start">
                        <span className="text-red-500 mr-2">•</span>
                        <span>暂停所有功能权限</span>
                      </li>
                      <li className="flex items-start">
                        <span className="text-red-500 mr-2">•</span>
                        <span>保留用户数据和历史</span>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>


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
                          创建时间
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
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {formatDate(user.created_at)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : (
            // 项目团队标签页
            <div className="space-y-6">
              {/* 权限级别说明 */}
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-6 shadow-sm">
                <div className="flex items-center mb-6">
                  <div className="flex-shrink-0">
                    <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                      <ShieldCheckIcon className="w-6 h-6 text-blue-600" />
                    </div>
                  </div>
                  <div className="ml-4">
                    <h3 className="text-xl font-bold text-gray-900">项目权限体系</h3>
                    <p className="text-sm text-gray-600">了解不同角色的权限范围和职责</p>
                  </div>
                </div>
                
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                  {/* 项目负责人 */}
                  <div className="bg-white rounded-lg p-4 border border-yellow-200 shadow-sm">
                    <div className="flex items-center mb-3">
                      <StarIcon className="w-5 h-5 text-yellow-500 mr-2" />
                      <h4 className="font-semibold text-gray-900">项目负责人</h4>
                    </div>
                    <ul className="space-y-2 text-sm text-gray-700">
                      <li className="flex items-start">
                        <span className="text-yellow-500 mr-2">•</span>
                        <span>完全控制项目设置</span>
                      </li>
                      <li className="flex items-start">
                        <span className="text-yellow-500 mr-2">•</span>
                        <span>管理所有项目成员</span>
                      </li>
                      <li className="flex items-start">
                        <span className="text-yellow-500 mr-2">•</span>
                        <span>删除和归档项目</span>
                      </li>
                    </ul>
                  </div>

                  {/* 项目管理员 */}
                  <div className="bg-white rounded-lg p-4 border border-blue-200 shadow-sm">
                    <div className="flex items-center mb-3">
                      <ShieldCheckIcon className="w-5 h-5 text-blue-500 mr-2" />
                      <h4 className="font-semibold text-gray-900">项目管理员</h4>
                    </div>
                    <ul className="space-y-2 text-sm text-gray-700">
                      <li className="flex items-start">
                        <span className="text-blue-500 mr-2">•</span>
                        <span>管理项目成员权限</span>
                      </li>
                      <li className="flex items-start">
                        <span className="text-blue-500 mr-2">•</span>
                        <span>查看所有项目文件</span>
                      </li>
                      <li className="flex items-start">
                        <span className="text-blue-500 mr-2">•</span>
                        <span>修改项目基本信息</span>
                      </li>
                    </ul>
                  </div>

                  {/* 项目成员 */}
                  <div className="bg-white rounded-lg p-4 border border-green-200 shadow-sm">
                    <div className="flex items-center mb-3">
                      <UserIcon className="w-5 h-5 text-green-500 mr-2" />
                      <h4 className="font-semibold text-gray-900">项目成员</h4>
                    </div>
                    <ul className="space-y-2 text-sm text-gray-700">
                      <li className="flex items-start">
                        <span className="text-green-500 mr-2">•</span>
                        <span>参与项目协作</span>
                      </li>
                      <li className="flex items-start">
                        <span className="text-green-500 mr-2">•</span>
                        <span>上传和下载文件</span>
                      </li>
                      <li className="flex items-start">
                        <span className="text-green-500 mr-2">•</span>
                        <span>使用AI聊天功能</span>
                      </li>
                    </ul>
                  </div>

                  {/* 观察者 */}
                  <div className="bg-white rounded-lg p-4 border border-gray-200 shadow-sm">
                    <div className="flex items-center mb-3">
                      <EyeIcon className="w-5 h-5 text-gray-500 mr-2" />
                      <h4 className="font-semibold text-gray-900">观察者</h4>
                    </div>
                    <ul className="space-y-2 text-sm text-gray-700">
                      <li className="flex items-start">
                        <span className="text-gray-500 mr-2">•</span>
                        <span>只读访问项目</span>
                      </li>
                      <li className="flex items-start">
                        <span className="text-gray-500 mr-2">•</span>
                        <span>查看项目文件</span>
                      </li>
                      <li className="flex items-start">
                        <span className="text-gray-500 mr-2">•</span>
                        <span>无编辑和上传权限</span>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>


              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* 项目列表 */}
                <div className="lg:col-span-1">
                  <div className="bg-white rounded-lg shadow border">
                    <div className="p-4 border-b border-gray-200">
                      <h3 className="text-lg font-medium text-gray-900">项目列表</h3>
                      <p className="text-sm text-gray-600">选择项目查看团队成员</p>
                    </div>
                    <div className="p-4 space-y-2 max-h-96 overflow-y-auto">
                      {projectLoading ? (
                        <div className="text-center py-4">
                          <div className="text-sm text-gray-500">加载中...</div>
                        </div>
                      ) : projects.length === 0 ? (
                        <div className="text-center py-4">
                          <div className="text-sm text-gray-500">暂无项目</div>
                        </div>
                      ) : (
                        projects.map((project) => (
                          <div
                            key={project.id}
                            onClick={() => handleSelectProject(project)}
                            className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                              selectedProject?.id === project.id
                                ? 'bg-blue-50 border-blue-200'
                                : 'bg-gray-50 border-gray-200 hover:bg-gray-100'
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex-1 min-w-0">
                                <h4 className="text-sm font-medium text-gray-900 truncate">
                                  {project.name}
                                </h4>
                                <p className="text-xs text-gray-500 mt-1">
                                  {project.stage} • {project.status}
                                </p>
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>

                {/* 项目成员详情 */}
                <div className="lg:col-span-2">
                  {selectedProject ? (
                    <div className="bg-white rounded-lg shadow border">
                      <div className="p-4 border-b border-gray-200">
                        <div className="flex items-center justify-between">
                          <div>
                            <h3 className="text-lg font-medium text-gray-900">
                              {selectedProject.name} - 团队成员
                            </h3>
                            <p className="text-sm text-gray-600">
                              {projectMembers.length} 名成员
                            </p>
                          </div>
                          <Button
                            onClick={() => setShowAddMemberModal(true)}
                            className="bg-blue-600 hover:bg-blue-700 text-white"
                          >
                            <UserPlusIcon className="w-4 h-4 mr-2" />
                            添加成员
                          </Button>
                        </div>
                      </div>
                      <div className="p-4">
                        {projectMembers.length === 0 ? (
                          <div className="text-center py-8">
                            <UsersIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                            <div className="text-sm text-gray-500">该项目暂无团队成员</div>
                          </div>
                        ) : (
                          <div className="space-y-3">
                            {projectMembers.map((member) => (
                              <div
                                key={`${member.project_id}-${member.user_id}`}
                                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                              >
                                <div className="flex items-center space-x-3">
                                  <div className="flex-shrink-0">
                                    <div className="h-8 w-8 rounded-full bg-gray-300 flex items-center justify-center">
                                      <span className="text-xs font-medium text-gray-700">
                                        {member.username.charAt(0).toUpperCase()}
                                      </span>
                                    </div>
                                  </div>
                                  <div>
                                    <div className="text-sm font-medium text-gray-900">
                                      {member.username}
                                    </div>
                                    <div className="text-xs text-gray-500">
                                      {member.email}
                                    </div>
                                  </div>
                                </div>
                                <div className="flex items-center space-x-3">
                                  <div className="flex items-center space-x-1">
                                    {getRoleIcon(member.role)}
                                    <span className="text-sm text-gray-700">
                                      {getRoleName(member.role)}
                                    </span>
                                  </div>
                                  <div className="flex items-center space-x-1">
                                    <Button
                                      onClick={() => handleEditMember(member)}
                                      className="text-xs px-2 py-1 bg-gray-100 text-gray-700 hover:bg-gray-200"
                                      title="编辑角色"
                                    >
                                      <CogIcon className="w-3 h-3" />
                                    </Button>
                                    <Button
                                      onClick={() => handleRemoveMember(member)}
                                      className="text-xs px-2 py-1 bg-red-100 text-red-700 hover:bg-red-200"
                                      title="移除成员"
                                    >
                                      <TrashIcon className="w-3 h-3" />
                                    </Button>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="bg-white rounded-lg shadow border">
                      <div className="p-8 text-center">
                        <FolderIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                        <div className="text-sm text-gray-500">请选择一个项目查看团队成员</div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 添加成员模态框 */}
      {showAddMemberModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              添加项目成员
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  邮箱地址
                </label>
                <Input
                  type="email"
                  value={newMemberEmail}
                  onChange={(e) => setNewMemberEmail(e.target.value)}
                  placeholder="输入用户邮箱"
                  className="w-full"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  角色权限
                </label>
                <select
                  value={newMemberRole}
                  onChange={(e) => setNewMemberRole(e.target.value as any)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="viewer">观察者 - 只读权限</option>
                  <option value="member">成员 - 基本权限</option>
                  <option value="admin">管理员 - 管理权限</option>
                  <option value="owner">负责人 - 完全权限</option>
                </select>
              </div>
            </div>
            <div className="flex justify-end space-x-3 mt-6">
              <Button
                onClick={() => {
                  setShowAddMemberModal(false);
                  setNewMemberEmail('');
                  setNewMemberRole('member');
                }}
                className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200"
              >
                取消
              </Button>
              <Button
                onClick={handleAddMember}
                className="px-4 py-2 bg-blue-600 text-white hover:bg-blue-700"
              >
                添加成员
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* 编辑成员角色模态框 */}
      {showEditMemberModal && editingMember && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              编辑成员角色
            </h3>
            <div className="mb-4">
              <div className="text-sm text-gray-600 mb-2">
                成员: {editingMember.username} ({editingMember.email})
              </div>
              <div className="text-sm text-gray-600">
                当前角色: {getRoleName(editingMember.role)}
              </div>
            </div>
            <div className="space-y-2">
              {(['viewer', 'member', 'admin', 'owner'] as const).map((role) => (
                <button
                  key={role}
                  onClick={() => handleUpdateMemberRole(role)}
                  className={`w-full text-left px-4 py-3 rounded-lg border transition-colors ${
                    editingMember.role.toLowerCase() === role.toLowerCase()
                      ? 'bg-blue-50 border-blue-200 text-blue-800'
                      : 'bg-gray-50 border-gray-200 text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    {getRoleIcon(role)}
                    <div>
                      <div className="font-medium">{getRoleName(role)}</div>
                      <div className="text-xs text-gray-500">
                        {role === 'owner' && '完全控制项目和成员'}
                        {role === 'admin' && '管理项目成员和设置'}
                        {role === 'member' && '参与项目和查看文件'}
                        {role === 'viewer' && '只能查看项目内容'}
                      </div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
            <div className="flex justify-end space-x-3 mt-6">
              <Button
                onClick={() => {
                  setShowEditMemberModal(false);
                  setEditingMember(null);
                }}
                className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200"
              >
                取消
              </Button>
            </div>
          </div>
        </div>
      )}
      </div>
    </div>
  );
}