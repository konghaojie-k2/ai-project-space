/** @type {import('next').NextConfig} */
const nextConfig = {
  // 实验性功能配置
  experimental: {
    // appDir 选项在 Next.js 14 中已经默认启用，不需要显式配置
  },
  
  // 图片优化配置
  images: {
    domains: ['localhost'],
    unoptimized: process.env.NODE_ENV === 'development'
  },

  // API 代理配置 (可选)
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*'
      }
    ]
  },

  // 环境变量配置
  env: {
    CUSTOM_KEY: process.env.CUSTOM_KEY,
  },

  // 输出配置
  output: 'standalone'
}

module.exports = nextConfig 