"use client";

import { useState } from "react";
import { useChatStore } from "@/stores/chatStore";
import { useUIStore } from "@/stores/uiStore";
import { useWatchlist } from "@/hooks/useWatchlist";
import { cn } from "@/lib/utils";
import { ResultTable } from "@/components/results/ResultTable";
import { ResultCards } from "@/components/results/ResultCards";
import { ResultSummary } from "@/components/results/ResultSummary";
import { SkillTracePanel } from "./SkillTracePanel";
import { FollowUpSuggestions } from "./FollowUpSuggestions";
import { Button } from "@/components/ui/Button";
import type { JsonValue, ChatMode } from "@/types/common";
import type { WatchBucket } from "@/types/common";

type Tab = "overview" | "skills" | "followups";

const TAB_CONFIG: Record<Tab, { label: string; icon: string }> = {
  overview: { label: "结果概览", icon: "📋" },
  skills: { label: "Skills", icon: "⚡" },
  followups: { label: "追问", icon: "💬" },
};

export function ResultPanel() {
  const [activeTab, setActiveTab] = useState<Tab>("overview");
  const [watchlistFeedback, setWatchlistFeedback] = useState<string | null>(null);
  const { currentResult, partialSummary, streamingStatus, messages } = useChatStore();
  const { resultViewMode, setResultViewMode } = useUIStore();
  const { createItemAsync } = useWatchlist();

  const latestAssistantMessage = [...messages].reverse().find((m) => m.role === "assistant");
  const skills = latestAssistantMessage?.skills_used || [];
  const followUps = currentResult?.follow_ups || [];

  const tabs: Tab[] = ["overview", "skills", "followups"];
  const tabCounts = {
    overview: 0,
    skills: skills.length,
    followups: followUps.length,
  };

  const priorityCardTypes = new Set(["operation_guidance", "multi_horizon_analysis", "portfolio_context"]);
  const actionCards =
    currentResult?.cards?.filter(
      (card) => priorityCardTypes.has(card.type) || card.title === "财报与基本面"
    ) || [];
  const secondaryCards =
    currentResult?.cards?.filter(
      (card) => !(priorityCardTypes.has(card.type) || card.title === "财报与基本面")
    ) || [];
  const hasResult = currentResult || partialSummary;

  const handleFavorite = async (row: Record<string, JsonValue>) => {
    const symbol = String(row["代码"] || "").trim();
    const name = String(row["名称"] || "").trim();
    if (!symbol || !name || symbol === "-" || name === "-") {
      setWatchlistFeedback("当前这一行没有可加入候选池的股票代码或名称");
      return;
    }
    try {
      await createItemAsync({
        symbol,
        name,
        bucket: mapModeToBucket(latestAssistantMessage?.mode),
        tags: [],
        note: null,
        source_session_id: latestAssistantMessage?.session_id || null,
      });
      setWatchlistFeedback(`✅ 已加入候选池：${name}（${symbol}）`);
    } catch (error) {
      setWatchlistFeedback(`❌ ${error instanceof Error ? error.message : "加入候选池失败"}`);
    }
  };

  return (
    <div className="flex flex-col h-full border-l bg-gradient-to-b from-card to-muted/20">
      {/* Tab Bar */}
      <div className="border-b bg-card/80 backdrop-blur-sm">
        <div className="flex items-center justify-between px-3 py-2.5">
          {/* Pill Tabs */}
          <div className="flex bg-muted/70 rounded-xl p-0.5 gap-0.5">
            {tabs.map((tab) => {
              const config = TAB_CONFIG[tab];
              const count = tabCounts[tab];
              const isActive = activeTab === tab;
              return (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200",
                    isActive
                      ? "bg-card shadow-sm text-foreground"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                  )}
                >
                  <span>{config.icon}</span>
                  <span>{config.label}</span>
                  {count > 0 && (
                    <span
                      className={cn(
                        "px-1.5 py-0.5 rounded-full text-[10px] font-semibold",
                        isActive ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
                      )}
                    >
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* View Toggle */}
          {activeTab === "overview" && hasResult && (
            <div className="flex gap-1">
              {(["table", "cards"] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setResultViewMode(mode)}
                  className={cn(
                    "px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all",
                    resultViewMode === mode
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-muted"
                  )}
                >
                  {mode === "table" ? "📊" : "📦"} {mode === "table" ? "表格" : "卡片"}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {watchlistFeedback && (
          <div
            className={cn(
              "rounded-xl border px-3 py-2.5 text-xs font-medium animate-slide-up",
              watchlistFeedback.includes("✅")
                ? "bg-green-50/80 border-green-200/50 text-green-700"
                : "bg-red-50/80 border-red-200/50 text-red-700"
            )}
          >
            {watchlistFeedback}
          </div>
        )}

        {activeTab === "overview" && (
          <>
            <ResultSummary result={currentResult} partialSummary={partialSummary} />
            {actionCards.length > 0 && <ResultCards cards={actionCards} />}
            {resultViewMode === "table" && currentResult?.table && (
              <ResultTable table={currentResult.table} onFavorite={(row) => void handleFavorite(row)} />
            )}
            {resultViewMode === "cards" && secondaryCards.length > 0 && (
              <ResultCards cards={secondaryCards} />
            )}
          </>
        )}

        {activeTab === "skills" && <SkillTracePanel skills={skills} />}
        {activeTab === "followups" && (
          <FollowUpSuggestions suggestions={followUps} onSuggestionClick={() => setActiveTab("overview")} />
        )}
      </div>
    </div>
  );
}

function mapModeToBucket(mode: ChatMode | null | undefined): WatchBucket {
  if (mode === "short_term") return "short_term";
  if (mode === "swing") return "swing";
  if (mode === "mid_term_value") return "mid_term_value";
  return "observe";
}
