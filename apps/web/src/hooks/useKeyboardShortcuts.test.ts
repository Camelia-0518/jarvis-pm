import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import {
  useKeyboardShortcuts,
  createChatShortcuts,
  createEditorShortcuts,
  createNavigationShortcuts,
} from './useKeyboardShortcuts'

describe('useKeyboardShortcuts', () => {
  let addEventListenerSpy: ReturnType<typeof vi.spyOn>
  let removeEventListenerSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    addEventListenerSpy = vi.spyOn(window, 'addEventListener')
    removeEventListenerSpy = vi.spyOn(window, 'removeEventListener')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('registers keydown listener on mount', () => {
    renderHook(() => useKeyboardShortcuts([]))
    expect(addEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function))
  })

  it('removes keydown listener on unmount', () => {
    const { unmount } = renderHook(() => useKeyboardShortcuts([]))
    unmount()
    expect(removeEventListenerSpy).toHaveBeenCalledWith('keydown', expect.any(Function))
  })

  it('calls handler when shortcut key matches', () => {
    const handler = vi.fn()
    renderHook(() =>
      useKeyboardShortcuts([{ key: 'a', handler }])
    )

    const keydownHandler = addEventListenerSpy.mock.calls.find(
      (call) => call[0] === 'keydown'
    )?.[1] as EventListener

    keydownHandler(new KeyboardEvent('keydown', { key: 'a' }))
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('calls handler with ctrl modifier', () => {
    const handler = vi.fn()
    renderHook(() =>
      useKeyboardShortcuts([{ key: 's', ctrl: true, handler }])
    )

    const keydownHandler = addEventListenerSpy.mock.calls.find(
      (call) => call[0] === 'keydown'
    )?.[1] as EventListener

    keydownHandler(new KeyboardEvent('keydown', { key: 's', ctrlKey: true }))
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('does not call handler when ctrl modifier missing', () => {
    const handler = vi.fn()
    renderHook(() =>
      useKeyboardShortcuts([{ key: 's', ctrl: true, handler }])
    )

    const keydownHandler = addEventListenerSpy.mock.calls.find(
      (call) => call[0] === 'keydown'
    )?.[1] as EventListener

    keydownHandler(new KeyboardEvent('keydown', { key: 's' }))
    expect(handler).not.toHaveBeenCalled()
  })

  it('calls handler with shift modifier', () => {
    const handler = vi.fn()
    renderHook(() =>
      useKeyboardShortcuts([{ key: 'z', ctrl: true, shift: true, handler }])
    )

    const keydownHandler = addEventListenerSpy.mock.calls.find(
      (call) => call[0] === 'keydown'
    )?.[1] as EventListener

    keydownHandler(new KeyboardEvent('keydown', { key: 'z', ctrlKey: true, shiftKey: true }))
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('calls handler with alt modifier', () => {
    const handler = vi.fn()
    renderHook(() =>
      useKeyboardShortcuts([{ key: 'f4', alt: true, handler }])
    )

    const keydownHandler = addEventListenerSpy.mock.calls.find(
      (call) => call[0] === 'keydown'
    )?.[1] as EventListener

    keydownHandler(new KeyboardEvent('keydown', { key: 'f4', altKey: true }))
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('calls handler with meta modifier', () => {
    const handler = vi.fn()
    renderHook(() =>
      useKeyboardShortcuts([{ key: 'k', meta: true, handler }])
    )

    const keydownHandler = addEventListenerSpy.mock.calls.find(
      (call) => call[0] === 'keydown'
    )?.[1] as EventListener

    keydownHandler(new KeyboardEvent('keydown', { key: 'k', metaKey: true }))
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('is case-insensitive for key matching', () => {
    const handler = vi.fn()
    renderHook(() =>
      useKeyboardShortcuts([{ key: 'A', handler }])
    )

    const keydownHandler = addEventListenerSpy.mock.calls.find(
      (call) => call[0] === 'keydown'
    )?.[1] as EventListener

    keydownHandler(new KeyboardEvent('keydown', { key: 'a' }))
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('prevents default by default', () => {
    const handler = vi.fn()
    renderHook(() =>
      useKeyboardShortcuts([{ key: 's', ctrl: true, handler }])
    )

    const keydownHandler = addEventListenerSpy.mock.calls.find(
      (call) => call[0] === 'keydown'
    )?.[1] as EventListener

    const event = new KeyboardEvent('keydown', { key: 's', ctrlKey: true })
    const preventDefaultSpy = vi.spyOn(event, 'preventDefault')
    keydownHandler(event)
    expect(preventDefaultSpy).toHaveBeenCalledTimes(1)
  })

  it('does not prevent default when preventDefault is false', () => {
    const handler = vi.fn()
    renderHook(() =>
      useKeyboardShortcuts([{ key: 's', ctrl: true, handler, preventDefault: false }])
    )

    const keydownHandler = addEventListenerSpy.mock.calls.find(
      (call) => call[0] === 'keydown'
    )?.[1] as EventListener

    const event = new KeyboardEvent('keydown', { key: 's', ctrlKey: true })
    const preventDefaultSpy = vi.spyOn(event, 'preventDefault')
    keydownHandler(event)
    expect(preventDefaultSpy).not.toHaveBeenCalled()
  })

  it('calls only the first matching handler', () => {
    const handler1 = vi.fn()
    const handler2 = vi.fn()
    renderHook(() =>
      useKeyboardShortcuts([
        { key: 'a', handler: handler1 },
        { key: 'a', handler: handler2 },
      ])
    )

    const keydownHandler = addEventListenerSpy.mock.calls.find(
      (call) => call[0] === 'keydown'
    )?.[1] as EventListener

    keydownHandler(new KeyboardEvent('keydown', { key: 'a' }))
    expect(handler1).toHaveBeenCalledTimes(1)
    expect(handler2).not.toHaveBeenCalled()
  })

  it('does not call handler when extra modifiers are pressed', () => {
    const handler = vi.fn()
    renderHook(() =>
      useKeyboardShortcuts([{ key: 's', ctrl: true, handler }])
    )

    const keydownHandler = addEventListenerSpy.mock.calls.find(
      (call) => call[0] === 'keydown'
    )?.[1] as EventListener

    keydownHandler(new KeyboardEvent('keydown', { key: 's', ctrlKey: true, shiftKey: true }))
    expect(handler).not.toHaveBeenCalled()
  })
})

describe('createChatShortcuts', () => {
  it('returns chat shortcuts config', () => {
    const onSend = vi.fn()
    const onNewConversation = vi.fn()
    const onFocusInput = vi.fn()

    const shortcuts = createChatShortcuts({ onSend, onNewConversation, onFocusInput })

    expect(shortcuts).toHaveLength(2)
    expect(shortcuts[0]).toMatchObject({ key: 'n', ctrl: true, description: '新建对话' })
    expect(shortcuts[1]).toMatchObject({ key: 'l', ctrl: true, description: '聚焦输入框' })

    shortcuts[0].handler()
    expect(onNewConversation).toHaveBeenCalled()

    shortcuts[1].handler()
    expect(onFocusInput).toHaveBeenCalled()
  })
})

describe('createEditorShortcuts', () => {
  it('returns editor shortcuts config', () => {
    const onBold = vi.fn()
    const onItalic = vi.fn()
    const onSave = vi.fn()
    const onUndo = vi.fn()
    const onRedo = vi.fn()

    const shortcuts = createEditorShortcuts({ onBold, onItalic, onSave, onUndo, onRedo })

    expect(shortcuts).toHaveLength(5)
    expect(shortcuts.find((s) => s.key === 'b' && s.ctrl)).toBeDefined()
    expect(shortcuts.find((s) => s.key === 'i' && s.ctrl)).toBeDefined()
    expect(shortcuts.find((s) => s.key === 's' && s.ctrl)).toBeDefined()
    expect(shortcuts.find((s) => s.key === 'z' && s.ctrl && !s.shift)).toBeDefined()
    expect(shortcuts.find((s) => s.key === 'z' && s.ctrl && s.shift)).toBeDefined()

    shortcuts.find((s) => s.key === 'b')!.handler()
    expect(onBold).toHaveBeenCalled()

    shortcuts.find((s) => s.key === 's')!.handler()
    expect(onSave).toHaveBeenCalled()
  })
})

describe('createNavigationShortcuts', () => {
  it('returns navigation shortcuts config', () => {
    const onSearch = vi.fn()
    const onSettings = vi.fn()

    const shortcuts = createNavigationShortcuts({ onSearch, onSettings })

    expect(shortcuts).toHaveLength(2)
    expect(shortcuts[0]).toMatchObject({ key: 'k', ctrl: true, description: '打开搜索' })
    expect(shortcuts[1]).toMatchObject({ key: ',', ctrl: true, description: '打开设置' })

    shortcuts[0].handler()
    expect(onSearch).toHaveBeenCalled()

    shortcuts[1].handler()
    expect(onSettings).toHaveBeenCalled()
  })
})
