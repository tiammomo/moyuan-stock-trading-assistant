"use client";

import { cn, formatLatency } from "@/lib/utils";
import type { SkillUsage } from "@/types/common";

interface SkillTracePanelProps {
  skills: SkillUsage[];
}

const STATUS_CONFIG: Record<string, { icon: string; color: string; glow: string }> = {
  pending: { icon: "○", color: "text-muted-foreground/50", glow: "" },
  running: { icon: "◐", color: "text-primary animate-spin", glow: "" },
  success: { icon: "●", color: "text-green-400", glow: "shadow-green-500/30" },
  failed: { icon: "✕", color: "text-red-400", glow: "shadow-red-500/30" },
};

export function SkillTracePanel({ skills }: SkillTracePanelProps) {
  if (skills.length === 0) {
    return (
      <div className="text-center py-8">
        <div className="font-mono text-xs text-muted-foreground/50">
          &gt; No skills executed yet
        </div>
      </div>
    );
  }

  const totalLatency = skills.reduce((acc, s) => acc + (s.latency_ms || 0), 0);
  const successCount = skills.filter((s) => s.status === "success").length;

  return (
    <div className="space-y-2 font-mono">
      <div className="text-[10px] text-muted-foreground/50 mb-3">
        // Skill Execution Trace ({skills.length} tasks)
      </div>

      {skills.map((skill, idx) => {
        const config = STATUS_CONFIG[skill.status] || STATUS_CONFIG.pending;
        return (
          <div
            key={idx}
            className="flex items-start gap-3 p-3 rounded-lg bg-muted/30 border border-border/30 hover:border-primary/20 transition-all group"
          >
            <span className={cn("text-sm w-5 text-center", config.color)}>
              {config.icon}
            </span>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-foreground/90">
                {skill.name}
              </div>
              {skill.reason && (
                <div className="text-[11px] text-muted-foreground/60 mt-0.5 leading-relaxed">
                  // {skill.reason}
                </div>
              )}
            </div>
            <span className="text-[11px] text-muted-foreground/50 shrink-0">
              {formatLatency(skill.latency_ms)}
            </span>
          </div>
        );
      })}

      {/* Execution summary */}
      <div className="mt-4 pt-3 border-t border-border/30 space-y-1 text-[10px] text-muted-foreground/40">
        <div>// Total: {skills.length} skills</div>
        <div>// Success: {successCount}/{skills.length}</div>
        <div>// Time: {formatLatency(totalLatency)}</div>
      </div>
    </div>
  );
}
