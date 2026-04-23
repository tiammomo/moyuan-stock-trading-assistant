"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center justify-center rounded-md px-2 py-0.5 text-xs font-semibold transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-ring/50",
  {
    variants: {
      variant: {
        default:
          "bg-primary/15 text-primary border border-primary/20",
        secondary:
          "bg-secondary/80 text-secondary-foreground border border-secondary/30",
        destructive:
          "bg-red-500/15 text-red-400 border border-red-500/20",
        outline:
          "bg-transparent text-muted-foreground border border-border/50",
        success:
          "bg-green-500/15 text-green-400 border border-green-500/20",
        warning:
          "bg-amber-500/15 text-amber-400 border border-amber-500/20",
        info:
          "bg-blue-500/15 text-blue-400 border border-blue-500/20",
        glow:
          "bg-primary/10 text-primary border border-primary/30 shadow-glow",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
