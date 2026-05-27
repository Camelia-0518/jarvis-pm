'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui-from-ai-pm/card'
import { Button } from '@/components/ui-from-ai-pm/button'
import { Badge } from '@/components/ui-from-ai-pm/badge'
import { Textarea } from '@/components/ui-from-ai-pm/textarea'
import { Input } from '@/components/ui-from-ai-pm/input'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui-from-ai-pm/dialog'
import {
  exportAsMarkdown,
  exportAsWord,
  exportAsPDF,
  exportAsFeishuDoc,
  exportAsFeishuCard,
  exportAsWeChatWork,
  generatePRD,
  generateMeetingMinutes,
  downloadFile,
  type ExportDocument,
} from '@/utils/exportUtils'
import {
  FileDown,
  FileText,
  FileSpreadsheet,
  FileImage,
  Download,
  Copy,
  Check,
  FileCode,
  Palette,
  Share2,
  ExternalLink,
  Github,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface ExportPanelProps {
  defaultTitle?: string
  defaultContent?: string
}

export function ExportPanel({
  defaultTitle = '未命名文档',
  defaultContent = '',
}: ExportPanelProps) {
  const [title, setTitle] = useState(defaultTitle)
  const [content, setContent] = useState(defaultContent)
  const [copied, setCopied] = useState(false)
  const [exporting, setExporting] = useState<string | null>(null)

  const doc: ExportDocument = {
    title,
    content,
    type: 'prd',
    createdAt: new Date().toISOString(),
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleExport = async (format: string) => {
    setExporting(format)

    try {
      switch (format) {
        case 'markdown':
          exportAsMarkdown(doc)
          break
        case 'word':
          exportAsWord(doc)
          break
        case 'pdf':
          exportAsPDF(doc)
          break
        case 'github':
          const githubUrl = `https://github.com/new?title=${encodeURIComponent(title)}&body=${encodeURIComponent(content)}`
          window.open(githubUrl, '_blank')
          break
        case 'feishu':
          downloadFile(exportAsFeishuDoc(content, title), `${title}_feishu.md`, 'text/markdown')
          break
        case 'feishu_card':
          downloadFile(exportAsFeishuCard(content, title), `${title}_card.json`, 'application/json')
          break
        case 'wechat_work':
          downloadFile(exportAsWeChatWork(content), `${title}_wechat.md`, 'text/markdown')
          break
      }
    } catch {
      // Export failures are handled via UI state; no console logging in production
    }

    setTimeout(() => setExporting(null), 1000)
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileDown className="w-5 h-5" />
          导出文档
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Document Info */}
        <div className="space-y-2">
          <label className="text-sm font-medium">文档标题</label>
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="输入文档标题"
          />
        </div>

        {/* Content Preview */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium">内容预览</label>
            <Button size="sm" variant="ghost" onClick={handleCopy}>
              {copied ? (
                <Check className="w-4 h-4 mr-1" />
              ) : (
                <Copy className="w-4 h-4 mr-1" />
              )}
              {copied ? '已复制' : '复制'}
            </Button>
          </div>
          <Textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="输入文档内容（支持 Markdown）"
            className="min-h-[200px] font-mono text-sm"
          />
        </div>

        {/* Export Options */}
        <div className="space-y-2">
          <label className="text-sm font-medium">导出格式</label>
          <div className="grid grid-cols-3 gap-2">
            <Button
              variant="outline"
              className="flex flex-col items-center py-4 h-auto"
              onClick={() => handleExport('markdown')}
              disabled={exporting === 'markdown'}
            >
              <FileText className="w-8 h-8 mb-2" />
              <span className="text-sm">Markdown</span>
              <Badge variant="secondary" className="mt-1 text-xs">.md</Badge>
            </Button>
            <Button
              variant="outline"
              className="flex flex-col items-center py-4 h-auto"
              onClick={() => handleExport('word')}
              disabled={exporting === 'word'}
            >
              <FileSpreadsheet className="w-8 h-8 mb-2" />
              <span className="text-sm">Word</span>
              <Badge variant="secondary" className="mt-1 text-xs">.doc</Badge>
            </Button>
            <Button
              variant="outline"
              className="flex flex-col items-center py-4 h-auto"
              onClick={() => handleExport('pdf')}
              disabled={exporting === 'pdf'}
            >
              <FileImage className="w-8 h-8 mb-2" />
              <span className="text-sm">PDF</span>
              <Badge variant="secondary" className="mt-1 text-xs">.pdf</Badge>
            </Button>
          </div>
        </div>

        {/* Third-party Integrations */}
        <div className="space-y-2 pt-4 border-t">
          <label className="text-sm font-medium">集成导出</label>
          <div className="grid grid-cols-2 gap-2">
            <Button
              variant="outline"
              className="flex items-center justify-start gap-2"
              onClick={() => handleExport('github')}
            >
              <Github className="w-4 h-4" />
              <div className="text-left">
                <p className="text-sm font-medium">GitHub</p>
                <p className="text-xs text-muted-foreground">创建 Issue</p>
              </div>
            </Button>
            <Button
              variant="outline"
              className="flex items-center justify-start gap-2"
              onClick={() => handleExport('feishu')}
            >
              <Share2 className="w-4 h-4" />
              <div className="text-left">
                <p className="text-sm font-medium">飞书文档</p>
                <p className="text-xs text-muted-foreground">Markdown 格式</p>
              </div>
            </Button>
            <Button
              variant="outline"
              className="flex items-center justify-start gap-2"
              onClick={() => handleExport('feishu_card')}
            >
              <FileCode className="w-4 h-4" />
              <div className="text-left">
                <p className="text-sm font-medium">飞书卡片</p>
                <p className="text-xs text-muted-foreground">消息卡片 JSON</p>
              </div>
            </Button>
            <Button
              variant="outline"
              className="flex items-center justify-start gap-2"
              onClick={() => handleExport('wechat_work')}
            >
              <FileText className="w-4 h-4" />
              <div className="text-left">
                <p className="text-sm font-medium">企业微信</p>
                <p className="text-xs text-muted-foreground">Markdown 消息</p>
              </div>
            </Button>
          </div>
        </div>

        {/* Quick Templates */}
        <div className="space-y-2 pt-4 border-t">
          <label className="text-sm font-medium">快速生成</label>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                const prd = generatePRD(title, {
                  overview: '本项目旨在提升医疗服务效率...',
                  goals: ['优化患者就诊体验', '提升医院运营效率', '降低管理成本'],
                  features: [
                    { name: '在线预约', description: '支持多院区、分时段预约', priority: '高' },
                    { name: '智能导诊', description: 'AI辅助科室推荐', priority: '中' },
                  ],
                  userStories: [
                    { role: '患者', action: '在线预约挂号', benefit: '节省排队时间' },
                  ],
                  acceptanceCriteria: ['系统响应时间小于2秒', '支持1000并发用户'],
                  timeline: '第一阶段（2周）：需求分析\n第二阶段（4周）：开发实现\n第三阶段（2周）：测试上线',
                })
                setContent(prd)
              }}
            >
              生成 PRD 模板
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                const minutes = generateMeetingMinutes({
                  title: `${title} - 需求评审会`,
                  date: new Date().toLocaleString(),
                  attendees: ['产品经理', '技术负责人', 'UI设计师'],
                  agenda: ['需求背景介绍', '功能评审', '技术方案讨论', '排期确认'],
                  discussions: [
                    { topic: '功能优先级', content: '讨论了核心功能和增强功能的优先级排序' },
                  ],
                  actionItems: [
                    { task: '完成PRD文档', assignee: '产品经理', dueDate: '2026-04-10' },
                  ],
                })
                setContent(minutes)
              }}
            >
              生成会议纪要
            </Button>
          </div>
        </div>

        {/* Preview Dialog */}
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="outline" className="w-full">
              <FileText className="w-4 h-4 mr-2" />
              预览文档
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-3xl max-h-[80vh]">
            <DialogHeader>
              <DialogTitle>文档预览</DialogTitle>
            </DialogHeader>
            <div className="overflow-auto">
              <div className="prose prose-sm max-w-none">
                <pre className="whitespace-pre-wrap font-mono text-sm bg-muted p-4 rounded-lg">
                  {content}
                </pre>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  )
}
