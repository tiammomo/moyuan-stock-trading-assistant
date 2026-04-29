export type TradingStyle = "short" | "swing" | "long";
export type PortfolioBrokerTemplate =
  | "auto"
  | "generic_cn"
  | "tonghuashun"
  | "guotai_haitong"
  | "eastmoney"
  | "huatai"
  | "pingan";

export interface PortfolioAccountCreate {
  name: string;
  available_funds: number;
  enabled: boolean;
}

export interface PortfolioAccountUpdate {
  name?: string | null;
  available_funds?: number | null;
  enabled?: boolean | null;
}

export interface PortfolioAccountRecord {
  id: string;
  name: string;
  available_funds: number;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface PortfolioPositionLot {
  acquired_at?: string | null;
  quantity: number;
  cost_price: number;
  note?: string | null;
}

export interface PortfolioPositionCreate {
  account_id: string;
  symbol: string;
  name?: string | null;
  cost_price: number;
  quantity: number;
  available_quantity?: number | null;
  frozen_quantity?: number | null;
  invested_amount?: number | null;
  trading_style: TradingStyle;
  industry?: string | null;
  note?: string | null;
  lots?: PortfolioPositionLot[];
}

export interface PortfolioPositionUpdate {
  account_id?: string | null;
  symbol?: string | null;
  name?: string | null;
  cost_price?: number | null;
  quantity?: number | null;
  available_quantity?: number | null;
  frozen_quantity?: number | null;
  invested_amount?: number | null;
  trading_style?: TradingStyle | null;
  industry?: string | null;
  note?: string | null;
  lots?: PortfolioPositionLot[] | null;
}

export interface PortfolioPositionRecord {
  id: string;
  account_id: string;
  symbol: string;
  name: string;
  cost_price: number;
  quantity: number;
  available_quantity: number;
  frozen_quantity: number;
  invested_amount?: number | null;
  trading_style: TradingStyle;
  industry?: string | null;
  note?: string | null;
  lots: PortfolioPositionLot[];
  created_at: string;
  updated_at: string;
}

export interface PortfolioPositionAdvice {
  headline: string;
  risk: string;
  action: string;
  template: string;
}

export interface PortfolioPositionView extends PortfolioPositionRecord {
  account_name: string;
  latest_price?: number | null;
  change_pct?: number | null;
  market_value?: number | null;
  cost_value: number;
  pnl?: number | null;
  pnl_pct?: number | null;
  daily_pnl?: number | null;
  weight_pct: number;
  available_ratio_pct: number;
  quote_error?: string | null;
  advice?: PortfolioPositionAdvice | null;
}

export interface PortfolioIndustryExposure {
  industry: string;
  market_value: number;
  weight_pct: number;
  position_count: number;
  symbols: string[];
}

export interface PortfolioAccountView extends PortfolioAccountRecord {
  positions: PortfolioPositionView[];
  total_cost: number;
  total_market_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  total_daily_pnl: number;
  total_assets: number;
  position_ratio_pct: number;
  industry_exposures: PortfolioIndustryExposure[];
}

export interface PortfolioMarketSchedule {
  calendar_source: string;
  market_phase: "open" | "closed";
  is_trading_day: boolean;
  next_open_at?: string | null;
  next_refresh_in_ms: number;
}

export interface PortfolioSummary {
  accounts: PortfolioAccountView[];
  available_funds_total: number;
  total_cost: number;
  total_market_value: number;
  total_assets: number;
  total_position_ratio_pct: number;
  total_pnl: number;
  total_pnl_pct: number;
  total_daily_pnl: number;
  quote_error_count: number;
  industry_exposures: PortfolioIndustryExposure[];
  market_schedule: PortfolioMarketSchedule;
}

export interface PortfolioScreenshotImportRequest {
  account_id: string;
  image_data_url?: string | null;
  dry_run?: boolean;
  skip_zero_quantity?: boolean;
  broker_template?: PortfolioBrokerTemplate;
  broker_name?: string | null;
  parsed_rows?: PortfolioScreenshotImportRow[];
}

export interface PortfolioScreenshotImportRow {
  name: string;
  symbol?: string | null;
  quantity: number;
  available_quantity?: number | null;
  cost_price: number;
  latest_price?: number | null;
  market_value?: number | null;
  pnl_amount?: number | null;
  pnl_pct?: number | null;
  action: "created" | "updated" | "skipped" | "preview";
  reason?: string | null;
  position_id?: string | null;
}

export interface PortfolioScreenshotImportResponse {
  account_id: string;
  account_name: string;
  broker_name?: string | null;
  detected_at: string;
  parsed_count: number;
  imported_count: number;
  updated_count: number;
  skipped_count: number;
  rows: PortfolioScreenshotImportRow[];
}

export interface PortfolioCsvImportRequest {
  account_id: string;
  csv_text: string;
  dry_run?: boolean;
  preserve_existing_note?: boolean;
  default_trading_style?: TradingStyle;
}

export interface PortfolioCsvImportRow {
  symbol: string;
  name?: string | null;
  quantity: number;
  available_quantity?: number | null;
  frozen_quantity?: number | null;
  cost_price: number;
  industry?: string | null;
  trading_style: TradingStyle;
  lots: PortfolioPositionLot[];
  action: "created" | "updated" | "skipped" | "preview";
  reason?: string | null;
  position_id?: string | null;
}

export interface PortfolioCsvImportResponse {
  account_id: string;
  account_name: string;
  detected_at: string;
  parsed_count: number;
  imported_count: number;
  updated_count: number;
  skipped_count: number;
  rows: PortfolioCsvImportRow[];
}
