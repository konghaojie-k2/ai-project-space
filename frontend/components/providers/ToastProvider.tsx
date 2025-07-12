'use client'

import { Toaster } from 'react-hot-toast'

const ToastProvider = () => {
  return (
    <Toaster
      position="top-right"
      toastOptions={{
        // 默认选项
        duration: 4000,
        style: {
          background: '#363636',
          color: '#fff',
          borderRadius: '8px',
          fontSize: '14px',
          padding: '12px 16px',
        },
        // 成功通知
        success: {
          duration: 3000,
          style: {
            background: '#10B981',
            color: '#fff',
          },
          iconTheme: {
            primary: '#fff',
            secondary: '#10B981',
          },
        },
        // 错误通知
        error: {
          duration: 5000,
          style: {
            background: '#EF4444',
            color: '#fff',
          },
          iconTheme: {
            primary: '#fff',
            secondary: '#EF4444',
          },
        },
        // 加载通知
        loading: {
          style: {
            background: '#3B82F6',
            color: '#fff',
          },
          iconTheme: {
            primary: '#fff',
            secondary: '#3B82F6',
          },
        },
      }}
    />
  )
}

export default ToastProvider 