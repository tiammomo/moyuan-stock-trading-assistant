from datetime import datetime
from typing import List, Literal, Optional

from pydantic import Field

from .common import ContractModel


ScheduledReportType = Literal[
    "pre_market_watchlist",
    "post_market_review",
    "portfolio_daily",
    "news_digest",
]
ScheduledReportRunStatus = Literal["success", "failed", "skipped"]
ScheduledReportTrigger = Literal["manual", "scheduled"]


class ScheduledReportJobUpdate(ContractModel):
    enabled: Optional[bool] = None
    schedule_time: Optional[str] = None
    channel_ids: Optional[List[str]] = None


class ScheduledReportJobRecord(ContractModel):
    report_type: ScheduledReportType
    enabled: bool = False
    schedule_time: str
    channel_ids: List[str] = Field(default_factory=list)
    updated_at: datetime


class ScheduledReportRunRecord(ContractModel):
    id: str
    report_type: ScheduledReportType
    title: str
    summary: str
    body: str
    status: ScheduledReportRunStatus
    trigger: ScheduledReportTrigger
    channel_ids: List[str] = Field(default_factory=list)
    delivered_count: int = 0
    ai_enhanced: bool = False
    ai_provider: Optional[str] = None
    reason: Optional[str] = None
    trading_date: Optional[str] = None
    created_at: datetime
