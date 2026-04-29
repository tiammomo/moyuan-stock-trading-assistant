"use client";

import { usePathname } from "next/navigation";
import { ThemeToggle } from "@/components/ui/ThemeToggle";

const pageTitles: Record<string, string> = {
  "/": "研究工作台",
  "/templates": "模板中心",
  "/watchlist": "候选池",
  "/portfolio": "持仓账户",
  "/monitor": "盯盘区",
  "/settings": "系统设置",
};

export function Header() {
  const pathname = usePathname();
  const title = pageTitles[pathname] || "UNKNOWN";

  return (
    <header className="h-14 border-b border-border/60 bg-card/70 px-5 backdrop-blur-sm flex items-center justify-between">
      <div className="flex items-center gap-3">
        <span className="text-[11px] uppercase tracking-[0.24em] text-muted-foreground/50">Desk</span>
        <h2 className="font-display text-lg font-semibold text-foreground/86">
          {title}
        </h2>
        <span className="text-accent">•</span>
      </div>
      <div className="flex items-center gap-4">
        <ThemeToggle />
        <div className="flex items-center gap-2 text-[11px] text-muted-foreground/60">
          <span>系统就绪</span>
          <span className="text-primary">●</span>
        </div>
      </div>
    </header>
  );
}
