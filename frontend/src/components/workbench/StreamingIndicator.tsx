"use client";

import { cn, STATUS_LABELS } from "@/lib/utils";
import type { ChatResponseStatus } from "@/types/common";
import { useChatStore } from "@/stores/chatStore";

const STATUS_CONFIG: Record<
  ChatResponseStatus,
  { color: string; animation: boolean }
> = {
  idle: { color: "bg-gray-400", animation: false },
  analyzing: { color: "bg-blue-500", animation: true },
  running_skills: { color: "bg-blue-500", animation: true },
  partial_ready: { color: "bg-yellow-500", animation: true },
  completed: { color: "bg-green-500", animation: false },
  failed: { color: "bg-red-500", animation: false },
};

export function StreamingIndicator() {
  const { streamingStatus } = useChatStore();
  const config = STATUS_CONFIG[streamingStatus];

  if (streamingStatus === "idle") return null;

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-muted/50 rounded-lg">
      <span
        className={cn(
          "w-2 h-2 rounded-full",
          config.color,
          config.animation && "animate-pulse"
        )}
      />
      <span className="text-xs text-muted-foreground">
        {STATUS_LABELS[streamingStatus]}
      </span>
    </div>
  );
}
