'use client';

import React, { useState, useRef, useEffect, useMemo } from 'react';
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

  // 复制整个消息内容的功能
  const copyMessageContent = useCallback(async (content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      // 可以添加复制成功的提示
    } catch (err) {
      console.error('复制失败:', err);
    }
  }, []);

  // 使用新的StreamingMarkdown组件渲染消息内容
  const renderMessageContent = useMemo(() => (content: string, isStreaming: boolean = false) => {
    // 处理流式回复中的不完整Markdown语法
    const processStreamingMarkdown = (text: string) => {
      if (!text) return text;
      
      let processedText = text;
      
      // 1. 处理不完整的代码块
      const codeBlockMatches = processedText.match(/```[\w]*\n?[^`]*$/);
      if (codeBlockMatches && !processedText.endsWith('```')) {
        // 如果有未闭合的代码块，临时闭合它以便正确渲染
        processedText = processedText + '\n```';
      }
      
      // 2. 处理不完整的行内代码
      const inlineCodeMatches = processedText.match(/`[^`]*$/);
      if (inlineCodeMatches && !processedText.endsWith('`')) {
        processedText = processedText + '`';
      }
      
      // 3. 处理不完整的粗体/斜体
      const boldMatches = processedText.match(/\*\*[^*]*$/);
      if (boldMatches) {
        processedText = processedText + '**';
      }
      
      const italicMatches = processedText.match(/\*[^*]*$/);
      if (italicMatches && !boldMatches) {
        processedText = processedText + '*';
      }
      
      // 4. 处理不完整的链接
      const linkMatches = processedText.match(/\[[^\]]*$/);
      if (linkMatches) {
        processedText = processedText + ']';
      }
      
      return processedText;
    };

    const processedContent = processStreamingMarkdown(content);

    return (
      <div className="prose prose-sm max-w-none text-gray-800 dark:text-gray-200">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            // 自定义代码块组件
            code({ node, inline, className, children, ...props }: any) {
              const match = /language-(\w+)/.exec(className || '');
              const language = match ? match[1] : 'text';
              
              if (!inline) {
                return (
                  <div className="bg-gray-900 text-gray-100 rounded-lg overflow-hidden my-4">
                    <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
                      <span className="text-sm text-gray-300">{language}</span>
                      <button
                        onClick={() => navigator.clipboard.writeText(String(children))}
                        className="text-xs text-gray-400 hover:text-gray-200 transition-colors"
                      >
                        复制代码
                      </button>
                    </div>
                    <SyntaxHighlighter
                      style={oneDark}
                      language={language}
                      PreTag="div"
                      className="!m-0 !bg-gray-900"
                      {...props}
                    >
                      {String(children).replace(/\n$/, '')}
                    </SyntaxHighlighter>
                  </div>
                );
              }
              
              // 行内代码
              return (
                <code 
                  className="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded text-sm font-mono text-gray-900 dark:text-gray-100"
                  {...props}
                >
                  {children}
                </code>
              );
            },
            
            // 自定义标题样式 - 更清晰的层级
            h1: ({ children }) => (
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4 mt-6 pb-2 border-b border-gray-200 dark:border-gray-700">
                {children}
              </h1>
            ),
            h2: ({ children }) => (
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-3 mt-5">
                {children}
              </h2>
            ),
            h3: ({ children }) => (
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2 mt-4">
                {children}
              </h3>
            ),
            h4: ({ children }) => (
              <h4 className="text-base font-medium text-gray-900 dark:text-white mb-2 mt-3">
                {children}
              </h4>
            ),
            h5: ({ children }) => (
              <h5 className="text-sm font-medium text-gray-900 dark:text-white mb-1 mt-2">
                {children}
              </h5>
            ),
            h6: ({ children }) => (
              <h6 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 mt-2">
                {children}
              </h6>
            ),
            
            // 自定义列表样式 - 更好的间距
            ul: ({ children }) => (
              <ul className="list-disc list-outside ml-6 space-y-1 my-3 text-gray-800 dark:text-gray-200">
                {children}
              </ul>
            ),
            ol: ({ children }) => (
              <ol className="list-decimal list-outside ml-6 space-y-1 my-3 text-gray-800 dark:text-gray-200">
                {children}
              </ol>
            ),
            li: ({ children }) => (
              <li className="leading-relaxed">
                {children}
              </li>
            ),
            
            // 自定义段落样式 - 更好的行距和间距
            p: ({ children }) => (
              <p className="text-gray-800 dark:text-gray-200 leading-7 my-3">
                {children}
              </p>
            ),
            
            // 自定义强调样式
            strong: ({ children }) => (
              <strong className="font-semibold text-gray-900 dark:text-white">
                {children}
              </strong>
            ),
            em: ({ children }) => (
              <em className="italic text-gray-700 dark:text-gray-300">
                {children}
              </em>
            ),
            
            // 分隔线
            hr: () => (
              <hr className="my-6 border-t border-gray-300 dark:border-gray-600" />
            ),
            
            // 自定义表格样式
            table: ({ children }) => (
              <div className="overflow-x-auto my-4">
                <table className="min-w-full border-collapse border border-gray-300 dark:border-gray-600 rounded-lg">
                  {children}
                </table>
              </div>
            ),
            thead: ({ children }) => (
              <thead className="bg-gray-50 dark:bg-gray-700">
                {children}
              </thead>
            ),
            th: ({ children }) => (
              <th className="border border-gray-300 dark:border-gray-600 px-4 py-2 text-left font-medium text-gray-900 dark:text-white">
                {children}
              </th>
            ),
            td: ({ children }) => (
              <td className="border border-gray-300 dark:border-gray-600 px-4 py-2 text-gray-800 dark:text-gray-200">
                {children}
              </td>
            ),
            
            // 自定义引用样式
            blockquote: ({ children }) => (
              <blockquote className="border-l-4 border-blue-500 pl-4 my-4 italic text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 py-2 rounded-r">
                {children}
              </blockquote>
            ),
            
            // 自定义链接样式
            a: ({ children, href }) => (
              <a 
                href={href} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 underline decoration-blue-500 underline-offset-2"
              >
                {children}
              </a>
            ),
            
            // 换行处理
            br: () => <br className="my-1" />,
            
            // 删除线
            del: ({ children }) => (
              <del className="line-through text-gray-500 dark:text-gray-400">
                {children}
              </del>
            )
          }}
        >
          {processedContent}
        </ReactMarkdown>
      </div>
    );
  }, []); // 空依赖数组，因为我们希望这个函数是稳定的

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
                          {/* 流式渲染：每次内容更新都重新渲染Markdown */}
                          <div className="markdown-content">
                            {renderMessageContent(message.content)}
                          </div>
                          {/* 流式回复时显示光标 */}
                          {message.status === 'sending' && message.content && (
                            <span className="inline-block w-0.5 h-4 bg-blue-500 ml-1 animate-pulse"></span>
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