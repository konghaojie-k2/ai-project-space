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
  const [newTag, setNewTag] = useState({
    name: '',
    color: TAG_COLORS[0],
    category: 'other' as FileTag['category']
  });

  // 获取所有标签（预定义 + 自定义）
  const allTags = [...PREDEFINED_TAGS, ...customTags];

  // 筛选标签
  const filteredTags = allTags.filter(tag => {
    const matchesSearch = tag.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         tag.description?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || tag.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  // 处理标签选择
  const handleTagToggle = (tagId: string) => {
    if (selectedTags.includes(tagId)) {
      onTagsChange(selectedTags.filter(id => id !== tagId));
    } else {
      onTagsChange([...selectedTags, tagId]);
    }
  };

  // 创建自定义标签
  const handleCreateTag = () => {
    if (newTag.name.trim()) {
      const customTag = createCustomTag(newTag.name, newTag.color, newTag.category);
      setCustomTags([...customTags, customTag]);
      setNewTag({ name: '', color: TAG_COLORS[0], category: 'other' });
      setShowCreateForm(false);
      
      // 自动选择新创建的标签
      onTagsChange([...selectedTags, customTag.id]);
    }
  };

  // 删除自定义标签
  const handleDeleteTag = (tagId: string) => {
    setCustomTags(customTags.filter(tag => tag.id !== tagId));
    onTagsChange(selectedTags.filter(id => id !== tagId));
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* 头部 */}
        <div className="flex items-center justify-between p-6 border-b">
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

        {/* 搜索和筛选 */}
        <div className="p-6 border-b space-y-4">
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

        {/* 标签列表 */}
        <div className="p-6 max-h-96 overflow-y-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {filteredTags.map(tag => (
              <div
                key={tag.id}
                className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${
                  selectedTags.includes(tag.id)
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                onClick={() => handleTagToggle(tag.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${tag.color}`}>
                      {tag.name}
                    </span>
                    {selectedTags.includes(tag.id) && (
                      <div className="w-4 h-4 bg-blue-500 rounded-full flex items-center justify-center">
                        <div className="w-2 h-2 bg-white rounded-full"></div>
                      </div>
                    )}
                  </div>
                  {customTags.some(ct => ct.id === tag.id) && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteTag(tag.id);
                      }}
                      className="p-1 hover:bg-red-100 rounded text-red-600 transition-colors"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  )}
                </div>
                {tag.description && (
                  <p className="text-xs text-gray-500 mt-1">{tag.description}</p>
                )}
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

        {/* 底部操作 */}
        <div className="p-6 border-t flex items-center justify-between">
          <button
            onClick={() => setShowCreateForm(true)}
            className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
          >
            <PlusIcon className="h-4 w-4" />
            <span>创建标签</span>
          </button>

          <div className="flex items-center space-x-3">
            <span className="text-sm text-gray-500">
              已选择 {selectedTags.length} 个标签
            </span>
            <button
              onClick={onClose}
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