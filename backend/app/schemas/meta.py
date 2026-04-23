from .common import ContractModel


class EnvironmentStatus(ContractModel):
    api_base_url: str
    api_key_configured: bool
    skill_count: int
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
