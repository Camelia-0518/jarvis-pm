/**
 * 原型预览组件
 * 集成到PRD编辑器的原型预览窗口
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Monitor,
  Smartphone,
  Tablet,
  Download,
  Code,
  Eye,
  RefreshCw,
  Check,
  X,
  ExternalLink,
  FileCode,
  FileJson,
  Zap
} from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

// Utility for tailwind class merging
function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Types
export interface PrototypeFile {
  name: string;
  content: string;
  type: 'html' | 'css' | 'js' | 'json';
}

export interface PrototypeData {
  files: Record<string, string>;
  metadata: {
    name: string;
    description: string;
    page_count: number;
    pages: Array<{
      name: string;
      route: string;
      title: string;
    }>;
  };
}

export interface PrototypePreviewProps {
  prdContent: string;
  onGenerate?: (data: PrototypeData) => void;
  onExport?: (format: 'html' | 'zip' | 'json') => void;
  onDeploy?: () => void;
  className?: string;
}

type DeviceType = 'desktop' | 'tablet' | 'mobile';
type ViewMode = 'preview' | 'code' | 'split';

// Device dimensions
const DEVICE_DIMENSIONS: Record<DeviceType, { width: number; height: number; label: string }> = {
  desktop: { width: 1280, height: 800, label: '桌面端' },
  tablet: { width: 768, height: 1024, label: '平板' },
  mobile: { width: 375, height: 812, label: '手机' },
};

// API client
const generatePrototype = async (prdContent: string): Promise<PrototypeData> => {
  const response = await fetch('/api/v1/code/prototype', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prd_content: prdContent }),
  });

  if (!response.ok) {
    throw new Error('Failed to generate prototype');
  }

  return response.json();
};

// Components
const DeviceSelector: React.FC<{
  current: DeviceType;
  onChange: (device: DeviceType) => void;
}> = ({ current, onChange }) => {
  const devices: { type: DeviceType; icon: React.ReactNode; label: string }[] = [
    { type: 'desktop', icon: <Monitor className="w-4 h-4" />, label: '桌面' },
    { type: 'tablet', icon: <Tablet className="w-4 h-4" />, label: '平板' },
    { type: 'mobile', icon: <Smartphone className="w-4 h-4" />, label: '手机' },
  ];

  return (
    <div className="flex items-center bg-gray-100 rounded-lg p-1">
      {devices.map((device) => (
        <button
          key={device.type}
          onClick={() => onChange(device.type)}
          className={cn(
            'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-all',
            current === device.type
              ? 'bg-white text-sky-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          )}
        >
          {device.icon}
          <span className="hidden sm:inline">{device.label}</span>
        </button>
      ))}
    </div>
  );
};

const ViewModeSelector: React.FC<{
  current: ViewMode;
  onChange: (mode: ViewMode) => void;
}> = ({ current, onChange }) => {
  const modes: { mode: ViewMode; icon: React.ReactNode; label: string }[] = [
    { mode: 'preview', icon: <Eye className="w-4 h-4" />, label: '预览' },
    { mode: 'code', icon: <Code className="w-4 h-4" />, label: '代码' },
    { mode: 'split', icon: <FileCode className="w-4 h-4" />, label: '分屏' },
  ];

  return (
    <div className="flex items-center bg-gray-100 rounded-lg p-1">
      {modes.map((mode) => (
        <button
          key={mode.mode}
          onClick={() => onChange(mode.mode)}
          className={cn(
            'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-all',
            current === mode.mode
              ? 'bg-white text-sky-600 shadow-sm'
              : 'text-gray-600 hover:text-gray-900'
          )}
        >
          {mode.icon}
          <span className="hidden sm:inline">{mode.label}</span>
        </button>
      ))}
    </div>
  );
};

const CodeEditor: React.FC<{
  files: Record<string, string>;
  activeFile: string;
  onFileChange: (file: string) => void;
}> = ({ files, activeFile, onFileChange }) => {
  const fileNames = Object.keys(files);

  const getLanguage = (filename: string): string => {
    if (filename.endsWith('.html')) return 'html';
    if (filename.endsWith('.css')) return 'css';
    if (filename.endsWith('.js')) return 'javascript';
    if (filename.endsWith('.json')) return 'json';
    return 'text';
  };

  return (
    <div className="flex flex-col h-full bg-gray-900 rounded-lg overflow-hidden">
      {/* File tabs */}
      <div className="flex items-center gap-1 px-2 py-2 bg-gray-800 border-b border-gray-700 overflow-x-auto">
        {fileNames.map((filename) => (
          <button
            key={filename}
            onClick={() => onFileChange(filename)}
            className={cn(
              'px-3 py-1.5 text-sm rounded-md transition-colors whitespace-nowrap',
              activeFile === filename
                ? 'bg-gray-700 text-white'
                : 'text-gray-400 hover:text-white hover:bg-gray-700/50'
            )}
          >
            {filename}
          </button>
        ))}
      </div>

      {/* Code content */}
      <div className="flex-1 overflow-auto">
        <pre className="p-4 text-sm font-mono text-gray-300">
          <code>{files[activeFile] || 'Select a file to view'}</code>
        </pre>
      </div>
    </div>
  );
};

const PreviewFrame: React.FC<{
  files: Record<string, string>;
  device: DeviceType;
}> = ({ files, device }) => {
  const [srcDoc, setSrcDoc] = useState('');
  const dimensions = DEVICE_DIMENSIONS[device];

  useEffect(() => {
    // Combine HTML, CSS, and JS into a single document
    const html = files['index.html'] || files['preview.html'] || '';
    const css = files['styles.css'] || '';
    const js = files['scripts.js'] || '';

    if (html) {
      // Inject CSS and JS into HTML
      let combinedHtml = html;

      if (css && !html.includes('styles.css')) {
        combinedHtml = combinedHtml.replace(
          '</head>',
          `<style>${css}</style></head>`
        );
      }

      if (js && !html.includes('scripts.js')) {
        combinedHtml = combinedHtml.replace(
          '</body>',
          `<script>${js}</script></body>`
        );
      }

      setSrcDoc(combinedHtml);
    }
  }, [files]);

  return (
    <div className="flex items-center justify-center min-h-full bg-gray-100 p-4">
      <div
        className="relative bg-white rounded-lg shadow-lg overflow-hidden transition-all duration-300"
        style={{
          width: device === 'desktop' ? '100%' : dimensions.width,
          height: dimensions.height,
          maxWidth: '100%',
        }}
      >
        {/* Device frame header */}
        {device !== 'desktop' && (
          <div className="h-6 bg-gray-800 flex items-center justify-center">
            <div className="w-16 h-4 bg-gray-700 rounded-full" />
          </div>
        )}

        {/* Preview iframe */}
        <iframe
          srcDoc={srcDoc}
          title="Prototype Preview"
          className="w-full h-full border-0"
          style={{
            height: device === 'desktop' ? '100%' : dimensions.height - 24,
          }}
          sandbox="allow-scripts allow-same-origin"
        />
      </div>
    </div>
  );
};

const ExportMenu: React.FC<{
  onExport: (format: 'html' | 'zip' | 'json') => void;
  onDeploy: () => void;
}> = ({ onExport, onDeploy }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-4 py-2 bg-sky-600 text-white rounded-lg hover:bg-sky-700 transition-colors"
      >
        <Download className="w-4 h-4" />
        <span>导出</span>
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg border border-gray-200 z-50 py-1">
            <button
              onClick={() => { onExport('html'); setIsOpen(false); }}
              className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
            >
              <FileCode className="w-4 h-4" />
              导出 HTML
            </button>
            <button
              onClick={() => { onExport('zip'); setIsOpen(false); }}
              className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              导出 ZIP
            </button>
            <button
              onClick={() => { onExport('json'); setIsOpen(false); }}
              className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center gap-2"
            >
              <FileJson className="w-4 h-4" />
              导出 JSON
            </button>
            <hr className="my-1 border-gray-200" />
            <button
              onClick={() => { onDeploy(); setIsOpen(false); }}
              className="w-full px-4 py-2 text-left text-sm text-sky-600 hover:bg-sky-50 flex items-center gap-2"
            >
              <ExternalLink className="w-4 h-4" />
              部署预览
            </button>
          </div>
        </>
      )}
    </div>
  );
};

const PageNavigator: React.FC<{
  pages: Array<{ name: string; route: string; title: string }>;
  currentPage: string;
  onPageChange: (route: string) => void;
}> = ({ pages, currentPage, onPageChange }) => {
  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-gray-50 border-b border-gray-200 overflow-x-auto">
      <span className="text-xs font-medium text-gray-500 whitespace-nowrap">页面:</span>
      {pages.map((page) => (
        <button
          key={page.route}
          onClick={() => onPageChange(page.route)}
          className={cn(
            'px-3 py-1 text-xs rounded-full transition-colors whitespace-nowrap',
            currentPage === page.route
              ? 'bg-sky-100 text-sky-700'
              : 'bg-white text-gray-600 hover:bg-gray-100 border border-gray-200'
          )}
        >
          {page.title}
        </button>
      ))}
    </div>
  );
};

// Main Component
export const PrototypePreview: React.FC<PrototypePreviewProps> = ({
  prdContent,
  onGenerate,
  onExport,
  onDeploy,
  className,
}) => {
  const [device, setDevice] = useState<DeviceType>('desktop');
  const [viewMode, setViewMode] = useState<ViewMode>('preview');
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [prototypeData, setPrototypeData] = useState<PrototypeData | null>(null);
  const [activeFile, setActiveFile] = useState('index.html');
  const [currentPage, setCurrentPage] = useState('/');

  const handleGenerate = useCallback(async () => {
    if (!prdContent.trim()) {
      setError('请输入PRD内容');
      return;
    }

    setIsGenerating(true);
    setError(null);

    try {
      const data = await generatePrototype(prdContent);
      setPrototypeData(data);
      onGenerate?.(data);

      // Set initial active file
      const files = Object.keys(data.files);
      if (files.length > 0) {
        setActiveFile(files[0]);
      }

      // Set initial page
      if (data.metadata.pages.length > 0) {
        setCurrentPage(data.metadata.pages[0].route);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '生成失败');
    } finally {
      setIsGenerating(false);
    }
  }, [prdContent, onGenerate]);

  const handleExport = useCallback((format: 'html' | 'zip' | 'json') => {
    if (!prototypeData) return;

    if (format === 'json') {
      const blob = new Blob([JSON.stringify(prototypeData, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${prototypeData.metadata.name || 'prototype'}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } else if (format === 'html') {
      const html = prototypeData.files['index.html'] || '';
      const blob = new Blob([html], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'index.html';
      a.click();
      URL.revokeObjectURL(url);
    }

    onExport?.(format);
  }, [prototypeData, onExport]);

  const handleDeploy = useCallback(() => {
    onDeploy?.();
  }, [onDeploy]);

  // Auto-generate on mount if prdContent is provided
  useEffect(() => {
    if (prdContent && !prototypeData) {
      handleGenerate();
    }
  }, []);

  return (
    <div className={cn('flex flex-col h-full bg-white rounded-lg border border-gray-200 overflow-hidden', className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-white">
        <div className="flex items-center gap-4">
          <h3 className="text-lg font-semibold text-gray-900">原型预览</h3>
          {prototypeData && (
            <span className="text-sm text-gray-500">
              {prototypeData.metadata.page_count} 个页面
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          <DeviceSelector current={device} onChange={setDevice} />
          <ViewModeSelector current={viewMode} onChange={setViewMode} />

          <button
            onClick={handleGenerate}
            disabled={isGenerating}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              isGenerating
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            )}
          >
            <RefreshCw className={cn('w-4 h-4', isGenerating && 'animate-spin')} />
            <span className="hidden sm:inline">{isGenerating ? '生成中...' : '重新生成'}</span>
          </button>

          {prototypeData && (
            <ExportMenu onExport={handleExport} onDeploy={handleDeploy} />
          )}
        </div>
      </div>

      {/* Page Navigator */}
      {prototypeData && prototypeData.metadata.pages.length > 1 && (
        <PageNavigator
          pages={prototypeData.metadata.pages}
          currentPage={currentPage}
          onPageChange={setCurrentPage}
        />
      )}

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {error ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <X className="w-12 h-12 text-rose-500 mx-auto mb-4" />
              <p className="text-rose-600 font-medium">{error}</p>
              <button
                onClick={handleGenerate}
                className="mt-4 px-4 py-2 bg-sky-600 text-white rounded-lg hover:bg-sky-700"
              >
                重试
              </button>
            </div>
          </div>
        ) : isGenerating ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <RefreshCw className="w-12 h-12 text-sky-500 mx-auto mb-4 animate-spin" />
              <p className="text-gray-600">正在生成原型...</p>
            </div>
          </div>
        ) : prototypeData ? (
          <div className={cn(
            'h-full',
            viewMode === 'split' && 'grid grid-cols-2'
          )}>
            {(viewMode === 'preview' || viewMode === 'split') && (
              <div className={cn('h-full', viewMode === 'split' && 'border-r border-gray-200')}>
                <PreviewFrame files={prototypeData.files} device={device} />
              </div>
            )}

            {(viewMode === 'code' || viewMode === 'split') && (
              <div className="h-full">
                <CodeEditor
                  files={prototypeData.files}
                  activeFile={activeFile}
                  onFileChange={setActiveFile}
                />
              </div>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <Zap className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500 mb-4">输入PRD内容并点击生成原型</p>
              <button
                onClick={handleGenerate}
                className="px-4 py-2 bg-sky-600 text-white rounded-lg hover:bg-sky-700"
              >
                生成原型
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      {prototypeData && (
        <div className="flex items-center justify-between px-4 py-2 bg-gray-50 border-t border-gray-200 text-xs text-gray-500">
          <div className="flex items-center gap-4">
            <span>项目: {prototypeData.metadata.name}</span>
            <span className="flex items-center gap-1">
              <Check className="w-3 h-3 text-emerald-500" />
              已生成
            </span>
          </div>
          <div className="flex items-center gap-4">
            <span>{Object.keys(prototypeData.files).length} 个文件</span>
            <span>响应式设计</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default PrototypePreview;
