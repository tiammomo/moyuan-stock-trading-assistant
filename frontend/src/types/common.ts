export type JsonPrimitive = string | number | boolean | null;

export type JsonValue =
  | JsonPrimitive
  | JsonValue[]
  | { [key: string]: JsonValue };

export type ChatMode =
  | "short_term"
  | "swing"
  | "mid_term_value"
  | "generic_data_query"
  | "compare"
  | "follow_up";

export type SkillStrategy =
  | "screen_then_enrich"
  | "single_source"
  | "compare_existing"
  | "research_expand";

export type SkillRunStatus = "pending" | "running" | "success" | "failed";

export type ChatResponseStatus =
  | "idle"
  | "analyzing"
  | "running_skills"
  | "partial_ready"
  | "completed"
  | "failed";

export type StreamEventType =
  | "analysis_started"
  | "mode_detected"
  | "skill_routing_ready"
  | "skill_started"
  | "skill_finished"
  | "partial_result"
  | "completed"
  | "result_enhanced"
  | "failed";

export type CardType =
  | "market_overview"
  | "sector_overview"
  | "candidate_summary"
  | "operation_guidance"
  | "portfolio_context"
  | "multi_horizon_analysis"
  | "risk_warning"
  | "research_next_step"
  | "custom";

export type WatchBucket =
  | "short_term"
  | "swing"
  | "mid_term_value"
  | "observe"
  | "discard";

export type GptReasoningPolicy = "auto" | "medium" | "high" | "xhigh";

export type UserVisibleErrorSeverity = "warning" | "error";

export interface UserVisibleError {
  code: string;
  severity: UserVisibleErrorSeverity;
  title: string;
  message: string;
  retryable: boolean;
}

export interface SkillUsage {
  name: string;
  status: SkillRunStatus;
  latency_ms: number | null;
  reason: string | null;
}

export interface ResultCard {
  type: CardType | string;
  title: string;
  content: string;
  metadata: Record<string, JsonValue>;
}

export interface ResultTable {
  columns: string[];
  rows: Array<Record<string, JsonValue>>;
}

export interface SourceRef {
  skill: string;
  query: string;
}

export interface StructuredResult {
  summary: string;
  table: ResultTable | null;
  cards: ResultCard[];
  facts: string[];
  judgements: string[];
  follow_ups: string[];
  sources: SourceRef[];
}

export interface StreamEvent {
  event: StreamEventType;
  data: Record<string, JsonValue>;
  emitted_at: string | null;
}
