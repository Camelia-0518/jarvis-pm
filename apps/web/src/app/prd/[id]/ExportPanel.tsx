"use client";

interface Props {
  onExport: (format: string) => void;
  onClose: () => void;
}

const EXPORT_FORMATS = [
  { id: "markdown", name: "Markdown", icon: "📝" },
  { id: "json", name: "JSON", icon: "📄" },
  { id: "pdf", name: "PDF", icon: "📕" },
  { id: "docx", name: "Word", icon: "📘" },
];

export default function ExportPanel({ onExport, onClose }: Props) {
  return (
    <div className="mb-6 rounded-lg border border-emerald-200 bg-emerald-50/50 p-4 dark:border-emerald-800 dark:bg-emerald-900/20">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-medium text-emerald-900 dark:text-emerald-100">导出文档</h3>
        <button onClick={onClose} className="text-emerald-600 hover:text-emerald-800 transition-colors duration-150">✕</button>
      </div>
      <div className="space-y-2">
        {EXPORT_FORMATS.map((format) => (
          <button
            key={format.id}
            onClick={() => onExport(format.id)}
            className="flex w-full items-center gap-3 rounded-lg bg-white px-3 py-2 text-left transition-colors duration-150 hover:bg-emerald-100 dark:bg-slate-800 dark:hover:bg-emerald-900/30"
          >
            <span>{format.icon}</span>
            <span className="text-sm text-slate-700 dark:text-slate-300">导出为 {format.name}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
