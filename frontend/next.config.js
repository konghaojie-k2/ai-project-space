/** @type {import('next').NextConfig} */
const nextConfig = {
  // 实验性功能配置
  experimental: {
    // appDir 选项在 Next.js 14 中已经默认启用，不需要显式配置
  },
  
  // 图片优化配置
  images: {
    domains: ['localhost', '127.0.0.1'],
    unoptimized: process.env.NODE_ENV === 'development'
  },

  // API 代理配置
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/:path*`
      }
    ]
  },

  // 环境变量配置
  env: {
    // 应用信息
    NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME || 'AI项目管理系统',
    NEXT_PUBLIC_APP_VERSION: process.env.NEXT_PUBLIC_APP_VERSION || '0.1.0',
    NEXT_PUBLIC_APP_ENVIRONMENT: process.env.NEXT_PUBLIC_APP_ENVIRONMENT || 'development',
    
    // API配置
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_API_VERSION: process.env.NEXT_PUBLIC_API_VERSION || 'v1',
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1',
    
    // 功能开关
    NEXT_PUBLIC_DEBUG_MODE: process.env.NEXT_PUBLIC_DEBUG_MODE === 'true',
    NEXT_PUBLIC_ENABLE_DEV_TOOLS: process.env.NEXT_PUBLIC_ENABLE_DEV_TOOLS === 'true',
    NEXT_PUBLIC_ENABLE_PERFORMANCE_MONITORING: process.env.NEXT_PUBLIC_ENABLE_PERFORMANCE_MONITORING === 'true',
    
    // 文件上传配置
    NEXT_PUBLIC_MAX_FILE_SIZE: process.env.NEXT_PUBLIC_MAX_FILE_SIZE || '100',
    NEXT_PUBLIC_ALLOWED_FILE_TYPES: process.env.NEXT_PUBLIC_ALLOWED_FILE_TYPES || 'pdf,docx,xlsx,pptx,txt,md,jpg,jpeg,png,gif,bmp,mp4,avi,mov,wmv,mp3,wav,flac',
    
    // UI配置
    NEXT_PUBLIC_DEFAULT_THEME: process.env.NEXT_PUBLIC_DEFAULT_THEME || 'light',
    NEXT_PUBLIC_ENABLE_ANIMATIONS: process.env.NEXT_PUBLIC_ENABLE_ANIMATIONS !== 'false',
    NEXT_PUBLIC_SIDEBAR_DEFAULT_COLLAPSED: process.env.NEXT_PUBLIC_SIDEBAR_DEFAULT_COLLAPSED === 'true',
    
    // 开发配置
    NEXT_PUBLIC_HOT_RELOAD: process.env.NEXT_PUBLIC_HOT_RELOAD !== 'false',
    NEXT_PUBLIC_VERBOSE_LOGGING: process.env.NEXT_PUBLIC_VERBOSE_LOGGING === 'true',
    NEXT_PUBLIC_MOCK_API_DELAY: process.env.NEXT_PUBLIC_MOCK_API_DELAY || '500',
  },

  // 输出配置
  output: 'standalone',
  
  // 压缩配置
  compress: true,
  
  // 开发服务器配置
  devIndicators: {
    buildActivity: true,
    buildActivityPosition: 'bottom-right',
  },
  
  // 类型检查配置
  typescript: {
    // 在生产构建时忽略TypeScript错误
    ignoreBuildErrors: process.env.NODE_ENV === 'production',
  },
  
  // ESLint配置
  eslint: {
    // 在生产构建时忽略ESLint错误
    ignoreDuringBuilds: process.env.NODE_ENV === 'production',
  },
}

module.exports = nextConfig 