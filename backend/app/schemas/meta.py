from typing import List, Optional

from pydantic import Field

from .common import ContractModel


class SkillAssetMetaStatus(ContractModel):
    slug: Optional[str] = None
    version: Optional[str] = None
    owner_id: Optional[str] = None
    published_at: Optional[int] = None
    meta_path: Optional[str] = None


class RuntimeSkillStatus(ContractModel):
    skill_id: str
    display_name: str
    adapter_kind: str
    default_channel: Optional[str] = None
    asset_path: Optional[str] = None
    asset_meta: Optional[SkillAssetMetaStatus] = None
    enabled: bool = True


class EnvironmentStatus(ContractModel):
    api_base_url: str
    api_key_configured: bool
    skill_count: int
    runtime_skills: List[RuntimeSkillStatus] = Field(default_factory=list)
    llm_chain_mode: str
    llm_agent_runtime: str
    llm_enabled: bool
    llm_account_pool_adapter: str
    llm_system_prompt_source: str
    llm_system_prompt_role: str
    openai_base_url: str
    openai_api_key_configured: bool
    openai_model: str
    openai_reasoning_effort: str
    openai_enabled: bool
    openai_account_count: int
    anthropic_base_url: str
    anthropic_auth_token_configured: bool
    anthropic_model: str
    anthropic_enabled: bool
    anthropic_account_count: int
    version: str
