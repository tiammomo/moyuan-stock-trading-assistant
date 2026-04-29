import type { ChatMode, JsonValue } from "./common";

export interface TemplateRecord {
  id: string;
  name: string;
  category: string;
  mode: ChatMode | null;
  content: string;
  default_params: Record<string, JsonValue>;
  created_at: string;
}

export interface TemplateCreate {
  name: string;
  category: string;
  mode?: ChatMode | null;
  content: string;
  default_params: Record<string, JsonValue>;
}

export interface TemplateUpdate {
  name?: string | null;
  category?: string | null;
  mode?: ChatMode | null;
  content?: string | null;
  default_params?: Record<string, JsonValue> | null;
}
