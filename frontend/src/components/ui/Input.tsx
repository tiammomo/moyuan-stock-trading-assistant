"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-10 w-full rounded-lg border border-input bg-background px-3.5 py-2 text-sm transition-all duration-200 font-mono",
          "placeholder:text-muted-foreground/40",
          "focus:outline-none focus:ring-2 focus:ring-ring/30 focus:border-primary/50",
          "disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-muted/30",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";

export { Input };
