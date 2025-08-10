'use client';

import React, { useState, useEffect } from 'react';
import { CheckCircleIcon, XCircleIcon, ClockIcon } from '@heroicons/react/24/outline';

interface ServiceStatus {
  name: string;
  status: 'healthy' | 'unhealthy' | 'checking';
  url: string;
  lastCheck?: string;
  responseTime?: number;
  error?: string;
}

/**
 * 服务状态检查页面
 */
export default function StatusPage() {
  const [services, setServices] = useState<ServiceStatus[]>([
    {
      name: '前端应用',
      status: 'healthy',
      url: window.location.origin,
    },
    {
      name: '后端API',
      status: 'checking',
      url: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1',
    },
    {
      name: '聊天服务',
      status: 'checking',
      url: (process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1') + '/chat/health',
    }
  ]);

  const checkServiceHealth = async (service: ServiceStatus): Promise<ServiceStatus> => {
    const startTime = Date.now();
    
    try {
      const response = await fetch(service.url, {
        method: 'GET',
        timeout: 5000,
      });
      
      const responseTime = Date.now() - startTime;
      
      if (response.ok) {
        return {
          ...service,
          status: 'healthy',
          lastCheck: new Date().toISOString(),
          responseTime,
          error: undefined
        };
      } else {
        return {
          ...service,
          status: 'unhealthy',
          lastCheck: new Date().toISOString(),
          responseTime,
          error: `HTTP ${response.status}: ${response.statusText}`
        };
      }
    } catch (error) {
      return {
        ...service,
        status: 'unhealthy',
        lastCheck: new Date().toISOString(),
        responseTime: Date.now() - startTime,
        error: error instanceof Error ? error.message : '连接失败'
      };
    }
  };

  const checkAllServices = async () => {
    setServices(prev => prev.map(service => ({ ...service, status: 'checking' })));
    
    const updatedServices = await Promise.all(
      services.map(service => checkServiceHealth(service))
    );
    
    setServices(updatedServices);
  };

  useEffect(() => {
    checkAllServices();
    // 每30秒检查一次
    const interval = setInterval(checkAllServices, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusIcon = (status: ServiceStatus['status']) => {
    switch (status) {
      case 'healthy':
        return <CheckCircleIcon className="w-6 h-6 text-green-500" />;
      case 'unhealthy':
        return <XCircleIcon className="w-6 h-6 text-red-500" />;
      case 'checking':
        return <ClockIcon className="w-6 h-6 text-yellow-500 animate-spin" />;
    }
  };

  const getStatusText = (status: ServiceStatus['status']) => {
    switch (status) {
      case 'healthy':
        return '正常';
      case 'unhealthy':
        return '异常';
      case 'checking':
        return '检查中...';
    }
  };

  const getStatusColor = (status: ServiceStatus['status']) => {
    switch (status) {
      case 'healthy':
        return 'text-green-600 dark:text-green-400';
      case 'unhealthy':
        return 'text-red-600 dark:text-red-400';
      case 'checking':
        return 'text-yellow-600 dark:text-yellow-400';
    }
  };

  const overallStatus = services.every(s => s.status === 'healthy') ? 'healthy' :
                      services.some(s => s.status === 'unhealthy') ? 'unhealthy' : 'checking';

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          {/* 页面标题 */}
          <div className="mb-8 text-center">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              系统状态监控
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              实时监控各个服务的运行状态
            </p>
          </div>

          {/* 整体状态 */}
          <div className="mb-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                {getStatusIcon(overallStatus)}
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                    整体状态
                  </h2>
                  <p className={`text-lg ${getStatusColor(overallStatus)}`}>
                    {getStatusText(overallStatus)}
                  </p>
                </div>
              </div>
              <button
                onClick={checkAllServices}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                刷新状态
              </button>
            </div>
          </div>

          {/* 服务列表 */}
          <div className="space-y-4">
            {services.map((service, index) => (
              <div key={index} className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    {getStatusIcon(service.status)}
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                        {service.name}
                      </h3>
                      <p className={`${getStatusColor(service.status)}`}>
                        {getStatusText(service.status)}
                      </p>
                    </div>
                  </div>
                  <div className="text-right text-sm text-gray-500 dark:text-gray-400">
                    {service.responseTime && (
                      <p>响应时间: {service.responseTime}ms</p>
                    )}
                    {service.lastCheck && (
                      <p>最后检查: {new Date(service.lastCheck).toLocaleTimeString()}</p>
                    )}
                  </div>
                </div>
                
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  <p><strong>URL:</strong> {service.url}</p>
                  {service.error && (
                    <p className="text-red-600 dark:text-red-400 mt-1">
                      <strong>错误:</strong> {service.error}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* 测试链接 */}
          <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              功能测试
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <a
                href="/test/streaming"
                className="block p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <h4 className="font-medium text-gray-900 dark:text-white">流式响应测试</h4>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  测试流式回复和Markdown渲染
                </p>
              </a>
              <a
                href="/dashboard/chat"
                className="block p-4 border border-gray-200 dark:border-gray-700 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <h4 className="font-medium text-gray-900 dark:text-white">聊天功能</h4>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  进入聊天页面体验功能
                </p>
              </a>
            </div>
          </div>

          {/* 系统信息 */}
          <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              系统信息
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <p><strong>应用版本:</strong> {process.env.NEXT_PUBLIC_APP_VERSION || '0.1.0'}</p>
                <p><strong>环境:</strong> {process.env.NEXT_PUBLIC_APP_ENVIRONMENT || 'development'}</p>
                <p><strong>API版本:</strong> {process.env.NEXT_PUBLIC_API_VERSION || 'v1'}</p>
              </div>
              <div>
                <p><strong>浏览器:</strong> {navigator.userAgent.split(' ')[0]}</p>
                <p><strong>当前时间:</strong> {new Date().toLocaleString()}</p>
                <p><strong>时区:</strong> {Intl.DateTimeFormat().resolvedOptions().timeZone}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
