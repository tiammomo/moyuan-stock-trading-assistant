"use client";

import { Badge } from "@/components/ui/Badge";
import { Chip } from "@/components/ui/Chip";
import { cn } from "@/lib/utils";
import type { JsonValue, ResultCard as ResultCardType } from "@/types/common";

interface StructuredResultCardContentProps {
  card: ResultCardType;
}

interface MetricItemProps {
  label: string;
  value: string;
  tone?: "neutral" | "good" | "bad" | "warn";
}

interface SectionBlockProps {
  badge: string;
  title: string;
  summary?: string | null;
  chips?: string[];
  accentClassName?: string;
}

const METRIC_TONE_STYLES: Record<NonNullable<MetricItemProps["tone"]>, string> = {
  neutral: "border-border/50 bg-background/70 text-foreground/88",
  good: "border-emerald-200 bg-emerald-50 text-emerald-800",
  bad: "border-rose-200 bg-rose-50 text-rose-800",
  warn: "border-amber-200 bg-amber-50 text-amber-800",
};

function asNumber(value: JsonValue | undefined): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function asString(value: JsonValue | undefined): string | null {
  if (typeof value === "string") {
    const text = value.trim();
    return text ? text : null;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return null;
}

function asStringArray(value: JsonValue | undefined): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => (typeof item === "string" ? item.trim() : ""))
    .filter(Boolean);
}

function formatPrice(value: number | null): string | null {
  if (value === null) return null;
  return `${value.toFixed(2)} 元`;
}

function formatPercent(value: number | null, digits = 2): string | null {
  if (value === null) return null;
  return `${value.toFixed(digits)}%`;
}

function formatRaw(value: number | null, digits = 2): string | null {
  if (value === null) return null;
  return value.toFixed(digits);
}

function formatMoney(value: number | null): string | null {
  if (value === null) return null;
  const amount = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (amount >= 100000000) return `${sign}${(amount / 100000000).toFixed(2)}亿`;
  if (amount >= 10000) return `${sign}${(amount / 10000).toFixed(2)}万`;
  return `${value.toFixed(2)}`;
}

function formatMoneyFlow(value: number | null): string | null {
  if (value === null) return null;
  const amount = Math.abs(value);
  const text =
    amount >= 100000000
      ? `${(amount / 100000000).toFixed(2)}亿`
      : amount >= 10000
        ? `${(amount / 10000).toFixed(2)}万`
        : amount.toFixed(0);
  return `${value >= 0 ? "净流入" : "净流出"}${text}`;
}

function formatRelative(current: number | null, anchor: number | null, label: string): string | null {
  if (current === null || anchor === null || anchor === 0) return null;
  const diffPct = ((current - anchor) / anchor) * 100;
  return `${diffPct >= 0 ? "高于" : "低于"}${label} ${Math.abs(diffPct).toFixed(1)}%`;
}

function formatRange(low: number | null, high: number | null, unit = "元"): string | null {
  if (low === null && high === null) return null;
  if (low !== null && high !== null) return `${low.toFixed(2)}-${high.toFixed(2)} ${unit}`;
  const value = low ?? high;
  return value === null ? null : `${value.toFixed(2)} ${unit}`;
}

function parseLabeledLines(content: string): Array<{ label: string; value: string }> {
  return content
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const match = line.match(/^([^：:]+)[：:]\s*(.+)$/);
      if (!match) {
        return { label: "说明", value: line };
      }
      return { label: match[1].trim(), value: match[2].trim() };
    });
}

function getToneFromNumber(value: number | null, reverse = false): MetricItemProps["tone"] {
  if (value === null) return "neutral";
  if (value === 0) return "neutral";
  if (reverse) return value < 0 ? "good" : "bad";
  return value > 0 ? "good" : "bad";
}

function MetricItem({ label, value, tone = "neutral" }: MetricItemProps) {
  return (
    <div className={cn("rounded-xl border px-3 py-2.5", METRIC_TONE_STYLES[tone])}>
      <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground/70">{label}</div>
      <div className="mt-1 text-sm font-semibold leading-6">{value}</div>
    </div>
  );
}

function MetricGrid({ items }: { items: MetricItemProps[] }) {
  if (items.length === 0) return null;
  return (
    <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
      {items.map((item) => (
        <MetricItem key={`${item.label}-${item.value}`} {...item} />
      ))}
    </div>
  );
}

function SectionBlock({
  badge,
  title,
  summary = null,
  chips = [],
  accentClassName = "border-slate-200 bg-white/70",
}: SectionBlockProps) {
  return (
    <div className={cn("rounded-2xl border p-3.5", accentClassName)}>
      <div className="flex items-center gap-2">
        <Badge variant="outline" className="min-w-10 justify-center text-[11px]">
          {badge}
        </Badge>
        <div className="text-sm font-semibold text-foreground/92">{title}</div>
      </div>
      {summary && <p className="mt-2 text-sm leading-6 text-foreground/82">{summary}</p>}
      {chips.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {chips.map((chip) => (
            <Chip key={chip} variant="outline" className="border-border/50 bg-background/80 text-xs">
              {chip}
            </Chip>
          ))}
        </div>
      )}
    </div>
  );
}

function renderOperationGuidance(card: ResultCardType) {
  const metadata = card.metadata;
  const observeLow = asNumber(metadata.observe_low);
  const observeHigh = asNumber(metadata.observe_high);
  const stopPrice = asNumber(metadata.stop_price);
  const sections = parseLabeledLines(card.content);

  return (
    <div className="space-y-3">
      <MetricGrid
        items={[
          formatRange(observeLow, observeHigh) ? { label: "观察区间", value: formatRange(observeLow, observeHigh)! } : null,
          formatPrice(stopPrice) ? { label: "止损参考", value: formatPrice(stopPrice)! } : null,
        ].filter(Boolean) as MetricItemProps[]}
      />
      <div className="space-y-2">
        {sections.map((section) => (
          <div key={`${section.label}-${section.value}`} className="rounded-2xl border border-border/50 bg-background/70 p-3.5">
            <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground/70">{section.label}</div>
            <p className="mt-1.5 text-sm leading-6 text-foreground/86">{section.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function renderMultiHorizon(card: ResultCardType) {
  const metadata = card.metadata;
  const close = asNumber(metadata.close);
  const open = asNumber(metadata.open);
  const high = asNumber(metadata.high);
  const low = asNumber(metadata.low);
  const moneyFlow = asNumber(metadata.money_flow);
  const volumeRatio = asNumber(metadata.volume_ratio);
  const turnover = asNumber(metadata.turnover);
  const amount = asNumber(metadata.amount);
  const ma5 = asNumber(metadata.ma5);
  const ma10 = asNumber(metadata.ma10);
  const ma20 = asNumber(metadata.ma20);
  const ma60 = asNumber(metadata.ma60);
  const bollMid = asNumber(metadata.boll_mid);
  const rsi = asNumber(metadata.rsi);
  const macd = asNumber(metadata.macd);
  const diff = asNumber(metadata.diff);
  const dea = asNumber(metadata.dea);
  const pe = asNumber(metadata.pe);
  const pb = asNumber(metadata.pb);
  const roe = asNumber(metadata.roe);
  const revenueGrowth = asNumber(metadata.revenue_growth);
  const profitGrowth = asNumber(metadata.profit_growth);
  const operatingCashFlow = asNumber(metadata.operating_cash_flow);
  const fiveDayChange = asNumber(metadata.five_day_change);
  const twentyDayChange = asNumber(metadata.twenty_day_change);
  const reportPeriod = asString(metadata.report_period);
  const listingBoard = asString(metadata.listing_board);
  const listingPlace = asString(metadata.listing_place);
  const industry = asString(metadata.industry);
  const concept = asString(metadata.concept);

  const labeledLines = parseLabeledLines(card.content);
  const shortLine = labeledLines.find((line) => line.label === "短线")?.value || null;
  const midLine = labeledLines.find((line) => line.label === "中线")?.value || null;
  const longLine = labeledLines.find((line) => line.label === "长线")?.value || null;

  return (
    <div className="space-y-3">
      <MetricGrid
        items={[
          formatPrice(close) ? { label: "收盘", value: formatPrice(close)! } : null,
          open !== null && high !== null && low !== null
            ? { label: "日内区间", value: `${open.toFixed(2)} / ${high.toFixed(2)} / ${low.toFixed(2)}` }
            : null,
          formatMoneyFlow(moneyFlow)
            ? { label: "主力资金", value: formatMoneyFlow(moneyFlow)!, tone: getToneFromNumber(moneyFlow, true) }
            : null,
          formatPercent(volumeRatio, 2) ? { label: "量比", value: formatPercent(volumeRatio, 2)! } : null,
          formatPercent(turnover, 2) ? { label: "换手率", value: formatPercent(turnover, 2)! } : null,
          formatMoney(amount) ? { label: "成交额", value: formatMoney(amount)! } : null,
        ].filter(Boolean) as MetricItemProps[]}
      />

      <SectionBlock
        badge="短线"
        title="日内与短线节奏"
        summary={shortLine}
        chips={[
          formatRelative(close, ma5, "MA5"),
          formatRelative(close, ma10, "MA10"),
          formatPercent(rsi, 1) ? `RSI ${formatPercent(rsi, 1)}` : null,
          formatPercent(fiveDayChange, 2) ? `近5日 ${formatPercent(fiveDayChange, 2)}` : null,
          formatPercent(volumeRatio, 2) ? `量比 ${formatPercent(volumeRatio, 2)}` : null,
          formatMoneyFlow(moneyFlow),
        ].filter(Boolean) as string[]}
        accentClassName="border-amber-200 bg-amber-50/75"
      />

      <SectionBlock
        badge="中线"
        title="趋势修复与波段确认"
        summary={midLine}
        chips={[
          formatRelative(close, ma20, "MA20"),
          formatRelative(close, bollMid, "布林中轨"),
          formatPercent(twentyDayChange, 2) ? `近20日 ${formatPercent(twentyDayChange, 2)}` : null,
          formatRaw(macd, 3) ? `MACD ${formatRaw(macd, 3)}` : null,
          formatRaw(diff, 3) && formatRaw(dea, 3) ? `DIF ${formatRaw(diff, 3)} / DEA ${formatRaw(dea, 3)}` : null,
        ].filter(Boolean) as string[]}
        accentClassName="border-sky-200 bg-sky-50/75"
      />

      <SectionBlock
        badge="长线"
        title="估值、财报与产业位置"
        summary={longLine}
        chips={[
          formatRelative(close, ma60, "MA60"),
          formatRaw(pe, 2) ? `PE ${formatRaw(pe, 2)}` : null,
          formatRaw(pb, 2) ? `PB ${formatRaw(pb, 2)}` : null,
          formatPercent(roe, 2) ? `ROE ${formatPercent(roe, 2)}` : null,
          formatPercent(revenueGrowth, 2) ? `营收同比 ${formatPercent(revenueGrowth, 2)}` : null,
          formatPercent(profitGrowth, 2) ? `净利同比 ${formatPercent(profitGrowth, 2)}` : null,
          formatMoney(operatingCashFlow) ? `经营现金流 ${formatMoney(operatingCashFlow)}` : null,
          reportPeriod ? `财报期 ${reportPeriod}` : null,
          listingBoard ? `板块 ${listingBoard}` : null,
          listingPlace ? `上市地 ${listingPlace}` : null,
          industry ? `行业 ${industry}` : null,
          concept ? `题材 ${concept}` : null,
        ].filter(Boolean) as string[]}
        accentClassName="border-violet-200 bg-violet-50/75"
      />
    </div>
  );
}

function renderFundamental(card: ResultCardType) {
  const metadata = card.metadata;
  const reportPeriod = asString(metadata.report_period);
  const listingBoard = asString(metadata.listing_board);
  const listingPlace = asString(metadata.listing_place);
  const industry = asString(metadata.industry);
  const concept = asString(metadata.concept);
  const revenue = asNumber(metadata.revenue);
  const netProfit = asNumber(metadata.net_profit);
  const deductNetProfit = asNumber(metadata.deduct_net_profit);
  const operatingCashFlow = asNumber(metadata.operating_cash_flow);
  const revenueGrowth = asNumber(metadata.revenue_growth);
  const profitGrowth = asNumber(metadata.profit_growth);
  const roe = asNumber(metadata.roe);
  const grossMargin = asNumber(metadata.gross_margin);
  const debtRatio = asNumber(metadata.debt_ratio);
  const pe = asNumber(metadata.pe);
  const pb = asNumber(metadata.pb);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {reportPeriod && <Badge variant="success">财报期 {reportPeriod}</Badge>}
        {listingBoard && <Badge variant="outline">{listingBoard}</Badge>}
        {listingPlace && <Badge variant="outline">{listingPlace}</Badge>}
      </div>

      <MetricGrid
        items={[
          formatMoney(revenue) ? { label: "营业收入", value: formatMoney(revenue)! } : null,
          formatPercent(revenueGrowth, 2)
            ? { label: "营收同比", value: formatPercent(revenueGrowth, 2)!, tone: getToneFromNumber(revenueGrowth) }
            : null,
          formatMoney(netProfit) ? { label: "归母净利润", value: formatMoney(netProfit)! } : null,
          formatPercent(profitGrowth, 2)
            ? { label: "净利同比", value: formatPercent(profitGrowth, 2)!, tone: getToneFromNumber(profitGrowth) }
            : null,
          formatMoney(deductNetProfit) ? { label: "扣非归母", value: formatMoney(deductNetProfit)! } : null,
          formatMoney(operatingCashFlow) ? { label: "经营现金流", value: formatMoney(operatingCashFlow)! } : null,
          formatPercent(roe, 2) ? { label: "ROE", value: formatPercent(roe, 2)!, tone: getToneFromNumber(roe) } : null,
          formatPercent(grossMargin, 2) ? { label: "毛利率", value: formatPercent(grossMargin, 2)! } : null,
          formatPercent(debtRatio, 2) ? { label: "资产负债率", value: formatPercent(debtRatio, 2)!, tone: getToneFromNumber(debtRatio, true) } : null,
          formatRaw(pe, 2) ? { label: "PE(TTM)", value: formatRaw(pe, 2)! } : null,
          formatRaw(pb, 2) ? { label: "PB", value: formatRaw(pb, 2)! } : null,
        ].filter(Boolean) as MetricItemProps[]}
      />

      {(industry || concept) && (
        <div className="rounded-2xl border border-border/50 bg-background/70 p-3.5">
          <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground/70">行业与题材</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {industry && <Chip variant="outline" className="border-emerald-200 bg-emerald-50">{industry}</Chip>}
            {concept && <Chip variant="outline" className="border-sky-200 bg-sky-50">{concept}</Chip>}
          </div>
        </div>
      )}
    </div>
  );
}

function renderOrderbook(card: ResultCardType) {
  const metadata = card.metadata;
  const supportLow = asNumber(metadata.support_low);
  const supportHigh = asNumber(metadata.support_high);
  const weibi = asNumber(metadata.weibi);
  const weicha = asNumber(metadata.weicha);
  const lines = card.content
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  return (
    <div className="space-y-3">
      <MetricGrid
        items={[
          formatRange(supportLow, supportHigh) ? { label: "承接区间", value: formatRange(supportLow, supportHigh)! } : null,
          formatPercent(weibi, 2) ? { label: "委比", value: formatPercent(weibi, 2)!, tone: getToneFromNumber(weibi) } : null,
          formatRaw(weicha, 0) ? { label: "委差", value: formatRaw(weicha, 0)! } : null,
        ].filter(Boolean) as MetricItemProps[]}
      />

      <div className="grid gap-2">
        {lines.map((line) => (
          <div key={line} className="rounded-2xl border border-border/50 bg-background/70 px-3 py-2.5 text-sm leading-6 text-foreground/84">
            {line}
          </div>
        ))}
      </div>
    </div>
  );
}

function renderTheme(card: ResultCardType) {
  const metadata = card.metadata;
  const region = asString(metadata.region);
  const themes = asStringArray(metadata.themes);
  const lines = card.content
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  const business = lines.find((line) => line.startsWith("主营业务"))?.split("：").slice(1).join("：").trim();

  return (
    <div className="space-y-3">
      {region && <Badge variant="info">所属地域 {region}</Badge>}

      {themes.length > 0 && (
        <div className="rounded-2xl border border-border/50 bg-background/70 p-3.5">
          <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground/70">题材标签</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {themes.map((theme) => (
              <Chip key={theme} variant="outline" className="border-violet-200 bg-violet-50">
                {theme}
              </Chip>
            ))}
          </div>
        </div>
      )}

      {business && (
        <div className="rounded-2xl border border-border/50 bg-background/70 p-3.5">
          <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground/70">主营业务</div>
          <p className="mt-1.5 text-sm leading-6 text-foreground/84">{business}</p>
        </div>
      )}
    </div>
  );
}

function renderFallback(card: ResultCardType) {
  return <p className="text-sm whitespace-pre-wrap leading-7 text-foreground/84">{card.content}</p>;
}

export function StructuredResultCardContent({ card }: StructuredResultCardContentProps) {
  if (card.type === "operation_guidance") {
    return renderOperationGuidance(card);
  }
  if (card.type === "multi_horizon_analysis") {
    return renderMultiHorizon(card);
  }
  if (card.title === "财报与基本面") {
    return renderFundamental(card);
  }
  if (card.title === "同花顺盘口补充") {
    return renderOrderbook(card);
  }
  if (card.title === "同花顺题材补充") {
    return renderTheme(card);
  }
  return renderFallback(card);
}
