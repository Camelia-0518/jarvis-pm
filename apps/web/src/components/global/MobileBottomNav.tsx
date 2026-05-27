"use client";

import { usePathname, useRouter } from "next/navigation";

const NAV_ITEMS = [
  { path: "/dashboard", label: "工作台", icon: "◻" },
  { path: "/prd", label: "PRD", icon: "▤" },
  { path: "/delivery", label: "交付", icon: "▦" },
  { path: "/workspace", label: "工作区", icon: "⬡" },
];

export default function MobileBottomNav() {
  const pathname = usePathname();
  const router = useRouter();

  // Only show on mobile
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 md:hidden">
      <div className="flex items-center justify-around">
        {NAV_ITEMS.map((item) => {
          const isActive =
            pathname === item.path || pathname.startsWith(item.path + "/");
          return (
            <button
              key={item.path}
              onClick={() => router.push(item.path)}
              className={`flex flex-col items-center py-2 px-3 min-w-[64px] min-h-[48px] ${
                isActive
                  ? "text-sky-600 dark:text-sky-400"
                  : "text-slate-400 dark:text-slate-500"
              }`}
            >
              <span className="text-xl">{item.icon}</span>
              <span className="text-xs mt-0.5">{item.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
