import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ExportPanel } from './ExportPanel'

const mockExportAsMarkdown = vi.fn()
const mockExportAsWord = vi.fn()
const mockExportAsPDF = vi.fn()
const mockGeneratePRD = vi.fn().mockReturnValue('# Generated PRD')
const mockGenerateMeetingMinutes = vi.fn().mockReturnValue('# Meeting Minutes')

vi.mock('@/utils/exportUtils', () => ({
  exportAsMarkdown: (...args: unknown[]) => mockExportAsMarkdown(...args),
  exportAsWord: (...args: unknown[]) => mockExportAsWord(...args),
  exportAsPDF: (...args: unknown[]) => mockExportAsPDF(...args),
  generatePRD: (...args: unknown[]) => mockGeneratePRD(...args),
  generateMeetingMinutes: (...args: unknown[]) => mockGenerateMeetingMinutes(...args),
}))

describe('ExportPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders with default title and content', () => {
    render(<ExportPanel />)

    expect(screen.getByText('导出文档')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('输入文档标题')).toHaveValue('未命名文档')
    expect(screen.getByPlaceholderText('输入文档内容（支持 Markdown）')).toHaveValue('')
  })

  it('renders with provided props', () => {
    render(<ExportPanel defaultTitle="测试文档" defaultContent="测试内容" />)

    expect(screen.getByPlaceholderText('输入文档标题')).toHaveValue('测试文档')
    expect(screen.getByPlaceholderText('输入文档内容（支持 Markdown）')).toHaveValue('测试内容')
  })

  it('updates title on input change', () => {
    render(<ExportPanel />)

    const titleInput = screen.getByPlaceholderText('输入文档标题')
    fireEvent.change(titleInput, { target: { value: '新标题' } })

    expect(titleInput).toHaveValue('新标题')
  })

  it('updates content on textarea change', () => {
    render(<ExportPanel />)

    const contentInput = screen.getByPlaceholderText('输入文档内容（支持 Markdown）')
    fireEvent.change(contentInput, { target: { value: '新内容' } })

    expect(contentInput).toHaveValue('新内容')
  })

  it('copies content to clipboard', async () => {
    render(<ExportPanel defaultContent="要复制的内容" />)

    const copyButton = screen.getByText('复制')
    fireEvent.click(copyButton)

    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('要复制的内容')
    })

    expect(screen.getByText('已复制')).toBeInTheDocument()
  })

  it('exports markdown when markdown button clicked', () => {
    render(<ExportPanel defaultTitle="Test Doc" defaultContent="Test content" />)

    const markdownButton = screen.getByText('Markdown')
    fireEvent.click(markdownButton)

    expect(mockExportAsMarkdown).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Test Doc',
        content: 'Test content',
        type: 'prd',
      })
    )
  })

  it('exports word when word button clicked', () => {
    render(<ExportPanel defaultTitle="Test Doc" defaultContent="Test content" />)

    const wordButton = screen.getByText('Word')
    fireEvent.click(wordButton)

    expect(mockExportAsWord).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Test Doc',
        content: 'Test content',
        type: 'prd',
      })
    )
  })

  it('exports pdf when pdf button clicked', () => {
    render(<ExportPanel defaultTitle="Test Doc" defaultContent="Test content" />)

    const pdfButton = screen.getByText('PDF')
    fireEvent.click(pdfButton)

    expect(mockExportAsPDF).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Test Doc',
        content: 'Test content',
        type: 'prd',
      })
    )
  })

  it('opens GitHub issue in new window', () => {
    const mockOpen = vi.fn()
    vi.stubGlobal('open', mockOpen)

    render(<ExportPanel defaultTitle="GitHub Test" defaultContent="Issue body" />)

    const githubButton = screen.getByText('GitHub')
    fireEvent.click(githubButton)

    expect(mockOpen).toHaveBeenCalledWith(
      expect.stringContaining('github.com/new'),
      '_blank'
    )

    vi.unstubAllGlobals()
  })

  it('generates PRD template when button clicked', () => {
    render(<ExportPanel defaultTitle="PRD Title" />)

    const prdButton = screen.getByText('生成 PRD 模板')
    fireEvent.click(prdButton)

    expect(mockGeneratePRD).toHaveBeenCalledWith('PRD Title', expect.any(Object))
  })

  it('generates meeting minutes when button clicked', () => {
    render(<ExportPanel defaultTitle="Meeting Title" />)

    const minutesButton = screen.getByText('生成会议纪要')
    fireEvent.click(minutesButton)

    expect(mockGenerateMeetingMinutes).toHaveBeenCalledWith(expect.any(Object))
  })

  it('disables export button while exporting', async () => {
    render(<ExportPanel defaultTitle="Test" defaultContent="Content" />)

    const markdownButton = screen.getByText('Markdown').closest('button')
    expect(markdownButton).not.toBeDisabled()

    fireEvent.click(markdownButton!)
    expect(markdownButton).toBeDisabled()

    // After timeout, should be re-enabled
    await waitFor(() => expect(markdownButton).not.toBeDisabled(), { timeout: 1500 })
  })

  it('shows all export format badges', () => {
    render(<ExportPanel />)

    expect(screen.getByText('.md')).toBeInTheDocument()
    expect(screen.getByText('.doc')).toBeInTheDocument()
    expect(screen.getByText('.pdf')).toBeInTheDocument()
  })

  it('shows preview dialog trigger', () => {
    render(<ExportPanel />)

    expect(screen.getByText('预览文档')).toBeInTheDocument()
  })
})
