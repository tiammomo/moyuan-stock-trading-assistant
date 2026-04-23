"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { useChatSubmit } from "@/hooks/useChatSubmit";

interface FollowUpSuggestionsProps {
  suggestions: string[];
  onSuggestionClick?: (suggestion: string) => void;
}

export function FollowUpSuggestions({
  suggestions,
  onSuggestionClick,
}: FollowUpSuggestionsProps) {
  const [pendingSuggestion, setPendingSuggestion] = useState<string | null>(null);
  const { isSubmitting, submitMessage } = useChatSubmit();

  useEffect(() => {
    if (!isSubmitting) {
      setPendingSuggestion(null);
    }
  }, [isSubmitting]);

  if (suggestions.length === 0) return null;

  const handleClick = async (suggestion: string) => {
    if (isSubmitting) return;
    setPendingSuggestion(suggestion);
    onSuggestionClick?.(suggestion);
    await submitMessage(suggestion, { preferFollowUp: true });
  };

  return (
    <div className="space-y-3">
      <div className="text-[10px] text-muted-foreground/50 font-mono">
        // Suggested Follow-ups
      </div>
      <div className="flex flex-col gap-2">
        {suggestions.map((suggestion, idx) => (
          <button
            key={idx}
            onClick={() => void handleClick(suggestion)}
            disabled={isSubmitting}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm text-left",
              "bg-muted/30 border border-border/30 hover:border-primary/30",
              "hover:bg-primary/5 hover:shadow-glow transition-all group",
              "font-mono text-xs disabled:cursor-not-allowed disabled:opacity-70"
            )}
          >
            {pendingSuggestion === suggestion ? (
              <span className="h-3.5 w-3.5 rounded-full border border-primary/40 border-t-primary animate-spin" />
            ) : (
              <span className="text-primary/60 group-hover:text-primary transition-colors">
                ▸
              </span>
            )}
            <span className="text-muted-foreground/80 group-hover:text-foreground transition-colors">
              {suggestion}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
