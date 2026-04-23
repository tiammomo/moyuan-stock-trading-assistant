from typing import Dict, List, Optional

from pydantic import Field

from .common import (
    ChatMode,
    ChatResponseStatus,
    ContractModel,
    JsonValue,
    ResultCard,
    ResultTable,
    SkillUsage,
    SourceRef,
    StructuredResult,
    StreamEvent,
    UserVisibleError,
)


class ChatRequest(ContractModel):
    session_id: Optional[str] = None
    message: str = Field(..., min_length=1)
    mode_hint: Optional[ChatMode] = None
    stream: bool = False


class ChatFollowUpRequest(ContractModel):
    session_id: str
    parent_message_id: str
    message: str = Field(..., min_length=1)
    stream: bool = False


class ChatCompareRequest(ContractModel):
    session_id: str
    parent_message_id: Optional[str] = None
    symbols: List[str] = Field(default_factory=list)
    message: Optional[str] = None
    stream: bool = False


class ChatResponse(ContractModel):
    session_id: str
    message_id: str
    mode: ChatMode
    skills_used: List[SkillUsage] = Field(default_factory=list)
    summary: str = ""
    table: Optional[ResultTable] = None
    cards: List[ResultCard] = Field(default_factory=list)
    facts: List[str] = Field(default_factory=list)
    judgements: List[str] = Field(default_factory=list)
    follow_ups: List[str] = Field(default_factory=list)
    sources: List[SourceRef] = Field(default_factory=list)
    status: ChatResponseStatus
    user_visible_error: Optional[UserVisibleError] = None


class SkillExecutionResult(ContractModel):
    skill_name: str
    success: bool
    latency_ms: Optional[int] = Field(default=None, ge=0)
    query: str
    raw: Dict[str, JsonValue] = Field(default_factory=dict)
    normalized: StructuredResult = Field(default_factory=StructuredResult)


__all__ = [
    "ChatCompareRequest",
    "ChatFollowUpRequest",
    "ChatRequest",
    "ChatResponse",
    "SkillExecutionResult",
    "StreamEvent",
]
