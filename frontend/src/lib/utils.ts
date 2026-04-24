import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatTimestamp(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "刚刚";
  if (diffMins < 60) return `${diffMins}分钟前`;
  if (diffHours < 24) return `${diffHours}小时前`;
  if (diffDays < 7) return `${diffDays}天前`;

  return date.toLocaleDateString("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDateTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatLatency(ms: number | null): string {
  if (ms === null) return "-";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function normalizeStockSymbol(value: string | null | undefined): string {
  const text = String(value || "").trim().toUpperCase().replace(/\s+/g, "");
  if (!text) return "";
  if (/^\d{6}\.(SH|SZ|BJ)$/.test(text)) return text;
  if (!/^\d{6}$/.test(text)) return text;
  if (/^(60|68|90)/.test(text)) return `${text}.SH`;
  if (/^(00|20|30)/.test(text)) return `${text}.SZ`;
  if (/^(43|83|87|88|92|8)/.test(text)) return `${text}.BJ`;
  return text;
}

export const MODE_LABELS: Record<string, string> = {
  short_term: "短线",
  swing: "波段",
  mid_term_value: "中线价值",
  generic_data_query: "通用",
  compare: "比较",
  follow_up: "追问",
};

export const MODE_COLORS: Record<string, string> = {
  short_term: "bg-amber-500/12 text-amber-200 border-amber-400/20",
  swing: "bg-emerald-500/12 text-emerald-200 border-emerald-400/20",
  mid_term_value: "bg-sky-500/12 text-sky-200 border-sky-400/20",
  generic_data_query: "bg-slate-500/12 text-slate-200 border-slate-400/20",
  compare: "bg-blue-500/12 text-blue-200 border-blue-400/20",
  follow_up: "bg-teal-500/12 text-teal-200 border-teal-400/20",
};

export const STATUS_LABELS: Record<string, string> = {
  idle: "空闲",
  analyzing: "分析中",
  running_skills: "执行Skills中",
  partial_ready: "部分就绪",
  completed: "已完成",
  failed: "失败",
};

export const SKILL_STATUS_COLORS: Record<string, string> = {
  pending: "text-gray-400",
  running: "text-blue-500",
  success: "text-green-500",
  failed: "text-red-500",
};

export const CARD_TYPE_LABELS: Record<string, string> = {
  market_overview: "市场概览",
  sector_overview: "板块概览",
  candidate_summary: "候选摘要",
  operation_guidance: "操作建议",
  portfolio_context: "持仓上下文",
  multi_horizon_analysis: "三周期分析",
  risk_warning: "风险提示",
  research_next_step: "研究建议",
  custom: "自定义",
};

export const BUCKET_LABELS: Record<string, string> = {
  short_term: "短线",
  swing: "波段",
  mid_term_value: "中线价值",
  observe: "观察",
  discard: "丢弃",
};

export const BUCKET_COLORS: Record<string, string> = {
  short_term: "bg-amber-500/12 text-amber-200 border-amber-400/20",
  swing: "bg-emerald-500/12 text-emerald-200 border-emerald-400/20",
  mid_term_value: "bg-sky-500/12 text-sky-200 border-sky-400/20",
  observe: "bg-blue-500/12 text-blue-200 border-blue-400/20",
  discard: "bg-red-500/12 text-red-200 border-red-400/20",
};
