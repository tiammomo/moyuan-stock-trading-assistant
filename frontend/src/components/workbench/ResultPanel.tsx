"use client";

import { useState } from "react";
import { useChatStore } from "@/stores/chatStore";
import { useUIStore } from "@/stores/uiStore";
import { useWatchlist } from "@/hooks/useWatchlist";
import { cn, normalizeStockSymbol } from "@/lib/utils";
import { ResultTable } from "@/components/results/ResultTable";
import { ResultCards } from "@/components/results/ResultCards";
import { ResultSummary } from "@/components/results/ResultSummary";
import { UserVisibleErrorNotice } from "@/components/ui/UserVisibleErrorNotice";
import { SkillTracePanel } from "./SkillTracePanel";
import { FollowUpSuggestions } from "./FollowUpSuggestions";
import { Button } from "@/components/ui/Button";
import { toast } from "@/components/ui/Toast";
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
  const { currentResult, streamingStatus, messages } = useChatStore();
  const { resultViewMode, setResultViewMode } = useUIStore();
  const { watchlist, createItemAsync } = useWatchlist();

  const latestAssistantMessage = [...messages].reverse().find((m) => m.role === "assistant");
  const latestUserVisibleError = latestAssistantMessage?.user_visible_error ?? null;
  const skills = latestAssistantMessage?.skills_used || [];
  const followUps = currentResult?.follow_ups || [];
  const favoriteSymbols = new Set(watchlist.map((item) => normalizeStockSymbol(item.symbol)));

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
  const hasTable = Boolean(currentResult?.table);
  const hasSecondaryCards = secondaryCards.length > 0;
  const hasOverviewContent = Boolean(
    latestUserVisibleError ||
      currentResult?.facts?.length ||
      currentResult?.judgements?.length ||
      actionCards.length > 0 ||
      hasSecondaryCards ||
      hasTable
  );
  const hasSwitchableResultView = hasTable && hasSecondaryCards;
  const showStructuredCardsFirst =
    resultViewMode === "cards" || (!hasTable && (actionCards.length > 0 || hasSecondaryCards));

  const handleFavorite = async (row: Record<string, JsonValue>) => {
    const symbol = String(row["代码"] || "").trim();
    const name = String(row["名称"] || "").trim();
    if (!symbol || !name || symbol === "-" || name === "-") {
      setWatchlistFeedback("当前这一行没有可加入候选池的股票代码或名称");
      toast.warning("当前这一行没有可加入候选池的股票代码或名称");
      return;
    }
    const normalizedSymbol = normalizeStockSymbol(symbol);
    const existingItem = watchlist.find(
      (item) => normalizeStockSymbol(item.symbol) === normalizedSymbol
    );
    if (existingItem) {
      const message = `${name}（${existingItem.symbol}）已在候选池中`;
      setWatchlistFeedback(`ℹ ${message}`);
      toast.info(message);
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
      toast.success(`已加入候选池：${name}（${normalizedSymbol || symbol}）`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "加入候选池失败";
      if (message.includes("已在候选池中")) {
        setWatchlistFeedback(`ℹ ${message}`);
        toast.info(message);
        return;
      }
      setWatchlistFeedback(`❌ ${message}`);
      toast.error(message);
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
          {activeTab === "overview" && hasSwitchableResultView && (
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
                : watchlistFeedback.startsWith("ℹ")
                  ? "bg-blue-50/80 border-blue-200/50 text-blue-700"
                  : "bg-red-50/80 border-red-200/50 text-red-700"
            )}
          >
            {watchlistFeedback}
          </div>
        )}

        {activeTab === "overview" && (
          <>
            {hasOverviewContent ? (
              showStructuredCardsFirst ? (
                <>
                  {latestUserVisibleError && <UserVisibleErrorNotice error={latestUserVisibleError} />}
                  {actionCards.length > 0 && <ResultCards cards={actionCards} />}
                  {hasSecondaryCards && <ResultCards cards={secondaryCards} />}
                  <ResultSummary result={currentResult} userVisibleError={null} />
                </>
              ) : (
                <>
                  <ResultSummary result={currentResult} userVisibleError={latestUserVisibleError} />
                  {actionCards.length > 0 && <ResultCards cards={actionCards} />}
                {resultViewMode === "table" && hasTable && (
                  <ResultTable
                    table={currentResult!.table}
                    onFavorite={(row) => void handleFavorite(row)}
                    favoriteSymbols={favoriteSymbols}
                  />
                )}
              </>
            )
          ) : (
              <div className="py-8 text-center text-sm text-muted-foreground">暂无分析结果</div>
            )}
          </>
        )}

        {activeTab === "skills" && <SkillTracePanel skills={skills} status={streamingStatus} />}
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
