"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          "flex min-h-[60px] w-full rounded-lg border border-input bg-background px-3.5 py-2.5 text-sm transition-all duration-200 font-mono",
          "placeholder:text-muted-foreground/40",
          "focus:outline-none focus:ring-0 focus:border-transparent focus:shadow-none",
          "disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-muted/30",
          "resize-none",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Textarea.displayName = "Textarea";

export { Textarea };
