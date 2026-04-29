"use client";

import { useRef, useCallback, KeyboardEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Textarea";
import { ModeChips } from "./ModeChips";
import { useChatStore } from "@/stores/chatStore";
import { useChatSubmit } from "@/hooks/useChatSubmit";

const QUICK_TEMPLATES = [
  { label: "短线选股", query: "今天适合做什么方向？给我 5 只短线观察股" },
  { label: "波段候选", query: "找 5 只未来 2 到 4 周值得跟踪的趋势股" },
  { label: "估值筛选", query: "筛几只估值不贵、财务质量不错的 A 股" },
];

export function ChatComposer() {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { isSubmitting, submitMessage } = useChatSubmit();

  const { inputValue, setInputValue } = useChatStore();

  const handleSubmit = useCallback(async () => {
    await submitMessage(inputValue);
  }, [inputValue, submitMessage]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  return (
    <div className="space-y-4 border-t border-border/60 bg-gradient-to-t from-card/90 to-card px-5 py-4">
      <ModeChips />

      <div className="relative group">
        <div className="absolute -inset-0.5 rounded-[24px] bg-gradient-to-r from-primary/18 via-accent/10 to-primary/8 blur opacity-0 transition duration-300 group-focus-within:opacity-100" />
        <div className="relative flex gap-3 rounded-[24px] border border-border/55 bg-muted/28 p-2.5 shadow-neo">
          <Textarea
            ref={textareaRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入你的问题，例如：我目前持有通富微电，今天该怎么看持仓和财报？"
            className="min-h-[72px] max-h-[180px] resize-none border-0 bg-transparent p-2 text-[15px] leading-7 shadow-none focus:ring-0 focus:shadow-none"
            disabled={isSubmitting}
          />
          <Button
            onClick={() => void handleSubmit()}
            disabled={!inputValue.trim() || isSubmitting}
            className="h-auto self-end rounded-2xl px-6 shadow-glow"
            size="lg"
          >
            {isSubmitting ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                <span className="text-xs">分析中</span>
              </span>
            ) : (
              <span className="text-sm">开始分析</span>
            )}
          </Button>
        </div>
      </div>

      <div className="flex items-center gap-2 px-1">
        <span className="text-[11px] text-muted-foreground/50">快捷模板</span>
        <div className="flex gap-1.5 flex-wrap">
          {QUICK_TEMPLATES.map((tpl) => (
            <button
              key={tpl.label}
              onClick={() => setInputValue(tpl.query)}
              disabled={isSubmitting}
              className="rounded-full border border-transparent bg-muted/50 px-3.5 py-1.5 text-[12px] text-muted-foreground transition-all duration-200 hover:border-primary/20 hover:bg-primary/10 hover:text-primary disabled:opacity-50"
            >
              {tpl.label}
            </button>
          ))}
        </div>
      </div>

      <p className="text-center text-[11px] text-muted-foreground/42">
        Enter 发送 · Shift + Enter 换行 · 支持上下文追问与候选池联动
      </p>
    </div>
  );
}
