'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { useChatStore } from '@/stores/chatStore'
import { useProjectStore } from '@/stores/projectStore'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui-from-ai-pm/card'
import { Button } from '@/components/ui-from-ai-pm/button'
import { Input } from '@/components/ui-from-ai-pm/input'
import { ScrollArea } from '@/components/ui-from-ai-pm/scroll-area'
import { Badge } from '@/components/ui-from-ai-pm/badge'
import { Send, Bot, User, Sparkles, Plus } from 'lucide-react'
import { cn } from '@/lib/utils'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useKeyboardShortcuts, createChatShortcuts } from '@/hooks/useKeyboardShortcuts'
import { KeyboardShortcutsHelp } from './KeyboardShortcutsHelp'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface MessageContentProps {
  content: string
  isUser: boolean
}

function MessageContent({ content, isUser }: MessageContentProps) {
  if (isUser) {
    return <span className="whitespace-pre-wrap">{content}</span>
  }

  return (
    <div className="prose prose-sm max-w-none dark:prose-invert">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code: ({ className, children, ...props }: React.ComponentPropsWithoutRef<'code'>) => {
            const isInline = !className
            return isInline ? (
              <code className="bg-muted px-1 py-0.5 rounded text-xs" {...props}>
                {children}
              </code>
            ) : (
              <pre className="bg-muted p-2 rounded-lg overflow-x-auto my-2">
                <code className="text-xs" {...props}>
                  {children}
                </code>
              </pre>
            )
          },
          p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
          ul: ({ children }) => <ul className="list-disc pl-4 mb-2">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal pl-4 mb-2">{children}</ol>,
          li: ({ children }) => <li className="mb-0.5">{children}</li>,
          h1: ({ children }) => <h1 className="text-lg font-bold mb-2">{children}</h1>,
          h2: ({ children }) => <h2 className="text-base font-bold mb-2">{children}</h2>,
          h3: ({ children }) => <h3 className="text-sm font-bold mb-1">{children}</h3>,
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-muted-foreground/30 pl-3 italic my-2">
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <table className="w-full text-xs border-collapse my-2">{children}</table>
          ),
          th: ({ children }) => (
            <th className="border border-muted-foreground/20 px-2 py-1 bg-muted font-medium">{children}</th>
          ),
          td: ({ children }) => (
            <td className="border border-muted-foreground/20 px-2 py-1">{children}</td>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}

export function ChatInterface() {
  const {
    currentConversation,
    createConversation,
    addMessage,
    setCurrentConversation,
    getConversationByProject,
    isProcessing,
    setProcessing
  } = useChatStore()
  const { currentProject } = useProjectStore()
  const [input, setInput] = useState('')
  const [streamingContent, setStreamingContent] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Auto-create conversation if none exists
  useEffect(() => {
    if (currentProject && !currentConversation) {
      const projectConversations = getConversationByProject(currentProject.id)
      if (projectConversations.length === 0) {
        createConversation(currentProject.id, `${currentProject.name} - 对话`)
      } else {
        setCurrentConversation(projectConversations[0])
      }
    }
  }, [currentProject, currentConversation, createConversation, getConversationByProject, setCurrentConversation])

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [currentConversation?.messages, streamingContent])

  const sendMessageStream = useCallback(async (content: string) => {
    if (!currentConversation) return

    setProcessing(true)
    setStreamingContent('')

    try {
      // First, add user message locally
      addMessage(currentConversation.id, {
        conversationId: currentConversation.id,
        sender: {
          type: 'user',
          id: 'user_1',
          name: '我',
        },
        content: content,
        type: 'text',
      })

      // Call streaming API
      const response = await fetch(
        `${API_BASE_URL}/ai/chat/stream?conversation_id=${currentConversation.id}&content=${encodeURIComponent(content)}&agent_role=orchestrator`,
        {
          method: 'POST',
        }
      )

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let fullContent = ''

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                if (data.content) {
                  fullContent += data.content
                  setStreamingContent(fullContent)
                }
                if (data.done) {
                  // Add AI message to store
                  addMessage(currentConversation.id, {
                    conversationId: currentConversation.id,
                    sender: {
                      type: 'agent',
                      id: 'orchestrator',
                      name: 'Orchestrator',
                      role: '编排器',
                    },
                    content: fullContent || data.full_content || '',
                    type: 'text',
                    metadata: { skillUsed: 'AI助手', model: 'kimi-k2.5' },
                  })
                  setStreamingContent('')
                }
              } catch (e) {
                console.error('SSE parse error:', e, 'line:', line)
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Chat stream error:', error)
      addMessage(currentConversation.id, {
        conversationId: currentConversation.id,
        sender: {
          type: 'agent',
          id: 'orchestrator',
          name: 'Orchestrator',
          role: '编排器',
        },
        content: '抱歉，连接 AI 服务失败。请检查后端服务是否正常运行。',
        type: 'text',
      })
    } finally {
      setProcessing(false)
      setStreamingContent('')
    }
  }, [currentConversation, addMessage, setProcessing])

  const handleSend = () => {
    if (!input.trim() || isProcessing || !currentProject) return
    const content = input.trim()
    setInput('')
    sendMessageStream(content)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleNewConversation = () => {
    if (currentProject) {
      createConversation(currentProject.id)
    }
  }

  // Setup keyboard shortcuts
  useKeyboardShortcuts(
    createChatShortcuts({
      onSend: handleSend,
      onNewConversation: handleNewConversation,
      onFocusInput: () => inputRef.current?.focus(),
    })
  )

  const messages = currentConversation?.messages || []

  return (
    <Card className="h-[400px] flex flex-col">
      <CardHeader className="pb-2 pt-3 px-3">
        <CardTitle className="text-sm flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5" />
            <span className="text-xs">{currentConversation?.title || 'AI 助手'}</span>
          </div>
          <div className="flex items-center gap-1">
            {currentProject && (
              <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4">
                {currentProject.name}
              </Badge>
            )}
            <KeyboardShortcutsHelp />
            <Button
              size="icon"
              variant="ghost"
              className="h-6 w-6"
              onClick={handleNewConversation}
              disabled={!currentProject}
            >
              <Plus className="w-3.5 h-3.5" />
            </Button>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col gap-2 px-3 pb-3">
        <ScrollArea className="flex-1 pr-2" ref={scrollRef}>
          <div className="space-y-2">
            {messages.length === 0 && !streamingContent && (
              <div className="text-center text-muted-foreground py-6">
                <Bot className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-xs">开始与 Multi-Agent 系统对话</p>
                <p className="text-[10px] mt-0.5">
                  {currentProject
                    ? `项目: ${currentProject.name}`
                    : '请先选择一个项目'}
                </p>
              </div>
            )}
            {messages.map((message) => (
              <div
                key={message.id}
                className={cn(
                  'flex gap-2',
                  message.sender.type === 'user' ? 'flex-row-reverse' : ''
                )}
              >
                <div
                  className={cn(
                    'w-6 h-6 rounded-full flex items-center justify-center shrink-0',
                    message.sender.type === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted'
                  )}
                >
                  {message.sender.type === 'user' ? (
                    <User className="w-3 h-3" />
                  ) : (
                    <Bot className="w-3 h-3" />
                  )}
                </div>
                <div className={cn(
                  'flex-1 space-y-0.5 min-w-0',
                  message.sender.type === 'user' ? 'text-right' : ''
                )}>
                  <div className={cn(
                    "flex items-center gap-1.5 text-[10px] text-muted-foreground",
                    message.sender.type === 'user' ? 'justify-end' : ''
                  )}>
                    {message.sender.type !== 'user' && (
                      <>
                        <span className="truncate">{message.sender.name}</span>
                        {message.sender.role && (
                          <Badge variant="secondary" className="text-[10px] px-1 py-0 h-3.5 shrink-0">
                            {message.sender.role}
                          </Badge>
                        )}
                      </>
                    )}
                  </div>
                  <div
                    className={cn(
                      'inline-block px-2.5 py-1.5 rounded-lg text-xs text-left',
                      message.sender.type === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted'
                    )}
                  >
                    <MessageContent
                      content={message.content}
                      isUser={message.sender.type === 'user'}
                    />
                  </div>
                  {message.metadata?.skillUsed && (
                    <div className="text-[10px] text-muted-foreground">
                      使用技能: {message.metadata.skillUsed}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {/* Streaming message */}
            {streamingContent && (
              <div className="flex gap-2">
                <div className="w-6 h-6 rounded-full bg-muted flex items-center justify-center">
                  <Bot className="w-3 h-3" />
                </div>
                <div className="flex-1 space-y-0.5 min-w-0">
                  <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                    <span>Orchestrator</span>
                    <Badge variant="secondary" className="text-[10px] px-1 py-0 h-3.5">编排器</Badge>
                  </div>
                  <div className="bg-muted px-2.5 py-1.5 rounded-lg text-xs">
                    <MessageContent content={streamingContent} isUser={false} />
                    <span className="animate-pulse">▊</span>
                  </div>
                </div>
              </div>
            )}
            {/* Loading indicator */}
            {isProcessing && !streamingContent && (
              <div className="flex gap-2">
                <div className="w-6 h-6 rounded-full bg-muted flex items-center justify-center">
                  <Bot className="w-3 h-3" />
                </div>
                <div className="flex-1 space-y-0.5">
                  <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                    <span>Orchestrator</span>
                    <Badge variant="secondary" className="text-[10px] px-1 py-0 h-3.5">编排器</Badge>
                  </div>
                  <div className="bg-muted px-2.5 py-1.5 rounded-lg text-xs">
                    <span className="animate-pulse">正在思考...</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </ScrollArea>

        <div className="flex gap-1.5 items-end">
          <textarea
            ref={inputRef}
            placeholder={currentProject ? "输入消息..." : "请先选择一个项目"}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isProcessing || !currentProject}
            rows={1}
            className="flex-1 min-h-[32px] max-h-[120px] resize-none rounded-md border border-input bg-transparent px-3 py-1.5 text-xs shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          />
          <Button
            size="icon"
            className="h-8 w-8 shrink-0"
            onClick={handleSend}
            disabled={!input.trim() || isProcessing || !currentProject}
            aria-label="发送"
          >
            <Send className="w-3.5 h-3.5" />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
