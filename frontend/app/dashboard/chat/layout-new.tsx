'use client';

import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { ChatOptimized as Chat, Message } from '@/components/features/ChatOptimized';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Modal from '@/components/ui/Modal';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { 
  PlusIcon,
  ArrowLeftIcon,
  FolderIcon,
  DocumentTextIcon,
  ChatBubbleLeftRightIcon,
  TrashIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  EyeIcon,
  ArchiveBoxIcon,
  SparklesIcon
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';
import { chatAPI, Conversation, ConversationCreateRequest, ChatRequest } from '@/lib/api/chat';

interface Project {
  id: string;
  name: string;
  description: string;
  stage: string;
  fileCount: number;
  lastActivity: string;
}

interface FileItem {
  id: string;
  name: string;
  type: string;
  size: number;
  uploadDate: string;
  tags: string[];
  status: 'uploaded' | 'processing' | 'analyzed' | 'error';
}

/**
 * 新的三栏布局聊天页面
 * 左侧：项目信息和对话历史
 * 中间：聊天对话框（可滚动）
 * 右侧：文件信息和相关资源
 */
export default function ChatPageNewLayout() {
  const searchParams = useSearchParams();
  
  // 状态管理
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingConversations, setIsLoadingConversations] = useState(false);
  
  // 项目和文件相关状态
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [projectFiles, setProjectFiles] = useState<FileItem[]>([]);
  const [showNewConversationModal, setShowNewConversationModal] = useState(false);
  const [newConversationTitle, setNewConversationTitle] = useState('');

  // 界面状态
  const [leftSidebarCollapsed, setLeftSidebarCollapsed] = useState(false);
  const [rightSidebarCollapsed, setRightSidebarCollapsed] = useState(false);
  const [projectInfoExpanded, setProjectInfoExpanded] = useState(true);
  const [fileInfoExpanded, setFileInfoExpanded] = useState(true);

  // 模拟数据
  const mockProject: Project = {
    id: 'proj_1',
    name: '数据分析与可视化报告',
    description: '基于销售数据的深度分析和可视化展示',
    stage: '分析阶段',
    fileCount: 12,
    lastActivity: '2小时前'
  };

  const mockFiles: FileItem[] = [
    {
      id: 'file_1',
      name: '数据分析与可视化报告 (1).pdf',
      type: 'pdf',
      size: 2048000,
      uploadDate: '2024-01-15',
      tags: ['分析', '报告'],
      status: 'analyzed'
    },
    {
      id: 'file_2',
      name: '销售数据.xlsx',
      type: 'xlsx',
      size: 1024000,
      uploadDate: '2024-01-14',
      tags: ['数据', '销售'],
      status: 'analyzed'
    },
    {
      id: 'file_3',
      name: '用户行为分析.py',
      type: 'python',
      size: 15360,
      uploadDate: '2024-01-13',
      tags: ['代码', '分析'],
      status: 'uploaded'
    }
  ];

  useEffect(() => {
    setSelectedProject(mockProject);
    setProjectFiles(mockFiles);
    loadConversations();
  }, []);

  const loadConversations = async () => {
    try {
      setIsLoadingConversations(true);
      const data = await chatAPI.getConversations();
      setConversations(data);
    } catch (error) {
      console.error('加载会话列表失败:', error);
    } finally {
      setIsLoadingConversations(false);
    }
  };

  const handleSelectConversation = async (conversation: Conversation) => {
    if (conversation.id === currentConversation?.id) return;
    
    setCurrentConversation(conversation);
    setSelectedProject(mockProject);
    
    try {
      const messagesData = await chatAPI.getMessages(conversation.id);
      setMessages(messagesData);
    } catch (error) {
      console.error('加载消息失败:', error);
      setMessages([]);
    }
  };

  const handleSendMessage = async (content: string) => {
    if (!currentConversation) return;

    const userMessage: Message = {
      id: `msg_${Date.now()}`,
      content,
      role: 'user',
      timestamp: new Date(),
      status: 'sent'
    };
    setMessages(prev => [...prev, userMessage]);

    const aiMessageId = `msg_${Date.now() + 1}`;
    const aiMessage: Message = {
      id: aiMessageId,
      content: '',
      role: 'assistant',
      timestamp: new Date(),
      status: 'sending'
    };
    setMessages(prev => [...prev, aiMessage]);
    setIsLoading(true);

    try {
      const request: ChatRequest = {
        messages: [{ role: 'user', content }],
        model: 'gpt-3.5-turbo',
        project_id: currentConversation.project_id,
        stream: true
      };

      await chatAPI.sendMessageStream(currentConversation.id, request, {
        onStart: (messageId) => {
          console.log('AI开始回复:', messageId);
        },
        onContent: (chunk) => {
          setMessages(prev => prev.map(msg => 
            msg.id === aiMessageId 
              ? { ...msg, content: msg.content + chunk, status: 'sending' }
              : msg
          ));
        },
        onEnd: (messageId) => {
          setMessages(prev => prev.map(msg => 
            msg.id === aiMessageId 
              ? { ...msg, status: 'sent' }
              : msg
          ));
          setIsLoading(false);
          loadConversations();
        },
        onError: (error) => {
          console.error('流式回复失败:', error);
          setMessages(prev => prev.map(msg => 
            msg.id === aiMessageId 
              ? { ...msg, content: '抱歉，回复失败，请重试。', status: 'error' }
              : msg
          ));
          setIsLoading(false);
        }
      });

    } catch (error) {
      console.error('发送消息失败:', error);
      setMessages(prev => prev.map(msg => 
        msg.id === aiMessageId 
          ? { ...msg, content: '网络错误，请检查连接。', status: 'error' }
          : msg
      ));
      setIsLoading(false);
    }
  };

  const handleCreateConversation = async () => {
    if (!newConversationTitle.trim()) return;

    try {
      const request: ConversationCreateRequest = {
        title: newConversationTitle,
        project_id: selectedProject?.id
      };

      const newConversation = await chatAPI.createConversation(request);
      setConversations(prev => [newConversation, ...prev]);
      setCurrentConversation(newConversation);
      setMessages([]);
      setShowNewConversationModal(false);
      setNewConversationTitle('');
    } catch (error) {
      console.error('创建会话失败:', error);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFileIcon = (type: string) => {
    switch (type) {
      case 'pdf':
        return '📄';
      case 'xlsx':
        return '📊';
      case 'python':
        return '🐍';
      default:
        return '📁';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'analyzed':
        return 'text-green-600 bg-green-100';
      case 'processing':
        return 'text-yellow-600 bg-yellow-100';
      case 'uploaded':
        return 'text-blue-600 bg-blue-100';
      case 'error':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
      {/* 左侧边栏 - 项目信息和对话历史 */}
      <div className={cn(
        "bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col transition-all duration-300",
        leftSidebarCollapsed ? "w-12" : "w-80"
      )}>
        {!leftSidebarCollapsed && (
          <>
            {/* 顶部导航 */}
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-3 mb-4">
                <Link href="/dashboard" className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors">
                  <ArrowLeftIcon className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                </Link>
                <h1 className="text-lg font-semibold text-gray-900 dark:text-white">AI助手</h1>
              </div>
              
              <Button
                onClick={() => setShowNewConversationModal(true)}
                className="w-full"
                variant="primary"
              >
                <PlusIcon className="w-4 h-4 mr-2" />
                新建对话
              </Button>
            </div>

            {/* 项目信息区域 */}
            {selectedProject && (
              <div className="border-b border-gray-200 dark:border-gray-700">
                <button
                  onClick={() => setProjectInfoExpanded(!projectInfoExpanded)}
                  className="w-full p-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <FolderIcon className="w-5 h-5 text-blue-600" />
                    <span className="font-medium text-gray-900 dark:text-white">项目信息</span>
                  </div>
                  {projectInfoExpanded ? (
                    <ChevronUpIcon className="w-4 h-4 text-gray-500" />
                  ) : (
                    <ChevronDownIcon className="w-4 h-4 text-gray-500" />
                  )}
                </button>
                
                {projectInfoExpanded && (
                  <div className="px-4 pb-4">
                    <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3">
                      <h3 className="font-medium text-blue-900 dark:text-blue-100 mb-1">
                        {selectedProject.name}
                      </h3>
                      <p className="text-xs text-blue-700 dark:text-blue-300 mb-2">
                        {selectedProject.description}
                      </p>
                      <div className="flex items-center justify-between text-xs text-blue-600 dark:text-blue-400">
                        <span>{selectedProject.stage}</span>
                        <span>{selectedProject.fileCount} 个文件</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* 对话历史 */}
            <div className="flex-1 overflow-y-auto">
              <div className="p-3">
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">对话历史</h3>
              </div>
              
              {isLoadingConversations ? (
                <div className="p-4 text-center text-gray-500 dark:text-gray-400">
                  <div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto mb-2" />
                  加载对话中...
                </div>
              ) : conversations.length === 0 ? (
                <div className="p-4 text-center text-gray-500 dark:text-gray-400">
                  <ChatBubbleLeftRightIcon className="w-12 h-12 mx-auto mb-2 text-gray-300 dark:text-gray-600" />
                  <p>还没有对话</p>
                  <p className="text-sm">创建新对话开始聊天</p>
                </div>
              ) : (
                <div className="space-y-1 px-3">
                  {conversations.map((conversation) => (
                    <button
                      key={conversation.id}
                      onClick={() => handleSelectConversation(conversation)}
                      className={cn(
                        "w-full text-left p-3 rounded-lg transition-colors",
                        currentConversation?.id === conversation.id
                          ? "bg-blue-100 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700"
                          : "hover:bg-gray-100 dark:hover:bg-gray-700"
                      )}
                    >
                      <h4 className="font-medium text-gray-900 dark:text-white text-sm mb-1 truncate">
                        {conversation.title}
                      </h4>
                      <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                        {conversation.last_message || '新对话'}
                      </p>
                      <div className="flex items-center justify-between mt-1">
                        <span className="text-xs text-gray-400 dark:text-gray-500">
                          {conversation.message_count} 条消息
                        </span>
                        <span className="text-xs text-gray-400 dark:text-gray-500">
                          {new Date(conversation.updated_at).toLocaleDateString()}
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
        
        {/* 折叠按钮 */}
        <button
          onClick={() => setLeftSidebarCollapsed(!leftSidebarCollapsed)}
          className="absolute left-2 top-1/2 transform -translate-y-1/2 p-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-full shadow-md hover:shadow-lg transition-all z-10"
        >
          {leftSidebarCollapsed ? (
            <ChevronDownIcon className="w-3 h-3 text-gray-600 dark:text-gray-400 rotate-90" />
          ) : (
            <ChevronUpIcon className="w-3 h-3 text-gray-600 dark:text-gray-400 -rotate-90" />
          )}
        </button>
      </div>

      {/* 中间主内容区域 - 聊天对话框 */}
      <div className="flex-1 flex flex-col">
        {currentConversation ? (
          <Chat
            messages={messages}
            onSendMessage={handleSendMessage}
            isLoading={isLoading}
            className="h-full"
          />
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <SparklesIcon className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                欢迎使用 AI 助手
              </h2>
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                选择一个对话或创建新对话开始聊天
              </p>
              <Button
                onClick={() => setShowNewConversationModal(true)}
                variant="primary"
              >
                <PlusIcon className="w-4 h-4 mr-2" />
                创建新对话
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* 右侧边栏 - 文件信息 */}
      <div className={cn(
        "bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 flex flex-col transition-all duration-300",
        rightSidebarCollapsed ? "w-12" : "w-80"
      )}>
        {!rightSidebarCollapsed && (
          <>
            {/* 文件信息标题 */}
            <div className="p-4 border-b border-gray-200 dark:border-gray-700">
              <button
                onClick={() => setFileInfoExpanded(!fileInfoExpanded)}
                className="w-full flex items-center justify-between"
              >
                <div className="flex items-center gap-2">
                  <DocumentTextIcon className="w-5 h-5 text-green-600" />
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white">项目文件</h2>
                </div>
                {fileInfoExpanded ? (
                  <ChevronUpIcon className="w-4 h-4 text-gray-500" />
                ) : (
                  <ChevronDownIcon className="w-4 h-4 text-gray-500" />
                )}
              </button>
            </div>

            {/* 文件列表 */}
            {fileInfoExpanded && (
              <div className="flex-1 overflow-y-auto p-4">
                {projectFiles.length === 0 ? (
                  <div className="text-center text-gray-500 dark:text-gray-400 mt-8">
                    <ArchiveBoxIcon className="w-12 h-12 mx-auto mb-2 text-gray-300 dark:text-gray-600" />
                    <p>暂无文件</p>
                    <p className="text-sm">上传文件来增强AI的理解能力</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {projectFiles.map((file) => (
                      <div
                        key={file.id}
                        className="p-3 border border-gray-200 dark:border-gray-700 rounded-lg hover:shadow-md transition-shadow"
                      >
                        <div className="flex items-start gap-3">
                          <span className="text-2xl">{getFileIcon(file.type)}</span>
                          <div className="flex-1 min-w-0">
                            <h4 className="font-medium text-gray-900 dark:text-white text-sm truncate">
                              {file.name}
                            </h4>
                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                              {formatFileSize(file.size)} • {file.uploadDate}
                            </p>
                            
                            {/* 状态标签 */}
                            <span className={cn(
                              "inline-block px-2 py-1 text-xs rounded-full mt-2",
                              getStatusColor(file.status)
                            )}>
                              {file.status === 'analyzed' && '已分析'}
                              {file.status === 'processing' && '处理中'}
                              {file.status === 'uploaded' && '已上传'}
                              {file.status === 'error' && '错误'}
                            </span>
                            
                            {/* 标签 */}
                            {file.tags.length > 0 && (
                              <div className="flex flex-wrap gap-1 mt-2">
                                {file.tags.map((tag, index) => (
                                  <span
                                    key={index}
                                    className="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded"
                                  >
                                    {tag}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                          
                          <button className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors">
                            <EyeIcon className="w-4 h-4 text-gray-500" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
        )}
        
        {/* 折叠按钮 */}
        <button
          onClick={() => setRightSidebarCollapsed(!rightSidebarCollapsed)}
          className="absolute right-2 top-1/2 transform -translate-y-1/2 p-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-full shadow-md hover:shadow-lg transition-all z-10"
        >
          {rightSidebarCollapsed ? (
            <ChevronDownIcon className="w-3 h-3 text-gray-600 dark:text-gray-400 -rotate-90" />
          ) : (
            <ChevronUpIcon className="w-3 h-3 text-gray-600 dark:text-gray-400 rotate-90" />
          )}
        </button>
      </div>

      {/* 新建对话模态框 */}
      {showNewConversationModal && (
        <Modal
          isOpen={showNewConversationModal}
          onClose={() => setShowNewConversationModal(false)}
          title="创建新对话"
        >
          <div className="space-y-4">
            <Input
              label="对话标题"
              value={newConversationTitle}
              onChange={(e) => setNewConversationTitle(e.target.value)}
              placeholder="输入对话标题..."
              autoFocus
            />
            
            {selectedProject && (
              <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <p className="text-sm text-blue-900 dark:text-blue-100">
                  <strong>项目上下文:</strong> {selectedProject.name}
                </p>
              </div>
            )}
            
            <div className="flex gap-3 pt-4">
              <Button
                onClick={handleCreateConversation}
                disabled={!newConversationTitle.trim()}
                className="flex-1"
                variant="primary"
              >
                创建对话
              </Button>
              <Button
                onClick={() => setShowNewConversationModal(false)}
                variant="outline"
              >
                取消
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
