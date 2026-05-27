"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/dashboard", label: "工作台" },
  { href: "/workspace", label: "写PRD" },
  { href: "/delivery", label: "交付中心" },
  { href: "/templates", label: "模板管理" },
  { href: "/battle", label: "需求Battle" },
  { href: "/workflow", label: "工作流" },
  { href: "/skills", label: "技能广场" },
  { href: "/prompts", label: "提示词" },
];

interface Props {
  /** Right-side actions (buttons, user avatar, etc.) */
  children?: React.ReactNode;
}

export default function NavHeader({ children }: Props) {
  const pathname = usePathname();

  const linkClass = (href: string) =>
    href === pathname
      ? "text-sm font-medium text-sky-600"
      : "text-sm font-medium text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-100";

  return (
    <header className="border-b bg-white dark:bg-slate-950">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-8">
          <Link href="/" className="flex items-center gap-2 flex-shrink-0">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-600 text-white font-bold">
              J
            </div>
            <span className="text-xl font-semibold text-slate-900 dark:text-white">
              Jarvis PM
            </span>
          </Link>
          <nav className="hidden md:flex items-center gap-4">
            {NAV_ITEMS.map((item) => (
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
