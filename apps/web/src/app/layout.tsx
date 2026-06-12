import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { SkillInitializer } from "@/components/skills/SkillInitializer";
import { AIChatFAB } from "@/components/global/AIChatFAB";
import { GlobalSearch } from "@/components/global/GlobalSearch";
import MobileBottomNav from "@/components/global/MobileBottomNav";
import { Toaster } from "sonner";
import ConfirmDialogProvider from "@/components/ui/ConfirmDialog";
import { WorkspaceInitializer } from "@/components/global/WorkspaceInitializer";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Jarvis PM - AI产品与交付管理平台",
  description: "AI驱动的产品需求文档生成与项目交付管理平台，专为医疗信息化项目优化",
  manifest: "/manifest.json",
  viewport: "width=device-width, initial-scale=1, viewport-fit=cover",
  themeColor: "#0284c7",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="zh-CN"
      className={`${inter.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <ConfirmDialogProvider>
          <WorkspaceInitializer />
          <SkillInitializer />
          <main className="flex-1 pb-16 md:pb-0">{children}</main>
          <MobileBottomNav />
          <GlobalSearch />
          <AIChatFAB />
          <Toaster position="top-center" richColors />
        </ConfirmDialogProvider>
      </body>
    </html>
  );
}
