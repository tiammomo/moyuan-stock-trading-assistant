import type {
  ChatMode,
  ChatResponseStatus,
  JsonValue,
  ResultCard,
  ResultTable,
  SkillUsage,
  SourceRef,
  StructuredResult,
  UserVisibleError,
} from "./common";

export interface ChatRequest {
  session_id?: string | null;
  message: string;
  mode_hint?: ChatMode | null;
  stream: boolean;
}

export interface ChatFollowUpRequest {
  session_id: string;
  parent_message_id: string;
  message: string;
  stream: boolean;
}

export interface ChatCompareRequest {
  session_id: string;
  parent_message_id?: string | null;
  symbols: string[];
  message?: string | null;
  stream: boolean;
}

export interface ChatResponse {
  session_id: string;
  message_id: string;
  mode: ChatMode;
  skills_used: SkillUsage[];
  summary: string;
  table: ResultTable | null;
  cards: ResultCard[];
  facts: string[];
  judgements: string[];
  follow_ups: string[];
  sources: SourceRef[];
  status: ChatResponseStatus;
  user_visible_error: UserVisibleError | null;
}

export interface SkillExecutionResult {
  skill_name: string;
  success: boolean;
  latency_ms: number | null;
  query: string;
  raw: Record<string, JsonValue>;
  normalized: StructuredResult;
}
