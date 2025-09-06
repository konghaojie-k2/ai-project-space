'use client';

import React, { useState, useEffect } from 'react';
import { 
  UsersIcon,
  UserIcon,
  ShieldCheckIcon,
  EyeIcon,
  StarIcon
} from '@heroicons/react/24/outline';

interface ProjectMember {
  project_id: string;
  user_id: number;
  username: string;
  email: string;
  full_name?: string;
  avatar_url?: string;
  department?: string;
  position?: string;
  role: 'owner' | 'admin' | 'member' | 'viewer';
  joined_at: string;
  is_superuser: boolean;
}

interface ProjectMembersTooltipProps {
  projectId: string;
  memberCount: number;
  className?: string;
}

/**
 * 项目成员悬停提示组件
 * 显示项目成员列表和角色信息
 */
export default function ProjectMembersTooltip({ 
  projectId, 
  memberCount, 
  className = '' 
}: ProjectMembersTooltipProps) {
  const [members, setMembers] = useState<ProjectMember[]>([]);
  const [loading, setLoading] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);

  // 角色图标映射
  const getRoleIcon = (role: string) => {
    switch (role) {
      case 'owner':
        return <StarIcon className="w-3 h-3 text-yellow-500" />;
      case 'admin':
        return <ShieldCheckIcon className="w-3 h-3 text-blue-500" />;
      case 'member':
        return <UserIcon className="w-3 h-3 text-green-500" />;
      case 'viewer':
        return <EyeIcon className="w-3 h-3 text-gray-500" />;
      default:
        return <UserIcon className="w-3 h-3 text-gray-400" />;
    }
  };

  // 角色名称映射
  const getRoleName = (role: string) => {
    const roleMap = {
      'owner': '所有者',
      'admin': '管理员',
      'member': '成员',
      'viewer': '访客'
    };
    return roleMap[role as keyof typeof roleMap] || role;
  };

  // 加载项目成员
  const loadMembers = async () => {
    if (loading || members.length > 0) return;
    
    try {
      setLoading(true);
      const { apiGet } = await import('@/lib/api');
      const response = await apiGet(`/api/v1/projects/${projectId}/members`);
      
      if (response.ok) {
        const data = await response.json();
        setMembers(data);
      }
    } catch (error) {
      console.error('加载项目成员失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 鼠标悬停时加载成员数据
  const handleMouseEnter = () => {
    setShowTooltip(true);
    loadMembers();
  };

  const handleMouseLeave = () => {
    setShowTooltip(false);
  };

  return (
    <div 
      className={`relative inline-flex items-center ${className}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {/* 触发元素 */}
      <div className="flex items-center text-sm text-gray-600 hover:text-gray-800 cursor-pointer">
        <UsersIcon className="w-4 h-4 mr-1" />
        <span>{memberCount} 成员</span>
      </div>

      {/* 悬停提示框 */}
      {showTooltip && (
        <div className="absolute bottom-full left-0 mb-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
          <div className="p-3 border-b border-gray-100">
            <h4 className="text-sm font-semibold text-gray-900 flex items-center">
              <UsersIcon className="w-4 h-4 mr-2" />
              项目成员 ({memberCount})
            </h4>
          </div>
          
          <div className="max-h-64 overflow-y-auto">
            {loading ? (
              <div className="p-4 text-center text-gray-500">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto mb-2"></div>
                加载中...
              </div>
            ) : members.length > 0 ? (
              <div className="p-2">
                {members.map((member) => (
                  <div 
                    key={member.user_id} 
                    className="flex items-center p-2 hover:bg-gray-50 rounded"
                  >
                    {/* 头像 */}
                    <div className="flex-shrink-0 w-8 h-8 mr-3">
                      {member.avatar_url ? (
                        <img 
                          className="w-8 h-8 rounded-full" 
                          src={member.avatar_url} 
                          alt={member.username}
                        />
                      ) : (
                        <div className="w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center">
                          <UserIcon className="w-4 h-4 text-gray-600" />
                        </div>
                      )}
                    </div>
                    
                    {/* 用户信息 */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {member.full_name || member.username}
                        </p>
                        {member.is_superuser && (
                          <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                            管理员
                          </span>
                        )}
                      </div>
                      <div className="flex items-center mt-1">
                        <p className="text-xs text-gray-500 truncate mr-2">
                          {member.email}
                        </p>
                        <div className="flex items-center">
                          {getRoleIcon(member.role)}
                          <span className="ml-1 text-xs text-gray-600">
                            {getRoleName(member.role)}
                          </span>
                        </div>
                      </div>
                      {member.department && (
                        <p className="text-xs text-gray-400 truncate">
                          {member.department} {member.position && `· ${member.position}`}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-4 text-center text-gray-500">
                <UserIcon className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                <p className="text-sm">暂无成员数据</p>
              </div>
            )}
          </div>
          
          {/* 底部操作 */}
          {members.length > 0 && (
            <div className="p-2 border-t border-gray-100">
              <button className="w-full text-xs text-blue-600 hover:text-blue-800 py-1">
                查看完整成员列表 →
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
