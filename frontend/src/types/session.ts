import type {
  ChatMode,
  ChatResponseStatus,
  SkillUsage,
  StructuredResult,
  UserVisibleError,
} from "./common";

export interface SessionSummary {
  id: string;
  title: string;
  mode: ChatMode | null;
  archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface ChatMessageRecord {
  id: string;
  session_id: string;
  parent_message_id?: string | null;
  role: string;
  content: string;
  mode: ChatMode | null;
  rewritten_query?: string | null;
  skills_used: SkillUsage[];
  result_snapshot?: StructuredResult | null;
  status?: ChatResponseStatus | null;
  user_visible_error?: UserVisibleError | null;
  created_at: string;
}

export interface SessionDetail {
  id: string;
  title: string;
  mode: ChatMode | null;
  archived: boolean;
  created_at: string;
  updated_at: string;
  messages: ChatMessageRecord[];
}
