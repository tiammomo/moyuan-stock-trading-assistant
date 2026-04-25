"use client";

import { useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { useMonitorNotifications } from "@/hooks/useMonitorNotifications";
import { useScheduledReports } from "@/hooks/useScheduledReports";
import { cn, formatDateTime, formatTimestamp } from "@/lib/utils";
import type {
  ScheduledReportJobRecord,
  ScheduledReportType,
} from "@/types/scheduledReport";


const REPORT_META: Record<
  ScheduledReportType,
  {
    title: string;
    description: string;
    defaultTimeHint: string;
  }
> = {
  news_digest: {
    title: "新闻摘要",
    description: "按候选池和持仓聚合新闻标题，适合开盘前快速过一遍催化。",
    defaultTimeHint: "08:50",
  },
  pre_market_watchlist: {
    title: "盘前观察清单",
    description: "基于候选池和规则，给出当天优先观察标的。",
    defaultTimeHint: "09:05",
  },
  portfolio_daily: {
    title: "持仓日报",
    description: "汇总持仓盈亏、日内波动和重点仓位表现。",
    defaultTimeHint: "15:10",
  },
  post_market_review: {
    title: "盘后复盘",
    description: "统计当天监控事件和观察池表现，沉淀收盘复盘。",
    defaultTimeHint: "15:20",
  },
};

const STATUS_META: Record<
  string,
  {
    label: string;
    className: string;
  }
> = {
  success: { label: "成功", className: "bg-emerald-500/12 text-emerald-200 border-emerald-400/20" },
  failed: { label: "失败", className: "bg-red-500/12 text-red-200 border-red-400/20" },
  skipped: { label: "跳过", className: "bg-amber-500/12 text-amber-200 border-amber-400/20" },
};

type JobDraftMap = Record<
  ScheduledReportType,
  {
    enabled: boolean;
    schedule_time: string;
    channel_ids: string[];
  }
>;

function buildDrafts(jobs: ScheduledReportJobRecord[]): JobDraftMap {
  return jobs.reduce((acc, job) => {
    acc[job.report_type] = {
      enabled: job.enabled,
      schedule_time: job.schedule_time,
      channel_ids: job.channel_ids ?? [],
    };
    return acc;
  }, {} as JobDraftMap);
}

export function ScheduledReportSettings() {
  const { channels } = useMonitorNotifications({ includeSettings: false, includeDeliveries: false });
  const { jobs, runs, isLoading, isSaving, isTriggering, updateJobAsync, triggerJobAsync } =
    useScheduledReports();
  const [drafts, setDrafts] = useState<JobDraftMap>({} as JobDraftMap);

  useEffect(() => {
    if (jobs.length > 0) {
      setDrafts(buildDrafts(jobs));
    }
  }, [jobs]);

  const enabledChannels = useMemo(
    () => channels.filter((channel) => channel.enabled),
    [channels]
  );

  const updateDraft = (
    reportType: ScheduledReportType,
    patch: Partial<JobDraftMap[ScheduledReportType]>
  ) => {
    setDrafts((current) => ({
      ...current,
      [reportType]: {
        enabled: current[reportType]?.enabled ?? false,
        schedule_time: current[reportType]?.schedule_time ?? REPORT_META[reportType].defaultTimeHint,
        channel_ids: current[reportType]?.channel_ids ?? [],
        ...patch,
      },
    }));
  };

  const toggleChannel = (reportType: ScheduledReportType, channelId: string) => {
    const currentIds = drafts[reportType]?.channel_ids ?? [];
    const nextIds = currentIds.includes(channelId)
      ? currentIds.filter((id) => id !== channelId)
      : [...currentIds, channelId];
    updateDraft(reportType, { channel_ids: nextIds });
  };

  const handleSave = async (job: ScheduledReportJobRecord) => {
    const draft = drafts[job.report_type];
    if (!draft) return;
    await updateJobAsync({
      reportType: job.report_type,
      data: {
        enabled: draft.enabled,
        schedule_time: draft.schedule_time,
        channel_ids: draft.channel_ids,
      },
    });
  };

  const handleTrigger = async (reportType: ScheduledReportType) => {
    await triggerJobAsync(reportType);
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>调度型日报</CardTitle>
          <CardDescription>加载日报配置中…</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <section className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>调度型日报</CardTitle>
          <CardDescription>
            为盘前、盘后、持仓和新闻建立固定推送节奏。频道留空时会回落到盯盘默认通知渠道。
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {jobs.map((job) => {
            const draft = drafts[job.report_type] ?? {
              enabled: job.enabled,
              schedule_time: job.schedule_time,
              channel_ids: job.channel_ids ?? [],
            };
            return (
              <div
                key={job.report_type}
                className="rounded-2xl border border-border/60 bg-muted/20 p-4"
              >
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-base font-semibold">{REPORT_META[job.report_type].title}</h3>
                      <Badge
                        variant="outline"
                        className={cn(
                          draft.enabled
                            ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-200"
                            : "border-border/60 bg-background/50 text-muted-foreground"
                        )}
                      >
                        {draft.enabled ? "已启用" : "未启用"}
                      </Badge>
                    </div>
                    <p className="text-sm leading-6 text-muted-foreground">
                      {REPORT_META[job.report_type].description}
                    </p>
                    <div className="text-xs text-muted-foreground">
                      最近修改：{formatTimestamp(job.updated_at)}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant={draft.enabled ? "secondary" : "outline"}
                      size="sm"
                      onClick={() => updateDraft(job.report_type, { enabled: !draft.enabled })}
                    >
                      {draft.enabled ? "停用" : "启用"}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={isTriggering}
                      onClick={() => void handleTrigger(job.report_type)}
                    >
                      立即触发
                    </Button>
                    <Button
                      size="sm"
                      disabled={isSaving}
                      onClick={() => void handleSave(job)}
                    >
                      保存配置
                    </Button>
                  </div>
                </div>

                <div className="mt-4 grid gap-4 lg:grid-cols-[180px,1fr]">
                  <div>
                    <label className="mb-1 block text-sm font-medium">发送时间</label>
                    <Input
                      type="time"
                      value={draft.schedule_time}
                      onChange={(event) =>
                        updateDraft(job.report_type, { schedule_time: event.target.value })
                      }
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-sm font-medium">通知渠道覆盖</label>
                    {enabledChannels.length === 0 ? (
                      <div className="rounded-xl border border-dashed border-border/70 px-3 py-2 text-sm text-muted-foreground">
                        当前还没有可用通知渠道，保存后会回落到默认配置。
                      </div>
                    ) : (
                      <div className="flex flex-wrap gap-2">
                        {enabledChannels.map((channel) => {
                          const selected = draft.channel_ids.includes(channel.id);
                          return (
                            <Button
                              key={channel.id}
                              type="button"
                              variant={selected ? "secondary" : "outline"}
                              size="sm"
                              onClick={() => toggleChannel(job.report_type, channel.id)}
                            >
                              {channel.name}
                            </Button>
                          );
                        })}
                      </div>
                    )}
                    <div className="mt-2 text-xs text-muted-foreground">
                      {draft.channel_ids.length > 0
                        ? `已覆盖 ${draft.channel_ids.length} 个渠道`
                        : "未覆盖时使用盯盘默认通知渠道"}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>最近运行</CardTitle>
          <CardDescription>包含手动触发和自动调度的日报执行结果。</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {runs.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border/70 px-4 py-5 text-sm text-muted-foreground">
              还没有日报运行记录。
            </div>
          ) : (
            runs.map((run) => {
              const statusMeta = STATUS_META[run.status] ?? STATUS_META.skipped;
              return (
                <div
                  key={run.id}
                  className="rounded-2xl border border-border/60 bg-muted/20 p-4"
                >
                  <div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <div className="font-medium">{run.title}</div>
                        <Badge variant="outline" className={statusMeta.className}>
                          {statusMeta.label}
                        </Badge>
                        <Badge variant="outline" className="border-border/60 bg-background/50 text-muted-foreground">
                          {run.trigger === "scheduled" ? "自动调度" : "手动触发"}
                        </Badge>
                        {run.ai_enhanced && (
                          <Badge variant="outline" className="border-primary/30 bg-primary/10 text-primary">
                            AI 增强{run.ai_provider ? ` · ${run.ai_provider}` : ""}
                          </Badge>
                        )}
                      </div>
                      <div className="text-sm text-muted-foreground">{run.summary}</div>
                      {run.reason && (
                        <div className="text-xs text-amber-300">{run.reason}</div>
                      )}
                    </div>
                    <div className="text-right text-xs text-muted-foreground">
                      <div>{formatDateTime(run.created_at)}</div>
                      <div>
                        发送成功 {run.delivered_count} 次
                        {run.channel_ids.length > 0 ? ` · 指定渠道 ${run.channel_ids.length} 个` : " · 默认渠道"}
                      </div>
                    </div>
                  </div>
                  {run.body && (
                    <pre className="mt-3 whitespace-pre-wrap rounded-xl bg-background/60 p-3 text-xs leading-6 text-muted-foreground">
                      {run.body}
                    </pre>
                  )}
                </div>
              );
            })
          )}
        </CardContent>
      </Card>
    </section>
  );
}
