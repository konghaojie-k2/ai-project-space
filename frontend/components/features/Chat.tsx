'use client';

import React, { useState, useRef, useEffect } from 'react';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import { 
  PaperAirplaneIcon, 
  StopIcon, 
  BookmarkIcon,
  ClipboardDocumentIcon
} from '@heroicons/react/24/outline';
import { cn } from '@/lib/utils';

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
  onSaveToDraft?: (message: Message) => void;
  isLoading?: boolean;
  className?: string;
}

export const Chat: React.FC<ChatProps> = ({
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
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 处理发送消息
  const handleSendMessage = () => {
    if (inputValue.trim() && !isLoading) {
      onSendMessage(inputValue.trim());
      setInputValue('');
    }
  };

  // 处理回车键发送
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // 代码高亮显示组件
  const CodeBlock: React.FC<{ content: string }> = ({ content }) => {
    const [copied, setCopied] = useState(false);

    const copyToClipboard = async () => {
      try {
        await navigator.clipboard.writeText(content);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch (err) {
        console.error('复制失败:', err);
      }
    };

    return (
      <div className="relative bg-gray-900 rounded-lg p-4 my-2">
        <div className="flex justify-between items-center mb-2">
          <span className="text-xs text-gray-400">代码</span>
          <Button
            variant="ghost"
            size="sm"
            onClick={copyToClipboard}
            className="text-gray-400 hover:text-white"
          >
            {copied ? '已复制' : '复制'}
          </Button>
        </div>
        <pre className="text-sm text-gray-100 overflow-x-auto">
          <code>{content}</code>
        </pre>
      </div>
    );
  };

  // 消息内容渲染
  const renderMessageContent = (content: string) => {
    // 检测代码块 (```code```)
    const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = codeBlockRegex.exec(content)) !== null) {
      // 添加代码块前的文本
      if (match.index > lastIndex) {
        parts.push({
          type: 'text',
          content: content.slice(lastIndex, match.index)
        });
      }

      // 添加代码块
      parts.push({
        type: 'code',
        content: match[2],
        language: match[1] || 'text'
      });

      lastIndex = match.index + match[0].length;
    }

    // 添加剩余文本
    if (lastIndex < content.length) {
      parts.push({
        type: 'text',
        content: content.slice(lastIndex)
      });
    }

    return parts.map((part, index) => {
      if (part.type === 'code') {
        return <CodeBlock key={index} content={part.content} />;
      }
      return (
        <p key={index} className="whitespace-pre-wrap">
          {part.content}
        </p>
      );
    });
  };

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* 消息列表区域 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
                <PaperAirplaneIcon className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-medium mb-2">开始对话</h3>
              <p className="text-sm">输入您的问题，AI助手将为您提供帮助</p>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={cn(
                'flex gap-3',
                message.role === 'user' ? 'justify-end' : 'justify-start'
              )}
            >
              {/* 用户消息 */}
              {message.role === 'user' && (
                <div className="flex items-end gap-2 max-w-[80%]">
                  <div className="bg-blue-600 text-white rounded-2xl rounded-br-md px-4 py-2">
                    <div className="text-sm">{message.content}</div>
                  </div>
                  <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white text-sm font-medium">
                    U
                  </div>
                </div>
              )}

              {/* AI助手消息 */}
              {message.role === 'assistant' && (
                <div className="flex items-start gap-2 max-w-[80%] group">
                  <div className="w-8 h-8 bg-gray-600 rounded-full flex items-center justify-center text-white text-sm">
                    AI
                  </div>
                  <div className="flex-1">
                  <div className="bg-gray-100 rounded-2xl rounded-bl-md px-4 py-2">
                    <div className="text-sm text-gray-800">
                      {message.status === 'sending' && !message.content ? (
                        // 等待AI回复状态
                        <div className="flex items-center gap-1">
                          <span>AI正在思考</span>
                          <div className="flex gap-1">
                            <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce"></div>
                            <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                            <div className="w-1 h-1 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                          </div>
                        </div>
                      ) : (
                        <div className="relative">
                          {renderMessageContent(message.content)}
                          {/* 流式回复时显示光标 */}
                          {message.status === 'sending' && message.content && (
                            <span className="inline-block w-0.5 h-4 bg-gray-600 ml-1 animate-pulse"></span>
                          )}
                        </div>
                      )}
                    </div>
                    {/* 显示消息状态 */}
                    {message.status && (
                      <div className="text-xs text-gray-500 mt-1">
                        {message.status === 'sending' ? '发送中...' : 
                         message.status === 'sent' ? '已发送' : 
                         message.status === 'error' ? '发送失败' : ''}
                        </div>
                      )}
                    </div>
                    
                    {/* AI消息操作按钮 */}
                    {message.status === 'sent' && message.content && onSaveToDraft && (
                      <div className="flex items-center gap-2 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => onSaveToDraft(message)}
                          className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-50 text-blue-700 rounded-md hover:bg-blue-100 transition-colors"
                          title="暂存这个回答"
                        >
                          <BookmarkIcon className="w-3 h-3" />
                          暂存
                        </button>
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(message.content);
                          }}
                          className="flex items-center gap-1 px-2 py-1 text-xs bg-gray-50 text-gray-700 rounded-md hover:bg-gray-100 transition-colors"
                          title="复制回答"
                        >
                          <ClipboardDocumentIcon className="w-3 h-3" />
                          复制
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 输入区域 */}
      <div className="border-t bg-white p-4">
        <div className="flex gap-2">
          <Input
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="输入您的问题..."
            disabled={isLoading}
            className="flex-1"
          />
          {isLoading ? (
            <Button
              onClick={onStopGeneration}
              variant="outline"
              className="px-4"
            >
              <StopIcon className="w-4 h-4 mr-2" />
              停止
            </Button>
          ) : (
            <Button
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || isLoading}
              className="px-4"
            >
              <PaperAirplaneIcon className="w-4 h-4" />
            </Button>
          )}
        </div>
        <div className="mt-2 text-xs text-gray-500">
          按 Enter 发送，Shift + Enter 换行
        </div>
      </div>
    </div>
  );
}; 