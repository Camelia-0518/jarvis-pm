"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useMemo, useState, useEffect } from "react";
import WorkspaceSwitcher from "./WorkspaceSwitcher";
import { usePermission } from "@/hooks/usePermission";

const NAV_ITEMS = [
  { href: "/dashboard", label: "工作台", minRole: null as "viewer" | null },
  { href: "/workspace", label: "写PRD", minRole: "viewer" as const },
  { href: "/delivery", label: "交付中心", minRole: "viewer" as const },
  { href: "/health", label: "健康度", minRole: "viewer" as const },
  { href: "/assets", label: "资产中心", minRole: "viewer" as const },
  { href: "/workflow", label: "工作流", minRole: "editor" as const },
  { href: "/audit", label: "审计日志", minRole: "admin" as const },
  { href: "/jobs", label: "任务中心", minRole: "admin" as const },
  { href: "/settings/workspace", label: "设置", minRole: "admin" as const },
  { href: "/system", label: "系统", minRole: "admin" as const },
];

interface Props {
  /** Right-side actions (buttons, user avatar, etc.) */
  children?: React.ReactNode;
}

export default function NavHeader({ children }: Props) {
  const pathname = usePathname();
  const canEdit = usePermission("editor");
  const canAdmin = usePermission("admin");
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);

  const visibleItems = useMemo(() => {
    // Before hydration, show all items to match server render
    if (!mounted) return NAV_ITEMS;
    return NAV_ITEMS.filter((item) => {
      if (!item.minRole) return true;
      if (item.minRole === "admin") return canAdmin;
      if (item.minRole === "editor") return canEdit;
      return true;
    });
  }, [canEdit, canAdmin, mounted]);

  const linkClass = (href: string) =>
    href === pathname
      ? "text-sm font-medium text-sky-600"
      : "text-sm font-medium text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-100";

  return (
    <header className="border-b bg-white dark:bg-slate-950">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2 flex-shrink-0">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-600 text-white font-bold">
              J
            </div>
            <span className="text-xl font-semibold text-slate-900 dark:text-white hidden sm:inline">
              Jarvis PM
            </span>
          </Link>
          <WorkspaceSwitcher />
          <nav className="hidden lg:flex items-center gap-4">
            {visibleItems.map((item) => (
              <Link key={item.href} href={item.href} className={linkClass(item.href)}>
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-3 md:gap-4">
          {children}
        </div>
      </div>
    </header>
  );
}
