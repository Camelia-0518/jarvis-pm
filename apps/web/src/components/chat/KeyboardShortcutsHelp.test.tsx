import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { KeyboardShortcutsHelp } from './KeyboardShortcutsHelp'

describe('KeyboardShortcutsHelp', () => {
  it('renders dialog trigger button', () => {
    render(<KeyboardShortcutsHelp />)

    const trigger = screen.getByRole('button')
    expect(trigger).toBeInTheDocument()
  })

  it('opens dialog and shows shortcuts when clicked', () => {
    render(<KeyboardShortcutsHelp />)

    const trigger = screen.getByRole('button')
    fireEvent.click(trigger)

    expect(screen.getByText('键盘快捷键')).toBeInTheDocument()
  })

  it('shows chat shortcuts section', () => {
    render(<KeyboardShortcutsHelp />)

    const trigger = screen.getByRole('button')
    fireEvent.click(trigger)

    expect(screen.getByText('聊天')).toBeInTheDocument()
    expect(screen.getByText('发送消息')).toBeInTheDocument()
    expect(screen.getByText('新建对话')).toBeInTheDocument()
    expect(screen.getByText('聚焦输入框')).toBeInTheDocument()
  })

  it('shows editor shortcuts section', () => {
    render(<KeyboardShortcutsHelp />)

    const trigger = screen.getByRole('button')
    fireEvent.click(trigger)

    expect(screen.getByText('编辑器')).toBeInTheDocument()
    expect(screen.getByText('粗体')).toBeInTheDocument()
    expect(screen.getByText('斜体')).toBeInTheDocument()
    expect(screen.getByText('保存')).toBeInTheDocument()
    expect(screen.getByText('撤销')).toBeInTheDocument()
    expect(screen.getByText('重做')).toBeInTheDocument()
  })

  it('shows navigation shortcuts section', () => {
    render(<KeyboardShortcutsHelp />)

    const trigger = screen.getByRole('button')
    fireEvent.click(trigger)

    expect(screen.getByText('导航')).toBeInTheDocument()
    expect(screen.getByText('打开搜索')).toBeInTheDocument()
    expect(screen.getByText('打开设置')).toBeInTheDocument()
  })

  it('displays keyboard shortcut keys', () => {
    render(<KeyboardShortcutsHelp />)

    const trigger = screen.getByRole('button')
    fireEvent.click(trigger)

    // Check for shortcut key labels (using getAllByText for short keys that may appear multiple times)
    expect(screen.getAllByText('Ctrl').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Enter').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('B').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('K').length).toBeGreaterThanOrEqual(1)
  })
})
