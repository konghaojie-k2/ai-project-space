'use client';

import React, { useState, useMemo, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { ClipboardDocumentIcon, CheckIcon } from '@heroicons/react/24/outline';
import { copyCodeBlock, copyMarkdown } from '@/lib/utils/copy';
import 'katex/dist/katex.min.css';

interface StreamingMarkdownProps {
  content: string;
  isStreaming?: boolean;
  className?: string;
}

/**
 * 流式Markdown渲染组件 - 参考DeerFlow优化实现
 * 特点：
 * 1. 智能处理不完整的Markdown语法
 * 2. 优化的代码块渲染和复制功能
 * 3. 流式显示时的稳定渲染
 * 4. 支持数学公式和表格
 */
export const StreamingMarkdown: React.FC<StreamingMarkdownProps> = ({
  content,
  isStreaming = false,
  className = ''
}) => {
  const [copiedBlocks, setCopiedBlocks] = useState<Set<string>>(new Set());

  // 智能处理流式Markdown内容
  const processedContent = useMemo(() => {
    if (!content) return '';
    
    let processedText = content;
    
    // 如果正在流式输出，需要处理不完整的语法
    if (isStreaming) {
      // 1. 处理不完整的代码块
      const codeBlockPattern = /```[\w]*\n?([^`]*)$/;
      const codeBlockMatch = processedText.match(codeBlockPattern);
      if (codeBlockMatch && !processedText.endsWith('```')) {
        // 临时闭合代码块以便正确渲染
        processedText = processedText + '\n```';
      }
      
      // 2. 处理不完整的行内代码
      const inlineCodePattern = /`[^`\n]*$/;
      const inlineCodeMatch = processedText.match(inlineCodePattern);
      if (inlineCodeMatch && !processedText.endsWith('`')) {
        processedText = processedText + '`';
      }
      
      // 3. 处理不完整的粗体/斜体
      const boldPattern = /\*\*[^*\n]*$/;
      const boldMatch = processedText.match(boldPattern);
      if (boldMatch) {
        processedText = processedText + '**';
      }
      
      const italicPattern = /(?<!\*)\*[^*\n]*$/;
      const italicMatch = processedText.match(italicPattern);
      if (italicMatch && !boldMatch) {
        processedText = processedText + '*';
      }
      
      // 4. 处理不完整的链接
      const linkPattern = /\[[^\]]*$/;
      const linkMatch = processedText.match(linkPattern);
      if (linkMatch) {
        processedText = processedText + ']';
      }
      
      // 5. 处理不完整的列表项
      const listPattern = /^\s*[-*+]\s*[^\n]*$/m;
      if (listPattern.test(processedText.split('\n').pop() || '')) {
        // 列表项在流式输出时可能会被截断，但这通常不需要特殊处理
      }
    }
    
    return processedText;
  }, [content, isStreaming]);

  // 复制到剪贴板的功能
  const copyToClipboard = useCallback(async (text: string, blockId: string, language?: string) => {
    const success = await copyCodeBlock(text, language, { showToast: true });
    
    if (success) {
      setCopiedBlocks(prev => new Set(prev).add(blockId));
      
      // 2秒后清除复制状态
      setTimeout(() => {
        setCopiedBlocks(prev => {
          const newSet = new Set(prev);
          newSet.delete(blockId);
          return newSet;
        });
      }, 2000);
    }
  }, []);

  // 生成代码块ID
  const generateBlockId = useCallback((content: string, language: string) => {
    return `${language}-${content.slice(0, 50).replace(/\s/g, '')}-${Date.now()}`;
  }, []);

  return (
    <div className={`prose prose-sm max-w-none text-gray-800 dark:text-gray-200 ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          // 自定义代码块组件 - 参考DeerFlow实现
          code({ node, inline, className, children, ...props }: any) {
            const match = /language-(\w+)/.exec(className || '');
            const language = match ? match[1] : 'text';
            const codeContent = String(children).replace(/\n$/, '');
            
            if (!inline) {
              const blockId = generateBlockId(codeContent, language);
              const isCopied = copiedBlocks.has(blockId);
              
              return (
                <div className="bg-gray-900 text-gray-100 rounded-lg overflow-hidden my-4 shadow-lg">
                  {/* 代码块头部 */}
                  <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-gray-300 font-medium">{language}</span>
                      {isStreaming && (
                        <div className="flex space-x-1">
                          <div className="w-1 h-1 bg-green-400 rounded-full animate-pulse"></div>
                          <div className="w-1 h-1 bg-green-400 rounded-full animate-pulse delay-75"></div>
                          <div className="w-1 h-1 bg-green-400 rounded-full animate-pulse delay-150"></div>
                        </div>
                      )}
                    </div>
                    <button
                      onClick={() => copyToClipboard(codeContent, blockId, language)}
                      className="flex items-center space-x-1 text-xs text-gray-400 hover:text-gray-200 transition-colors px-2 py-1 rounded hover:bg-gray-700"
                      title={isCopied ? '已复制' : '复制代码'}
                    >
                      {isCopied ? (
                        <>
                          <CheckIcon className="w-3 h-3" />
                          <span>已复制</span>
                        </>
                      ) : (
                        <>
                          <ClipboardDocumentIcon className="w-3 h-3" />
                          <span>复制</span>
                        </>
                      )}
                    </button>
                  </div>
                  
                  {/* 代码内容 */}
                  <SyntaxHighlighter
                    style={oneDark}
                    language={language}
                    PreTag="div"
                    className="!m-0 !bg-gray-900"
                    customStyle={{
                      margin: 0,
                      padding: '1rem',
                      background: 'rgb(31, 41, 55)',
                    }}
                    showLineNumbers={codeContent.split('\n').length > 5}
                    lineNumberStyle={{ color: 'rgb(107, 114, 126)', fontSize: '0.75rem' }}
                    {...props}
                  >
                    {codeContent}
                  </SyntaxHighlighter>
                </div>
              );
            }
            
            // 行内代码
            return (
              <code 
                className="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded text-sm font-mono text-gray-900 dark:text-gray-100 border border-gray-200 dark:border-gray-700"
                {...props}
              >
                {children}
              </code>
            );
          },
          
          // 自定义标题样式 - 更清晰的层级和锚点
          h1: ({ children, ...props }) => (
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4 mt-6 pb-2 border-b border-gray-200 dark:border-gray-700 scroll-mt-4" {...props}>
              {children}
            </h1>
          ),
          h2: ({ children, ...props }) => (
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-3 mt-5 scroll-mt-4" {...props}>
              {children}
            </h2>
          ),
          h3: ({ children, ...props }) => (
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2 mt-4 scroll-mt-4" {...props}>
              {children}
            </h3>
          ),
          h4: ({ children, ...props }) => (
            <h4 className="text-base font-medium text-gray-900 dark:text-white mb-2 mt-3 scroll-mt-4" {...props}>
              {children}
            </h4>
          ),
          h5: ({ children, ...props }) => (
            <h5 className="text-sm font-medium text-gray-900 dark:text-white mb-1 mt-2 scroll-mt-4" {...props}>
              {children}
            </h5>
          ),
          h6: ({ children, ...props }) => (
            <h6 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 mt-2 scroll-mt-4" {...props}>
              {children}
            </h6>
          ),
          
          // 自定义列表样式 - 更好的间距和缩进
          ul: ({ children, ...props }) => (
            <ul className="list-disc list-outside ml-6 space-y-1 my-3 text-gray-800 dark:text-gray-200" {...props}>
              {children}
            </ul>
          ),
          ol: ({ children, ...props }) => (
            <ol className="list-decimal list-outside ml-6 space-y-1 my-3 text-gray-800 dark:text-gray-200" {...props}>
              {children}
            </ol>
          ),
          li: ({ children, ...props }) => (
            <li className="leading-relaxed" {...props}>
              {children}
            </li>
          ),
          
          // 自定义段落样式 - 更好的行距和间距
          p: ({ children, ...props }) => (
            <p className="text-gray-800 dark:text-gray-200 leading-7 my-3" {...props}>
              {children}
            </p>
          ),
          
          // 自定义引用块样式 - 现代化设计
          blockquote: ({ children, ...props }) => (
            <blockquote className="border-l-4 border-blue-500 bg-blue-50 dark:bg-blue-900/20 pl-4 py-2 my-4 italic text-gray-700 dark:text-gray-300" {...props}>
              {children}
            </blockquote>
          ),
          
          // 自定义表格样式 - 响应式设计
          table: ({ children, ...props }) => (
            <div className="overflow-x-auto my-4">
              <table className="min-w-full divide-y divide-gray-300 dark:divide-gray-600 border border-gray-300 dark:border-gray-600 rounded-lg" {...props}>
                {children}
              </table>
            </div>
          ),
          thead: ({ children, ...props }) => (
            <thead className="bg-gray-50 dark:bg-gray-800" {...props}>
              {children}
            </thead>
          ),
          tbody: ({ children, ...props }) => (
            <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700" {...props}>
              {children}
            </tbody>
          ),
          th: ({ children, ...props }) => (
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider" {...props}>
              {children}
            </th>
          ),
          td: ({ children, ...props }) => (
            <td className="px-3 py-2 text-sm text-gray-900 dark:text-gray-100" {...props}>
              {children}
            </td>
          ),
          
          // 自定义链接样式 - 更好的可访问性
          a: ({ children, href, ...props }) => (
            <a 
              href={href}
              className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 underline decoration-blue-600/30 hover:decoration-blue-600 transition-colors"
              target={href?.startsWith('http') ? '_blank' : undefined}
              rel={href?.startsWith('http') ? 'noopener noreferrer' : undefined}
              {...props}
            >
              {children}
            </a>
          ),
          
          // 自定义分割线
          hr: ({ ...props }) => (
            <hr className="my-6 border-gray-300 dark:border-gray-600" {...props} />
          ),
          
          // 自定义图片 - 响应式和懒加载
          img: ({ src, alt, ...props }) => (
            <img 
              src={src}
              alt={alt}
              className="max-w-full h-auto rounded-lg shadow-lg my-4"
              loading="lazy"
              {...props}
            />
          ),
        }}
      >
        {processedContent}
      </ReactMarkdown>
      
      {/* 流式输出指示器 */}
      {isStreaming && (
        <div className="flex items-center space-x-2 mt-2 text-sm text-gray-500 dark:text-gray-400">
          <div className="flex space-x-1">
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce delay-75"></div>
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce delay-150"></div>
          </div>
          <span>正在生成中...</span>
        </div>
      )}
    </div>
  );
};

export default StreamingMarkdown;
