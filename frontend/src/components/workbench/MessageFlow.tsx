"use client";

import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { cn, MODE_LABELS, MODE_COLORS } from "@/lib/utils";
import { useChatStore } from "@/stores/chatStore";
import { useChatStream } from "@/hooks/useChatStream";
import { Badge } from "@/components/ui/Badge";
import type { ChatMessageRecord } from "@/types/session";
import type { ChatRequest } from "@/types/chat";

const STATUS_TEXT: Record<string, string> = {
  analyzing: "ANALYZING_QUERY...",
  running_skills: "EXECUTING_SKILLS...",
  partial_ready: "PROCESSING_RESULTS...",
};

const QUICK_START_PROMPTS = [
  "今天适合做什么方向？",
  "给我 5 只短线观察股",
  "帮我看一只股票的财报和 K 线",
  "我目前持有的股票今天怎么处理",
];

export function MessageFlow() {
  const queryClient = useQueryClient();
  const { messages, currentSessionId, modeHint, setInputValue } = useChatStore();
  const bottomRef = useRef<HTMLDivElement>(null);
  const { sendChat, streamingState } = useChatStream({
    onComplete: (response) => {
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
      queryClient.invalidateQueries({ queryKey: ["session", response.session_id] });
    },
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const isSubmitting = streamingState === "connecting" || streamingState === "streaming";

  const handleQuickStart = async (message: string) => {
    if (isSubmitting) return;
    setInputValue("");
    const request: ChatRequest = {
      session_id: currentSessionId,
      message,
      mode_hint: modeHint,
      stream: true,
    };
    await sendChat(request);
  };

  if (messages.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto px-8 py-10">
        <div className="mx-auto w-full max-w-6xl">
          <div className="rounded-[32px] border border-border/50 bg-card/78 p-7 shadow-neo">
            <div className="text-[12px] uppercase tracking-[0.24em] text-muted-foreground/56">
              Quick Start
            </div>
            <div className="mt-3 max-w-3xl font-display text-[32px] leading-[1.45] text-foreground/92">
              直接开始一轮新的问财分析
            </div>
            <p className="mt-4 max-w-4xl text-[15px] leading-8 text-muted-foreground">
              点击下面任一问题会直接发起问答。适合快速进入市场方向、短线观察股、财报与 K 线、当前持仓处理这几类高频场景。
            </p>
            <div className="mt-6 grid gap-3 md:grid-cols-2">
              {QUICK_START_PROMPTS.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  disabled={isSubmitting}
                  onClick={() => void handleQuickStart(suggestion)}
                  className={cn(
                    "rounded-2xl border border-border/50 bg-muted/32 px-5 py-4 text-left text-[15px] leading-7 text-muted-foreground transition-all",
                    "hover:border-primary/30 hover:bg-primary/8 hover:text-primary",
                    "disabled:cursor-not-allowed disabled:opacity-60"
                  )}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessageRecord }) {
  const isUser = message.role === "user";
  const isAnalyzing = !isUser && !message.content && message.status && message.status !== "idle";
  const statusText = message.status ? STATUS_TEXT[message.status] : null;
  const resultCardCount = message.result_snapshot?.cards?.length ?? 0;
  const factCount = message.result_snapshot?.facts?.length ?? 0;
  const followUpCount = message.result_snapshot?.follow_ups?.length ?? 0;
  const showResultMeta = !isUser && !isAnalyzing && (resultCardCount > 0 || factCount > 0 || followUpCount > 0);

  return (
    <div
      className={cn(
        "flex items-end gap-3 animate-slide-up",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      {/* Avatar for assistant */}
      {!isUser && (
        <div className="w-9 h-9 rounded-2xl bg-gradient-to-br from-primary/90 via-primary to-accent/80 flex items-center justify-center text-slate-950 text-[11px] font-semibold shadow-glow flex-shrink-0 font-display">
          理
        </div>
      )}

      <div
        className={cn(
          "max-w-[78%] rounded-[22px] px-4 py-3.5 shadow-neo transition-all duration-200",
          isUser
            ? "bg-gradient-to-br from-primary/22 via-primary/16 to-primary/10 border border-primary/18 text-foreground"
            : "bg-card/95 border border-border/70 hover:border-primary/18"
        )}
      >
        {message.mode && !isUser && (
          <Badge
            variant="outline"
            className={cn("text-[10px] px-2 py-0.5 mb-2.5 tracking-wide", MODE_COLORS[message.mode])}
          >
            {MODE_LABELS[message.mode]}
          </Badge>
        )}

        {/* Content or thinking state */}
        {isAnalyzing ? (
            <div className="space-y-3 min-w-[240px]">
              <div className="flex items-center gap-2 font-mono">
                <span className="text-[10px] text-primary animate-pulse">&gt;</span>
                <span className="text-xs text-muted-foreground">{statusText}</span>
              </div>
            <div className="flex gap-1">
              {[0, 150, 300].map((delay) => (
                <span
                  key={delay}
                  className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce"
                  style={{ animationDelay: `${delay}ms` }}
                />
              ))}
            </div>
            {message.status === "running_skills" && message.skills_used?.length > 0 && (
              <div className="flex flex-wrap gap-1 pt-1 border-t border-border/20">
                {message.skills_used.map((skill, i) => (
                  <span
                    key={i}
                    className={cn(
                      "px-2 py-0.5 rounded text-[10px] font-mono",
                      skill.status === "running"
                        ? "bg-primary/10 text-primary animate-pulse"
                        : "bg-muted/50 text-muted-foreground/70"
                    )}
                  >
                    {skill.name}
                  </span>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="text-[15px] whitespace-pre-wrap leading-8 tracking-[0.01em]">
            {isUser ? (
              <span className="text-foreground">{message.content}</span>
            ) : (
              <span className="text-foreground/92">{message.content}</span>
            )}
          </div>
        )}

        {showResultMeta && (
          <div className="mt-3 flex flex-wrap gap-1.5 border-t border-border/40 pt-2.5">
            {resultCardCount > 0 && (
              <span className="rounded-full border border-border/60 bg-muted/40 px-2.5 py-1 text-[11px] text-muted-foreground">
                {resultCardCount} 张卡片
              </span>
            )}
            {factCount > 0 && (
              <span className="rounded-full border border-border/60 bg-muted/40 px-2.5 py-1 text-[11px] text-muted-foreground">
                {factCount} 条事实
              </span>
            )}
            {followUpCount > 0 && (
              <span className="rounded-full border border-border/60 bg-muted/40 px-2.5 py-1 text-[11px] text-muted-foreground">
                {followUpCount} 个追问
              </span>
            )}
          </div>
        )}
      </div>

      {/* Avatar for user */}
      {isUser && (
        <div className="w-9 h-9 rounded-2xl bg-gradient-to-br from-secondary to-muted flex items-center justify-center text-[11px] font-semibold text-muted-foreground shadow-sm flex-shrink-0">
          我
        </div>
      )}
    </div>
  );
}
