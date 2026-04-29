"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useMetaStatus } from "@/hooks/useMetaStatus";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "工作台", icon: "⌨️" },
  { href: "/templates", label: "模板中心", icon: "📝" },
  { href: "/watchlist", label: "候选池", icon: "⭐" },
  { href: "/portfolio", label: "持仓账户", icon: "💼" },
  { href: "/monitor", label: "盯盘区", icon: "📡" },
  { href: "/reports", label: "日报中心", icon: "📰" },
  { href: "/settings", label: "设置", icon: "⚙️" },
];

export function Sidebar() {
  const pathname = usePathname();
  const { status, isError } = useMetaStatus();

  return (
    <aside className="w-64 border-r border-border/60 bg-card/82 backdrop-blur-sm flex flex-col h-full relative overflow-hidden">
      <div className="absolute inset-0 grid-bg opacity-50" />

      <div className="relative p-5 border-b border-border/50">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-primary/95 via-primary to-accent/85 flex items-center justify-center text-slate-950 font-semibold text-sm shadow-glow">
            财
          </div>
          <div>
            <h1 className="font-display text-lg font-semibold text-foreground/92">
              个人理财助手
            </h1>
            <p className="mt-0.5 text-[11px] text-muted-foreground">
              A 股研究与问财辅助台
            </p>
          </div>
        </div>
      </div>

      <nav className="relative flex-1 p-3 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "relative overflow-hidden rounded-2xl px-4 py-3 text-sm font-medium transition-all duration-200 flex items-center gap-3",
                isActive
                  ? "bg-gradient-to-r from-primary/20 to-primary/5 text-foreground"
                  : "text-muted-foreground hover:bg-muted/45 hover:text-foreground"
              )}
            >
              {isActive && (
                <div className="absolute inset-0 bg-gradient-to-r from-primary/6 to-transparent" />
              )}
              <span className="text-base relative z-10">{item.icon}</span>
              <span className="relative z-10">{item.label}</span>
              {isActive && (
                <span className="ml-auto h-2 w-2 rounded-full bg-primary shadow-glow" />
              )}
            </Link>
          );
        })}
      </nav>

      <div className="relative mx-3 mb-3 rounded-2xl border border-border/40 bg-muted/26 p-4">
        <div className="flex items-center gap-2.5">
          <span
            className={cn(
              "w-2.5 h-2.5 rounded-full shadow-sm",
              isError
                ? "bg-red-500 shadow-red-500/50"
                : "bg-primary shadow-primary/50 animate-glow-pulse"
            )}
          />
          <span className="text-xs text-muted-foreground">
            {isError ? "接口异常" : `已连接 · ${status?.skill_count ?? "-"} 个 Skills`}
          </span>
        </div>
        {!isError && status?.llm_enabled && (
          <div className="mt-2 pt-2 border-t border-border/20">
            <div className="text-[11px] text-muted-foreground/70">
              LLM: {status.llm_chain_mode ?? "ENABLED"} · {status.llm_agent_runtime ?? "-"}
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
