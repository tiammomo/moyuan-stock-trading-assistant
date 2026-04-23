export interface SkillAssetMetaStatus {
  slug: string | null;
  version: string | null;
  owner_id: string | null;
  published_at: number | null;
  meta_path: string | null;
}

export interface RuntimeSkillStatus {
  skill_id: string;
  display_name: string;
  adapter_kind: string;
  default_channel: string | null;
  asset_path: string | null;
  asset_meta: SkillAssetMetaStatus | null;
  enabled: boolean;
}

export interface EnvironmentStatus {
  api_base_url: string;
  api_key_configured: boolean;
  skill_count: number;
  runtime_skills: RuntimeSkillStatus[];
  llm_chain_mode: string;
  llm_agent_runtime: string;
  llm_enabled: boolean;
  llm_account_pool_adapter: string;
  llm_system_prompt_source: string;
  llm_system_prompt_role: string;
  openai_base_url: string;
  openai_api_key_configured: boolean;
  openai_model: string;
  openai_reasoning_effort: string;
  openai_enabled: boolean;
  openai_account_count: number;
  anthropic_base_url: string;
  anthropic_auth_token_configured: boolean;
  anthropic_model: string;
  anthropic_enabled: boolean;
  anthropic_account_count: number;
  version: string;
}
