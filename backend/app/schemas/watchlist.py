from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import Field

from .common import ContractModel, JsonValue, WatchBucket


class WatchItemCreate(ContractModel):
    query: Optional[str] = None
    symbol: Optional[str] = None
    name: Optional[str] = None
    bucket: WatchBucket
    tags: List[str] = Field(default_factory=list)
    note: Optional[str] = None
    source_session_id: Optional[str] = None


class WatchItemUpdate(ContractModel):
    bucket: Optional[WatchBucket] = None
    tags: Optional[List[str]] = None
    note: Optional[str] = None


class WatchItemRecord(ContractModel):
    id: str
    symbol: str
    name: str
    bucket: WatchBucket
    tags: List[str] = Field(default_factory=list)
    note: Optional[str] = None
    source_session_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class WatchStockResolveRequest(ContractModel):
    query: str


class WatchStockCandidate(ContractModel):
    symbol: str
    name: str
    latest_price: Optional[float] = None
    change_pct: Optional[float] = None
    industry: Optional[str] = None
    concepts: List[str] = Field(default_factory=list)
    source_query: str


class WatchlistBackfillItemResult(ContractModel):
    item_id: str
    symbol: str
    name: str
    updated: bool = False
    tags_added: List[str] = Field(default_factory=list)
    note_added: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    note: Optional[str] = None
    skipped_reason: Optional[str] = None


class WatchlistBackfillResponse(ContractModel):
    scanned_count: int
    updated_count: int
    unchanged_count: int
    items: List[WatchlistBackfillItemResult] = Field(default_factory=list)


class WatchMonitorEvent(ContractModel):
    id: str
    symbol: str
    name: str
    bucket: WatchBucket
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    event_type: str
    severity: str = "info"
    title: str
    summary: str
    ai_explanation: Optional[str] = None
    action_hint: Optional[str] = None
    reasons: List[str] = Field(default_factory=list)
    metrics: Dict[str, JsonValue] = Field(default_factory=dict)
    created_at: datetime


class WatchMonitorStatus(ContractModel):
    enabled: bool = True
    running: bool = False
    market_phase: str = "closed"
    interval_seconds: int
    watchlist_count: int = 0
    event_count: int = 0
    last_scan_at: Optional[datetime] = None
    last_event_at: Optional[datetime] = None
    last_scan_duration_ms: Optional[int] = None
    last_error: Optional[str] = None


class WatchMonitorScanResponse(ContractModel):
    scanned_count: int
    triggered_count: int
    skipped_count: int = 0
    events: List[WatchMonitorEvent] = Field(default_factory=list)
    status: WatchMonitorStatus


class MonitorRuleCondition(ContractModel):
    type: Literal[
        "latest_price",
        "change_pct",
        "volume_ratio",
        "weibi",
        "amount",
        "volume",
        "turnover_pct",
        "amplitude_pct",
        "waipan",
        "neipan",
        "weicha",
        "pb",
        "pe_dynamic",
        "total_market_value",
        "float_market_value",
        "intraday_position_pct",
        "gap_pct",
        "price_vs_open_pct",
        "upper_shadow_pct",
        "lower_shadow_pct",
    ]
    op: Literal[">", ">=", "<", "<=", "between"]
    value: JsonValue


class MonitorRuleConditionGroup(ContractModel):
    op: Literal["and", "or"] = "or"
    items: List[MonitorRuleCondition] = Field(default_factory=list)


class MonitorRuleCreate(ContractModel):
    item_id: str
    rule_name: str
    enabled: bool = True
    severity: Literal["info", "warning"] = "info"
    condition_group: MonitorRuleConditionGroup
    notify_channel_ids: List[str] = Field(default_factory=list)
    market_hours_mode: Literal["trading_only", "always"] = "trading_only"
    repeat_mode: Literal["repeat", "once"] = "repeat"
    expire_at: Optional[datetime] = None
    cooldown_minutes: int = Field(default=30, ge=0, le=1440)
    max_triggers_per_day: int = Field(default=5, ge=0, le=999)


class MonitorRuleUpdate(ContractModel):
    rule_name: Optional[str] = None
    enabled: Optional[bool] = None
    severity: Optional[Literal["info", "warning"]] = None
    condition_group: Optional[MonitorRuleConditionGroup] = None
    notify_channel_ids: Optional[List[str]] = None
    market_hours_mode: Optional[Literal["trading_only", "always"]] = None
    repeat_mode: Optional[Literal["repeat", "once"]] = None
    expire_at: Optional[datetime] = None
    cooldown_minutes: Optional[int] = Field(default=None, ge=0, le=1440)
    max_triggers_per_day: Optional[int] = Field(default=None, ge=0, le=999)


class MonitorRuleRecord(ContractModel):
    id: str
    item_id: str
    symbol: str
    name: str
    bucket: WatchBucket
    rule_name: str
    enabled: bool = True
    severity: Literal["info", "warning"] = "info"
    condition_group: MonitorRuleConditionGroup
    notify_channel_ids: List[str] = Field(default_factory=list)
    market_hours_mode: Literal["trading_only", "always"] = "trading_only"
    repeat_mode: Literal["repeat", "once"] = "repeat"
    expire_at: Optional[datetime] = None
    cooldown_minutes: int = Field(default=30, ge=0, le=1440)
    max_triggers_per_day: int = Field(default=5, ge=0, le=999)
    created_at: datetime
    updated_at: datetime
