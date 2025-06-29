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
  const [stats, setStats] = useState({
    projects: 0,
    files: 0,
    conversations: 0
  })

  useEffect(() => {
    setIsLoaded(true)
    // 模拟加载统计数据
    setTimeout(() => {
      setStats({
        projects: 12,
        files: 156,
        conversations: 324
      })
    }, 1000)
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
              <Link 
                href="/dashboard" 
                className="btn btn-primary bg-white text-primary-700 hover:bg-primary-50 px-8 py-3 text-lg font-semibold rounded-lg transition-all duration-300 transform hover:scale-105"
              >
                开始使用
                <ArrowRightIcon className="w-5 h-5 ml-2 inline" />
              </Link>
              <Link 
                href="/demo" 
                className="btn border-2 border-white text-white hover:bg-white hover:text-primary-700 px-8 py-3 text-lg font-semibold rounded-lg transition-all duration-300"
              >
                查看演示
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-16 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="text-4xl font-bold text-primary-600 mb-2">
                {stats.projects}
              </div>
              <div className="text-secondary-600">活跃项目</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-green-600 mb-2">
                {stats.files}
              </div>
              <div className="text-secondary-600">文件数量</div>
            </div>
            <div className="text-center">
              <div className="text-4xl font-bold text-purple-600 mb-2">
                {stats.conversations}
              </div>
              <div className="text-secondary-600">AI对话次数</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-secondary-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-secondary-900 mb-4">
              🎯 核心特性
            </h2>
            <p className="text-xl text-secondary-600 max-w-3xl mx-auto">
              集成最新AI技术，为项目管理提供智能化解决方案
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <div 
                key={index}
                className="card hover:shadow-lg transition-all duration-300 transform hover:-translate-y-1 animate-scale-in"
                style={{ animationDelay: `${index * 100}ms` }}
              >
                <feature.icon className={`w-12 h-12 ${feature.color} mb-4`} />
                <h3 className="text-xl font-semibold mb-3 text-secondary-900">
                  {feature.title}
                </h3>
                <p className="text-secondary-600 leading-relaxed">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Project Stages Section */}
      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-secondary-900 mb-4">
              📋 项目阶段管理
            </h2>
            <p className="text-xl text-secondary-600 max-w-3xl mx-auto">
              按阶段组织项目内容，让管理更有序
            </p>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {projectStages.map((stage, index) => (
              <div 
                key={index}
                className="bg-gradient-to-br from-primary-50 to-primary-100 p-4 rounded-lg text-center border border-primary-200 hover:shadow-md transition-all duration-300 animate-fade-in"
                style={{ animationDelay: `${index * 150}ms` }}
              >
                <CheckCircleIcon className="w-8 h-8 text-primary-600 mx-auto mb-2" />
                <div className="text-sm font-medium text-primary-800">
                  {stage}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-r from-primary-600 to-primary-700 text-white">
        <div className="max-w-4xl mx-auto text-center px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl md:text-4xl font-bold mb-6">
            准备开始您的智能项目管理之旅？
          </h2>
          <p className="text-xl mb-8 text-primary-100">
            立即体验AI加持的项目管理系统，提升团队协作效率
          </p>
          <Link 
            href="/register" 
            className="btn bg-white text-primary-700 hover:bg-primary-50 px-8 py-4 text-lg font-semibold rounded-lg transition-all duration-300 transform hover:scale-105 inline-flex items-center"
          >
            免费注册
            <ArrowRightIcon className="w-5 h-5 ml-2" />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-secondary-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div className="col-span-1 md:col-span-2">
              <h3 className="text-2xl font-bold mb-4">AI项目管理系统</h3>
              <p className="text-secondary-300 mb-4">
                让项目管理更智能，让协作更高效
              </p>
              <p className="text-secondary-400 text-sm">
                © 2024 AI项目管理系统. 保留所有权利.
              </p>
            </div>
            <div>
              <h4 className="text-lg font-semibold mb-4">产品</h4>
              <ul className="space-y-2 text-secondary-300">
                <li><Link href="/features" className="hover:text-white transition-colors">功能特性</Link></li>
                <li><Link href="/pricing" className="hover:text-white transition-colors">价格方案</Link></li>
                <li><Link href="/demo" className="hover:text-white transition-colors">产品演示</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="text-lg font-semibold mb-4">支持</h4>
              <ul className="space-y-2 text-secondary-300">
                <li><Link href="/docs" className="hover:text-white transition-colors">使用文档</Link></li>
                <li><Link href="/help" className="hover:text-white transition-colors">帮助中心</Link></li>
                <li><Link href="/contact" className="hover:text-white transition-colors">联系我们</Link></li>
              </ul>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
} 