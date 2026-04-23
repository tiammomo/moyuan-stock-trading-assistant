"use client";

import { UserVisibleErrorNotice } from "@/components/ui/UserVisibleErrorNotice";
import type { StructuredResult, UserVisibleError } from "@/types/common";

interface ResultSummaryProps {
  result: StructuredResult | null;
  userVisibleError?: UserVisibleError | null;
}

export function ResultSummary({ result, userVisibleError = null }: ResultSummaryProps) {
  const facts = result?.facts || [];
  const judgements = result?.judgements || [];

  if (facts.length === 0 && judgements.length === 0 && !userVisibleError) {
    return null;
  }

  return (
    <div className="space-y-4">
      {userVisibleError && <UserVisibleErrorNotice error={userVisibleError} />}

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
