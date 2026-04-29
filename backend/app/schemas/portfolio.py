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


class PortfolioPositionLot(ContractModel):
    acquired_at: Optional[datetime] = None
    quantity: int = Field(..., gt=0)
    cost_price: float = Field(..., gt=0)
    note: Optional[str] = None


class PortfolioPositionCreate(ContractModel):
    account_id: str
    symbol: str
    name: Optional[str] = None
    cost_price: float = Field(..., gt=0)
    quantity: int = Field(..., gt=0)
    available_quantity: Optional[int] = Field(default=None, ge=0)
    frozen_quantity: Optional[int] = Field(default=None, ge=0)
    invested_amount: Optional[float] = None
    trading_style: TradingStyle = "swing"
    industry: Optional[str] = None
    note: Optional[str] = None
    lots: List[PortfolioPositionLot] = Field(default_factory=list)


class PortfolioPositionUpdate(ContractModel):
    account_id: Optional[str] = None
    symbol: Optional[str] = None
    name: Optional[str] = None
    cost_price: Optional[float] = Field(default=None, gt=0)
    quantity: Optional[int] = Field(default=None, gt=0)
    available_quantity: Optional[int] = Field(default=None, ge=0)
    frozen_quantity: Optional[int] = Field(default=None, ge=0)
    invested_amount: Optional[float] = None
    trading_style: Optional[TradingStyle] = None
    industry: Optional[str] = None
    note: Optional[str] = None
    lots: Optional[List[PortfolioPositionLot]] = None


class PortfolioPositionRecord(ContractModel):
    id: str
    account_id: str
    symbol: str
    name: str
    cost_price: float
    quantity: int
    available_quantity: int = 0
    frozen_quantity: int = 0
    invested_amount: Optional[float] = None
    trading_style: TradingStyle = "swing"
    industry: Optional[str] = None
    note: Optional[str] = None
    lots: List[PortfolioPositionLot] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class PortfolioPositionAdvice(ContractModel):
    headline: str
    risk: str
    action: str
    template: str


class PortfolioPositionView(PortfolioPositionRecord):
    account_name: str
    latest_price: Optional[float] = None
    change_pct: Optional[float] = None
    market_value: Optional[float] = None
    cost_value: float
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    daily_pnl: Optional[float] = None
    weight_pct: float = 0
    available_ratio_pct: float = 0
    quote_error: Optional[str] = None
    advice: Optional[PortfolioPositionAdvice] = None


class PortfolioMarketSchedule(ContractModel):
    calendar_source: str
    market_phase: Literal["open", "closed"] = "closed"
    is_trading_day: bool = False
    next_open_at: Optional[datetime] = None
    next_refresh_in_ms: int = 10000


class PortfolioIndustryExposure(ContractModel):
    industry: str
    market_value: float = 0
    weight_pct: float = 0
    position_count: int = 0
    symbols: List[str] = Field(default_factory=list)


class PortfolioAccountView(PortfolioAccountRecord):
    positions: List[PortfolioPositionView] = Field(default_factory=list)
    total_cost: float = 0
    total_market_value: float = 0
    total_pnl: float = 0
    total_pnl_pct: float = 0
    total_daily_pnl: float = 0
    total_assets: float = 0
    position_ratio_pct: float = 0
    industry_exposures: List[PortfolioIndustryExposure] = Field(default_factory=list)


class PortfolioSummary(ContractModel):
    accounts: List[PortfolioAccountView] = Field(default_factory=list)
    available_funds_total: float = 0
    total_cost: float = 0
    total_market_value: float = 0
    total_assets: float = 0
    total_position_ratio_pct: float = 0
    total_pnl: float = 0
    total_pnl_pct: float = 0
    total_daily_pnl: float = 0
    quote_error_count: int = 0
    industry_exposures: List[PortfolioIndustryExposure] = Field(default_factory=list)
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


class PortfolioCsvImportRequest(ContractModel):
    account_id: str
    csv_text: str
    dry_run: bool = False
    preserve_existing_note: bool = True
    default_trading_style: TradingStyle = "swing"


class PortfolioCsvImportRow(ContractModel):
    symbol: str
    name: Optional[str] = None
    quantity: int
    available_quantity: Optional[int] = None
    frozen_quantity: Optional[int] = None
    cost_price: float
    industry: Optional[str] = None
    trading_style: TradingStyle = "swing"
    lots: List[PortfolioPositionLot] = Field(default_factory=list)
    action: Literal["created", "updated", "skipped", "preview"]
    reason: Optional[str] = None
    position_id: Optional[str] = None


class PortfolioCsvImportResponse(ContractModel):
    account_id: str
    account_name: str
    detected_at: datetime
    parsed_count: int = 0
    imported_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    rows: List[PortfolioCsvImportRow] = Field(default_factory=list)


PortfolioScreenshotImportRequest.model_rebuild()
