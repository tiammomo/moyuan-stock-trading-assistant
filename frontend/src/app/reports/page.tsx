"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button, buttonVariants } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { toast } from "@/components/ui/Toast";
import { useScheduledReports } from "@/hooks/useScheduledReports";
import { cn, formatDateTime, formatTimestamp } from "@/lib/utils";
import type {
  ScheduledReportRunRecord,
  ScheduledReportRunStatus,
  ScheduledReportType,
} from "@/types/scheduledReport";

const REPORT_META: Record<
  ScheduledReportType,
  {
    title: string;
    description: string;
  }
> = {
  news_digest: {
    title: "新闻摘要",
    description: "开盘前快速过一遍催化、公告和新闻主线。",
  },
  pre_market_watchlist: {
    title: "盘前观察清单",
    description: "给出今日优先观察标的、风险点和开盘动作。",
  },
  portfolio_daily: {
    title: "持仓日报",
    description: "汇总持仓盈亏、仓位结构和重点仓位表现。",
  },
  post_market_review: {
    title: "盘后复盘",
    description: "沉淀当日异动、关键事件和次日观察点。",
  },
};

const STATUS_META: Record<
  ScheduledReportRunStatus,
  {
    label: string;
    className: string;
  }
> = {
  success: { label: "成功", className: "border-emerald-400/30 bg-emerald-500/10 text-emerald-200" },
  failed: { label: "失败", className: "border-red-400/30 bg-red-500/10 text-red-200" },
  skipped: { label: "跳过", className: "border-amber-400/30 bg-amber-500/10 text-amber-200" },
};

const REPORT_FILTER_OPTIONS = [
  { value: "all", label: "全部日报" },
  { value: "pre_market_watchlist", label: "盘前观察清单" },
  { value: "post_market_review", label: "盘后复盘" },
  { value: "portfolio_daily", label: "持仓日报" },
  { value: "news_digest", label: "新闻摘要" },
];

const STATUS_FILTER_OPTIONS = [
  { value: "all", label: "全部状态" },
  { value: "success", label: "成功" },
  { value: "failed", label: "失败" },
  { value: "skipped", label: "跳过" },
];

function statusBadge(status: ScheduledReportRunStatus) {
  const meta = STATUS_META[status];
  return (
    <Badge variant="outline" className={meta.className}>
      {meta.label}
    </Badge>
  );
}

function runCount(runs: ScheduledReportRunRecord[], status: ScheduledReportRunStatus) {
  return runs.filter((run) => run.status === status).length;
}

export default function ReportsPage() {
  const { jobs, runs, isLoading, isTriggering, triggerJobAsync } = useScheduledReports({
    runsLimit: 40,
    runsRefetchInterval: 30_000,
  });
  const [reportFilter, setReportFilter] = useState<"all" | ScheduledReportType>("all");
  const [statusFilter, setStatusFilter] = useState<"all" | ScheduledReportRunStatus>("all");

  const latestRuns = useMemo(() => {
    return Object.fromEntries(
      jobs.map((job) => [
        job.report_type,
        runs.find((run) => run.report_type === job.report_type) ?? null,
      ])
    ) as Record<ScheduledReportType, ScheduledReportRunRecord | null>;
  }, [jobs, runs]);

  const filteredRuns = useMemo(() => {
    return runs.filter((run) => {
      if (reportFilter !== "all" && run.report_type !== reportFilter) return false;
      if (statusFilter !== "all" && run.status !== statusFilter) return false;
      return true;
    });
  }, [reportFilter, runs, statusFilter]);

  const handleTrigger = async (reportType: ScheduledReportType) => {
    try {
      await triggerJobAsync(reportType);
      toast.success(`${REPORT_META[reportType].title}已触发`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "触发日报失败");
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">日报中心</h1>
          <p className="text-sm text-muted-foreground">
            集中查看盘前、盘后、持仓和新闻日报。配置仍在设置页，阅读和手动触发放在这里。
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/settings" className={buttonVariants({ variant: "outline" })}>
            去配置日报
          </Link>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {jobs.map((job) => {
          const latestRun = latestRuns[job.report_type];
          return (
            <Card key={job.report_type}>
              <CardHeader className="space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <CardTitle className="text-base">{REPORT_META[job.report_type].title}</CardTitle>
                    <CardDescription className="mt-1 leading-6">
                      {REPORT_META[job.report_type].description}
                    </CardDescription>
                  </div>
                  <Badge
                    variant="outline"
                    className={cn(
                      job.enabled
                        ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-200"
                        : "border-border/60 bg-background/50 text-muted-foreground"
                    )}
                  >
                    {job.enabled ? "已启用" : "未启用"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-1 text-sm text-muted-foreground">
                  <div>计划时间：{job.schedule_time}</div>
                  <div>通知渠道：{job.channel_ids.length > 0 ? `${job.channel_ids.length} 个覆盖渠道` : "默认渠道"}</div>
                  <div>最近修改：{formatTimestamp(job.updated_at)}</div>
                </div>

                {latestRun ? (
                  <div className="rounded-xl border border-border/60 bg-muted/20 p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      {statusBadge(latestRun.status)}
                      <Badge variant="outline" className="border-border/60 bg-background/60 text-muted-foreground">
                        {latestRun.trigger === "scheduled" ? "自动调度" : "手动触发"}
                      </Badge>
                      {latestRun.ai_enhanced ? (
                        <Badge variant="outline" className="border-primary/30 bg-primary/10 text-primary">
                          AI 增强
                        </Badge>
                      ) : null}
                    </div>
                    <div className="mt-2 text-sm font-medium">{latestRun.title}</div>
                    <div className="mt-1 text-xs leading-6 text-muted-foreground">{latestRun.summary}</div>
                    <div className="mt-2 text-xs text-muted-foreground">
                      {formatDateTime(latestRun.created_at)}
                    </div>
                  </div>
                ) : (
                  <div className="rounded-xl border border-dashed border-border/70 px-3 py-4 text-sm text-muted-foreground">
                    还没有运行记录。
                  </div>
                )}

                <Button
                  size="sm"
                  disabled={isTriggering}
                  onClick={() => void handleTrigger(job.report_type)}
                >
                  立即触发
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>最近记录</CardDescription>
          </CardHeader>
          <CardContent className="text-2xl font-semibold">{runs.length}</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>成功</CardDescription>
          </CardHeader>
          <CardContent className="text-2xl font-semibold text-emerald-300">
            {runCount(runs, "success")}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>失败</CardDescription>
          </CardHeader>
          <CardContent className="text-2xl font-semibold text-red-300">
            {runCount(runs, "failed")}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>跳过</CardDescription>
          </CardHeader>
          <CardContent className="text-2xl font-semibold text-amber-300">
            {runCount(runs, "skipped")}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle>运行记录</CardTitle>
              <CardDescription>
                这里展示最近 40 条日报执行结果，可按日报类型和状态筛选。
              </CardDescription>
            </div>
            <div className="grid min-w-[280px] gap-3 sm:grid-cols-2">
              <Select
                value={reportFilter}
                onChange={(event) => setReportFilter(event.target.value as "all" | ScheduledReportType)}
                options={REPORT_FILTER_OPTIONS}
              />
              <Select
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value as "all" | ScheduledReportRunStatus)}
                options={STATUS_FILTER_OPTIONS}
              />
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoading ? (
            <div className="rounded-xl border border-dashed border-border/70 px-4 py-5 text-sm text-muted-foreground">
              日报加载中…
            </div>
          ) : filteredRuns.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border/70 px-4 py-5 text-sm text-muted-foreground">
              当前筛选条件下没有日报记录。
            </div>
          ) : (
            filteredRuns.map((run) => (
              <div key={run.id} className="rounded-2xl border border-border/60 bg-muted/20 p-4">
                <div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="font-medium">{run.title}</div>
                      <Badge variant="outline">{REPORT_META[run.report_type].title}</Badge>
                      {statusBadge(run.status)}
                      <Badge variant="outline" className="border-border/60 bg-background/60 text-muted-foreground">
                        {run.trigger === "scheduled" ? "自动调度" : "手动触发"}
                      </Badge>
                      {run.ai_enhanced ? (
                        <Badge variant="outline" className="border-primary/30 bg-primary/10 text-primary">
                          AI 增强{run.ai_provider ? ` · ${run.ai_provider}` : ""}
                        </Badge>
                      ) : null}
                    </div>
                    <div className="text-sm leading-6 text-muted-foreground">{run.summary}</div>
                    {run.reason ? <div className="text-xs text-amber-300">{run.reason}</div> : null}
                  </div>
                  <div className="text-right text-xs text-muted-foreground">
                    <div>{formatDateTime(run.created_at)}</div>
                    <div>{run.trading_date ? `交易日 ${run.trading_date}` : "非交易日/无交易日标记"}</div>
                    <div>
                      发送成功 {run.delivered_count} 次
                      {run.channel_ids.length > 0 ? ` · 指定渠道 ${run.channel_ids.length} 个` : " · 默认渠道"}
                    </div>
                  </div>
                </div>
                {run.body ? (
                  <pre className="mt-3 whitespace-pre-wrap rounded-xl bg-background/60 p-3 text-xs leading-6 text-muted-foreground">
                    {run.body}
                  </pre>
                ) : null}
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
