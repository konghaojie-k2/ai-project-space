'use client';

import React, { useState } from 'react';
import { ChatOptimized, Message } from '@/components/features/ChatOptimized';
import { chatAPI } from '@/lib/api/chat';

/**
 * 流式响应和Markdown渲染测试页面
 */
export default function StreamingTestPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // 模拟会话ID
  const conversationId = 'test_conv_123';

  const handleSendMessage = async (content: string) => {
    // 添加用户消息
    const userMessage: Message = {
      id: `msg_${Date.now()}`,
      content,
      role: 'user',
      timestamp: new Date(),
      status: 'sent'
    };
    setMessages(prev => [...prev, userMessage]);

    // 创建AI消息
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
      // 使用流式API
      await chatAPI.sendMessageStream(conversationId, {
        messages: [{ role: 'user', content }],
        stream: true
      }, {
        onStart: (messageId) => {
          console.log('开始接收流式响应:', messageId);
        },
        onContent: (chunk) => {
          // 实时更新AI消息内容
          setMessages(prev => prev.map(msg => 
            msg.id === aiMessageId 
              ? { ...msg, content: msg.content + chunk, status: 'sending' }
              : msg
          ));
        },
        onEnd: (messageId) => {
          // 标记消息完成
          setMessages(prev => prev.map(msg => 
            msg.id === aiMessageId 
              ? { ...msg, status: 'sent' }
              : msg
          ));
          setIsLoading(false);
          console.log('流式响应完成:', messageId);
        },
        onError: (error) => {
          console.error('流式响应失败:', error);
          setMessages(prev => prev.map(msg => 
            msg.id === aiMessageId 
              ? { ...msg, content: '抱歉，响应失败。请重试。', status: 'error' }
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

  const handleClearMessages = () => {
    setMessages([]);
  };

  const testQuestions = [
    '请给我写一段Python代码',
    '什么是React Hook？',
    '如何优化前端性能？',
    '解释一下微服务架构',
    '设计一个简单的聊天应用'
  ];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          {/* 页面标题 */}
          <div className="mb-8 text-center">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              流式响应和Markdown渲染测试
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              测试流式回复的实时渲染效果和Markdown语法支持
            </p>
          </div>

          {/* 测试按钮 */}
          <div className="mb-6 flex flex-wrap gap-2">
            <h3 className="w-full text-lg font-semibold text-gray-900 dark:text-white mb-2">
              快速测试问题：
            </h3>
            {testQuestions.map((question, index) => (
              <button
                key={index}
                onClick={() => handleSendMessage(question)}
                disabled={isLoading}
                className="px-3 py-1 text-sm bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-900/50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {question}
              </button>
            ))}
            <button
              onClick={handleClearMessages}
              disabled={isLoading}
              className="px-3 py-1 text-sm bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              清空消息
            </button>
          </div>

          {/* 聊天界面 */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg h-[600px]">
            <ChatOptimized
              messages={messages}
              onSendMessage={handleSendMessage}
              isLoading={isLoading}
              className="h-full"
            />
          </div>

          {/* 调试信息 */}
          {process.env.NODE_ENV === 'development' && (
            <div className="mt-6 p-4 bg-gray-100 dark:bg-gray-800 rounded-lg">
              <h4 className="font-semibold text-gray-900 dark:text-white mb-2">调试信息：</h4>
              <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                <p>消息数量: {messages.length}</p>
                <p>是否加载中: {isLoading ? '是' : '否'}</p>
                <p>当前会话ID: {conversationId}</p>
                <p>API基础URL: {process.env.NEXT_PUBLIC_API_BASE_URL}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
