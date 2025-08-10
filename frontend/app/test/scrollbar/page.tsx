'use client';

import React from 'react';

export default function ScrollbarTestPage() {
  return (
    <div className="h-screen flex bg-gray-50 overflow-hidden">
      {/* 左侧栏 */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col min-h-0">
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">左侧边栏</h2>
        </div>
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          {Array.from({ length: 50 }, (_, i) => (
            <div key={i} className="p-3 border-b border-gray-100">
              <p className="text-sm text-gray-700">项目 {i + 1}</p>
              <p className="text-xs text-gray-500">这是一个测试项目的描述内容</p>
            </div>
          ))}
        </div>
      </div>

      {/* 中间内容区 */}
      <div className="flex-1 flex flex-col min-h-0 min-w-0">
        <div className="p-4 bg-white border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">中间聊天区</h2>
        </div>
        <div className="flex-1 overflow-y-auto custom-scrollbar bg-white">
          {Array.from({ length: 30 }, (_, i) => (
            <div key={i} className="p-4 border-b border-gray-100">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 bg-blue-500 rounded-full flex-shrink-0"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">用户 {i + 1}</p>
                  <p className="text-sm text-gray-700 mt-1">
                    这是一条测试消息，用来测试聊天区域的滚动条是否正常工作。
                    消息内容可能会很长，需要确保滚动条能够正确显示。
                  </p>
                  <p className="text-xs text-gray-500 mt-2">2分钟前</p>
                </div>
              </div>
            </div>
          ))}
        </div>
        <div className="flex-shrink-0 p-4 bg-white border-t border-gray-200">
          <input 
            type="text" 
            placeholder="输入消息..." 
            className="w-full px-3 py-2 border border-gray-300 rounded-lg"
          />
        </div>
      </div>

      {/* 右侧栏 */}
      <div className="w-80 bg-white border-l border-gray-200 flex flex-col min-h-0">
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">右侧工作区</h2>
        </div>
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          {Array.from({ length: 40 }, (_, i) => (
            <div key={i} className="p-3 border-b border-gray-100">
              <p className="text-sm font-medium text-gray-900">文件 {i + 1}.pdf</p>
              <p className="text-xs text-gray-500">大小: 2.5MB</p>
              <p className="text-xs text-gray-400 mt-1">上传于 1小时前</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
