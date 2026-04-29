import type { JsonValue, WatchBucket } from "./common";

export interface WatchItemCreate {
  query?: string | null;
  symbol?: string | null;
  name?: string | null;
  bucket: WatchBucket;
  tags: string[];
  note?: string | null;
  source_session_id?: string | null;
}

export interface WatchItemUpdate {
  bucket?: WatchBucket | null;
  tags?: string[] | null;
  note?: string | null;
}

export interface WatchItemRecord {
  id: string;
  symbol: string;
  name: string;
  bucket: WatchBucket;
  tags: string[];
  note?: string | null;
  source_session_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface WatchStockResolveRequest {
  query: string;
}

export interface WatchStockCandidate {
  symbol: string;
  name: string;
  latest_price?: number | null;
  change_pct?: number | null;
  industry?: string | null;
  concepts: string[];
  source_query: string;
}

export interface WatchMonitorEvent {
  id: string;
  symbol: string;
  name: string;
  bucket: WatchBucket;
  rule_id?: string | null;
  rule_name?: string | null;
  event_type: string;
  severity: string;
  title: string;
  summary: string;
  ai_explanation?: string | null;
  action_hint?: string | null;
  reasons: string[];
  metrics: Record<string, string | number | boolean | null>;
  created_at: string;
}

export interface WatchMonitorStatus {
  enabled: boolean;
  running: boolean;
  market_phase: string;
  interval_seconds: number;
  watchlist_count: number;
  event_count: number;
  last_scan_at?: string | null;
  last_event_at?: string | null;
  last_scan_duration_ms?: number | null;
  last_error?: string | null;
}

export interface WatchMonitorScanResponse {
  scanned_count: number;
  triggered_count: number;
  skipped_count: number;
  events: WatchMonitorEvent[];
  status: WatchMonitorStatus;
}

export type MonitorRuleConditionType =
  | "latest_price"
  | "change_pct"
  | "volume_ratio"
  | "weibi"
  | "amount"
  | "volume"
  | "turnover_pct"
  | "amplitude_pct"
  | "waipan"
  | "neipan"
  | "weicha"
  | "pb"
  | "pe_dynamic"
  | "total_market_value"
  | "float_market_value"
  | "intraday_position_pct"
  | "gap_pct"
  | "price_vs_open_pct"
  | "upper_shadow_pct"
  | "lower_shadow_pct";

export type MonitorRuleMarketHoursMode = "trading_only" | "always";

export type MonitorRuleRepeatMode = "repeat" | "once";

export type MonitorRuleConditionOperator = ">" | ">=" | "<" | "<=" | "between";

export interface MonitorRuleCondition {
  type: MonitorRuleConditionType;
  op: MonitorRuleConditionOperator;
  value: JsonValue;
}

export interface MonitorRuleConditionGroup {
  op: "and" | "or";
  items: MonitorRuleCondition[];
}

export interface MonitorRuleCreate {
  item_id: string;
  rule_name: string;
  enabled: boolean;
  severity: "info" | "warning";
  condition_group: MonitorRuleConditionGroup;
  notify_channel_ids: string[];
  market_hours_mode: MonitorRuleMarketHoursMode;
  repeat_mode: MonitorRuleRepeatMode;
  expire_at?: string | null;
  cooldown_minutes: number;
  max_triggers_per_day: number;
}

export interface MonitorRuleUpdate {
  rule_name?: string | null;
  enabled?: boolean | null;
  severity?: "info" | "warning" | null;
  condition_group?: MonitorRuleConditionGroup | null;
  notify_channel_ids?: string[] | null;
  market_hours_mode?: MonitorRuleMarketHoursMode | null;
  repeat_mode?: MonitorRuleRepeatMode | null;
  expire_at?: string | null;
  cooldown_minutes?: number | null;
  max_triggers_per_day?: number | null;
}

export interface MonitorRuleRecord {
  id: string;
  item_id: string;
  symbol: string;
  name: string;
  bucket: WatchBucket;
  rule_name: string;
  enabled: boolean;
  severity: "info" | "warning";
  condition_group: MonitorRuleConditionGroup;
  notify_channel_ids: string[];
  market_hours_mode: MonitorRuleMarketHoursMode;
  repeat_mode: MonitorRuleRepeatMode;
  expire_at?: string | null;
  cooldown_minutes: number;
  max_triggers_per_day: number;
  created_at: string;
  updated_at: string;
}
