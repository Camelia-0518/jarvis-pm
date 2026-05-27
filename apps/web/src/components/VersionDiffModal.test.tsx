import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import VersionDiffModal from './VersionDiffModal'

describe('VersionDiffModal', () => {
  const defaultProps = {
    isOpen: true,
    oldVersion: 'v1',
    newVersion: 'v2',
    oldContent: ['line1', 'line2', 'line3'].join('\n'),
    newContent: ['line1', 'line2 modified', 'line3', 'line4'].join('\n'),
    onClose: vi.fn(),
  }

  it('returns null when isOpen is false', () => {
    const { container } = render(<VersionDiffModal {...defaultProps} isOpen={false} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders version comparison header', () => {
    render(<VersionDiffModal {...defaultProps} />)

    expect(screen.getByText('版本对比')).toBeInTheDocument()
    expect(screen.getByText('v1')).toBeInTheDocument()
    expect(screen.getByText('v2')).toBeInTheDocument()
    expect(screen.getByText('→')).toBeInTheDocument()
  })

  it('renders diff statistics', () => {
    render(<VersionDiffModal {...defaultProps} />)

    // old: line1, line2, line3
    // new: line1, line2 modified, line3, line4
    // diff: same(line1), remove(line2), add(line2 modified), same(line3), add(line4)
    expect(screen.getByText('+2')).toBeInTheDocument()
    expect(screen.getByText('−1')).toBeInTheDocument()
    expect(screen.getByText('≈2')).toBeInTheDocument()
  })

  it('renders diff lines with correct markers', () => {
    render(<VersionDiffModal {...defaultProps} />)

    // Same lines
    expect(screen.getByText('line1')).toBeInTheDocument()
    expect(screen.getByText('line3')).toBeInTheDocument()

    // Modified line shows as remove + add
    expect(screen.getAllByText('line2').length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('line2 modified')).toBeInTheDocument()

    // Added line
    expect(screen.getByText('line4')).toBeInTheDocument()
  })

  it('renders legend', () => {
    render(<VersionDiffModal {...defaultProps} />)

    expect(screen.getByText('新增')).toBeInTheDocument()
    expect(screen.getByText('删除')).toBeInTheDocument()
  })

  it('calls onClose when close button clicked', () => {
    const onClose = vi.fn()
    render(<VersionDiffModal {...defaultProps} onClose={onClose} />)

    const closeButton = screen.getByText('✕')
    fireEvent.click(closeButton)

    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('calculates stats correctly for added content', () => {
    render(
      <VersionDiffModal
        isOpen={true}
        oldVersion="v1"
        newVersion="v2"
        oldContent={['a', 'b'].join('\n')}
        newContent={['a', 'b', 'c', 'd'].join('\n')}
        onClose={vi.fn()}
      />
    )

    expect(screen.getByText('+2')).toBeInTheDocument()
    expect(screen.getByText('−0')).toBeInTheDocument()
    expect(screen.getByText('≈2')).toBeInTheDocument()
  })

  it('calculates stats correctly for removed content', () => {
    render(
      <VersionDiffModal
        isOpen={true}
        oldVersion="v1"
        newVersion="v2"
        oldContent={['a', 'b', 'c'].join('\n')}
        newContent="a"
        onClose={vi.fn()}
      />
    )

    expect(screen.getByText('+0')).toBeInTheDocument()
    expect(screen.getByText('−2')).toBeInTheDocument()
    expect(screen.getByText('≈1')).toBeInTheDocument()
  })

  it('handles identical content', () => {
    render(
      <VersionDiffModal
        isOpen={true}
        oldVersion="v1"
        newVersion="v2"
        oldContent="same content"
        newContent="same content"
        onClose={vi.fn()}
      />
    )

    expect(screen.getByText('+0')).toBeInTheDocument()
    expect(screen.getByText('−0')).toBeInTheDocument()
    expect(screen.getByText('≈1')).toBeInTheDocument()
  })

  it('handles empty old content', () => {
    render(
      <VersionDiffModal
        isOpen={true}
        oldVersion="v1"
        newVersion="v2"
        oldContent=""
        newContent={['new line'].join('\n')}
        onClose={vi.fn()}
      />
    )

    // Empty string splits to [''], which diff treats as one removed empty line
    expect(screen.getByText('+1')).toBeInTheDocument()
    expect(screen.getByText('−1')).toBeInTheDocument()
  })
})
