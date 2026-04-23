from typing import List, Optional

from pydantic import Field

from .common import ChatMode, ContractModel, GptReasoningPolicy


class UserProfile(ContractModel):
    capital: Optional[int] = Field(default=None, ge=0)
    position_limit_pct: Optional[float] = Field(default=None, ge=0, le=100)
    max_drawdown_pct: Optional[float] = Field(default=None, ge=0, le=100)
    holding_horizon: Optional[str] = None
    risk_style: Optional[str] = None
    preferred_sectors: List[str] = Field(default_factory=list)
    default_mode: Optional[ChatMode] = None
    default_result_size: int = Field(default=5, ge=1, le=100)
    gpt_enhancement_enabled: bool = True
    gpt_reasoning_policy: GptReasoningPolicy = GptReasoningPolicy.AUTO


class UserProfileUpdate(ContractModel):
    capital: Optional[int] = Field(default=None, ge=0)
    position_limit_pct: Optional[float] = Field(default=None, ge=0, le=100)
    max_drawdown_pct: Optional[float] = Field(default=None, ge=0, le=100)
    holding_horizon: Optional[str] = None
    risk_style: Optional[str] = None
    preferred_sectors: Optional[List[str]] = None
    default_mode: Optional[ChatMode] = None
    default_result_size: Optional[int] = Field(default=None, ge=1, le=100)
    gpt_enhancement_enabled: Optional[bool] = None
    gpt_reasoning_policy: Optional[GptReasoningPolicy] = None
