from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


JsonPrimitive = Union[str, int, float, bool, None]
JsonValue = Any


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ChatMode(str, Enum):
    SHORT_TERM = "short_term"
    SWING = "swing"
    MID_TERM_VALUE = "mid_term_value"
    GENERIC_DATA_QUERY = "generic_data_query"
    COMPARE = "compare"
    FOLLOW_UP = "follow_up"


class SkillStrategy(str, Enum):
    SCREEN_THEN_ENRICH = "screen_then_enrich"
    SINGLE_SOURCE = "single_source"
    COMPARE_EXISTING = "compare_existing"
    RESEARCH_EXPAND = "research_expand"


class SkillRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class ChatResponseStatus(str, Enum):
    IDLE = "idle"
    ANALYZING = "analyzing"
    RUNNING_SKILLS = "running_skills"
    PARTIAL_READY = "partial_ready"
    COMPLETED = "completed"
    FAILED = "failed"


class StreamEventType(str, Enum):
    ANALYSIS_STARTED = "analysis_started"
    MODE_DETECTED = "mode_detected"
    SKILL_ROUTING_READY = "skill_routing_ready"
    SKILL_STARTED = "skill_started"
    SKILL_FINISHED = "skill_finished"
    PARTIAL_RESULT = "partial_result"
    COMPLETED = "completed"
    RESULT_ENHANCED = "result_enhanced"
    FAILED = "failed"


class CardType(str, Enum):
    MARKET_OVERVIEW = "market_overview"
    SECTOR_OVERVIEW = "sector_overview"
    CANDIDATE_SUMMARY = "candidate_summary"
    OPERATION_GUIDANCE = "operation_guidance"
    PORTFOLIO_CONTEXT = "portfolio_context"
    MULTI_HORIZON_ANALYSIS = "multi_horizon_analysis"
    RISK_WARNING = "risk_warning"
    RESEARCH_NEXT_STEP = "research_next_step"
    CUSTOM = "custom"


class WatchBucket(str, Enum):
    SHORT_TERM = "short_term"
    SWING = "swing"
    MID_TERM_VALUE = "mid_term_value"
    OBSERVE = "observe"
    DISCARD = "discard"


class GptReasoningPolicy(str, Enum):
    AUTO = "auto"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"


class UserVisibleErrorSeverity(str, Enum):
    WARNING = "warning"
    ERROR = "error"


class UserVisibleError(ContractModel):
    code: str
    severity: UserVisibleErrorSeverity = UserVisibleErrorSeverity.ERROR
    title: str
    message: str
    retryable: bool = False


class SkillUsage(ContractModel):
    name: str
    status: SkillRunStatus
    latency_ms: Optional[int] = Field(default=None, ge=0)
    reason: Optional[str] = None


class ResultCard(ContractModel):
    type: Union[CardType, str]
    title: str
    content: str
    metadata: Dict[str, JsonValue] = Field(default_factory=dict)


class ResultTable(ContractModel):
    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, JsonValue]] = Field(default_factory=list)


class SourceRef(ContractModel):
    skill: str
    query: str


class StructuredResult(ContractModel):
    summary: str = ""
    table: Optional[ResultTable] = None
    cards: List[ResultCard] = Field(default_factory=list)
    facts: List[str] = Field(default_factory=list)
    judgements: List[str] = Field(default_factory=list)
    follow_ups: List[str] = Field(default_factory=list)
    sources: List[SourceRef] = Field(default_factory=list)


class StreamEvent(ContractModel):
    event: StreamEventType
    data: Dict[str, JsonValue] = Field(default_factory=dict)
    emitted_at: Optional[datetime] = None
