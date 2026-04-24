"use client";

import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/Card";
import { toast } from "@/components/ui/Toast";
import { MonitorRuleForm } from "@/components/monitor/MonitorRuleForm";
import { useMonitorNotifications } from "@/hooks/useMonitorNotifications";
import { useMonitorRules } from "@/hooks/useMonitorRules";
import { useWatchMonitor } from "@/hooks/useWatchMonitor";
import { useWatchlist } from "@/hooks/useWatchlist";
import { BUCKET_COLORS, BUCKET_LABELS, cn, formatTimestamp } from "@/lib/utils";
import type {
  MonitorRuleCondition,
  MonitorRuleRecord,
  WatchMonitorEvent,
} from "@/types/watchlist";

const EVENT_TYPE_LABELS: Record<string, string> = {
  price_move: "价格异动",
  orderbook_bias: "盘口异动",
  volume_spike: "量能异动",
  volatility: "波动异动",
  valuation_watch: "估值观察",
  watch_update: "行情变化",
};

const EVENT_REASON_LABELS: Record<string, string> = {
  pct_threshold: "价格到阈值",
  pct_jump: "涨跌突变",
  volume_ratio_alert: "量比放大",
  orderbook_bias: "盘口偏移",
  latest_price: "现价",
  change_pct: "涨跌幅",
  volume_ratio: "量比",
  weibi: "委比",
  amount: "成交额",
  volume: "成交量",
  turnover_pct: "换手率",
  amplitude_pct: "振幅",
  waipan: "外盘",
  neipan: "内盘",
  weicha: "委差",
  pb: "市净率",
  pe_dynamic: "动态市盈率",
  total_market_value: "总市值",
  float_market_value: "流通市值",
};

const CONDITION_LABELS: Record<string, string> = {
  latest_price: "现价",
  change_pct: "涨跌幅",
  volume_ratio: "量比",
  weibi: "委比",
  amount: "成交额",
  volume: "成交量",
  turnover_pct: "换手率",
  amplitude_pct: "振幅",
  waipan: "外盘",
  neipan: "内盘",
  weicha: "委差",
  pb: "市净率",
  pe_dynamic: "动态市盈率",
  total_market_value: "总市值",
  float_market_value: "流通市值",
};

const SEVERITY_LABELS: Record<string, string> = {
  info: "普通",
  warning: "重点",
};

const MARKET_HOURS_LABELS: Record<string, string> = {
  trading_only: "仅交易时段",
  always: "全天生效",
};

const REPEAT_MODE_LABELS: Record<string, string> = {
  repeat: "重复触发",
  once: "仅一次",
};

function monitorEventTypeLabel(value: string): string {
  return EVENT_TYPE_LABELS[value] || value;
}

function monitorReasonLabel(value: string): string {
  return EVENT_REASON_LABELS[value] || value;
}

function formatConditionTarget(condition: MonitorRuleCondition): string {
  const suffix = ["change_pct", "weibi", "turnover_pct", "amplitude_pct"].includes(condition.type) ? "%" : "";
  if (condition.op === "between" && Array.isArray(condition.value)) {
    const [start, end] = condition.value;
    return `${start}${suffix} 到 ${end}${suffix}`;
  }
  return `${condition.op} ${condition.value}${suffix}`;
}

function ruleSummary(rule: MonitorRuleRecord): string {
  const prefix = rule.condition_group.op === "and" ? "全部满足" : "任一满足";
  const items = rule.condition_group.items.map((condition) => {
    const label = CONDITION_LABELS[condition.type] || condition.type;
    return `${label} ${formatConditionTarget(condition)}`;
  });
  return `${prefix}：${items.join("；")}`;
}

function renderEventBadges(event: WatchMonitorEvent) {
  const changePct = typeof event.metrics.change_pct === "number" ? event.metrics.change_pct : null;
  const volumeRatio = typeof event.metrics.volume_ratio === "number" ? event.metrics.volume_ratio : null;
  const weibi = typeof event.metrics.weibi === "number" ? event.metrics.weibi : null;
  const turnoverPct = typeof event.metrics.turnover_pct === "number" ? event.metrics.turnover_pct : null;
  const amplitudePct = typeof event.metrics.amplitude_pct === "number" ? event.metrics.amplitude_pct : null;

  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {event.reasons.map((reason) => (
        <Badge key={`${event.id}-${reason}`} variant="secondary" className="text-[10px]">
          {monitorReasonLabel(reason)}
        </Badge>
      ))}
      {changePct !== null && (
        <Badge variant="outline" className="text-[10px]">
          涨跌幅 {changePct >= 0 ? "+" : ""}
          {changePct.toFixed(2)}%
        </Badge>
      )}
      {volumeRatio !== null && (
        <Badge variant="outline" className="text-[10px]">
          量比 {volumeRatio.toFixed(2)}
        </Badge>
      )}
      {weibi !== null && (
        <Badge variant="outline" className="text-[10px]">
          委比 {weibi.toFixed(2)}%
        </Badge>
      )}
      {turnoverPct !== null && (
        <Badge variant="outline" className="text-[10px]">
          换手率 {turnoverPct.toFixed(2)}%
        </Badge>
      )}
      {amplitudePct !== null && (
        <Badge variant="outline" className="text-[10px]">
          振幅 {amplitudePct.toFixed(2)}%
        </Badge>
      )}
    </div>
  );
}

export function MonitorDashboard() {
  const [editingRule, setEditingRule] = useState<MonitorRuleRecord | null>(null);
  const [isRuleDialogOpen, setIsRuleDialogOpen] = useState(false);
  const {
    status: monitorStatus,
    events: monitorEvents,
    isScanning,
    triggerScanAsync,
  } = useWatchMonitor();
  const { watchlist } = useWatchlist();
  const { channels: notificationChannels } = useMonitorNotifications({
    includeSettings: false,
    includeDeliveries: false,
  });
  const {
    rules: monitorRules,
    isLoading: isRulesLoading,
    isCreating,
    isUpdating,
    isDeleting,
    createRuleAsync,
    updateRuleAsync,
    deleteRuleAsync,
  } = useMonitorRules();

  const isSubmittingRule = isCreating || isUpdating;
  const sortedRules = useMemo(
    () =>
      [...monitorRules].sort(
        (left, right) => new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime()
      ),
    [monitorRules]
  );

  const handleTriggerMonitorScan = async () => {
    try {
      const result = await triggerScanAsync();
      if (result.triggered_count > 0) {
        toast.success(`本轮扫描发现 ${result.triggered_count} 条盯盘事件`);
      } else if (result.scanned_count > 0) {
        toast.success(`已扫描 ${result.scanned_count} 只候选股，暂未发现新事件`);
      } else {
        toast.warning("当前非交易时段，本轮扫描未执行");
      }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "盯盘扫描失败");
    }
  };

  const handleCreateRule = async (payload: Parameters<typeof createRuleAsync>[0]) => {
    await createRuleAsync(payload);
    toast.success("提醒规则已创建");
  };

  const handleUpdateRule = async (
    ruleId: string,
    payload: Parameters<typeof updateRuleAsync>[0]["data"]
  ) => {
    await updateRuleAsync({ id: ruleId, data: payload });
    toast.success("提醒规则已更新");
  };

  const handleDeleteRule = async (rule: MonitorRuleRecord) => {
    if (!confirm(`确定删除规则「${rule.rule_name}」吗？`)) {
      return;
    }
    try {
      await deleteRuleAsync(rule.id);
      toast.success(`已删除规则：${rule.rule_name}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "删除规则失败");
    }
  };

  const openCreateRule = () => {
    setEditingRule(null);
    setIsRuleDialogOpen(true);
  };

  const openEditRule = (rule: MonitorRuleRecord) => {
    setEditingRule(rule);
    setIsRuleDialogOpen(true);
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <CardTitle>实时盯盘</CardTitle>
              <CardDescription>候选池驱动的后台扫描和异动事件流</CardDescription>
            </div>
            <Badge
              variant="outline"
              className={cn(
                "text-xs",
                monitorStatus?.market_phase === "open"
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                  : "border-slate-200 bg-slate-50 text-slate-600"
              )}
            >
              {monitorStatus?.market_phase === "open" ? "交易时段" : "非交易时段"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4 text-sm">
            <div className="rounded-xl border border-border/60 bg-muted/35 px-3 py-3">
              <div className="text-xs text-muted-foreground">扫描间隔</div>
              <div className="mt-1 font-medium">
                {monitorStatus ? `${monitorStatus.interval_seconds}s` : "--"}
              </div>
            </div>
            <div className="rounded-xl border border-border/60 bg-muted/35 px-3 py-3">
              <div className="text-xs text-muted-foreground">累计事件</div>
              <div className="mt-1 font-medium">
                {monitorStatus ? monitorStatus.event_count : "--"}
              </div>
            </div>
            <div className="rounded-xl border border-border/60 bg-muted/35 px-3 py-3">
              <div className="text-xs text-muted-foreground">候选池数量</div>
              <div className="mt-1 font-medium">
                {monitorStatus ? monitorStatus.watchlist_count : "--"}
              </div>
            </div>
            <div className="rounded-xl border border-border/60 bg-muted/35 px-3 py-3">
              <div className="text-xs text-muted-foreground">最近扫描</div>
              <div className="mt-1 font-medium">
                {monitorStatus?.last_scan_at ? formatTimestamp(monitorStatus.last_scan_at) : "暂无"}
              </div>
            </div>
          </div>
          {monitorStatus?.last_error && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700">
              最近一次扫描异常：{monitorStatus.last_error}
            </div>
          )}
          <div className="flex items-center justify-between gap-3">
            <div className="text-xs text-muted-foreground">
              {monitorStatus?.last_scan_duration_ms
                ? `最近一次扫描耗时 ${monitorStatus.last_scan_duration_ms}ms`
                : "当前版本基于候选池扫描，并按规则做冷却和日上限控制"}
            </div>
            <Button
              variant="outline"
              size="sm"
              disabled={isScanning}
              onClick={() => void handleTriggerMonitorScan()}
            >
              {isScanning ? "扫描中..." : "立即扫描"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <CardTitle>提醒规则</CardTitle>
              <CardDescription>支持多指标、规则级通知渠道覆盖、交易时段、过期时间、重复模式、冷却和日上限</CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={openCreateRule}
              disabled={watchlist.length === 0}
            >
              新增规则
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {watchlist.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border/70 px-4 py-8 text-center text-sm text-muted-foreground">
              候选池还是空的。先添加股票，再为单只股票配置提醒规则。
            </div>
          ) : isRulesLoading ? (
            <div className="rounded-xl border border-dashed border-border/70 px-4 py-8 text-center text-sm text-muted-foreground">
              正在加载规则...
            </div>
          ) : sortedRules.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border/70 px-4 py-8 text-center text-sm text-muted-foreground">
              还没有规则。候选池股票会自动 seed 一条默认异动提醒，你也可以手动新增更窄的规则。
            </div>
          ) : (
            <div className="space-y-3">
              {sortedRules.map((rule) => {
                const notifyChannelIds = rule.notify_channel_ids ?? [];
                return (
                  <div
                    key={rule.id}
                    className="rounded-2xl border border-border/70 bg-card/70 px-4 py-4"
                  >
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0 space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">{rule.rule_name}</span>
                        <Badge variant="outline" className="text-[10px]">
                          {rule.name} {rule.symbol}
                        </Badge>
                        <Badge
                          variant="outline"
                          className={cn("text-[10px]", BUCKET_COLORS[rule.bucket])}
                        >
                          {BUCKET_LABELS[rule.bucket]}
                        </Badge>
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-[10px]",
                            rule.enabled
                              ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                              : "border-slate-200 bg-slate-50 text-slate-500"
                          )}
                        >
                          {rule.enabled ? "启用中" : "已停用"}
                        </Badge>
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-[10px]",
                            rule.severity === "warning"
                              ? "border-amber-200 bg-amber-50 text-amber-700"
                              : "border-sky-200 bg-sky-50 text-sky-700"
                          )}
                        >
                          {SEVERITY_LABELS[rule.severity]}
                        </Badge>
                      </div>
                      <div className="text-sm leading-6 text-foreground/90">{ruleSummary(rule)}</div>
                      <div className="flex flex-wrap gap-1.5 text-xs text-muted-foreground">
                        <span>
                          {notifyChannelIds.length > 0
                            ? `通知渠道 ${notifyChannelIds.length} 个`
                            : "通知渠道使用默认配置"}
                        </span>
                        <span>{MARKET_HOURS_LABELS[rule.market_hours_mode] || rule.market_hours_mode}</span>
                        <span>{REPEAT_MODE_LABELS[rule.repeat_mode] || rule.repeat_mode}</span>
                        <span>冷却 {rule.cooldown_minutes} 分钟</span>
                        <span>每日上限 {rule.max_triggers_per_day} 次</span>
                        <span>
                          {rule.expire_at ? `过期于 ${formatTimestamp(rule.expire_at)}` : "长期有效"}
                        </span>
                        <span>更新于 {formatTimestamp(rule.updated_at)}</span>
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <Button variant="ghost" size="sm" onClick={() => openEditRule(rule)}>
                        编辑
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => void handleDeleteRule(rule)}
                        disabled={isDeleting}
                      >
                        删除
                      </Button>
                    </div>
                  </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle>最近盯盘事件</CardTitle>
          <CardDescription>事件会沉淀到本地事件流，并按默认渠道或规则覆盖渠道推送</CardDescription>
        </CardHeader>
        <CardContent>
          {monitorEvents.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border/70 px-4 py-8 text-center text-sm text-muted-foreground">
              还没有新的盯盘事件。后台会按候选池定时扫描，命中阈值后出现在这里。
            </div>
          ) : (
            <div className="space-y-3">
              {monitorEvents.map((event) => (
                <div
                  key={event.id}
                  className="rounded-2xl border border-border/70 bg-card/70 px-4 py-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium">{event.name}</span>
                        <span className="text-xs text-muted-foreground">{event.symbol}</span>
                        <Badge
                          variant="outline"
                          className={cn("text-[10px]", BUCKET_COLORS[event.bucket])}
                        >
                          {BUCKET_LABELS[event.bucket]}
                        </Badge>
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-[10px]",
                            event.severity === "warning"
                              ? "border-amber-200 bg-amber-50 text-amber-700"
                              : "border-sky-200 bg-sky-50 text-sky-700"
                          )}
                        >
                          {monitorEventTypeLabel(event.event_type)}
                        </Badge>
                        {event.rule_name && (
                          <Badge variant="secondary" className="text-[10px]">
                            {event.rule_name}
                          </Badge>
                        )}
                      </div>
                      <p className="mt-2 text-sm leading-6 text-foreground/90">{event.summary}</p>
                      {renderEventBadges(event)}
                    </div>
                    <div className="shrink-0 text-xs text-muted-foreground">
                      {formatTimestamp(event.created_at)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <MonitorRuleForm
        open={isRuleDialogOpen}
        onOpenChange={setIsRuleDialogOpen}
        watchlist={watchlist}
        notificationChannels={notificationChannels.filter((channel) => channel.enabled)}
        initialRule={editingRule}
        onCreate={handleCreateRule}
        onUpdate={handleUpdateRule}
        isSubmitting={isSubmittingRule}
      />
    </div>
  );
}
