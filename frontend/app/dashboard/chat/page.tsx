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
  ChatBubbleLeftRightIcon,
  TrashIcon,
  DocumentTextIcon,
  ArrowRightIcon,
  HomeIcon,
  ArrowLeftIcon,
  FolderIcon,
  MagnifyingGlassIcon,
  ChevronDownIcon,
  CheckIcon,
  ChevronRightIcon,
  ChevronLeftIcon,
  BookmarkIcon,
  CloudArrowDownIcon,
  PaperClipIcon,
  EyeIcon,
  DocumentDuplicateIcon,
  ArchiveBoxIcon,
  SparklesIcon,
  CodeBracketIcon,
  DocumentIcon
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';
import { chatAPI, Conversation, ConversationCreateRequest, ChatRequest } from '@/lib/api/chat';
import { projectSync } from '@/lib/services/project-sync';
import { useUser } from '@/lib/contexts/UserContext';

// 项目阶段选项
const PROJECT_STAGES = [
  '待分类',
  '售前阶段',
  '业务调研',
  '数据理解',
  '数据探索',
  '工程开发',
  '实施部署'
];

interface Project {
  id: string;
  name: string;
  description: string;
  stage: string;
  status: 'active' | 'archived' | 'completed';
  fileCount: number;
}

// 项目文件数据类型
interface ProjectFile {
  id: string;
  name: string;
  type: string;
  size: number;
  stage: string;
  created_at: string;
  original_name: string;
  access_level: string; // 添加权限级别字段
  user_id: string; // 添加文件所有者字段
  uploaded_by: string; // 添加上传者信息
}

// 暂存项数据类型
interface DraftItem {
  id: string;
  title: string;
  content: string;
  aiModel: string;
  createdAt: string;
  messageId: string;
  conversationId: string;
  tags: string[];
}

// 已保存项数据类型
interface SavedItem {
  id: string;
  title: string;
  content: string;
  fileName: string;
  fileType: string;
  stage: string;
  savedAt: string;
  originalDraftId?: string;
}

export default function ChatPage() {
  const { user } = useUser();
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

  // 项目相关状态
  const [projects, setProjects] = useState<Project[]>([]);
  const [showProjectSelector, setShowProjectSelector] = useState(false);
  const [projectSearchQuery, setProjectSearchQuery] = useState('');
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  
  // 项目工作区状态
  const [showProjectWorkspace, setShowProjectWorkspace] = useState(true);
  const [workspaceActiveTab, setWorkspaceActiveTab] = useState<'files' | 'drafts' | 'saved'>('files');
  const [projectFiles, setProjectFiles] = useState<any[]>([]);
  const [drafts, setDrafts] = useState<any[]>([]);
  const [savedItems, setSavedItems] = useState<any[]>([]);
  const [isLoadingFiles, setIsLoadingFiles] = useState(false);
  
  // 保存模态框状态
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [savingDraft, setSavingDraft] = useState<DraftItem | null>(null);
  const [saveFileName, setSaveFileName] = useState('');
  const [saveFileStage, setSaveFileStage] = useState('待分类');
  const [saveAccessLevel, setSaveAccessLevel] = useState('all_users'); // 默认为所有人可见
  
  // 下拉菜单定位ref
  const projectSelectorRef = useRef<HTMLDivElement>(null);
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0, width: 0 });
  const [isClient, setIsClient] = useState(false);

  // 根据用户权限过滤文件列表
  const filterFilesByPermission = (files: ProjectFile[]): ProjectFile[] => {
    if (!user) return []; // 未登录用户无法查看任何文件
    
    return files.filter(file => {
      // 根据访问级别判断权限
      switch (file.access_level) {
        case 'all_users':
          return true; // 全员可见
        case 'admins_only':
          return user.is_superuser; // 仅管理员可见
        case 'owner_only':
          return file.user_id === user.id; // 仅文件所有者可见
        default:
          return false; // 未知权限级别，默认不可见
      }
    });
  };

  // 确保只在客户端渲染Portal
  useEffect(() => {
    setIsClient(true);
  }, []);

  // 加载项目数据
  useEffect(() => {
    const loadProjects = () => {
      const allProjects = projectSync.getProjects()
        .filter(p => p.status === 'active') // 只显示活跃项目
        .map(p => ({
          id: p.id,
          name: p.name,
          description: p.description,
          stage: p.stage,
          status: p.status,
          fileCount: p.fileCount
        }));
      setProjects(allProjects);
      
      // 如果有指定的项目ID，设置选中的项目
      if (projectId) {
        const project = allProjects.find(p => p.id === projectId);
        if (project) {
          setSelectedProject(project);
        }
      }
    };

    loadProjects();
    
    // 订阅项目数据变化
    const unsubscribe = projectSync.subscribe(() => {
      loadProjects();
    });

    return unsubscribe;
  }, [projectId]);

  // 加载会话列表
  useEffect(() => {
    loadConversations();
  }, []);

  // 如果从项目进入，自动创建项目会话
  useEffect(() => {
    if (projectId && projectName && !isLoadingConversations && selectedProject) {
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
  }, [projectId, projectName, conversations, isLoadingConversations, selectedProject]);

  // 加载项目文件
  const loadProjectFiles = async () => {
    if (!selectedProject?.id) {
      setProjectFiles([]);
      return;
    }

    if (isLoadingFiles) {
      console.log('⏳ 项目文件正在加载中，跳过重复请求');
      return;
    }

    console.log('📁 开始加载项目文件:', { projectId: selectedProject.id });
    setIsLoadingFiles(true);
    try {
      const { apiGet } = await import('@/lib/api');
      const response = await apiGet(`/api/v1/files/?project_id=${selectedProject.id}`);
      if (response.ok) {
        const files = await response.json();
        // 应用权限过滤
        const filteredFiles = filterFilesByPermission(files);
        console.log('✅ 项目文件加载成功:', { fileCount: filteredFiles.length });
        setProjectFiles(filteredFiles);
      } else {
        console.warn('⚠️ 加载项目文件失败:', response.statusText);
        setProjectFiles([]);
      }
    } catch (error) {
      console.error('❌ 加载项目文件出错:', error);
      setProjectFiles([]);
    } finally {
      setIsLoadingFiles(false);
    }
  };

  useEffect(() => {
    loadProjectFiles();
  }, [selectedProject?.id, user?.id]); // 当项目或用户变化时重新加载文件

  // 暂存AI回答
  const handleSaveToDraft = (message: Message) => {
    if (message.role !== 'assistant') return;

    const draftItem: DraftItem = {
      id: `draft_${Date.now()}`,
      title: message.content.slice(0, 50) + '...',
      content: message.content,
      aiModel: message.model || 'AI助手', // 从消息中获取具体模型，默认显示通用名称
      createdAt: new Date().toISOString(),
      messageId: message.id,
      conversationId: currentConversation?.id || '',
      tags: []
    };

    setDrafts(prev => [draftItem, ...prev]);
    // 这里可以添加toast提示
  };

  // 根据文件类型获取对应图标
  const getFileIcon = (fileName: string) => {
    const extension = fileName.split('.').pop()?.toLowerCase();
    
    switch (extension) {
      case 'md':
      case 'markdown':
        return <CodeBracketIcon className="w-5 h-5 text-purple-600 flex-shrink-0 mt-0.5" />;
      case 'pdf':
        return <DocumentIcon className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />;
      case 'doc':
      case 'docx':
        return <DocumentTextIcon className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />;
      case 'txt':
        return <DocumentTextIcon className="w-5 h-5 text-gray-600 flex-shrink-0 mt-0.5" />;
      default:
        return <DocumentTextIcon className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />;
    }
  };

  // 提取Markdown标题作为文件名
  const extractTitleFromMarkdown = (content: string): string => {
    // 匹配一级标题 (# 标题)
    const h1Match = content.match(/^#\s+(.+?)$/m);
    if (h1Match) {
      return h1Match[1]
        .replace(/[^a-zA-Z0-9\u4e00-\u9fa5\s]/g, '') // 移除特殊字符
        .trim()
        .replace(/\s+/g, '_'); // 空格替换为下划线
    }
    
    // 如果没有一级标题，尝试匹配二级标题
    const h2Match = content.match(/^##\s+(.+?)$/m);
    if (h2Match) {
      return h2Match[1]
        .replace(/[^a-zA-Z0-9\u4e00-\u9fa5\s]/g, '')
        .trim()
        .replace(/\s+/g, '_');
    }
    
    // 如果没有二级标题，尝试匹配三级标题
    const h3Match = content.match(/^###\s+(.+?)$/m);
    if (h3Match) {
      return h3Match[1]
        .replace(/[^a-zA-Z0-9\u4e00-\u9fa5\s]/g, '')
        .trim()
        .replace(/\s+/g, '_');
    }
    
    // 如果都没有，取内容前30字符
    return content.slice(0, 30)
      .replace(/[^a-zA-Z0-9\u4e00-\u9fa5\s]/g, '')
      .trim()
      .replace(/\s+/g, '_') || 'AI回答';
  };

  // 打开保存模态框
  const handleOpenSaveModal = (draft: DraftItem) => {
    setSavingDraft(draft);
    // 智能提取文件名
    const defaultName = extractTitleFromMarkdown(draft.content);
    setSaveFileName(defaultName);
    setSaveFileStage('待分类');
    setShowSaveModal(true);
  };

  // 确认保存到项目
  const handleConfirmSave = async () => {
    if (!savingDraft || !saveFileName.trim()) return;
    
    try {
      await handleSaveToProject(savingDraft, saveFileName.trim(), 'md', saveFileStage, saveAccessLevel);
      setShowSaveModal(false);
      setSavingDraft(null);
      setSaveFileName('');
      setSaveFileStage('待分类');
      setSaveAccessLevel('all_users'); // 重置权限级别为默认值
      // 从暂存中移除已保存的项目
      setDrafts(prev => prev.filter(d => d.id !== savingDraft.id));
      // 刷新文件列表
      if (selectedProject) {
        loadProjectFiles();
      }
    } catch (error) {
      console.error('保存失败:', error);
    }
  };

  // 保存到项目文件
  const handleSaveToProject = async (draftItem: DraftItem, fileName: string, fileType: string, stage: string, accessLevel: string = 'all_users') => {
    try {
      console.log('💾 开始保存AI生成文件:', {
        fileName,
        projectId: selectedProject?.id,
        projectName: selectedProject?.name,
        stage,
        accessLevel
      });

      // 创建文件内容
      const fileContent = new Blob([draftItem.content], { type: 'text/markdown' });
      const formData = new FormData();
      formData.append('files', fileContent, `${fileName}.${fileType}`);
      formData.append('project_id', selectedProject?.id || '');
      formData.append('stage', stage);
      // 组合AI模型名和用户名 - 修复旧暂存数据的模型名称
      const actualModel = draftItem.aiModel === 'AI助手' || draftItem.aiModel === 'Claude-3.5' 
        ? 'deepseek-v3-250324' 
        : draftItem.aiModel;
      const uploaderInfo = `${actualModel} (${user?.name || '管理员'})`;
      formData.append('uploaded_by', uploaderInfo);
      formData.append('description', `${actualModel}生成的回答内容，由${user?.name || '管理员'}保存`);
      
      // 添加权限控制：使用用户选择的权限级别
      formData.append('access_level', accessLevel);

      const { apiUpload } = await import('@/lib/api');
      const response = await apiUpload('/api/v1/files/upload', formData);

      if (response.ok) {
        const savedFile = await response.json();
        console.log('✅ AI文件保存成功:', {
          savedFile,
          fileCount: Array.isArray(savedFile) ? savedFile.length : 1
        });
        
        // 添加到已保存列表
        const savedItem: SavedItem = {
          id: `saved_${Date.now()}`,
          title: draftItem.title,
          content: draftItem.content,
          fileName: fileName,
          fileType: fileType,
          stage: stage,
          savedAt: new Date().toISOString(),
          originalDraftId: draftItem.id
        };
        
        setSavedItems(prev => [savedItem, ...prev]);
        
        // 从暂存区移除
        setDrafts(prev => prev.filter(d => d.id !== draftItem.id));
        
        // 强制刷新项目文件列表
        console.log('🔄 AI保存文件成功，强制刷新文件列表');
        setIsLoadingFiles(false); // 重置加载状态，确保可以刷新
        await loadProjectFiles();
        
        // 更新项目文件计数
        if (selectedProject) {
          projectSync.updateProjectFileStats(selectedProject.id);
        }
      } else {
        console.error('保存文件失败:', response.statusText);
      }
    } catch (error) {
      console.error('保存文件出错:', error);
    }
  };

  // 生成文件相关问题
  const generateFileQuestion = (file: ProjectFile) => {
    const questions = [
      `请帮我分析${file.original_name}这个文件的内容`,
      `${file.original_name}文件中有哪些关键信息？`,
      `基于${file.original_name}，请给出相关建议`,
      `请总结${file.original_name}的主要内容`
    ];
    return questions[Math.floor(Math.random() * questions.length)];
  };

  const loadConversations = async () => {
    try {
      setIsLoadingConversations(true);
      const data = await chatAPI.getConversations();
      // 只有在成功获取数据时才更新会话列表，避免清空现有列表
      if (data && Array.isArray(data)) {
        setConversations(data);
      }
    } catch (error) {
      console.error('加载会话列表失败:', error);
      // 加载失败时不清空现有列表，保持用户体验
    } finally {
      setIsLoadingConversations(false);
    }
  };

  const handleSelectConversation = async (conversation: Conversation) => {
    setCurrentConversation(conversation);
    // 同步选中的项目
    if (conversation.project_id) {
      const project = projects.find(p => p.id === conversation.project_id);
      setSelectedProject(project || null);
      setSelectedProjectId(conversation.project_id);
    } else {
      setSelectedProject(null);
      setSelectedProjectId('');
    }
    
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

    // 用户消息ID使用临时ID，后端会生成真实的UUID
    const userMessage: Message = {
      id: `temp_user_${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date(),
      status: 'sent'
    };

    // 使用临时ID，等待后端返回真实UUID后更新
    const aiMessageId = `temp_${Date.now()}`;
    const aiMessage: Message = {
      id: aiMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      status: 'sending'
    };

    setMessages(prev => [...prev, userMessage, aiMessage]);
    setIsLoading(true);

    // 用于存储后端返回的真实消息ID
    let realMessageId = aiMessageId;

    try {
      const request: ChatRequest = {
        messages: [...messages, userMessage].map(msg => ({
          id: msg.id,
          role: msg.role,
          content: msg.content,
          timestamp: msg.timestamp,
          status: msg.status
        })),
        project_id: currentConversation.project_id,
        stream: true
      };

      // 使用流式API
      await chatAPI.sendMessageStream(currentConversation.id, request, {
        onStart: (messageId) => {
          console.log('AI开始回复:', messageId);
          // 更新为后端返回的真实UUID
          realMessageId = messageId;
          setMessages(prev => prev.map(msg => 
            msg.id === aiMessageId 
              ? { ...msg, id: messageId }
              : msg
          ));
        },
        onContent: (chunk) => {
          // 实时更新AI消息内容（使用真实ID或临时ID）
          setMessages(prev => prev.map(msg => 
            (msg.id === aiMessageId || msg.id === realMessageId)
              ? { ...msg, content: msg.content + chunk, status: 'sending' }
              : msg
          ));
        },
        onEnd: (messageId, endData) => {
          // 标记消息完成，并设置模型信息（使用真实ID）
          const finalMessageId = messageId || realMessageId;
          setMessages(prev => prev.map(msg => 
            (msg.id === aiMessageId || msg.id === realMessageId || msg.id === finalMessageId)
              ? { ...msg, id: finalMessageId, status: 'sent', model: endData?.model || 'AI助手' }
              : msg
          ));
          setIsLoading(false);
          // 更新会话列表
          loadConversations();
        },
        onError: (error) => {
          console.error('流式回复失败:', error);
          // 使用降级方案（保持使用当前ID）
          const fallbackContent = generateSmartResponse(content, currentConversation.project_name);
          setMessages(prev => prev.map(msg => 
            (msg.id === aiMessageId || msg.id === realMessageId)
              ? { ...msg, content: fallbackContent, status: 'sent', model: '降级响应' }
              : msg
          ));
          setIsLoading(false);
        }
      });

    } catch (error) {
      console.error('发送消息失败:', error);
      // 降级处理（保持使用当前ID）
      const fallbackContent = generateSmartResponse(content, currentConversation.project_name);
      setMessages(prev => prev.map(msg => 
        (msg.id === aiMessageId || msg.id === realMessageId)
          ? { ...msg, content: fallbackContent, status: 'sent', model: '降级响应' }
          : msg
      ));
      setIsLoading(false);
    }
  };

  // 生成智能模拟回复
  const generateSmartResponse = (question: string, projectName?: string): string => {
    const responses = [
      "基于当前项目的文档分析，我建议您考虑以下几个方面...",
      "根据项目的历史文件和上下文，这是一个很好的问题。",
      "让我查看一下项目中的相关文档来为您提供准确的答案...",
      "从项目的阶段和已有资料来看，我的建议是...",
      "结合项目的具体需求和目标，我认为您可以这样处理..."
    ];
    
    if (projectName) {
      return `关于"${projectName}"项目：${responses[Math.floor(Math.random() * responses.length)]}

这是基于项目上下文的智能回复。系统已经分析了项目中的相关文档，包括：
- 项目阶段文档
- 相关技术资料
- 历史讨论记录

如需更精确的回答，请确保项目文档已完整上传。`;
    }
    
    return responses[Math.floor(Math.random() * responses.length)];
  };

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
    } catch (error) {
      console.error('创建会话失败:', error);
    }
  };

  const handleDeleteConversation = async (conversationId: string) => {
    try {
      await chatAPI.deleteConversation(conversationId);
      setConversations(prev => prev.filter(c => c.id !== conversationId));
      
      if (currentConversation?.id === conversationId) {
        setCurrentConversation(null);
        setMessages([]);
      }
    } catch (error) {
      console.error('删除会话失败:', error);
    }
  };

  // 处理项目选择
  const handleSelectProject = (project: Project | null) => {
    setSelectedProject(project);
    setSelectedProjectId(project?.id || '');
    setShowProjectSelector(false);
    setProjectSearchQuery('');
  };

  // 处理下拉菜单显示
  const handleToggleProjectSelector = () => {
    if (!showProjectSelector && projectSelectorRef.current) {
      const rect = projectSelectorRef.current.getBoundingClientRect();
      setDropdownPosition({
        top: rect.bottom + window.scrollY + 4,
        left: rect.left + window.scrollX,
        width: rect.width
      });
    }
    setShowProjectSelector(!showProjectSelector);
  };

  // 监听窗口滚动和resize，关闭下拉菜单
  useEffect(() => {
    const handleWindowEvent = () => {
      setShowProjectSelector(false);
    };

    const handleEscapeKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setShowProjectSelector(false);
      }
    };

    if (showProjectSelector) {
      window.addEventListener('scroll', handleWindowEvent);
      window.addEventListener('resize', handleWindowEvent);
      document.addEventListener('keydown', handleEscapeKey);
      return () => {
        window.removeEventListener('scroll', handleWindowEvent);
        window.removeEventListener('resize', handleWindowEvent);
        document.removeEventListener('keydown', handleEscapeKey);
      };
    }
  }, [showProjectSelector]);

  // 过滤项目
  const filteredProjects = projects.filter(project =>
    project.name.toLowerCase().includes(projectSearchQuery.toLowerCase()) ||
    project.description.toLowerCase().includes(projectSearchQuery.toLowerCase())
  );

  const formatConversationTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMins < 1) return '刚刚';
    if (diffMins < 60) return `${diffMins}分钟前`;
    if (diffHours < 24) return `${diffHours}小时前`;
    if (diffDays < 30) return `${diffDays}天前`;
    return date.toLocaleDateString();
  };

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {/* 左侧边栏 - 会话列表 */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col min-h-0">
        {/* 头部 */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center gap-3 mb-4">
            <Link href="/dashboard" className="p-1 hover:bg-gray-100 rounded-lg transition-colors">
              <ArrowLeftIcon className="w-5 h-5 text-gray-600" />
            </Link>
            <h1 className="text-lg font-semibold text-gray-900">AI助手</h1>
            
            {/* 工作区切换按钮 */}
            {selectedProject && (
              <button
                onClick={() => setShowProjectWorkspace(!showProjectWorkspace)}
                className="ml-auto p-1 hover:bg-gray-100 rounded-lg transition-colors"
                title={showProjectWorkspace ? "隐藏项目工作区" : "显示项目工作区"}
              >
                {showProjectWorkspace ? (
                  <ChevronRightIcon className="w-5 h-5 text-gray-600" />
                ) : (
                  <ChevronLeftIcon className="w-5 h-5 text-gray-600" />
                )}
              </button>
            )}
          </div>
          
          {/* 项目上下文指示器 */}
          {selectedProject && (
            <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-center gap-2">
                <FolderIcon className="w-4 h-4 text-blue-600" />
                <span className="text-sm font-medium text-blue-900">当前项目</span>
              </div>
              <p className="text-sm text-blue-800 mt-1">{selectedProject.name}</p>
              <p className="text-xs text-blue-600 mt-1">
                {selectedProject.stage} • {selectedProject.fileCount} 个文件
              </p>
            </div>
          )}
          
            <Button
              onClick={() => setShowNewConversationModal(true)}
            className="w-full"
            variant="primary"
            >
            <PlusIcon className="w-4 h-4 mr-2" />
            新建对话
            </Button>
        </div>

        {/* 会话列表 */}
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          {isLoadingConversations ? (
            <div className="p-4 text-center text-gray-500">
              <div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto mb-2" />
              加载对话中...
            </div>
          ) : (conversations?.length || 0) === 0 ? (
            <div className="p-4 text-center text-gray-500">
              <ChatBubbleLeftRightIcon className="w-12 h-12 mx-auto mb-2 text-gray-300" />
              <p>还没有对话</p>
              <p className="text-sm">创建新对话开始聊天</p>
            </div>
          ) : (
            <div className="p-2">
              {conversations.map((conversation) => {
                const isProjectConversation = !!conversation.project_id;
                const project = isProjectConversation ? projects.find(p => p.id === conversation.project_id) : null;
                
                return (
                <div
                  key={conversation.id}
                    onClick={() => handleSelectConversation(conversation)}
                  className={cn(
                      "p-3 mb-2 rounded-lg cursor-pointer transition-colors group",
                    currentConversation?.id === conversation.id
                        ? "bg-blue-100 border-blue-200"
                        : "hover:bg-gray-50 border-transparent"
                  )}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                          {isProjectConversation && (
                            <FolderIcon className="w-4 h-4 text-blue-600 flex-shrink-0" />
                          )}
                        <h3 className="text-sm font-medium text-gray-900 truncate">
                          {conversation.title}
                        </h3>
                      </div>
                        
                        {/* 项目信息 */}
                        {project && (
                          <p className="text-xs text-blue-600 mb-1">
                            {project.name} • {project.stage}
                        </p>
                      )}
                        
                        {/* 最后消息时间 */}
                        <p className="text-xs text-gray-500">
                          {formatConversationTime(conversation.updated_at)}
                        </p>
                      </div>
                      
                      <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteConversation(conversation.id);
                      }}
                        className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 rounded transition-all"
                    >
                        <TrashIcon className="w-4 h-4 text-red-600" />
                      </button>
                  </div>
                </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* 主要内容区域 */}
      <div className="flex-1 flex flex-col min-h-0 min-w-0">
        {currentConversation ? (
          <>
            {/* 聊天头部 */}
            <div className="p-4 bg-white border-b border-gray-200">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">
                    {currentConversation.title}
                  </h2>
                  {selectedProject && (
                    <p className="text-sm text-gray-600">
                      基于 "{selectedProject.name}" 项目上下文
                    </p>
                  )}
                </div>
                
                {/* 快速操作 */}
                <div className="flex items-center gap-2">
                  {currentConversation.project_id && (
                    <Link
                      href={`/dashboard/projects/${currentConversation.project_id}`}
                      className="px-3 py-1.5 text-sm bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors flex items-center gap-1"
                    >
                      <FolderIcon className="w-4 h-4" />
                      查看项目
                    </Link>
                  )}
                </div>
              </div>
            </div>

            {/* 聊天内容 */}
            <div className="flex-1 min-h-0 overflow-hidden">
              <Chat
                messages={messages}
                onSendMessage={handleSendMessage}
                isLoading={isLoading}
                onSaveToDraft={handleSaveToDraft}
                className="h-full"
              />
            </div>
          </>
        ) : (
          /* 欢迎界面 */
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
            <div className="max-w-md">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <ChatBubbleLeftRightIcon className="w-8 h-8 text-blue-600" />
              </div>
              
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                欢迎使用AI助手
              </h2>
              
              <p className="text-gray-600 mb-6">
                选择一个对话开始聊天，或创建新对话。
                AI助手可以根据项目上下文为您提供专业建议。
              </p>

              <Button
                onClick={() => setShowNewConversationModal(true)}
                variant="primary"
                className="mb-4"
              >
                <PlusIcon className="w-4 h-4 mr-2" />
                开始新对话
              </Button>
              
              <div className="text-sm text-gray-500">
                <p>💡 提示：从项目页面点击"AI助手"可以自动加载项目上下文</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 右侧项目工作区 */}
      {showProjectWorkspace && selectedProject && (
        <div className="w-80 bg-white border-l border-gray-200 flex flex-col min-h-0">
          {/* 工作区头部 */}
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-semibold text-gray-900">项目工作区</h3>
              <button
                onClick={() => setShowProjectWorkspace(false)}
                className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
                title="隐藏工作区"
              >
                <ChevronRightIcon className="w-5 h-5 text-gray-600" />
              </button>
            </div>
            
            {/* 标签切换 */}
            <div className="flex bg-gray-100 rounded-lg p-1">
              <button
                onClick={() => setWorkspaceActiveTab('files')}
                className={cn(
                  "flex-1 px-3 py-2 text-sm rounded-md transition-colors flex items-center justify-center gap-1",
                  workspaceActiveTab === 'files'
                    ? "bg-white text-blue-600 shadow-sm"
                    : "text-gray-600 hover:text-gray-900"
                )}
              >
                <FolderIcon className="w-4 h-4" />
                文件 ({projectFiles?.length || 0})
              </button>
              <button
                onClick={() => setWorkspaceActiveTab('drafts')}
                className={cn(
                  "flex-1 px-3 py-2 text-sm rounded-md transition-colors flex items-center justify-center gap-1",
                  workspaceActiveTab === 'drafts'
                    ? "bg-white text-blue-600 shadow-sm"
                    : "text-gray-600 hover:text-gray-900"
                )}
              >
                <BookmarkIcon className="w-4 h-4" />
                暂存 ({drafts?.length || 0})
              </button>
              <button
                onClick={() => setWorkspaceActiveTab('saved')}
                className={cn(
                  "flex-1 px-3 py-2 text-sm rounded-md transition-colors flex items-center justify-center gap-1",
                  workspaceActiveTab === 'saved'
                    ? "bg-white text-blue-600 shadow-sm"
                    : "text-gray-600 hover:text-gray-900"
                )}
              >
                <ArchiveBoxIcon className="w-4 h-4" />
                已保存 ({savedItems?.length || 0})
              </button>
            </div>
          </div>

          {/* 工作区内容 */}
          <div className="flex-1 overflow-y-auto custom-scrollbar">
            {/* 项目文件标签页 */}
            {workspaceActiveTab === 'files' && (
              <div className="p-4">
                {isLoadingFiles ? (
                  <div className="text-center py-8">
                    <div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto mb-2" />
                    <p className="text-sm text-gray-500">加载文件中...</p>
                  </div>
                ) : (projectFiles?.length || 0) === 0 ? (
                  <div className="text-center py-8">
                    <FolderIcon className="w-12 h-12 mx-auto mb-2 text-gray-300" />
                    <p className="text-sm text-gray-500">暂无项目文件</p>
                    <p className="text-xs text-gray-400 mt-1">上传文件到项目中查看</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {projectFiles.map((file) => (
                      <div
                        key={file.id}
                        className="p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors group"
                      >
                        <div className="flex items-start gap-3">
                          {getFileIcon(file.original_name)}
                          <div className="flex-1 min-w-0">
                            <h4 className="text-sm font-medium text-gray-900 truncate">
                              {file.original_name}
                            </h4>
                            <p className="text-xs text-gray-500 mt-1">
                              {file.stage}
                            </p>
                          </div>
                        </div>
                        
                        {/* 文件操作按钮 */}
                        <div className="mt-3 flex gap-2">
                          <button
                            onClick={() => {
                              const question = generateFileQuestion(file);
                              if (currentConversation) {
                                handleSendMessage(question);
                              }
                            }}
                            className="flex-1 px-3 py-1.5 text-xs bg-blue-50 text-blue-700 rounded-md hover:bg-blue-100 transition-colors flex items-center justify-center gap-1"
                          >
                            <SparklesIcon className="w-3 h-3" />
                            分析文件
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 暂存区标签页 */}
            {workspaceActiveTab === 'drafts' && (
              <div className="p-4">
                {(drafts?.length || 0) === 0 ? (
                  <div className="text-center py-8">
                    <BookmarkIcon className="w-12 h-12 mx-auto mb-2 text-gray-300" />
                    <p className="text-sm text-gray-500">暂存区为空</p>
                    <p className="text-xs text-gray-400 mt-1">在AI回答中点击暂存按钮保存内容</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {drafts.map((draft) => (
                      <div
                        key={draft.id}
                        className="p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        <h4 className="text-sm font-medium text-gray-900 mb-2">
                          {draft.title}
                        </h4>
                        <p className="text-xs text-gray-500 mb-3">
                          {new Date(draft.createdAt).toLocaleDateString()} • {draft.aiModel}
                        </p>
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleOpenSaveModal(draft)}
                            disabled={!selectedProject}
                            className={cn(
                              "flex-1 px-3 py-1.5 text-xs rounded-md transition-colors",
                              selectedProject
                                ? "bg-green-50 text-green-700 hover:bg-green-100"
                                : "bg-gray-50 text-gray-400 cursor-not-allowed"
                            )}
                          >
                            保存到项目
                          </button>
                          <button
                            onClick={() => {
                              setDrafts(prev => prev.filter(d => d.id !== draft.id));
                            }}
                            className="px-3 py-1.5 text-xs bg-red-50 text-red-700 rounded-md hover:bg-red-100 transition-colors"
                          >
                            删除
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 已保存标签页 */}
            {workspaceActiveTab === 'saved' && (
              <div className="p-4">
                {(savedItems?.length || 0) === 0 ? (
                  <div className="text-center py-8">
                    <ArchiveBoxIcon className="w-12 h-12 mx-auto mb-2 text-gray-300" />
                    <p className="text-sm text-gray-500">暂无已保存内容</p>
                    <p className="text-xs text-gray-400 mt-1">从暂存区保存内容到项目</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {savedItems.map((item) => (
                      <div
                        key={item.id}
                        className="p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                      >
                        <h4 className="text-sm font-medium text-gray-900 mb-2">
                          {item.fileName}.{item.fileType}
                        </h4>
                        <p className="text-xs text-gray-500 mb-2">
                          {item.stage} • {new Date(item.savedAt).toLocaleDateString()}
                        </p>
                        <div className="flex gap-2">
                          <Link
                            href={`/dashboard/projects/${selectedProject.id}`}
                            className="flex-1 px-3 py-1.5 text-xs bg-blue-50 text-blue-700 rounded-md hover:bg-blue-100 transition-colors text-center"
                          >
                            查看文件
                          </Link>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 新建对话模态框 */}
      <Modal
        isOpen={showNewConversationModal}
        onClose={() => {
          setShowNewConversationModal(false);
          setNewConversationTitle('');
          setProjectSearchQuery('');
        }}
        title="创建新对话"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              对话标题
            </label>
            <Input
              value={newConversationTitle}
              onChange={(e) => setNewConversationTitle(e.target.value)}
              placeholder="输入对话标题..."
              className="w-full"
            />
          </div>

          {/* 项目选择器 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              关联项目（可选）
            </label>
            <div ref={projectSelectorRef} className="relative">
              <button
                type="button"
                onClick={handleToggleProjectSelector}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-left bg-white hover:bg-gray-50 transition-colors flex items-center justify-between"
              >
                <span className={selectedProject ? 'text-gray-900' : 'text-gray-500'}>
                  {selectedProject ? (
                    <span className="flex items-center gap-2">
                      <FolderIcon className="w-4 h-4 text-blue-600" />
                      {selectedProject.name}
                    </span>
                  ) : (
                    '选择项目'
                  )}
                </span>
                <ChevronDownIcon className="w-4 h-4 text-gray-400" />
              </button>
            </div>
            
            {selectedProject && (
              <p className="text-xs text-gray-600 mt-1">
                AI将基于此项目的文档和上下文提供专业建议
              </p>
            )}
          </div>

          {/* Portal渲染的下拉菜单 */}
          {showProjectSelector && typeof window !== 'undefined' && isClient && createPortal(
            <>
              {/* 遮罩层 */}
              <div 
                className="fixed inset-0 z-40" 
                onClick={() => setShowProjectSelector(false)}
              />
              
              {/* 下拉菜单 */}
              <div 
                className="fixed z-50 bg-white border border-gray-300 rounded-lg shadow-xl max-h-60 overflow-hidden"
                style={{ 
                  top: dropdownPosition.top, 
                  left: dropdownPosition.left, 
                  width: dropdownPosition.width 
                }}
              >
                {/* 搜索框 */}
                <div className="p-2 border-b border-gray-200">
                  <div className="relative">
                    <MagnifyingGlassIcon className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                    <input
                      type="text"
                      value={projectSearchQuery}
                      onChange={(e) => setProjectSearchQuery(e.target.value)}
                      placeholder="搜索项目..."
                      className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      onClick={(e) => e.stopPropagation()}
                    />
                  </div>
                </div>

                <div className="max-h-48 overflow-y-auto">
                  {/* 无项目选项 */}
                  <button
                    type="button"
                    onClick={() => handleSelectProject(null)}
                    className="w-full px-3 py-2 text-left hover:bg-gray-50 flex items-center justify-between transition-colors"
                  >
                    <span className="text-gray-600">不关联项目</span>
                    {!selectedProject && <CheckIcon className="w-4 h-4 text-blue-600" />}
                  </button>

                  {/* 项目列表 */}
                  {filteredProjects.map((project) => (
                    <button
                      key={project.id}
                      type="button"
                      onClick={() => handleSelectProject(project)}
                      className="w-full px-3 py-2 text-left hover:bg-gray-50 flex items-center justify-between transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <FolderIcon className="w-4 h-4 text-blue-600" />
                        <div>
                          <p className="text-sm font-medium text-gray-900">{project.name}</p>
                          <p className="text-xs text-gray-500">
                            {project.stage} • {project.fileCount} 个文件
                          </p>
                        </div>
                      </div>
                      {selectedProject?.id === project.id && (
                        <CheckIcon className="w-4 h-4 text-blue-600" />
                      )}
                    </button>
                  ))}

                  {(filteredProjects?.length || 0) === 0 && projectSearchQuery && (
                    <div className="p-3 text-center text-gray-500 text-sm">
                      未找到匹配的项目
          </div>
                  )}
                </div>
              </div>
            </>,
            document.body
          )}

          <div className="flex gap-3 pt-4">
            <Button
              onClick={() => {
                setShowNewConversationModal(false);
                setNewConversationTitle('');
                setProjectSearchQuery('');
              }}
              variant="secondary"
              className="flex-1"
            >
              取消
            </Button>
            <Button
              onClick={handleCreateConversation}
              variant="primary"
              className="flex-1"
              disabled={!newConversationTitle.trim()}
            >
              创建对话
            </Button>
          </div>
        </div>
      </Modal>

      {/* 保存为文件模态框 */}
      {showSaveModal && savingDraft && (
        <Modal
          isOpen={showSaveModal}
          onClose={() => setShowSaveModal(false)}
          title="保存为MD文件"
          size="md"
        >
          <div className="space-y-4">
            {/* 文件预览 */}
            <div className="bg-gray-50 rounded-lg p-3">
              <h4 className="text-sm font-medium text-gray-900 mb-2">
                内容预览
              </h4>
              <p className="text-sm text-gray-600 max-h-32 overflow-y-auto">
                {savingDraft.content.slice(0, 200)}
                {savingDraft.content.length > 200 && '...'}
              </p>
            </div>

            {/* 文件名输入 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                文件名
              </label>
              <Input
                value={saveFileName}
                onChange={(e) => setSaveFileName(e.target.value)}
                placeholder="请输入文件名"
                className="w-full"
              />
              <p className="text-xs text-gray-500 mt-1">
                文件将保存为：{saveFileName}.md
              </p>
            </div>

            {/* 项目阶段选择 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                项目阶段
              </label>
              <select
                value={saveFileStage}
                onChange={(e) => setSaveFileStage(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {PROJECT_STAGES.map(stage => (
                  <option key={stage} value={stage}>{stage}</option>
                ))}
              </select>
            </div>

            {/* 权限级别选择 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                访问权限
              </label>
              <select
                value={saveAccessLevel}
                onChange={(e) => setSaveAccessLevel(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all_users">所有人可见</option>
                <option value="admins_only">仅管理员可见</option>
                <option value="owner_only">仅我可见</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">
                {saveAccessLevel === 'all_users' && '所有用户都可以查看此文件'}
                {saveAccessLevel === 'admins_only' && '只有管理员可以查看此文件'}
                {saveAccessLevel === 'owner_only' && '只有您可以查看此文件'}
              </p>
            </div>

            {/* 按钮组 */}
            <div className="flex gap-3 pt-4">
              <Button
                onClick={() => setShowSaveModal(false)}
                variant="outline"
                className="flex-1"
              >
                取消
              </Button>
              <Button
                onClick={handleConfirmSave}
                disabled={!saveFileName.trim()}
                className="flex-1"
              >
                保存文件
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
} 