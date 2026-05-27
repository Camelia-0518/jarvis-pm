import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ChatInterface } from './ChatInterface'
import { useChatStore } from '@/stores/chatStore'
import { useProjectStore } from '@/stores/projectStore'

// Mock fetch globally
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

// Mock keyboard shortcuts hook
vi.mock('@/hooks/useKeyboardShortcuts', () => ({
  useKeyboardShortcuts: vi.fn(),
  createChatShortcuts: vi.fn(() => []),
}))

describe('ChatInterface', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Reset stores
    useChatStore.setState({
      conversations: [],
      currentConversation: null,
      isProcessing: false,
    })
    useProjectStore.setState({
      currentProject: null,
    })
  })

  it('renders empty state when no project selected', () => {
    render(<ChatInterface />)

    expect(screen.getByText('开始与 Multi-Agent 系统对话')).toBeInTheDocument()
    expect(screen.getByText('请先选择一个项目')).toBeInTheDocument()
  })

  it('renders with project name badge when project is selected', () => {
    useProjectStore.setState({
      currentProject: {
        id: 'proj-1',
        name: 'Test Project',
      } as any,
    })

    render(<ChatInterface />)

    expect(screen.getByText('Test Project')).toBeInTheDocument()
  })

  it('disables input when no project is selected', () => {
    render(<ChatInterface />)

    const textarea = screen.getByPlaceholderText('请先选择一个项目')
    expect(textarea).toBeDisabled()
  })

  it('enables input when project is selected', () => {
    useProjectStore.setState({
      currentProject: {
        id: 'proj-1',
        name: 'Test Project',
      } as any,
    })

    render(<ChatInterface />)

    const textarea = screen.getByPlaceholderText('输入消息...')
    expect(textarea).not.toBeDisabled()
  })

  it('auto-creates conversation when project is selected', () => {
    useProjectStore.setState({
      currentProject: {
        id: 'proj-1',
        name: 'Test Project',
      } as any,
    })

    render(<ChatInterface />)

    // Should show the new conversation title
    expect(screen.getByText('Test Project - 对话')).toBeInTheDocument()
  })

  it('shows existing messages', () => {
    const conversation = {
      id: 'conv-1',
      projectId: 'proj-1',
      title: 'Existing Chat',
      status: 'active' as const,
      messages: [
        {
          id: 'msg-1',
          conversationId: 'conv-1',
          sender: { type: 'user' as const, id: 'user_1', name: '我' },
          content: 'Hello AI',
          type: 'text' as const,
          createdAt: new Date().toISOString(),
        },
        {
          id: 'msg-2',
          conversationId: 'conv-1',
          sender: { type: 'agent' as const, id: 'orchestrator', name: 'Orchestrator', role: '编排器' },
          content: 'Hello user',
          type: 'text' as const,
          createdAt: new Date().toISOString(),
        },
      ],
      createdAt: new Date().toISOString(),
    }

    useProjectStore.setState({
      currentProject: {
        id: 'proj-1',
        name: 'Test Project',
      } as any,
    })
    useChatStore.setState({
      conversations: [conversation],
      currentConversation: conversation,
    })

    render(<ChatInterface />)

    expect(screen.getByText('Hello AI')).toBeInTheDocument()
    expect(screen.getByText('Hello user')).toBeInTheDocument()
  })

  it('sends message on button click', async () => {
    useProjectStore.setState({
      currentProject: {
        id: 'proj-1',
        name: 'Test Project',
      } as any,
    })

    mockFetch.mockResolvedValueOnce({
      ok: true,
      body: {
        getReader: () => ({
          read: vi
            .fn()
            .mockResolvedValueOnce({ done: false, value: new TextEncoder().encode('data: {"content":"Hi"}\n\n') })
            .mockResolvedValueOnce({ done: false, value: new TextEncoder().encode('data: {"done":true,"full_content":"Hi"}\n\n') })
            .mockResolvedValueOnce({ done: true, value: undefined }),
        }),
      },
    })

    render(<ChatInterface />)

    const textarea = screen.getByPlaceholderText('输入消息...')
    fireEvent.change(textarea, { target: { value: 'Test message' } })

    const sendButton = screen.getByRole('button', { name: /发送/i })
    fireEvent.click(sendButton)

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/ai/chat/stream'),
        expect.objectContaining({ method: 'POST' })
      )
    })
  })

  it('shows processing indicator while streaming', async () => {
    useProjectStore.setState({
      currentProject: {
        id: 'proj-1',
        name: 'Test Project',
      } as any,
    })

    mockFetch.mockResolvedValueOnce({
      ok: true,
      body: {
        getReader: () => ({
          read: vi
            .fn()
            .mockResolvedValueOnce({ done: false, value: new TextEncoder().encode('data: {"content":"partial"}\n\n') })
            .mockImplementation(() => new Promise(() => {})), // Never resolves (simulates ongoing stream)
        }),
      },
    })

    render(<ChatInterface />)

    const textarea = screen.getByPlaceholderText('输入消息...')
    fireEvent.change(textarea, { target: { value: 'Test' } })

    const sendButton = screen.getByRole('button', { name: /发送/i })
    fireEvent.click(sendButton)

    await waitFor(() => {
      expect(screen.getByText('partial')).toBeInTheDocument()
    })
  })

  it('shows error message on fetch failure', async () => {
    useProjectStore.setState({
      currentProject: {
        id: 'proj-1',
        name: 'Test Project',
      } as any,
    })

    mockFetch.mockRejectedValueOnce(new Error('Network error'))

    render(<ChatInterface />)

    const textarea = screen.getByPlaceholderText('输入消息...')
    fireEvent.change(textarea, { target: { value: 'Test' } })

    const sendButton = screen.getByRole('button', { name: /发送/i })
    fireEvent.click(sendButton)

    await waitFor(() => {
      expect(screen.getByText('抱歉，连接 AI 服务失败。请检查后端服务是否正常运行。')).toBeInTheDocument()
    })
  })

  it('disables send button when input is empty', () => {
    useProjectStore.setState({
      currentProject: {
        id: 'proj-1',
        name: 'Test Project',
      } as any,
    })

    render(<ChatInterface />)

    const sendButton = screen.getByRole('button', { name: /发送/i })
    expect(sendButton).toBeDisabled()
  })

  it('disables send button while processing', async () => {
    useProjectStore.setState({
      currentProject: {
        id: 'proj-1',
        name: 'Test Project',
      } as any,
    })
    useChatStore.setState({ isProcessing: true })

    render(<ChatInterface />)

    const textarea = screen.getByPlaceholderText('输入消息...')
    fireEvent.change(textarea, { target: { value: 'Test' } })

    const sendButton = screen.getByRole('button', { name: /发送/i })
    expect(sendButton).toBeDisabled()
  })

  it('shows skill used indicator in message', () => {
    const conversation = {
      id: 'conv-1',
      projectId: 'proj-1',
      title: 'Chat',
      status: 'active' as const,
      messages: [
        {
          id: 'msg-1',
          conversationId: 'conv-1',
          sender: { type: 'agent' as const, id: 'orchestrator', name: 'Orchestrator', role: '编排器' },
          content: 'Skill result',
          type: 'text' as const,
          metadata: { skillUsed: '需求分析' },
          createdAt: new Date().toISOString(),
        },
      ],
      createdAt: new Date().toISOString(),
    }

    useProjectStore.setState({
      currentProject: {
        id: 'proj-1',
        name: 'Test Project',
      } as any,
    })
    useChatStore.setState({
      conversations: [conversation],
      currentConversation: conversation,
    })

    render(<ChatInterface />)

    expect(screen.getByText('使用技能: 需求分析')).toBeInTheDocument()
  })
})
