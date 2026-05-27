// 键盘快捷键 Hook

import { useEffect, useCallback } from 'react';

export interface ShortcutConfig {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
  meta?: boolean;
  handler: () => void;
  description?: string;
  preventDefault?: boolean;
}

export function useKeyboardShortcuts(shortcuts: ShortcutConfig[]) {
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      for (const shortcut of shortcuts) {
        const keyMatch = event.key.toLowerCase() === shortcut.key.toLowerCase();
        const ctrlMatch = !!shortcut.ctrl === event.ctrlKey;
        const shiftMatch = !!shortcut.shift === event.shiftKey;
        const altMatch = !!shortcut.alt === event.altKey;
        const metaMatch = !!shortcut.meta === event.metaKey;

        if (keyMatch && ctrlMatch && shiftMatch && altMatch && metaMatch) {
          if (shortcut.preventDefault !== false) {
            event.preventDefault();
          }
          shortcut.handler();
          break;
        }
      }
    },
    [shortcuts]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
}

// 聊天相关快捷键
export function createChatShortcuts(config: {
  onSend: () => void;
  onNewConversation: () => void;
  onFocusInput: () => void;
}): ShortcutConfig[] {
  return [
    {
      key: 'n',
      ctrl: true,
      handler: config.onNewConversation,
      description: '新建对话',
    },
    {
      key: 'l',
      ctrl: true,
      handler: config.onFocusInput,
      description: '聚焦输入框',
    },
  ];
}

// 编辑器快捷键
export function createEditorShortcuts(config: {
  onBold: () => void;
  onItalic: () => void;
  onSave: () => void;
  onUndo: () => void;
  onRedo: () => void;
}): ShortcutConfig[] {
  return [
    {
      key: 'b',
      ctrl: true,
      handler: config.onBold,
      description: '粗体',
    },
    {
      key: 'i',
      ctrl: true,
      handler: config.onItalic,
      description: '斜体',
    },
    {
      key: 's',
      ctrl: true,
      handler: config.onSave,
      description: '保存',
    },
    {
      key: 'z',
      ctrl: true,
      handler: config.onUndo,
      description: '撤销',
    },
    {
      key: 'z',
      ctrl: true,
      shift: true,
      handler: config.onRedo,
      description: '重做',
    },
  ];
}

// 导航快捷键
export function createNavigationShortcuts(config: {
  onSearch: () => void;
  onSettings: () => void;
}): ShortcutConfig[] {
  return [
    {
      key: 'k',
      ctrl: true,
      handler: config.onSearch,
      description: '打开搜索',
    },
    {
      key: ',',
      ctrl: true,
      handler: config.onSettings,
      description: '打开设置',
    },
  ];
}

export default useKeyboardShortcuts;
