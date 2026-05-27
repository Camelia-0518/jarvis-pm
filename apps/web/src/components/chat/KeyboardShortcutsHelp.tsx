'use client';

import { Keyboard, X } from 'lucide-react';
import { Button } from '@/components/ui-from-ai-pm/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui-from-ai-pm/dialog';

interface ShortcutItemProps {
  keys: string[];
  description: string;
}

function ShortcutItem({ keys, description }: ShortcutItemProps) {
  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-sm text-muted-foreground">{description}</span>
      <div className="flex items-center gap-1">
        {keys.map((key, i) => (
          <kbd
            key={i}
            className="px-2 py-1 text-xs font-mono bg-muted rounded border"
          >
            {key}
          </kbd>
        ))}
      </div>
    </div>
  );
}

export function KeyboardShortcutsHelp() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" className="h-8 w-8">
          <Keyboard className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Keyboard className="h-4 w-4" />
            键盘快捷键
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <h4 className="text-sm font-medium mb-2">聊天</h4>
            <div className="space-y-1">
              <ShortcutItem keys={['Ctrl', 'Enter']} description="发送消息" />
              <ShortcutItem keys={['Ctrl', 'N']} description="新建对话" />
              <ShortcutItem keys={['Ctrl', 'L']} description="聚焦输入框" />
            </div>
          </div>

          <div>
            <h4 className="text-sm font-medium mb-2">编辑器</h4>
            <div className="space-y-1">
              <ShortcutItem keys={['Ctrl', 'B']} description="粗体" />
              <ShortcutItem keys={['Ctrl', 'I']} description="斜体" />
              <ShortcutItem keys={['Ctrl', 'S']} description="保存" />
              <ShortcutItem keys={['Ctrl', 'Z']} description="撤销" />
              <ShortcutItem keys={['Ctrl', 'Shift', 'Z']} description="重做" />
            </div>
          </div>

          <div>
            <h4 className="text-sm font-medium mb-2">导航</h4>
            <div className="space-y-1">
              <ShortcutItem keys={['Ctrl', 'K']} description="打开搜索" />
              <ShortcutItem keys={['Ctrl', ',']} description="打开设置" />
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default KeyboardShortcutsHelp;
