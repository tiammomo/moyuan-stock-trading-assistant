from datetime import datetime
from typing import List, Optional

from pydantic import Field

from .common import (
    ChatMode,
    ChatResponseStatus,
    ContractModel,
    SkillUsage,
    StructuredResult,
    UserVisibleError,
)


class SessionSummary(ContractModel):
    id: str
    title: str
    mode: Optional[ChatMode] = None
    archived: bool = False
    created_at: datetime
    updated_at: datetime


class ChatMessageRecord(ContractModel):
    id: str
    session_id: str
    parent_message_id: Optional[str] = None
    role: str
    content: str
    mode: Optional[ChatMode] = None
    rewritten_query: Optional[str] = None
    skills_used: List[SkillUsage] = Field(default_factory=list)
    result_snapshot: Optional[StructuredResult] = None
    status: Optional[ChatResponseStatus] = None
    user_visible_error: Optional[UserVisibleError] = None
    created_at: datetime


class SessionDetail(ContractModel):
    id: str
    title: str
    mode: Optional[ChatMode] = None
    archived: bool = False
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageRecord] = Field(default_factory=list)
