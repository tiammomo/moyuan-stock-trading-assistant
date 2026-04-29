"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { cn, CARD_TYPE_LABELS } from "@/lib/utils";
import { StructuredResultCardContent } from "@/components/results/StructuredResultCardContent";
import type { ResultCard as ResultCardType } from "@/types/common";

interface ResultCardsProps {
  cards: ResultCardType[];
}

const CARD_TYPE_STYLES: Record<string, { bg: string; icon: string }> = {
  market_overview: { bg: "bg-blue-50 border-blue-200", icon: "📊" },
  sector_overview: { bg: "bg-purple-50 border-purple-200", icon: "🏢" },
  candidate_summary: { bg: "bg-green-50 border-green-200", icon: "⭐" },
  operation_guidance: { bg: "bg-amber-50 border-amber-200", icon: "🎯" },
  portfolio_context: { bg: "bg-lime-50 border-lime-200", icon: "仓" },
  multi_horizon_analysis: { bg: "bg-sky-50 border-sky-200", icon: "3" },
  risk_warning: { bg: "bg-red-50 border-red-200", icon: "⚠️" },
  research_next_step: { bg: "bg-cyan-50 border-cyan-200", icon: "🔍" },
  custom: { bg: "bg-gray-50 border-gray-200", icon: "📝" },
};

function resolveCardStyle(card: ResultCardType) {
  if (card.title === "财报与基本面") {
    return { bg: "bg-emerald-50 border-emerald-200", icon: "财" };
  }
  return CARD_TYPE_STYLES[card.type] || CARD_TYPE_STYLES.custom;
}

export function ResultCards({ cards }: ResultCardsProps) {
  if (cards.length === 0) {
    return (
      <div className="text-center py-8 text-sm text-muted-foreground">
        暂无卡片数据
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {cards.map((card, idx) => {
        const style = resolveCardStyle(card);
        return (
            <Card key={idx} className={cn("border", style.bg)}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <span>{style.icon}</span>
                {card.title}
                <span className="text-xs font-normal text-muted-foreground ml-auto">
                  {CARD_TYPE_LABELS[card.type] || card.type}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <StructuredResultCardContent card={card} />
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
