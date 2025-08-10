'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import StreamingMarkdown from './StreamingMarkdown';
import { 
  PaperAirplaneIcon, 
  StopIcon, 
  BookmarkIcon,
  ClipboardDocumentIcon,
  UserIcon,
  CpuChipIcon
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';
import { copyMarkdown, copyAsPlainText } from '@/lib/utils/copy';

// 消息类型定义
export interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  status?: 'sending' | 'sent' | 'error';
  isTyping?: boolean;
}

// 聊天组件属性
interface ChatProps {
  messages: Message[];
  onSendMessage: (content: string) => void;
  onStopGeneration?: () => void;
  onSaveToDraft?: (content: string) => void;
  isLoading?: boolean;
  className?: string;
}

/**
 * 优化的聊天组件 - 参考DeerFlow实现
 * 特点：
 * 1. 使用StreamingMarkdown组件进行渲染
 * 2. 优化的用户体验和交互
 * 3. 完善的错误处理和加载状态
 * 4. 支持消息复制和保存功能
 */
export const ChatOptimized: React.FC<ChatProps> = ({
  messages,
  onSendMessage,
  onStopGeneration,
  onSaveToDraft,
  isLoading = false,
  className
}) => {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // 自动滚动到底部
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // 处理发送消息
  const handleSendMessage = useCallback(() => {
    if (inputValue.trim() && !isLoading) {
      onSendMessage(inputValue.trim());
      setInputValue('');
    }
  }, [inputValue, isLoading, onSendMessage]);

  // 处理回车键发送
  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  }, [handleSendMessage]);

  // 复制消息内容
  const copyMessageContent = useCallback(async (content: string, role: 'user' | 'assistant') => {
    if (role === 'assistant') {
      // AI消息保持Markdown格式
      await copyMarkdown(content, { showToast: true });
    } else {
      // 用户消息复制为纯文本
      await copyAsPlainText(content, { showToast: true });
    }
  }, []);

  // 格式化时间
  const formatTime = useCallback((timestamp: Date) => {
    return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }, []);

  return (
    <div className={cn('flex flex-col h-full bg-white dark:bg-gray-900 overflow-hidden', className)}>
      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6 custom-scrollbar custom-scrollbar-always min-h-0">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center mb-4">
              <CpuChipIcon className="w-8 h-8 text-blue-600 dark:text-blue-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              开始新的对话
            </h3>
            <p className="text-gray-600 dark:text-gray-400 max-w-md">
              向AI助手提问任何问题，我会尽力为您提供详细的回答和帮助。
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={cn(
                'flex items-start space-x-3',
                message.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''
              )}
            >
              {/* 头像 */}
              <div className={cn(
                'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
                message.role === 'user' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'
              )}>
                {message.role === 'user' ? (
                  <UserIcon className="w-5 h-5" />
                ) : (
                  <CpuChipIcon className="w-5 h-5" />
                )}
              </div>

              {/* 消息内容 */}
              <div className={cn(
                'flex-1 max-w-3xl',
                message.role === 'user' ? 'flex flex-col items-end' : ''
              )}>
                {/* 消息气泡 */}
                <div className={cn(
                  'relative group',
                  message.role === 'user' 
                    ? 'bg-blue-600 text-white rounded-2xl rounded-tr-md px-4 py-3 max-w-md'
                    : 'bg-gray-50 dark:bg-gray-800 rounded-2xl rounded-tl-md px-4 py-3 w-full'
                )}>
                  {message.role === 'user' ? (
                    <p className="text-sm leading-relaxed whitespace-pre-wrap text-white">
                      {message.content}
                    </p>
                  ) : (
                    <StreamingMarkdown
                      content={message.content}
                      isStreaming={message.status === 'sending' || message.isTyping}
                      className="text-gray-900 dark:text-gray-100"
                    />
                  )}

                  {/* 消息状态指示器 */}
                  {message.status === 'sending' && (
                    <div className="flex items-center space-x-1 mt-2 text-xs text-gray-500 dark:text-gray-400">
                      <div className="flex space-x-1">
                        <div className="w-1 h-1 bg-current rounded-full animate-bounce"></div>
                        <div className="w-1 h-1 bg-current rounded-full animate-bounce delay-75"></div>
                        <div className="w-1 h-1 bg-current rounded-full animate-bounce delay-150"></div>
                      </div>
                      <span>正在生成...</span>
                    </div>
                  )}

                  {message.status === 'error' && (
                    <div className="mt-2 text-xs text-red-500 dark:text-red-400">
                      发送失败，请重试
                    </div>
                  )}

                  {/* 消息操作按钮 */}
                  <div className="absolute -bottom-8 right-0 opacity-0 group-hover:opacity-100 transition-opacity">
                    <div className="flex space-x-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => copyMessageContent(message.content, message.role)}
                        className="h-6 px-2 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                      >
                        <ClipboardDocumentIcon className="w-3 h-3 mr-1" />
                        复制
                      </Button>
                      {message.role === 'assistant' && onSaveToDraft && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onSaveToDraft(message.content)}
                          className="h-6 px-2 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                        >
                          <BookmarkIcon className="w-3 h-3 mr-1" />
                          保存
                        </Button>
                      )}
                    </div>
                  </div>
                </div>

                {/* 时间戳 */}
                <div className={cn(
                  'text-xs text-gray-500 dark:text-gray-400 mt-1',
                  message.role === 'user' ? 'text-right' : 'text-left'
                )}>
                  {formatTime(message.timestamp)}
                </div>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 输入区域 */}
      <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-4">
        <div className="flex items-end space-x-3">
          <div className="flex-1">
            <Input
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="输入您的问题..."
              disabled={isLoading}
              className="resize-none min-h-[44px] max-h-32"
              rows={1}
              multiline
            />
          </div>
          
          <div className="flex space-x-2">
            {isLoading && onStopGeneration ? (
              <Button
                variant="outline"
                size="sm"
                onClick={onStopGeneration}
                className="px-3 py-2"
              >
                <StopIcon className="w-4 h-4 mr-1" />
                停止
              </Button>
            ) : (
              <Button
                onClick={handleSendMessage}
                disabled={!inputValue.trim() || isLoading}
                className="px-3 py-2"
              >
                <PaperAirplaneIcon className="w-4 h-4 mr-1" />
                发送
              </Button>
            )}
          </div>
        </div>

        {/* 提示信息 */}
        {!isLoading && (
          <div className="mt-2 text-xs text-gray-500 dark:text-gray-400 text-center">
            按 Enter 发送消息，Shift + Enter 换行
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatOptimized;
