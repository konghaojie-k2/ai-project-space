'use client';

import React, { useState, useEffect } from 'react';
import { Chat, Message } from '@/components/features/Chat';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Modal from '@/components/ui/Modal';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { 
  PlusIcon, 
  ChatBubbleLeftRightIcon,
  TrashIcon,
  DocumentTextIcon,
  ArrowRightIcon,
  HomeIcon,
  ArrowLeftIcon
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';
import { chatAPI, Conversation, ConversationCreateRequest } from '@/lib/api/chat';

export default function ChatPage() {
  const searchParams = useSearchParams();
  const projectId = searchParams.get('project');
  const projectName = searchParams.get('name');
  
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showNewConversationModal, setShowNewConversationModal] = useState(false);
  const [newConversationTitle, setNewConversationTitle] = useState('');
  const [selectedProjectId, setSelectedProjectId] = useState<string>(projectId || '');
  const [isLoadingConversations, setIsLoadingConversations] = useState(true);

  // 模拟项目数据
  const projects = [
    { id: 'project-1', name: '智能客服系统' },
    { id: 'project-2', name: '情感分析模型' },
    { id: 'project-3', name: '图像识别系统' }
  ];

  // 加载会话列表
  useEffect(() => {
    loadConversations();
  }, []);

  // 如果从项目进入，自动创建项目会话
  useEffect(() => {
    if (projectId && projectName && !isLoadingConversations) {
      // 检查是否已经有该项目的会话
      const existingProjectConversation = conversations.find(conv => 
        conv.project_id === projectId
      );
      
      if (!existingProjectConversation) {
        // 自动创建项目会话
        setNewConversationTitle(`${decodeURIComponent(projectName)} - 项目讨论`);
        setSelectedProjectId(projectId);
        handleCreateConversation();
      } else {
        // 选择现有的项目会话
        handleSelectConversation(existingProjectConversation);
      }
    }
  }, [projectId, projectName, conversations, isLoadingConversations]);

  const loadConversations = async () => {
    try {
      setIsLoadingConversations(true);
      const data = await chatAPI.getConversations();
      setConversations(data);
    } catch (error) {
      console.error('加载会话列表失败:', error);
      // 如果API调用失败，使用模拟数据
      setConversations([
        {
          id: '1',
          title: '项目需求分析',
          last_message: '请帮我分析一下这个AI项目的技术架构...',
          message_count: 12,
          created_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
          updated_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
          project_id: 'project-1',
          project_name: '智能客服系统'
        },
        {
          id: '2',
          title: '数据预处理方案',
          last_message: '对于文本数据的清洗和预处理，你有什么建议？',
          message_count: 8,
          created_at: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
          updated_at: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
          project_id: 'project-2',
          project_name: '情感分析模型'
        }
      ]);
    } finally {
      setIsLoadingConversations(false);
    }
  };

  // 处理发送消息
  const handleSendMessage = async (content: string) => {
    if (!currentConversation) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content,
      role: 'user',
      timestamp: new Date(),
      status: 'sent'
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // 直接使用chatAPI发送消息
      const request = {
        messages: [...messages, userMessage],
        project_id: currentConversation.project_id,
        stream: false
      };

      const apiResponse = await chatAPI.sendMessage(currentConversation.id, request);
      
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: apiResponse.content,
        role: 'assistant',
        timestamp: new Date(),
        status: 'sent'
      };

      setMessages(prev => [...prev, aiMessage]);

      // 更新会话列表
      await loadConversations();

    } catch (error) {
      console.error('发送消息失败:', error);
      // 最终降级处理
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: generateSmartResponse(content, currentConversation.project_name),
        role: 'assistant',
        timestamp: new Date(),
        status: 'sent'
      };

      setMessages(prev => [...prev, aiMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // 生成智能模拟回复
  const generateSmartResponse = (question: string, projectName?: string) => {
    const responses = [
      {
        keywords: ['架构', '设计', '系统', '技术'],
        response: `关于${projectName || '项目'}的架构设计，我建议考虑以下几个方面：

🏗️ **系统架构建议：**
1. **微服务架构** - 提高系统可扩展性
2. **负载均衡** - 确保高可用性  
3. **数据库优化** - 选择合适的存储方案
4. **缓存策略** - 提升系统性能

\`\`\`python
# 示例：基础架构模块
class SystemArchitecture:
    def __init__(self):
        self.services = {}
        self.database = None
        self.cache = None
    
    def setup_microservices(self):
        # 微服务配置
        pass
\`\`\`

需要更具体的技术实现细节吗？`
      },
      {
        keywords: ['数据', '分析', '处理', '清洗'],
        response: `对于${projectName || '项目'}的数据处理，我推荐以下方案：

📊 **数据处理流程：**
1. **数据收集** - 确保数据质量和完整性
2. **数据清洗** - 处理异常值和缺失值
3. **特征工程** - 提取有价值的特征
4. **数据存储** - 选择合适的存储格式

\`\`\`python
import pandas as pd
import numpy as np

def process_data(raw_data):
    # 数据清洗
    cleaned_data = raw_data.dropna()
    
    # 特征工程
    features = extract_features(cleaned_data)
    
    return features

def extract_features(data):
    # 特征提取逻辑
    return data
\`\`\`

您希望了解哪个具体环节的实现？`
      },
      {
        keywords: ['模型', '算法', 'AI', '机器学习', '深度学习'],
        response: `针对${projectName || '项目'}的AI模型开发，建议采用以下策略：

🤖 **模型开发建议：**
1. **模型选择** - 根据业务需求选择合适算法
2. **数据准备** - 确保训练数据质量
3. **模型训练** - 使用交叉验证等技术
4. **模型评估** - 多维度评估模型性能

\`\`\`python
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

def train_model(X, y):
    # 数据分割
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # 模型训练
    model = RandomForestClassifier(n_estimators=100)
    model.fit(X_train, y_train)
    
    return model
\`\`\`

需要讨论具体的模型类型或优化策略吗？`
      }
    ];

    // 根据关键词匹配合适的回复
    for (const item of responses) {
      if (item.keywords.some(keyword => question.toLowerCase().includes(keyword))) {
        return item.response;
      }
    }

    // 默认回复
    return `感谢您关于"${question}"的提问！

基于${projectName || '当前项目'}的上下文，我为您提供以下分析：

💡 **项目建议：**
- 深入分析项目需求和目标
- 制定详细的技术实施方案  
- 考虑系统的可扩展性和维护性
- 建立完善的测试和部署流程

如果您能提供更具体的技术需求或遇到的问题，我可以给出更有针对性的建议。您希望从哪个方面开始讨论？

*注：当前使用智能模拟回复，真实API服务连接中...*`;
  };

  // 处理停止生成
  const handleStopGeneration = () => {
    setIsLoading(false);
  };

  // 创建新会话
  const handleCreateConversation = async () => {
    if (!newConversationTitle.trim()) return;

    try {
      const request: ConversationCreateRequest = {
        title: newConversationTitle,
        project_id: selectedProjectId || undefined
      };

      const newConversation = await chatAPI.createConversation(request);
      
      setConversations(prev => [newConversation, ...prev]);
      setCurrentConversation(newConversation);
      setMessages([]);
      setShowNewConversationModal(false);
      setNewConversationTitle('');
      setSelectedProjectId('');

    } catch (error) {
      console.error('创建会话失败:', error);
      // 如果API调用失败，使用模拟数据
      const mockConversation: Conversation = {
        id: Date.now().toString(),
        title: newConversationTitle,
        message_count: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        project_id: selectedProjectId || undefined,
        project_name: projects.find(p => p.id === selectedProjectId)?.name
      };

      setConversations(prev => [mockConversation, ...prev]);
      setCurrentConversation(mockConversation);
      setMessages([]);
      setShowNewConversationModal(false);
      setNewConversationTitle('');
      setSelectedProjectId('');
    }
  };

  // 删除会话
  const handleDeleteConversation = async (conversationId: string) => {
    try {
      await chatAPI.deleteConversation(conversationId);
      setConversations(prev => prev.filter(conv => conv.id !== conversationId));
      
      if (currentConversation?.id === conversationId) {
        setCurrentConversation(null);
        setMessages([]);
      }
    } catch (error) {
      console.error('删除会话失败:', error);
      // 即使API调用失败，也更新本地状态
      setConversations(prev => prev.filter(conv => conv.id !== conversationId));
      if (currentConversation?.id === conversationId) {
        setCurrentConversation(null);
        setMessages([]);
      }
    }
  };

  // 选择会话
  const handleSelectConversation = async (conversation: Conversation) => {
    setCurrentConversation(conversation);
    
    try {
      // 加载会话消息
      const conversationMessages = await chatAPI.getMessages(conversation.id);
      setMessages(conversationMessages);
    } catch (error) {
      console.error('加载会话消息失败:', error);
      setMessages([]);
    }
  };

  // 格式化时间
  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / (1000 * 60));
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (minutes < 60) return `${minutes}分钟前`;
    if (hours < 24) return `${hours}小时前`;
    return `${days}天前`;
  };

  return (
    <div className="flex h-full bg-gray-50">
      {/* 侧边栏 - 会话列表 */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        {/* 头部 */}
        <div className="p-4 border-b border-gray-200">
          {/* 导航面包屑 */}
          <div className="flex items-center space-x-2 text-sm text-gray-500 mb-3">
            <Link href="/dashboard" className="hover:text-gray-700 flex items-center">
              <HomeIcon className="h-4 w-4 mr-1" />
              Dashboard
            </Link>
            <span>/</span>
            {projectName ? (
              <>
                <Link href="/dashboard/projects" className="hover:text-gray-700">
                  项目管理
                </Link>
                <span>/</span>
                <Link href={`/dashboard/projects/${projectId}`} className="hover:text-gray-700">
                  {decodeURIComponent(projectName)}
                </Link>
                <span>/</span>
                <span className="text-gray-900">AI 助手</span>
              </>
            ) : (
              <span className="text-gray-900">AI 助手</span>
            )}
          </div>
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-xl font-semibold text-gray-900">
              {projectName ? `${decodeURIComponent(projectName)} - AI 助手` : 'AI 助手'}
            </h1>
            <Button
              onClick={() => setShowNewConversationModal(true)}
              size="sm"
              className="flex items-center gap-2"
            >
              <PlusIcon className="w-4 h-4" />
              新建会话
            </Button>
          </div>
          
          {/* 搜索框 */}
          <Input
            placeholder="搜索会话..."
            className="w-full"
          />
        </div>

        {/* 会话列表 */}
        <div className="flex-1 overflow-y-auto">
          {isLoadingConversations ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                <p className="text-sm text-gray-500 mt-2">加载中...</p>
              </div>
            </div>
          ) : conversations.length === 0 ? (
            <div className="flex items-center justify-center h-full text-gray-500">
              <div className="text-center">
                <ChatBubbleLeftRightIcon className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                <p className="text-sm">暂无会话</p>
                <p className="text-xs text-gray-400 mt-1">点击"新建会话"开始对话</p>
              </div>
            </div>
          ) : (
            <div className="p-2">
              {conversations.map((conversation) => (
                <div
                  key={conversation.id}
                  className={cn(
                    'p-3 rounded-lg cursor-pointer transition-colors mb-2',
                    currentConversation?.id === conversation.id
                      ? 'bg-blue-50 border border-blue-200'
                      : 'hover:bg-gray-50'
                  )}
                  onClick={() => handleSelectConversation(conversation)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-sm font-medium text-gray-900 truncate">
                          {conversation.title}
                        </h3>
                        {conversation.project_name && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                            {conversation.project_name}
                          </span>
                        )}
                      </div>
                      {conversation.last_message && (
                        <p className="text-xs text-gray-500 truncate mb-1">
                          {conversation.last_message}
                        </p>
                      )}
                      <div className="flex items-center justify-between text-xs text-gray-400">
                        <span>{formatTime(conversation.updated_at)}</span>
                        <span>{conversation.message_count} 条消息</span>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteConversation(conversation.id);
                      }}
                      className="text-gray-400 hover:text-red-500"
                    >
                      <TrashIcon className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 主聊天区域 */}
      <div className="flex-1 flex flex-col">
        {currentConversation ? (
          <>
            {/* 聊天头部 */}
            <div className="bg-white border-b border-gray-200 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">
                    {currentConversation.title}
                  </h2>
                  {currentConversation.project_name && (
                    <p className="text-sm text-gray-500">
                      项目: {currentConversation.project_name}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  <span>{currentConversation.message_count} 条消息</span>
                  <span>•</span>
                  <span>{formatTime(currentConversation.updated_at)}</span>
                </div>
              </div>
            </div>

            {/* 聊天界面 */}
            <div className="flex-1">
              <Chat
                messages={messages}
                onSendMessage={handleSendMessage}
                onStopGeneration={handleStopGeneration}
                isLoading={isLoading}
              />
            </div>
          </>
        ) : (
          /* 空状态 */
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <ChatBubbleLeftRightIcon className="w-16 h-16 mx-auto mb-4 text-gray-300" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                选择会话开始对话
              </h3>
              <p className="text-sm text-gray-500 mb-4">
                从左侧选择一个会话，或者创建新的对话
              </p>
              <Button
                onClick={() => setShowNewConversationModal(true)}
                className="flex items-center gap-2"
              >
                <PlusIcon className="w-4 h-4" />
                新建会话
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* 新建会话模态框 */}
      <Modal
        isOpen={showNewConversationModal}
        onClose={() => setShowNewConversationModal(false)}
        title="新建会话"
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              会话标题
            </label>
            <Input
              value={newConversationTitle}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewConversationTitle(e.target.value)}
              placeholder="输入会话标题..."
              onKeyPress={(e: React.KeyboardEvent<HTMLInputElement>) => {
                if (e.key === 'Enter') {
                  handleCreateConversation();
                }
              }}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              关联项目 (可选)
            </label>
            <select
              value={selectedProjectId}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSelectedProjectId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">不关联项目</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <Button
              variant="outline"
              onClick={() => setShowNewConversationModal(false)}
            >
              取消
            </Button>
            <Button
              onClick={handleCreateConversation}
              disabled={!newConversationTitle.trim()}
            >
              创建会话
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
} 