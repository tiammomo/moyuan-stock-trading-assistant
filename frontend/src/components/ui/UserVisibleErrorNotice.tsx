"use client";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import type { UserVisibleError } from "@/types/common";

interface UserVisibleErrorNoticeProps {
  error: UserVisibleError;
  compact?: boolean;
  className?: string;
}

const NOTICE_STYLES = {
  warning: {
    container: "border-amber-200/70 bg-amber-50/90 text-amber-900",
    icon: "text-amber-600 bg-amber-100/90",
    tone: "warning" as const,
    label: "降级提示",
    glyph: "!",
  },
  error: {
    container: "border-red-200/70 bg-red-50/90 text-red-900",
    icon: "text-red-600 bg-red-100/90",
    tone: "destructive" as const,
    label: "执行失败",
    glyph: "x",
  },
};

export function UserVisibleErrorNotice({
  error,
  compact = false,
  className,
}: UserVisibleErrorNoticeProps) {
  const style = NOTICE_STYLES[error.severity];

  return (
    <div
      className={cn(
        "rounded-2xl border px-3 py-3 shadow-neo animate-slide-up",
        style.container,
        className
      )}
    >
      <div className="flex items-start gap-3">
        <div
          className={cn(
            "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[12px] font-semibold uppercase",
            style.icon
          )}
        >
          {style.glyph}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <div className="text-sm font-semibold leading-6">{error.title}</div>
            <Badge variant={style.tone} className="text-[10px]">
              {style.label}
            </Badge>
            {error.retryable && (
              <Badge variant="outline" className="border-current/20 bg-white/60 text-[10px] text-current">
                可重试
              </Badge>
            )}
          </div>
          <p className={cn("mt-1 whitespace-pre-wrap text-sm leading-6", compact ? "text-[13px]" : "")}>
            {error.message}
          </p>
          {!compact && error.retryable && (
            <p className="mt-2 text-xs text-current/70">
              可以稍后重试，或补充更具体的股票、时间范围、筛选条件后再发起。
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
