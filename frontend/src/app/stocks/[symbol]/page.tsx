"use client";

import Link from "next/link";
import { useMemo } from "react";
import { useParams } from "next/navigation";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { useMonitorRules } from "@/hooks/useMonitorRules";
import { usePortfolio } from "@/hooks/usePortfolio";
import { useWatchMonitor } from "@/hooks/useWatchMonitor";
import { useWatchlist } from "@/hooks/useWatchlist";
import { BUCKET_LABELS, formatTimestamp } from "@/lib/utils";

function normalizeSymbol(value: string): string {
  return decodeURIComponent(value || "").trim().toUpperCase();
}

export default function StockDetailPage() {
  const params = useParams<{ symbol: string }>();
  const symbol = normalizeSymbol(params.symbol);
  const { watchlist } = useWatchlist();
  const { rules } = useMonitorRules();
  const { events } = useWatchMonitor();
  const { summary } = usePortfolio();

  const watchItem = useMemo(
    () => watchlist.find((item) => item.symbol.toUpperCase() === symbol),
    [symbol, watchlist]
  );
  const stockRules = rules.filter((rule) => rule.symbol.toUpperCase() === symbol);
  const stockEvents = events.filter((event) => event.symbol.toUpperCase() === symbol);
  const positions = (summary?.accounts ?? [])
    .flatMap((account) => account.positions.map((position) => ({ ...position, account_name: account.name })))
    .filter((position) => position.symbol.toUpperCase() === symbol);

  const displayName = watchItem?.name || positions[0]?.name || symbol;

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-sm text-muted-foreground">个股详情</div>
          <h1 className="mt-1 text-2xl font-bold">{displayName}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <Badge variant="outline">{symbol}</Badge>
            {watchItem && <Badge variant="secondary">{BUCKET_LABELS[watchItem.bucket]}</Badge>}
            {positions.length > 0 && <Badge variant="outline">持仓 {positions.length} 笔</Badge>}
          </div>
        </div>
        <div className="flex gap-2">
          <Link href="/monitor"><Button variant="outline" size="sm">配置提醒</Button></Link>
          <Link href="/portfolio"><Button variant="outline" size="sm">查看持仓</Button></Link>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2"><CardDescription>候选池状态</CardDescription></CardHeader>
          <CardContent className="text-sm">
            {watchItem ? (
              <div className="space-y-2">
                <div>分组：{BUCKET_LABELS[watchItem.bucket]}</div>
                <div>标签：{watchItem.tags.length ? watchItem.tags.join("、") : "-"}</div>
                <div>更新：{formatTimestamp(watchItem.updated_at)}</div>
              </div>
            ) : "未加入候选池"}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardDescription>提醒规则</CardDescription></CardHeader>
          <CardContent className="text-2xl font-semibold">{stockRules.length}</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardDescription>最近事件</CardDescription></CardHeader>
          <CardContent className="text-2xl font-semibold">{stockEvents.length}</CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>持仓联动风险</CardTitle>
          <CardDescription>把持仓成本、盈亏和交易风格放到个股维度统一观察。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {positions.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border/70 px-4 py-6 text-sm text-muted-foreground">当前没有这只股票的持仓。</div>
          ) : positions.map((position) => (
            <div key={position.id} className="rounded-xl border border-border/70 px-4 py-3 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="font-medium">{position.account_name}</div>
                <Badge variant={position.pnl_pct !== null && position.pnl_pct !== undefined && position.pnl_pct < -5 ? "warning" : "secondary"}>
                  盈亏 {position.pnl_pct === null || position.pnl_pct === undefined ? "-" : `${position.pnl_pct.toFixed(2)}%`}
                </Badge>
              </div>
              <div className="mt-2 grid gap-2 text-muted-foreground md:grid-cols-4">
                <div>成本 {position.cost_price.toFixed(2)}</div>
                <div>现价 {position.latest_price?.toFixed(2) ?? "-"}</div>
                <div>数量 {position.quantity}</div>
                <div>仓位 {position.weight_pct.toFixed(1)}%</div>
              </div>
              {position.advice && <div className="mt-2 rounded-lg bg-muted/30 px-3 py-2 text-xs leading-5">{position.advice.action}</div>}
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>规则与事件</CardTitle>
          <CardDescription>后续可在这里继续接入 K 线、新闻、公告和 AI 交易计划卡。</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <div className="text-sm font-medium">提醒规则</div>
            {stockRules.length === 0 ? <div className="text-sm text-muted-foreground">暂无规则</div> : stockRules.map((rule) => (
              <div key={rule.id} className="rounded-xl border border-border/60 px-3 py-2 text-sm">
                <div className="font-medium">{rule.rule_name}</div>
                <div className="mt-1 text-xs text-muted-foreground">{rule.enabled ? "启用" : "停用"} · {rule.condition_group.items.length} 个条件</div>
              </div>
            ))}
          </div>
          <div className="space-y-2">
            <div className="text-sm font-medium">最近事件</div>
            {stockEvents.length === 0 ? <div className="text-sm text-muted-foreground">暂无事件</div> : stockEvents.map((event) => (
              <div key={event.id} className="rounded-xl border border-border/60 px-3 py-2 text-sm">
                <div className="font-medium">{event.title}</div>
                <div className="mt-1 text-xs leading-5 text-muted-foreground">{event.ai_explanation || event.summary}</div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
