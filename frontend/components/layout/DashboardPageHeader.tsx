'use client';

import React from 'react';
import Link from 'next/link';
import { ArrowLeftIcon } from '@heroicons/react/24/outline';
import Button from '@/components/ui/Button';

interface DashboardPageHeaderProps {
  title: string;
  description?: string;
  showBackButton?: boolean;
  backUrl?: string;
  backText?: string;
  actions?: React.ReactNode;
}

/**
 * Dashboard页面统一头部组件
 * 提供标题、描述、返回按钮和操作按钮的统一布局
 */
export default function DashboardPageHeader({
  title,
  description,
  showBackButton = true,
  backUrl = '/dashboard',
  backText = '返回Dashboard',
  actions
}: DashboardPageHeaderProps) {
  return (
    <div className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          {showBackButton && (
            <>
              <Link
                href={backUrl}
                className="flex items-center text-gray-600 hover:text-gray-900 transition-colors group"
              >
                <ArrowLeftIcon className="w-5 h-5 mr-2 group-hover:-translate-x-1 transition-transform" />
                <span className="text-sm font-medium">{backText}</span>
              </Link>
              <div className="border-l border-gray-300 h-6"></div>
            </>
          )}
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
            {description && (
              <p className="text-sm text-gray-600 mt-1">{description}</p>
            )}
          </div>
        </div>
        
        {actions && (
          <div className="flex items-center space-x-3">
            {actions}
          </div>
        )}
      </div>
    </div>
  );
}
