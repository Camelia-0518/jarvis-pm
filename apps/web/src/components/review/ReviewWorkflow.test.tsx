import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ReviewWorkflowList } from './ReviewWorkflow'
import { useReviewWorkflowStore } from '@/stores/reviewWorkflowStore'

describe('ReviewWorkflowList', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()

    useReviewWorkflowStore.setState({
      workflows: [
        {
          id: 'wf-test-1',
          requirementId: 'req-1',
          requirementTitle: 'Test Workflow Alpha',
          submitterId: 'rev-4',
          submitterName: 'Test Submitter',
          currentStage: 'medical-review',
          status: 'in-progress',
          stages: [
            { stage: 'draft', status: 'approved', completedAt: '2024-01-01', assignedReviewers: ['rev-4'] },
            { stage: 'medical-review', status: 'in-progress', startedAt: '2024-01-01', assignedReviewers: ['rev-1'] },
            { stage: 'compliance-review', status: 'pending', assignedReviewers: ['rev-2'] },
            { stage: 'technical-review', status: 'pending', assignedReviewers: ['rev-3'] },
            { stage: 'branch-review', status: 'pending', assignedReviewers: ['rev-5'] },
          ],
          comments: [
            {
              id: 'c-1',
              stage: 'draft',
              reviewerId: 'rev-4',
              reviewerName: 'Reviewer Four',
              reviewerRole: 'Product Manager',
              content: 'Initial comment text',
              type: 'comment',
              createdAt: '2024-01-01T00:00:00Z',
            },
          ],
          createdAt: '2024-01-01T00:00:00Z',
          updatedAt: '2024-01-01T00:00:00Z',
        },
        {
          id: 'wf-test-2',
          requirementId: 'req-2',
          requirementTitle: 'Test Workflow Beta',
          submitterId: 'rev-5',
          submitterName: 'Beta Submitter',
          currentStage: 'approved',
          status: 'approved',
          stages: [
            { stage: 'draft', status: 'approved', completedAt: '2024-01-01', assignedReviewers: ['rev-5'] },
          ],
          comments: [],
          createdAt: '2024-01-01T00:00:00Z',
          updatedAt: '2024-01-01T00:00:00Z',
        },
        {
          id: 'wf-test-3',
          requirementId: 'req-3',
          requirementTitle: 'Test Workflow Gamma',
          submitterId: 'rev-7',
          submitterName: 'Gamma Submitter',
          currentStage: 'compliance-review',
          status: 'needs-revision',
          stages: [
            { stage: 'draft', status: 'approved', completedAt: '2024-01-01', assignedReviewers: ['rev-7'] },
            { stage: 'medical-review', status: 'approved', completedAt: '2024-01-01', assignedReviewers: ['rev-1'] },
            { stage: 'compliance-review', status: 'needs-revision', startedAt: '2024-01-01', assignedReviewers: ['rev-2'] },
          ],
          comments: [
            {
              id: 'c-4',
              stage: 'compliance-review',
              reviewerId: 'rev-2',
              reviewerName: 'Reviewer Two',
              reviewerRole: 'Compliance Officer',
              content: 'Pricing issue found',
              type: 'revision-request',
              createdAt: '2024-01-01T00:00:00Z',
            },
          ],
          createdAt: '2024-01-01T00:00:00Z',
          updatedAt: '2024-01-01T00:00:00Z',
        },
      ],
      reviewers: [
        { id: 'rev-1', name: 'Doctor Zhang', role: 'medical-officer', department: 'Medical' },
        { id: 'rev-2', name: 'Compliance Li', role: 'compliance-officer', department: 'Compliance' },
        { id: 'rev-3', name: 'Architect Wang', role: 'tech-lead', department: 'Tech' },
        { id: 'rev-4', name: 'PM Chen', role: 'product-manager', department: 'Product' },
        { id: 'rev-5', name: 'Branch Liu', role: 'branch-rep', department: 'Jiangxi' },
        { id: 'rev-7', name: 'Branch Sun', role: 'branch-rep', department: 'Zhejiang' },
      ],
      currentWorkflow: null,
    })
  })

  it('renders workflow list header', () => {
    render(<ReviewWorkflowList />)
    expect(screen.getByText('需求评审工作流')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /提交需求/ })).toBeInTheDocument()
  })

  it('renders preset workflows', () => {
    render(<ReviewWorkflowList />)

    expect(screen.getAllByText('Test Workflow Alpha').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Test Workflow Beta').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Test Workflow Gamma').length).toBeGreaterThanOrEqual(1)
  })

  it('shows workflow status badges', () => {
    render(<ReviewWorkflowList />)

    expect(screen.getAllByText('进行中').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('已通过').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('需修改').length).toBeGreaterThanOrEqual(1)
  })

  it('shows workflow metadata', () => {
    render(<ReviewWorkflowList />)

    expect(screen.getByText(/提交人: Test Submitter/)).toBeInTheDocument()
    expect(screen.getByText(/提交人: Beta Submitter/)).toBeInTheDocument()
    expect(screen.getByText(/提交人: Gamma Submitter/)).toBeInTheDocument()
  })

  it('shows filter buttons', () => {
    render(<ReviewWorkflowList />)

    expect(screen.getByRole('button', { name: '全部' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '进行中' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '待处理' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '已通过' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '已驳回' })).toBeInTheDocument()
  })

  it('changes active filter on click', () => {
    render(<ReviewWorkflowList />)

    // Initially '全部' is active and all workflows visible
    expect(screen.getAllByText('Test Workflow Alpha').length).toBeGreaterThanOrEqual(1)

    // Click approved filter
    const approvedFilter = screen.getByRole('button', { name: '已通过' })
    fireEvent.click(approvedFilter)

    // Component should still render without error
    expect(screen.getByText('需求评审工作流')).toBeInTheDocument()
    expect(approvedFilter).toBeInTheDocument()
  })

  it('navigates to workflow detail on click', () => {
    render(<ReviewWorkflowList />)

    const buttons = screen.getAllByRole('button')
    const targetBtn = buttons.find(b => b.textContent?.includes('Test Workflow Alpha') && b.textContent?.includes('条评审'))
    expect(targetBtn).toBeDefined()
    fireEvent.click(targetBtn!)

    expect(screen.getByText('← 返回列表')).toBeInTheDocument()
    expect(screen.getByText('评审记录')).toBeInTheDocument()
  })

  it('returns to list from detail view', () => {
    render(<ReviewWorkflowList />)

    const buttons = screen.getAllByRole('button')
    const targetBtn = buttons.find(b => b.textContent?.includes('Test Workflow Alpha') && b.textContent?.includes('条评审'))
    fireEvent.click(targetBtn!)
    expect(screen.getByText('← 返回列表')).toBeInTheDocument()

    fireEvent.click(screen.getByText('← 返回列表'))
    expect(screen.getByText('需求评审工作流')).toBeInTheDocument()
  })

  it('shows comments in detail view', () => {
    render(<ReviewWorkflowList />)

    const buttons = screen.getAllByRole('button')
    const targetBtn = buttons.find(b => b.textContent?.includes('Test Workflow Alpha') && b.textContent?.includes('条评审'))
    fireEvent.click(targetBtn!)

    expect(screen.getByText('Initial comment text')).toBeInTheDocument()
  })

  it('shows stage progress in detail view', () => {
    render(<ReviewWorkflowList />)

    const buttons = screen.getAllByRole('button')
    const targetBtn = buttons.find(b => b.textContent?.includes('Test Workflow Alpha') && b.textContent?.includes('条评审'))
    fireEvent.click(targetBtn!)

    expect(screen.getByText('草稿')).toBeInTheDocument()
    expect(screen.getByText('医务审核')).toBeInTheDocument()
    expect(screen.getByText('合规审核')).toBeInTheDocument()
    expect(screen.getByText('技术评审')).toBeInTheDocument()
    expect(screen.getByText('分院评估')).toBeInTheDocument()
  })

  it('shows action buttons for current stage approver', () => {
    render(<ReviewWorkflowList />)

    const buttons = screen.getAllByRole('button')
    const targetBtn = buttons.find(b => b.textContent?.includes('Test Workflow Alpha') && b.textContent?.includes('条评审'))
    fireEvent.click(targetBtn!)

    expect(screen.getByRole('button', { name: /通过/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /需修改/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /驳回/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /添加评论/ })).toBeInTheDocument()
  })

  it('does not show action buttons for non-approver', () => {
    render(<ReviewWorkflowList />)

    const buttons = screen.getAllByRole('button')
    const targetBtn = buttons.find(b => b.textContent?.includes('Test Workflow Gamma') && b.textContent?.includes('条评审'))
    fireEvent.click(targetBtn!)

    expect(screen.queryByRole('button', { name: /通过/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /需修改/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /驳回/ })).not.toBeInTheDocument()
  })

  it('does not show action buttons for approved workflow', () => {
    render(<ReviewWorkflowList />)

    const buttons = screen.getAllByRole('button')
    const targetBtn = buttons.find(b => b.textContent?.includes('Test Workflow Beta') && b.textContent?.includes('条评审'))
    fireEvent.click(targetBtn!)

    expect(screen.queryByRole('button', { name: /通过/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /驳回/ })).not.toBeInTheDocument()
  })

  it('can add a comment via textarea', () => {
    render(<ReviewWorkflowList />)

    const buttons = screen.getAllByRole('button')
    const targetBtn = buttons.find(b => b.textContent?.includes('Test Workflow Alpha') && b.textContent?.includes('条评审'))
    fireEvent.click(targetBtn!)

    const textarea = screen.getByPlaceholderText('输入评审意见...')
    fireEvent.change(textarea, { target: { value: 'New comment text' } })

    expect(textarea).toHaveValue('New comment text')

    const addCommentButton = screen.getByRole('button', { name: /添加评论/ })
    expect(addCommentButton).toBeInTheDocument()
  })

  it('calls prompt on reject', () => {
    const promptSpy = vi.spyOn(window, 'prompt').mockReturnValue('Not compliant')

    render(<ReviewWorkflowList />)

    const buttons = screen.getAllByRole('button')
    const targetBtn = buttons.find(b => b.textContent?.includes('Test Workflow Alpha') && b.textContent?.includes('条评审'))
    fireEvent.click(targetBtn!)

    const rejectButton = screen.getByRole('button', { name: /驳回/ })
    fireEvent.click(rejectButton)

    expect(promptSpy).toHaveBeenCalledWith('请输入驳回原因：')

    promptSpy.mockRestore()
  })

  it('calls prompt on request revision', () => {
    const promptSpy = vi.spyOn(window, 'prompt').mockReturnValue('Needs more info')

    render(<ReviewWorkflowList />)

    const buttons = screen.getAllByRole('button')
    const targetBtn = buttons.find(b => b.textContent?.includes('Test Workflow Alpha') && b.textContent?.includes('条评审'))
    fireEvent.click(targetBtn!)

    const revisionButton = screen.getByRole('button', { name: /需修改/ })
    fireEvent.click(revisionButton)

    expect(promptSpy).toHaveBeenCalledWith('请输入修改建议：')

    promptSpy.mockRestore()
  })

  it('shows reviewer info in comments', () => {
    render(<ReviewWorkflowList />)

    const buttons = screen.getAllByRole('button')
    const targetBtn = buttons.find(b => b.textContent?.includes('Test Workflow Gamma') && b.textContent?.includes('条评审'))
    fireEvent.click(targetBtn!)

    expect(screen.getByText('Reviewer Two')).toBeInTheDocument()
    expect(screen.getByText('Compliance Officer')).toBeInTheDocument()
  })

  it('shows comment count in list view', () => {
    render(<ReviewWorkflowList />)

    expect(screen.getAllByText('1 条评审').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('0 条评审').length).toBeGreaterThanOrEqual(1)
  })

  it('shows "待我处理" section for assigned workflows', () => {
    render(<ReviewWorkflowList />)

    expect(screen.getByText(/待我处理/)).toBeInTheDocument()
  })
})
