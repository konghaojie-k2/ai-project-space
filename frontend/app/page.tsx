'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { 
  ArrowRightIcon,
  CloudArrowUpIcon,
  ChatBubbleLeftRightIcon,
  UsersIcon,
  CpuChipIcon,
  CheckCircleIcon,
  DocumentTextIcon,
  UserGroupIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline'
import MainNavbar from '@/components/layout/MainNavbar'

// 功能特性数据
const features = [
  {
    icon: DocumentTextIcon,
    title: '多模态支持',
    description: '支持文本、图片、视频、音频、PDF等多种格式文件上传和处理',
    color: 'text-blue-600'
  },
  {
    icon: ChatBubbleLeftRightIcon,
    title: 'AI智能问答',
    description: '基于项目上下文的智能问答，支持多轮对话和内容分析',
    color: 'text-green-600'
  },
  {
    icon: UserGroupIcon,
    title: '协作共享',
    description: '支持多用户协作，权限管理，让团队成员高效协作',
    color: 'text-purple-600'
  },
  {
    icon: ChartBarIcon,
    title: '智能优化',
    description: '基于使用数据持续优化AI响应质量，越用越好',
    color: 'text-orange-600'
  }
]

// 项目阶段数据
const projectStages = [
  '售前', '业务调研', '数据理解', '数据探索', '工程开发', '实施部署'
]

export default function HomePage() {
  const [isLoaded, setIsLoaded] = useState(false)
  
  useEffect(() => {
    setIsLoaded(true)
    
    console.log('🏠 HomePage: 页面加载完成');
    console.log('👤 HomePage: 保持在首页，用户可以选择登录或进入工作区');
  }, [])

  return (
    <div className={`min-h-screen transition-opacity duration-1000 ${isLoaded ? 'opacity-100' : 'opacity-0'}`}>
      <MainNavbar />
      {/* Hero Section */}
      <section className="relative bg-gradient-to-br from-primary-600 via-primary-700 to-primary-800 text-white">
        <div className="absolute inset-0 bg-black bg-opacity-20"></div>
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div className="text-center">
            <h1 className="text-4xl md:text-6xl font-bold mb-6 animate-slide-up">
              🚀 AI项目管理系统
            </h1>
            <p className="text-xl md:text-2xl mb-8 text-primary-100 animate-slide-up animation-delay-200">
              AI加持的智能项目管理，让协作更高效
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center animate-slide-up animation-delay-400">
              {/* 简化的登录选项 - 不依赖用户状态 */}
              <Link 
                href="/login" 
                className="btn btn-primary bg-white text-primary-700 hover:bg-primary-50 px-8 py-3 text-lg font-semibold rounded-lg transition-all duration-300 transform hover:scale-105"
              >
                立即登录
                <ArrowRightIcon className="w-5 h-5 ml-2 inline" />
              </Link>
              <Link 
                href="/register" 
                className="btn border-2 border-white text-white hover:bg-white hover:text-primary-700 px-8 py-3 text-lg font-semibold rounded-lg transition-all duration-300"
              >
                免费注册
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* 功能特性 */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              🎯 核心特性
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              集成最新AI技术，为项目管理提供智能化解决方案
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <div key={index} className="text-center p-6 rounded-xl hover:shadow-lg transition-shadow duration-300">
                <div className={`w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center`}>
                  <feature.icon className={`w-8 h-8 ${feature.color}`} />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">{feature.title}</h3>
                <p className="text-gray-600">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 项目阶段管理 */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              📋 项目阶段管理
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              按阶段组织项目内容，让管理更有序
            </p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {projectStages.map((stage, index) => (
              <div key={index} className="text-center p-4 bg-white rounded-lg shadow-sm hover:shadow-md transition-shadow duration-300">
                <div className="w-12 h-12 mx-auto mb-3 bg-primary-100 rounded-full flex items-center justify-center">
                  <CheckCircleIcon className="w-6 h-6 text-primary-600" />
                </div>
                <span className="text-sm font-medium text-gray-900">{stage}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-primary-600">
        <div className="max-w-4xl mx-auto text-center px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            准备开始您的智能项目管理之旅？
          </h2>
          <p className="text-xl text-primary-100 mb-8">
            立即体验AI加持的项目管理系统，提升团队协作效率
          </p>
          <Link
            href="/register"
            className="inline-flex items-center px-8 py-4 bg-white text-primary-700 font-semibold rounded-lg hover:bg-primary-50 transition-colors shadow-lg hover:shadow-xl transform hover:-translate-y-1 duration-300"
          >
            免费注册
            <ArrowRightIcon className="ml-2 w-5 h-5" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div>
              <h3 className="text-lg font-semibold mb-4">AI项目管理系统</h3>
              <p className="text-gray-400 mb-4">让项目管理更智能，让协作更高效</p>
              <p className="text-sm text-gray-500">© 2024 AI项目管理系统. 保留所有权利.</p>
            </div>
            <div>
              <h4 className="text-md font-semibold mb-4">产品</h4>
              <ul className="space-y-2">
                <li><Link href="/features" className="text-gray-400 hover:text-white transition-colors">功能特性</Link></li>
                <li><Link href="/pricing" className="text-gray-400 hover:text-white transition-colors">价格方案</Link></li>
                <li><Link href="/demo" className="text-gray-400 hover:text-white transition-colors">产品演示</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-md font-semibold mb-4">支持</h4>
              <ul className="space-y-2">
                <li><Link href="/docs" className="text-gray-400 hover:text-white transition-colors">使用文档</Link></li>
                <li><Link href="/help" className="text-gray-400 hover:text-white transition-colors">帮助中心</Link></li>
                <li><Link href="/contact" className="text-gray-400 hover:text-white transition-colors">联系我们</Link></li>
              </ul>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}