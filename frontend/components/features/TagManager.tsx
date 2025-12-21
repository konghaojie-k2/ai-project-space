'use client';

import { useState, useEffect } from 'react';
import { 
  XMarkIcon, 
  PlusIcon, 
  PencilIcon, 
  TrashIcon,
  TagIcon,
  MagnifyingGlassIcon
} from '@heroicons/react/24/outline';
import { 
  PREDEFINED_TAGS, 
  TAG_CATEGORIES, 
  TAG_COLORS, 
  FileTag, 
  createCustomTag,
  getTagsByCategory
} from '@/lib/constants/file-tags';

interface TagManagerProps {
  selectedTags: string[];
  onTagsChange: (tags: string[]) => void;
  onClose: () => void;
}

export default function TagManager({ selectedTags, onTagsChange, onClose }: TagManagerProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [customTags, setCustomTags] = useState<FileTag[]>([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  // 使用内部状态管理选中的标签，只在点击确定时才调用onTagsChange
  const [internalSelectedTags, setInternalSelectedTags] = useState<string[]>(selectedTags);
  const [newTag, setNewTag] = useState({
    name: '',
    color: TAG_COLORS[0],
    category: 'other' as FileTag['category']
  });

  // 从localStorage加载自定义标签
  useEffect(() => {
    if (typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem('custom-tags');
        if (stored) {
          const parsedTags = JSON.parse(stored);
          setCustomTags(parsedTags);
        }
      } catch (error) {
        console.error('加载自定义标签失败:', error);
      }
    }
  }, []);

  // 保存自定义标签到localStorage
  const saveCustomTags = (tags: FileTag[]) => {
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem('custom-tags', JSON.stringify(tags));
      } catch (error) {
        console.error('保存自定义标签失败:', error);
      }
    }
  };

  // 当外部selectedTags变化时，同步内部状态
  useEffect(() => {
    setInternalSelectedTags(selectedTags);
  }, [selectedTags]);

  // 获取所有标签（预定义 + 自定义）
  const allTags = [...PREDEFINED_TAGS, ...customTags];

  // 筛选标签
  const filteredTags = allTags.filter(tag => {
    const matchesSearch = tag.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         tag.description?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || tag.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  // 处理标签选择（只更新内部状态，不立即调用onTagsChange）
  const handleTagToggle = (tagId: string) => {
    if (internalSelectedTags.includes(tagId)) {
      setInternalSelectedTags(internalSelectedTags.filter(id => id !== tagId));
    } else {
      setInternalSelectedTags([...internalSelectedTags, tagId]);
    }
  };

  // 处理确定按钮点击
  const handleConfirm = () => {
    // 过滤掉不存在的tag（已删除的自定义tag或无效tag）
    const validTags = internalSelectedTags.filter(tagId => {
      return allTags.some(tag => tag.id === tagId);
    });
    onTagsChange(validTags);
    onClose();
  };

  // 创建自定义标签
  const handleCreateTag = () => {
    if (newTag.name.trim()) {
      const customTag = createCustomTag(newTag.name, newTag.color, newTag.category);
      const updatedCustomTags = [...customTags, customTag];
      setCustomTags(updatedCustomTags);
      saveCustomTags(updatedCustomTags); // 保存到localStorage
      setNewTag({ name: '', color: TAG_COLORS[0], category: 'other' });
      setShowCreateForm(false);
      
      // 自动选择新创建的标签（只更新内部状态）
      setInternalSelectedTags([...internalSelectedTags, customTag.id]);
    }
  };

  // 删除自定义标签（只更新内部状态）
  const handleDeleteTag = (tagId: string) => {
    // 检查是否有文件使用了这个tag（通过检查当前选中的标签）
    const isTagInUse = internalSelectedTags.includes(tagId);
    
    if (isTagInUse) {
      const tag = customTags.find(t => t.id === tagId);
      const tagName = tag?.name || tagId;
      const confirmMessage = `标签"${tagName}"正在被使用。删除后，已标记的文件将不再显示此标签，但文件中的标签数据不会被自动清理。\n\n是否继续删除？`;
      
      if (!window.confirm(confirmMessage)) {
        return; // 用户取消删除
      }
    }
    
    const updatedCustomTags = customTags.filter(tag => tag.id !== tagId);
    setCustomTags(updatedCustomTags);
    saveCustomTags(updatedCustomTags); // 保存到localStorage
    setInternalSelectedTags(internalSelectedTags.filter(id => id !== tagId));
  };

  // 处理背景点击（点击背景时不关闭，避免误操作丢失更改）
  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    // 如果点击的是背景本身（不是子元素），不执行任何操作
    // 用户必须点击"确定"或"取消"按钮来关闭
    if (e.target === e.currentTarget) {
      // 点击背景本身，不关闭
      e.stopPropagation();
    }
  };

  // 阻止内容区域的点击事件冒泡到背景
  const handleContentClick = (e: React.MouseEvent<HTMLDivElement>) => {
    e.stopPropagation();
  };

  // 处理标签点击（添加调试日志）
  const handleTagClick = (tagId: string, e: React.MouseEvent) => {
    e.stopPropagation(); // 阻止事件冒泡
    handleTagToggle(tagId);
  };

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
      onClick={handleBackdropClick}
    >
      <div 
        className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col overflow-hidden"
        onClick={handleContentClick}
      >
        {/* 头部 - 固定 */}
        <div className="flex items-center justify-between p-6 border-b flex-shrink-0">
          <div className="flex items-center space-x-2">
            <TagIcon className="h-6 w-6 text-blue-600" />
            <h2 className="text-xl font-semibold">标签管理</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        </div>

        {/* 搜索和筛选 - 固定 */}
        <div className="p-6 border-b space-y-4 flex-shrink-0">
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              placeholder="搜索标签..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setSelectedCategory('all')}
              className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                selectedCategory === 'all'
                  ? 'bg-blue-100 text-blue-800'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              全部
            </button>
            {TAG_CATEGORIES.map(category => (
              <button
                key={category.id}
                onClick={() => setSelectedCategory(category.id)}
                className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                  selectedCategory === category.id
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {category.icon} {category.name}
              </button>
            ))}
          </div>
        </div>

        {/* 可滚动内容区域 */}
        <div className="flex-1 overflow-y-auto min-h-0">
          {/* 标签列表 */}
          <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {filteredTags.map(tag => (
              <div
                key={tag.id}
                className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
                  internalSelectedTags.includes(tag.id)
                    ? 'border-blue-500 bg-blue-50 shadow-md ring-2 ring-blue-200'
                    : 'border-gray-200 hover:border-blue-300 hover:shadow-sm bg-white'
                }`}
                onClick={(e) => handleTagClick(tag.id, e)}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2 flex-1 min-w-0">
                    <span className={`px-2.5 py-1 rounded-md text-xs font-semibold ${tag.color} border border-opacity-20 shadow-sm`}>
                      {tag.name}
                    </span>
                    {internalSelectedTags.includes(tag.id) && (
                      <div className="flex-shrink-0 w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center ring-2 ring-blue-200">
                        <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                    )}
                  </div>
                  {customTags.some(ct => ct.id === tag.id) && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteTag(tag.id);
                      }}
                      className="flex-shrink-0 p-1.5 hover:bg-red-50 rounded-md text-red-600 transition-colors ml-2"
                      title="删除自定义标签"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  )}
                </div>
                {tag.description && (
                  <p className="text-xs text-gray-500 mt-1.5 line-clamp-2">{tag.description}</p>
                )}
                <div className="mt-2 flex items-center space-x-1">
                  <span className="text-xs text-gray-400">
                    {TAG_CATEGORIES.find(cat => cat.id === tag.category)?.icon || '📁'}
                  </span>
                  <span className="text-xs text-gray-400">
                    {TAG_CATEGORIES.find(cat => cat.id === tag.category)?.name || '其他'}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {filteredTags.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              <TagIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>没有找到匹配的标签</p>
            </div>
          )}
          </div>

          {/* 创建标签表单 */}
          {showCreateForm && (
            <div className="p-6 border-t bg-gray-50">
            <h3 className="text-lg font-medium mb-4">创建自定义标签</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  标签名称
                </label>
                <input
                  type="text"
                  value={newTag.name}
                  onChange={(e) => setNewTag({ ...newTag, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="输入标签名称"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  标签颜色
                </label>
                <div className="flex flex-wrap gap-2">
                  {TAG_COLORS.map(color => (
                    <button
                      key={color}
                      onClick={() => setNewTag({ ...newTag, color })}
                      className={`px-3 py-1 rounded-full text-xs font-medium ${color} ${
                        newTag.color === color ? 'ring-2 ring-blue-500' : ''
                      }`}
                    >
                      示例
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  标签分类
                </label>
                <select
                  value={newTag.category}
                  onChange={(e) => setNewTag({ ...newTag, category: e.target.value as FileTag['category'] })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {TAG_CATEGORIES.map(category => (
                    <option key={category.id} value={category.id}>
                      {category.icon} {category.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex space-x-3">
                <button
                  onClick={handleCreateTag}
                  className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors"
                >
                  创建标签
                </button>
                <button
                  onClick={() => setShowCreateForm(false)}
                  className="flex-1 bg-gray-300 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-400 transition-colors"
                >
                  取消
                </button>
              </div>
            </div>
          </div>
          )}
        </div>

        {/* 底部操作 - 固定 */}
        <div className="p-6 border-t flex items-center justify-between flex-shrink-0 bg-white">
          <button
            onClick={() => setShowCreateForm(true)}
            className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            <PlusIcon className="h-4 w-4" />
            <span>创建标签</span>
          </button>

          <div className="flex items-center space-x-3">
            <span className="text-sm text-gray-500">
              已选择 {internalSelectedTags.length} 个标签
            </span>
            <button
              onClick={() => {
                // 取消时恢复原始状态，不保存更改
                setInternalSelectedTags(selectedTags);
                onClose();
              }}
              className="px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400 transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleConfirm}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              确定
            </button>
          </div>
        </div>
      </div>
    </div>
  );
} 