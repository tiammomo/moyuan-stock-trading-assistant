"use client";

import type { StructuredResult } from "@/types/common";

interface ResultSummaryProps {
  result: StructuredResult | null;
  partialSummary?: string;
}

export function ResultSummary({ result, partialSummary }: ResultSummaryProps) {
  const summary = result?.summary || partialSummary || "";
  const facts = result?.facts || [];
  const judgements = result?.judgements || [];

  if (!summary && facts.length === 0 && judgements.length === 0) {
    return (
      <div className="text-center py-8 text-sm text-muted-foreground">
        暂无分析结果
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {summary && (
        <div className="rounded-2xl border border-border/50 bg-muted/34 p-4 shadow-neo">
          <div className="mb-2 text-[11px] uppercase tracking-[0.22em] text-muted-foreground/55">
            Summary
          </div>
          <p className="font-display text-[18px] leading-8 whitespace-pre-wrap text-foreground/92">{summary}</p>
        </div>
      )}

      {facts.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-medium tracking-[0.18em] text-muted-foreground/70 uppercase">Facts</div>
          <ul className="space-y-1">
            {facts.map((fact, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm leading-7 text-foreground/84">
                <span className="text-emerald-400">•</span>
                {fact}
              </li>
            ))}
          </ul>
        </div>
      )}

      {judgements.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-medium tracking-[0.18em] text-muted-foreground/70 uppercase">Judgements</div>
          <ul className="space-y-1">
            {judgements.map((judgement, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm leading-7 text-foreground/84">
                <span className="text-sky-400">•</span>
                {judgement}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
