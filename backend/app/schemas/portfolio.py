from datetime import datetime
from typing import List, Literal, Optional

from pydantic import Field

from .common import ContractModel


TradingStyle = Literal["short", "swing", "long"]
PortfolioBrokerTemplate = Literal[
    "auto",
    "generic_cn",
    "tonghuashun",
    "guotai_haitong",
    "eastmoney",
    "huatai",
    "pingan",
]


class PortfolioAccountCreate(ContractModel):
    name: str = Field(..., min_length=1)
    available_funds: float = 0
    enabled: bool = True


class PortfolioAccountUpdate(ContractModel):
    name: Optional[str] = None
    available_funds: Optional[float] = None
    enabled: Optional[bool] = None


class PortfolioAccountRecord(ContractModel):
    id: str
    name: str
    available_funds: float = 0
    enabled: bool = True
    created_at: datetime
    updated_at: datetime


class PortfolioPositionCreate(ContractModel):
    account_id: str
    symbol: str
    name: Optional[str] = None
    cost_price: float = Field(..., gt=0)
    quantity: int = Field(..., gt=0)
    invested_amount: Optional[float] = None
    trading_style: TradingStyle = "swing"
    note: Optional[str] = None


class PortfolioPositionUpdate(ContractModel):
    account_id: Optional[str] = None
    symbol: Optional[str] = None
    name: Optional[str] = None
    cost_price: Optional[float] = Field(default=None, gt=0)
    quantity: Optional[int] = Field(default=None, gt=0)
    invested_amount: Optional[float] = None
    trading_style: Optional[TradingStyle] = None
    note: Optional[str] = None


class PortfolioPositionRecord(ContractModel):
    id: str
    account_id: str
    symbol: str
    name: str
    cost_price: float
    quantity: int
    invested_amount: Optional[float] = None
    trading_style: TradingStyle = "swing"
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PortfolioPositionView(PortfolioPositionRecord):
    account_name: str
    latest_price: Optional[float] = None
    change_pct: Optional[float] = None
    market_value: Optional[float] = None
    cost_value: float
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    daily_pnl: Optional[float] = None
    quote_error: Optional[str] = None


class PortfolioMarketSchedule(ContractModel):
    calendar_source: str
    market_phase: Literal["open", "closed"] = "closed"
    is_trading_day: bool = False
    next_open_at: Optional[datetime] = None
    next_refresh_in_ms: int = 10000


class PortfolioAccountView(PortfolioAccountRecord):
    positions: List[PortfolioPositionView] = Field(default_factory=list)
    total_cost: float = 0
    total_market_value: float = 0
    total_pnl: float = 0
    total_pnl_pct: float = 0
    total_daily_pnl: float = 0


class PortfolioSummary(ContractModel):
    accounts: List[PortfolioAccountView] = Field(default_factory=list)
    total_cost: float = 0
    total_market_value: float = 0
    total_pnl: float = 0
    total_pnl_pct: float = 0
    total_daily_pnl: float = 0
    quote_error_count: int = 0
    market_schedule: PortfolioMarketSchedule


class PortfolioScreenshotImportRequest(ContractModel):
    account_id: str
    image_data_url: Optional[str] = None
    dry_run: bool = False
    skip_zero_quantity: bool = True
    broker_template: PortfolioBrokerTemplate = "auto"
    broker_name: Optional[str] = None
    parsed_rows: List["PortfolioScreenshotImportRow"] = Field(default_factory=list)


class PortfolioScreenshotImportRow(ContractModel):
    name: str
    symbol: Optional[str] = None
    quantity: int
    available_quantity: Optional[int] = None
    cost_price: float
    latest_price: Optional[float] = None
    market_value: Optional[float] = None
    pnl_amount: Optional[float] = None
    pnl_pct: Optional[float] = None
    action: Literal["created", "updated", "skipped", "preview"]
    reason: Optional[str] = None
    position_id: Optional[str] = None


class PortfolioScreenshotImportResponse(ContractModel):
    account_id: str
    account_name: str
    broker_name: Optional[str] = None
    detected_at: datetime
    parsed_count: int = 0
    imported_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    rows: List[PortfolioScreenshotImportRow] = Field(default_factory=list)


PortfolioScreenshotImportRequest.model_rebuild()
