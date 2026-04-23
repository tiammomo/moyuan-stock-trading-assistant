"use client";

import { cn } from "@/lib/utils";
import { useChatStore } from "@/stores/chatStore";

interface FollowUpSuggestionsProps {
  suggestions: string[];
  onSuggestionClick?: (suggestion: string) => void;
}

export function FollowUpSuggestions({
  suggestions,
  onSuggestionClick,
}: FollowUpSuggestionsProps) {
  const { setInputValue } = useChatStore();

  if (suggestions.length === 0) return null;

  const handleClick = (suggestion: string) => {
    setInputValue(suggestion);
    onSuggestionClick?.(suggestion);
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
            onClick={() => handleClick(suggestion)}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm text-left",
              "bg-muted/30 border border-border/30 hover:border-primary/30",
              "hover:bg-primary/5 hover:shadow-glow transition-all group",
              "font-mono text-xs"
            )}
          >
            <span className="text-primary/60 group-hover:text-primary transition-colors">
              ▸
            </span>
            <span className="text-muted-foreground/80 group-hover:text-foreground transition-colors">
              {suggestion}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
