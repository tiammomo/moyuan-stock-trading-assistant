"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface DialogProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  children?: React.ReactNode;
}

const Dialog = ({ open, onOpenChange, children }: DialogProps) => {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 animate-fade-in"
      role="dialog"
      aria-modal="true"
      onClick={() => onOpenChange?.(false)}
    >
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <div
          className="relative z-10 max-h-[85vh] w-full max-w-lg overflow-hidden rounded-xl border border-border/50 bg-card shadow-neo animate-scale-in"
          onClick={(e) => e.stopPropagation()}
        >
          {children}
        </div>
      </div>
    </div>
  );
};

const DialogHeader = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn("flex flex-col space-y-1.5 p-5 pb-3 border-b border-border/50", className)}
    {...props}
  />
);

const DialogTitle = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLHeadingElement>) => (
  <h2
    className={cn("text-base font-semibold text-foreground/90 tracking-tight", className)}
    {...props}
  />
);

const DialogDescription = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>) => (
  <p className={cn("text-sm text-muted-foreground", className)} {...props} />
);

const DialogContent = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("p-5", className)} {...props} />
);

const DialogFooter = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn("flex justify-end gap-2 p-5 pt-3 border-t border-border/50", className)}
    {...props}
  />
);

const DialogClose = ({
  onClose,
  ...props
}: React.HTMLAttributes<HTMLButtonElement> & { onClose?: () => void }) => (
  <button
    onClick={onClose}
    className={cn(
      "absolute right-4 top-4 w-8 h-8 flex items-center justify-center rounded-lg",
      "text-muted-foreground hover:text-foreground hover:bg-muted",
      "transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-ring/50"
    )}
    {...props}
  >
    ✕
  </button>
);

export {
  Dialog,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
  DialogContent,
  DialogClose,
};
