"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-lg text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50 active:scale-[0.97]",
  {
    variants: {
      variant: {
        default:
          "bg-gradient-to-r from-primary to-primary/80 text-primary-foreground shadow-glow hover:shadow-lg hover:shadow-primary/20 hover:-translate-y-0.5",
        destructive:
          "bg-gradient-to-r from-destructive to-destructive/80 text-destructive-foreground shadow-md hover:shadow-lg hover:-translate-y-0.5",
        outline:
          "border border-primary/30 bg-transparent text-primary hover:bg-primary/10 hover:border-primary/50 hover:shadow-glow",
        secondary:
          "bg-secondary text-secondary-foreground border border-border/50 hover:bg-secondary/80 hover:shadow-neo",
        ghost:
          "hover:bg-accent/20 hover:text-accent-foreground text-muted-foreground",
        link: "text-primary underline-offset-4 hover:underline",
        success:
          "bg-gradient-to-r from-green-600 to-green-500 text-white shadow-md hover:shadow-lg hover:-translate-y-0.5",
        glow:
          "bg-primary/10 text-primary border border-primary/30 hover:bg-primary/20 hover:border-primary/50 shadow-glow",
      },
      size: {
        default: "h-10 px-5 py-2.5",
        sm: "h-8 px-3 text-xs rounded-md",
        lg: "h-12 px-8 text-base rounded-lg",
        icon: "h-10 w-10 rounded-lg",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
