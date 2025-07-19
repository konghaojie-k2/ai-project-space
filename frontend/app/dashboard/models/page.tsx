'use client';

import React, { useState, useEffect } from 'react';
import Button from '@/components/ui/Button';
import { Loader2, Play, Square, Settings, Download, Trash2 } from 'lucide-react';

interface ModelInfo {
  name: string;
  model_id: string;
  provider: string;
  device: string;
  enabled: boolean;
  dimension?: number;
  context_length?: number;
}

interface ModelStatus {
  loaded_models: Record<string, any>;
  total_models: number;
  memory_usage: string;
  gpu_usage: string;
}

export default function ModelsPage() {
  const [embeddingModels, setEmbeddingModels] = useState<ModelInfo[]>([]);
  const [llmModels, setLlmModels] = useState<ModelInfo[]>([]);
  const [multimodalModels, setMultimodalModels] = useState<ModelInfo[]>([]);
  const [modelStatus, setModelStatus] = useState<ModelStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingModels, setLoadingModels] = useState<Set<string>>(new Set());
  const [activeTab, setActiveTab] = useState('embedding');

  useEffect(() => {
    loadModels();
    loadModelStatus();
  }, []);

  const loadModels = async () => {
    try {
      setLoading(true);
      
      // 加载嵌入模型
      const embeddingResponse = await fetch('/api/models/embedding');
      if (embeddingResponse.ok) {
        const embeddingData = await embeddingResponse.json();
        setEmbeddingModels(embeddingData);
      }
      
      // 加载LLM模型
      const llmResponse = await fetch('/api/models/llm');
      if (llmResponse.ok) {
        const llmData = await llmResponse.json();
        setLlmModels(llmData);
      }
      
      // 加载多模态模型
      const multimodalResponse = await fetch('/api/models/multimodal');
      if (multimodalResponse.ok) {
        const multimodalData = await multimodalResponse.json();
        setMultimodalModels(multimodalData);
      }
    } catch (error) {
      console.error('加载模型失败:', error);
      alert('加载模型失败');
    } finally {
      setLoading(false);
    }
  };

  const loadModelStatus = async () => {
    try {
      const response = await fetch('/api/models/status');
      if (response.ok) {
        const status = await response.json();
        setModelStatus(status);
      }
    } catch (error) {
      console.error('加载模型状态失败:', error);
    }
  };

  const loadModel = async (modelType: string, modelName: string) => {
    try {
      setLoadingModels(prev => new Set(prev).add(`${modelType}_${modelName}`));
      
      const response = await fetch('/api/models/load', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model_type: modelType,
          model_name: modelName,
          force_reload: false,
        }),
      });

      const result = await response.json();
      
      if (response.ok) {
        alert(result.message);
        loadModelStatus(); // 重新加载状态
      } else {
        alert(result.detail || '加载模型失败');
      }
    } catch (error) {
      console.error('加载模型失败:', error);
      alert('加载模型失败');
    } finally {
      setLoadingModels(prev => {
        const newSet = new Set(prev);
        newSet.delete(`${modelType}_${modelName}`);
        return newSet;
      });
    }
  };

  const unloadModel = async (modelKey: string) => {
    try {
      const response = await fetch(`/api/models/unload/${modelKey}`, {
        method: 'POST',
      });

      const result = await response.json();
      
      if (response.ok) {
        alert(result.message);
        loadModelStatus(); // 重新加载状态
      } else {
        alert(result.detail || '卸载模型失败');
      }
    } catch (error) {
      console.error('卸载模型失败:', error);
      alert('卸载模型失败');
    }
  };

  const testModel = async (modelType: string, modelName?: string) => {
    try {
      const url = modelName 
        ? `/api/models/test/${modelType}?model_name=${modelName}`
        : `/api/models/test/${modelType}`;
        
      const response = await fetch(url, {
        method: 'POST',
      });

      const result = await response.json();
      
      if (response.ok) {
        alert(result.message);
        console.log('测试结果:', result);
      } else {
        alert(result.detail || '测试模型失败');
      }
    } catch (error) {
      console.error('测试模型失败:', error);
      alert('测试模型失败');
    }
  };

  const clearAllModels = async () => {
    if (!confirm('确定要清除所有模型吗？这将卸载所有已加载的模型。')) {
      return;
    }

    try {
      const response = await fetch('/api/models/clear', {
        method: 'DELETE',
      });

      const result = await response.json();
      
      if (response.ok) {
        alert(result.message);
        loadModelStatus(); // 重新加载状态
      } else {
        alert(result.detail || '清除模型失败');
      }
    } catch (error) {
      console.error('清除模型失败:', error);
      alert('清除模型失败');
    }
  };

  const isModelLoaded = (modelType: string, modelName: string) => {
    if (!modelStatus?.loaded_models) return false;
    return `${modelType}_${modelName}` in modelStatus.loaded_models;
  };

  const renderModelCard = (model: ModelInfo, modelType: string) => {
    const isLoaded = isModelLoaded(modelType, model.name);
    const isLoading = loadingModels.has(`${modelType}_${model.name}`);

    return (
      <div key={model.name} className="border rounded-lg p-4 bg-white shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold">{model.name}</h3>
          <div className="flex items-center gap-2">
            <span className={`px-2 py-1 rounded text-xs ${
              model.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
            }`}>
              {model.enabled ? "启用" : "禁用"}
            </span>
            <span className={`px-2 py-1 rounded text-xs ${
              isLoaded ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'
            }`}>
              {isLoaded ? "已加载" : "未加载"}
            </span>
          </div>
        </div>
        <p className="text-sm text-gray-600 mb-3">{model.model_id}</p>
        
        <div className="space-y-2 mb-4">
          <div className="flex justify-between text-sm">
            <span>提供商:</span>
            <span className="font-medium">{model.provider}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span>设备:</span>
            <span className="font-medium">{model.device}</span>
          </div>
          {model.dimension && (
            <div className="flex justify-between text-sm">
              <span>维度:</span>
              <span className="font-medium">{model.dimension}</span>
            </div>
          )}
          {model.context_length && (
            <div className="flex justify-between text-sm">
              <span>上下文长度:</span>
              <span className="font-medium">{model.context_length.toLocaleString()}</span>
            </div>
          )}
        </div>
        
        <div className="flex gap-2">
          {!isLoaded ? (
            <Button
              size="sm"
              onClick={() => loadModel(modelType, model.name)}
              disabled={isLoading || !model.enabled}
              className="flex items-center gap-1"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
              加载
            </Button>
          ) : (
            <Button
              size="sm"
              variant="outline"
              onClick={() => unloadModel(`${modelType}_${model.name}`)}
              className="flex items-center gap-1"
            >
              <Square className="h-4 w-4" />
              卸载
            </Button>
          )}
          
          <Button
            size="sm"
            variant="outline"
            onClick={() => testModel(modelType, model.name)}
            disabled={!isLoaded}
            className="flex items-center gap-1"
          >
            <Play className="h-4 w-4" />
            测试
          </Button>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2">加载模型中...</span>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">模型管理</h1>
          <p className="text-gray-600">
            管理AI模型，包括嵌入模型、大语言模型和多模态模型
          </p>
        </div>
        <Button variant="outline" onClick={clearAllModels} className="flex items-center gap-2">
          <Trash2 className="h-4 w-4" />
          清除所有模型
        </Button>
      </div>

      {/* 模型状态 */}
      {modelStatus && (
        <div className="border rounded-lg p-6 bg-white shadow-sm">
          <h2 className="text-xl font-semibold mb-4">模型状态</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold">{modelStatus.total_models}</div>
              <div className="text-sm text-gray-600">已加载模型</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">{modelStatus.memory_usage}</div>
              <div className="text-sm text-gray-600">内存使用</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">{modelStatus.gpu_usage}</div>
              <div className="text-sm text-gray-600">GPU使用</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">
                {Object.keys(modelStatus.loaded_models).length}
              </div>
              <div className="text-sm text-gray-600">活跃模型</div>
            </div>
          </div>
        </div>
      )}

      {/* 模型标签页 */}
      <div className="border rounded-lg bg-white shadow-sm">
        <div className="border-b">
          <div className="flex">
            <button
              className={`px-4 py-2 font-medium ${
                activeTab === 'embedding' 
                  ? 'border-b-2 border-blue-500 text-blue-600' 
                  : 'text-gray-600 hover:text-gray-800'
              }`}
              onClick={() => setActiveTab('embedding')}
            >
              嵌入模型
            </button>
            <button
              className={`px-4 py-2 font-medium ${
                activeTab === 'llm' 
                  ? 'border-b-2 border-blue-500 text-blue-600' 
                  : 'text-gray-600 hover:text-gray-800'
              }`}
              onClick={() => setActiveTab('llm')}
            >
              大语言模型
            </button>
            <button
              className={`px-4 py-2 font-medium ${
                activeTab === 'multimodal' 
                  ? 'border-b-2 border-blue-500 text-blue-600' 
                  : 'text-gray-600 hover:text-gray-800'
              }`}
              onClick={() => setActiveTab('multimodal')}
            >
              多模态模型
            </button>
          </div>
        </div>
        
        <div className="p-6">
          {activeTab === 'embedding' && (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {embeddingModels.map(model => renderModelCard(model, 'embedding'))}
            </div>
          )}
          
          {activeTab === 'llm' && (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {llmModels.map(model => renderModelCard(model, 'llm'))}
            </div>
          )}
          
          {activeTab === 'multimodal' && (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {multimodalModels.map(model => renderModelCard(model, 'multimodal'))}
            </div>
          )}
        </div>
      </div>

      {/* 使用说明 */}
      <div className="border rounded-lg p-6 bg-blue-50">
        <div className="flex items-start gap-3">
          <Settings className="h-5 w-5 text-blue-600 mt-0.5" />
          <div>
            <h3 className="font-semibold text-blue-900 mb-2">使用说明</h3>
            <ul className="space-y-1 text-sm text-blue-800">
              <li>• 点击"加载"按钮下载并加载模型到内存</li>
              <li>• 点击"测试"按钮验证模型是否正常工作</li>
              <li>• 点击"卸载"按钮释放模型占用的内存</li>
              <li>• 禁用状态的模型无法加载，需要先在配置中启用</li>
              <li>• 首次加载模型可能需要较长时间，请耐心等待</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
} 