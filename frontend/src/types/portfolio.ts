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

export interface PortfolioPositionCreate {
  account_id: string;
  symbol: string;
  name?: string | null;
  cost_price: number;
  quantity: number;
  invested_amount?: number | null;
  trading_style: TradingStyle;
  note?: string | null;
}

export interface PortfolioPositionUpdate {
  account_id?: string | null;
  symbol?: string | null;
  name?: string | null;
  cost_price?: number | null;
  quantity?: number | null;
  invested_amount?: number | null;
  trading_style?: TradingStyle | null;
  note?: string | null;
}

export interface PortfolioPositionRecord {
  id: string;
  account_id: string;
  symbol: string;
  name: string;
  cost_price: number;
  quantity: number;
  invested_amount?: number | null;
  trading_style: TradingStyle;
  note?: string | null;
  created_at: string;
  updated_at: string;
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
  quote_error?: string | null;
}

export interface PortfolioAccountView extends PortfolioAccountRecord {
  positions: PortfolioPositionView[];
  total_cost: number;
  total_market_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  total_daily_pnl: number;
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
  total_cost: number;
  total_market_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  total_daily_pnl: number;
  quote_error_count: number;
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
