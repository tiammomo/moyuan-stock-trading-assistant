"use client";

import type { ReactNode } from "react";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";
import type { ChartConfig, ChartDataPoint } from "@/types/common";

interface TechnicalChartCardProps {
  chartConfig: ChartConfig;
}

const PANEL_WIDTH = 760;
const PANEL_HEIGHT = 220;
const PANEL_PADDING = { top: 18, right: 16, bottom: 24, left: 12 };

function numericValues(items: ChartDataPoint[], key: keyof ChartDataPoint): number[] {
  return items
    .map((item) => item[key])
    .filter((value): value is number => typeof value === "number" && Number.isFinite(value));
}

function clampRange(min: number, max: number) {
  if (min === max) {
    return { min: min - 1, max: max + 1 };
  }
  const padding = (max - min) * 0.08;
  return { min: min - padding, max: max + padding };
}

function buildLinePath(
  items: ChartDataPoint[],
  key: keyof ChartDataPoint,
  xAt: (index: number) => number,
  yAt: (value: number) => number
) {
  const commands: string[] = [];
  items.forEach((item, index) => {
    const value = item[key];
    if (typeof value !== "number" || !Number.isFinite(value)) return;
    commands.push(`${commands.length === 0 ? "M" : "L"} ${xAt(index)} ${yAt(value)}`);
  });
  return commands.join(" ");
}

function ChartShell({
  title,
  legend,
  children,
}: {
  title: string;
  legend: Array<{ label: string; color: string }>;
  children: ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-border/60 bg-background/90 p-3">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="text-sm font-semibold text-foreground/90">{title}</div>
        <div className="flex flex-wrap gap-2">
          {legend.map((item) => (
            <div key={item.label} className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
              <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.color }} />
              {item.label}
            </div>
          ))}
        </div>
      </div>
      {children}
    </section>
  );
}

function PricePanel({ items }: { items: ChartDataPoint[] }) {
  const highs = numericValues(items, "high");
  const lows = numericValues(items, "low");
  if (highs.length === 0 || lows.length === 0) return null;

  const range = clampRange(Math.min(...lows), Math.max(...highs));
  const innerWidth = PANEL_WIDTH - PANEL_PADDING.left - PANEL_PADDING.right;
  const innerHeight = PANEL_HEIGHT - PANEL_PADDING.top - PANEL_PADDING.bottom;
  const candleWidth = Math.max(4, innerWidth / Math.max(items.length, 1) - 2);
  const xAt = (index: number) => PANEL_PADDING.left + ((index + 0.5) * innerWidth) / items.length;
  const yAt = (value: number) =>
    PANEL_PADDING.top + ((range.max - value) / (range.max - range.min)) * innerHeight;

  return (
    <ChartShell
      title="K 线与均线"
      legend={[
        { label: "K线", color: "#0f172a" },
        { label: "MA5", color: "#f59e0b" },
        { label: "MA10", color: "#14b8a6" },
        { label: "MA20", color: "#8b5cf6" },
      ]}
    >
      <svg viewBox={`0 0 ${PANEL_WIDTH} ${PANEL_HEIGHT}`} className="w-full overflow-visible">
        <line x1={PANEL_PADDING.left} y1={PANEL_PADDING.top} x2={PANEL_PADDING.left} y2={PANEL_HEIGHT - PANEL_PADDING.bottom} stroke="#cbd5e1" strokeWidth={1} />
        <line x1={PANEL_PADDING.left} y1={PANEL_HEIGHT - PANEL_PADDING.bottom} x2={PANEL_WIDTH - PANEL_PADDING.right} y2={PANEL_HEIGHT - PANEL_PADDING.bottom} stroke="#cbd5e1" strokeWidth={1} />
        {items.map((item, index) => {
          if (
            item.open === null ||
            item.close === null ||
            item.high === null ||
            item.low === null
          ) {
            return null;
          }
          const x = xAt(index);
          const openY = yAt(item.open);
          const closeY = yAt(item.close);
          const highY = yAt(item.high);
          const lowY = yAt(item.low);
          const rise = item.close >= item.open;
          const bodyTop = Math.min(openY, closeY);
          const bodyHeight = Math.max(Math.abs(openY - closeY), 1.5);
          const color = rise ? "#ef4444" : "#22c55e";
          return (
            <g key={`${item.time}-${index}`}>
              <line x1={x} x2={x} y1={highY} y2={lowY} stroke={color} strokeWidth={1.2} />
              <rect x={x - candleWidth / 2} y={bodyTop} width={candleWidth} height={bodyHeight} fill={rise ? color : "transparent"} stroke={color} strokeWidth={1.2} />
            </g>
          );
        })}
        {[
          { key: "ma5" as const, color: "#f59e0b" },
          { key: "ma10" as const, color: "#14b8a6" },
          { key: "ma20" as const, color: "#8b5cf6" },
        ].map((line) => {
          const path = buildLinePath(items, line.key, xAt, yAt);
          if (!path) return null;
          return <path key={line.key} d={path} fill="none" stroke={line.color} strokeWidth={1.8} strokeLinejoin="round" strokeLinecap="round" />;
        })}
      </svg>
    </ChartShell>
  );
}

function VolumePanel({ items }: { items: ChartDataPoint[] }) {
  const volumes = numericValues(items, "volume");
  if (volumes.length === 0) return null;

  const maxVolume = Math.max(...volumes) || 1;
  const innerWidth = PANEL_WIDTH - PANEL_PADDING.left - PANEL_PADDING.right;
  const innerHeight = PANEL_HEIGHT - PANEL_PADDING.top - PANEL_PADDING.bottom;
  const barWidth = Math.max(3, innerWidth / Math.max(items.length, 1) - 2);
  const xAt = (index: number) => PANEL_PADDING.left + (index * innerWidth) / items.length;

  return (
    <ChartShell title="成交量" legend={[{ label: "Volume", color: "#38bdf8" }]}>
      <svg viewBox={`0 0 ${PANEL_WIDTH} ${PANEL_HEIGHT}`} className="w-full overflow-visible">
        <line x1={PANEL_PADDING.left} y1={PANEL_HEIGHT - PANEL_PADDING.bottom} x2={PANEL_WIDTH - PANEL_PADDING.right} y2={PANEL_HEIGHT - PANEL_PADDING.bottom} stroke="#cbd5e1" strokeWidth={1} />
        {items.map((item, index) => {
          if (item.volume === null) return null;
          const x = xAt(index);
          const height = (item.volume / maxVolume) * innerHeight;
          const y = PANEL_HEIGHT - PANEL_PADDING.bottom - height;
          const rise = typeof item.open === "number" && typeof item.close === "number" ? item.close >= item.open : true;
          return (
            <rect
              key={`${item.time}-${index}`}
              x={x}
              y={y}
              width={barWidth}
              height={height}
              rx={1.5}
              fill={rise ? "#fca5a5" : "#86efac"}
            />
          );
        })}
      </svg>
    </ChartShell>
  );
}

function OscillatorPanel({
  title,
  items,
  histogramKey,
  lineDefs,
  fixedRange,
}: {
  title: string;
  items: ChartDataPoint[];
  histogramKey?: keyof ChartDataPoint;
  lineDefs: Array<{ key: keyof ChartDataPoint; label: string; color: string }>;
  fixedRange?: { min: number; max: number };
}) {
  const values = [
    ...(histogramKey ? numericValues(items, histogramKey) : []),
    ...lineDefs.flatMap((line) => numericValues(items, line.key)),
  ];
  if (values.length === 0) return null;

  const inferred = fixedRange || clampRange(Math.min(...values), Math.max(...values));
  const range = fixedRange ? inferred : clampRange(inferred.min, inferred.max);
  const innerWidth = PANEL_WIDTH - PANEL_PADDING.left - PANEL_PADDING.right;
  const innerHeight = PANEL_HEIGHT - PANEL_PADDING.top - PANEL_PADDING.bottom;
  const xAt = (index: number) => PANEL_PADDING.left + ((index + 0.5) * innerWidth) / items.length;
  const yAt = (value: number) =>
    PANEL_PADDING.top + ((range.max - value) / (range.max - range.min)) * innerHeight;
  const zeroY = yAt(0);
  const barWidth = Math.max(3, innerWidth / Math.max(items.length, 1) - 2);

  return (
    <ChartShell
      title={title}
      legend={[
        ...(histogramKey ? [{ label: "Histogram", color: "#94a3b8" }] : []),
        ...lineDefs.map((line) => ({ label: line.label, color: line.color })),
      ]}
    >
      <svg viewBox={`0 0 ${PANEL_WIDTH} ${PANEL_HEIGHT}`} className="w-full overflow-visible">
        <line x1={PANEL_PADDING.left} y1={PANEL_HEIGHT - PANEL_PADDING.bottom} x2={PANEL_WIDTH - PANEL_PADDING.right} y2={PANEL_HEIGHT - PANEL_PADDING.bottom} stroke="#cbd5e1" strokeWidth={1} />
        {histogramKey &&
          items.map((item, index) => {
            const value = item[histogramKey];
            if (typeof value !== "number") return null;
            const x = PANEL_PADDING.left + (index * innerWidth) / items.length;
            const y = value >= 0 ? yAt(value) : zeroY;
            const height = Math.max(Math.abs(zeroY - yAt(value)), 1.5);
            return (
              <rect
                key={`${item.time}-${index}`}
                x={x}
                y={y}
                width={barWidth}
                height={height}
                rx={1}
                fill={value >= 0 ? "#f59e0b" : "#94a3b8"}
              />
            );
          })}
        {lineDefs.map((line) => {
          const path = buildLinePath(items, line.key, xAt, yAt);
          if (!path) return null;
          return <path key={line.key} d={path} fill="none" stroke={line.color} strokeWidth={1.8} strokeLinejoin="round" strokeLinecap="round" />;
        })}
      </svg>
    </ChartShell>
  );
}

export function TechnicalChartCard({ chartConfig }: TechnicalChartCardProps) {
  const items = chartConfig.items || [];
  if (items.length === 0) return null;

  const hasType = (type: string) => chartConfig.chart_types.includes(type);

  return (
    <div className="space-y-3 rounded-2xl border border-border/70 bg-card/95 p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground/70">Technical Charts</div>
          <div className="mt-1 text-base font-semibold text-foreground/92">
            {chartConfig.subject ? `${chartConfig.subject} 技术图表` : "技术图表"}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {chartConfig.chart_types.map((type) => (
            <Badge key={type} variant="outline" className="text-[11px]">
              {type.toUpperCase()}
            </Badge>
          ))}
        </div>
      </div>

      <div className={cn("space-y-3")}>
        {hasType("kline") && <PricePanel items={items} />}
        {hasType("volume") && <VolumePanel items={items} />}
        {hasType("macd") && (
          <OscillatorPanel
            title="MACD"
            items={items}
            histogramKey="macd"
            lineDefs={[
              { key: "dif", label: "DIF", color: "#2563eb" },
              { key: "dea", label: "DEA", color: "#dc2626" },
            ]}
          />
        )}
        {hasType("rsi") && (
          <OscillatorPanel
            title="RSI"
            items={items}
            lineDefs={[{ key: "rsi", label: "RSI", color: "#7c3aed" }]}
            fixedRange={{ min: 0, max: 100 }}
          />
        )}
        {hasType("kdj") && (
          <OscillatorPanel
            title="KDJ"
            items={items}
            lineDefs={[
              { key: "k", label: "K", color: "#0f766e" },
              { key: "d", label: "D", color: "#2563eb" },
              { key: "j", label: "J", color: "#db2777" },
            ]}
            fixedRange={{ min: 0, max: 100 }}
          />
        )}
      </div>
    </div>
  );
}
