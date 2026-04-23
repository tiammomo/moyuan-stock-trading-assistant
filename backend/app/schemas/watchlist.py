from datetime import datetime
from typing import List, Optional

from pydantic import Field

from .common import ContractModel, WatchBucket


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
