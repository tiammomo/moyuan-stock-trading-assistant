"use client";

import { cn } from "@/lib/utils";
import type { ChatMode } from "@/types";
import { useChatStore } from "@/stores/chatStore";

const MODES: { value: ChatMode; label: string; icon: string; gradient: string; active: string }[] = [
  {
    value: "short_term",
    label: "短线",
    icon: "⚡",
    gradient: "from-amber-500/12 to-amber-500/5",
    active: "bg-gradient-to-r from-amber-500 to-amber-400 text-slate-950 shadow-amber-500/20",
  },
  {
    value: "swing",
    label: "波段",
    icon: "📈",
    gradient: "from-emerald-500/12 to-emerald-500/5",
    active: "bg-gradient-to-r from-emerald-500 to-emerald-400 text-slate-950 shadow-emerald-500/20",
  },
  {
    value: "mid_term_value",
    label: "中线价值",
    icon: "🎯",
    gradient: "from-sky-500/12 to-sky-500/5",
    active: "bg-gradient-to-r from-sky-500 to-sky-400 text-slate-950 shadow-sky-500/20",
  },
  {
    value: "generic_data_query",
    label: "通用",
    icon: "🔍",
    gradient: "from-gray-500/10 to-gray-500/5",
    active: "bg-gradient-to-r from-gray-500 to-gray-400 text-white shadow-gray-500/25",
  },
];

export function ModeChips() {
  const { modeHint, autoDetectedMode, setModeHint } = useChatStore();
  const displayMode = modeHint || autoDetectedMode;
  const isAutoDetected = !!autoDetectedMode && !modeHint;

  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-muted-foreground font-medium">模式:</span>
      <div className="flex gap-1.5">
        {MODES.map((m) => {
          const isSelected = displayMode === m.value;
          const isThisAuto = autoDetectedMode === m.value && !modeHint;

          return (
            <button
              key={m.value}
              onClick={() => setModeHint(modeHint === m.value ? null : m.value)}
              className={cn(
                "relative px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200",
                "flex items-center gap-1.5",
                isSelected
                  ? cn(m.active, "shadow-md -translate-y-0.5")
                  : cn(
                      "bg-gradient-to-r border border-transparent",
                      m.gradient,
                      "text-muted-foreground hover:text-foreground hover:shadow-sm",
                      modeHint === m.value && "border-primary/20"
                    )
              )}
            >
              <span>{m.icon}</span>
              <span>{m.label}</span>
              {isThisAuto && (
                <span className="ml-0.5 text-[10px] opacity-70">(自动)</span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
