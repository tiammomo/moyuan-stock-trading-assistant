export type ScheduledReportType =
  | "pre_market_watchlist"
  | "post_market_review"
  | "portfolio_daily"
  | "news_digest";

export type ScheduledReportRunStatus = "success" | "failed" | "skipped";
export type ScheduledReportTrigger = "manual" | "scheduled";

export interface ScheduledReportJobRecord {
  report_type: ScheduledReportType;
  enabled: boolean;
  schedule_time: string;
  channel_ids: string[];
  updated_at: string;
}

export interface ScheduledReportJobUpdate {
  enabled?: boolean | null;
  schedule_time?: string | null;
  channel_ids?: string[] | null;
}

export interface ScheduledReportRunRecord {
  id: string;
  report_type: ScheduledReportType;
  title: string;
  summary: string;
  body: string;
  status: ScheduledReportRunStatus;
  trigger: ScheduledReportTrigger;
  channel_ids: string[];
  delivered_count: number;
  ai_enhanced: boolean;
  ai_provider?: string | null;
  reason?: string | null;
  trading_date?: string | null;
  created_at: string;
}
