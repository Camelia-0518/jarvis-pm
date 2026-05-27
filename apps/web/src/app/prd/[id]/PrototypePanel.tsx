"use client";

interface Props {
  html: string;
  device: "desktop" | "tablet" | "mobile";
  onDeviceChange: (device: "desktop" | "tablet" | "mobile") => void;
  onClose: () => void;
}

export default function PrototypePanel({ html, device, onDeviceChange, onClose }: Props) {
  if (!html) return null;

  return (
    <div className="flex flex-col border-b border-slate-200 dark:border-slate-700" style={{ height: '50%' }}>
      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50 px-4 py-2 dark:border-slate-700 dark:bg-slate-900">
        <span className="text-sm font-medium text-slate-700 dark:text-slate-300">原型预览</span>
        <div className="flex items-center gap-2">
          <div className="flex rounded-md border border-slate-200 bg-white dark:border-slate-600 dark:bg-slate-800">
            {[
              { key: 'desktop' as const, label: '桌面' },
              { key: 'tablet' as const, label: '平板' },
              { key: 'mobile' as const, label: '手机' },
            ].map((d) => (
              <button
                key={d.key}
                onClick={() => onDeviceChange(d.key)}
                className={`px-2.5 py-1 text-xs font-medium transition-colors ${
                  device === d.key
                    ? 'bg-sky-50 text-sky-700 dark:bg-sky-900/30 dark:text-sky-400'
                    : 'text-slate-500 hover:text-slate-700 dark:text-slate-400'
                }`}
              >
                {d.label}
              </button>
            ))}
          </div>
          <button
            onClick={onClose}
            className="rounded p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-600 dark:hover:bg-slate-700"
          >
            ✕
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-auto bg-slate-100 p-4 dark:bg-slate-900">
        <div
          className="mx-auto overflow-hidden rounded-lg bg-white shadow-lg"
          style={{
            width: device === 'mobile' ? 375 : device === 'tablet' ? 768 : '100%',
            height: device === 'mobile' ? 667 : device === 'tablet' ? 1024 : '100%',
            maxWidth: '100%',
          }}
        >
          <iframe
            srcDoc={html}
            title="Prototype Preview"
            className="h-full w-full border-0"
            sandbox="allow-scripts allow-same-origin"
          />
        </div>
      </div>
    </div>
  );
}
