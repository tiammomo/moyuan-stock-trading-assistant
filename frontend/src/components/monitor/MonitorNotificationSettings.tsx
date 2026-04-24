"use client";

import { useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/Card";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/Dialog";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { toast } from "@/components/ui/Toast";
import { useMonitorNotifications } from "@/hooks/useMonitorNotifications";
import { formatTimestamp } from "@/lib/utils";
import type {
  MonitorNotificationChannelRecord,
  MonitorNotificationChannelType,
} from "@/types/notification";

const CHANNEL_TYPE_OPTIONS = [
  { value: "bark", label: "Bark" },
  { value: "webhook", label: "Webhook" },
];

const CHANNEL_STATUS_OPTIONS = [
  { value: "enabled", label: "启用" },
  { value: "disabled", label: "停用" },
];

function channelSummary(channel: MonitorNotificationChannelRecord): string {
  if (channel.type === "bark") {
    return `${channel.bark_server_url || "-"} / ${channel.bark_device_key || "-"}`;
  }
  return channel.webhook_url || "-";
}

export function MonitorNotificationSettings() {
  const {
    channels,
    settings,
    deliveries,
    isLoading,
    isSavingChannel,
    isDeletingChannel,
    isTestingChannel,
    isSavingSettings,
    createChannelAsync,
    updateChannelAsync,
    deleteChannelAsync,
    testChannelAsync,
    updateSettingsAsync,
  } = useMonitorNotifications();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingChannel, setEditingChannel] = useState<MonitorNotificationChannelRecord | null>(null);
  const [channelName, setChannelName] = useState("");
  const [channelType, setChannelType] = useState<MonitorNotificationChannelType>("bark");
  const [channelEnabled, setChannelEnabled] = useState(true);
  const [barkServerUrl, setBarkServerUrl] = useState("https://api.day.app");
  const [barkDeviceKey, setBarkDeviceKey] = useState("");
  const [barkGroup, setBarkGroup] = useState("");
  const [barkSound, setBarkSound] = useState("");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const [defaultChannelIds, setDefaultChannelIds] = useState<string[]>([]);
  const [quietHoursEnabled, setQuietHoursEnabled] = useState(false);
  const [quietHoursStart, setQuietHoursStart] = useState("22:30");
  const [quietHoursEnd, setQuietHoursEnd] = useState("08:30");
  const [retryAttempts, setRetryAttempts] = useState("2");
  const [dedupeMinutes, setDedupeMinutes] = useState("30");

  useEffect(() => {
    if (!settings) return;
    setDefaultChannelIds(settings.default_channel_ids ?? []);
    setQuietHoursEnabled(settings.quiet_hours_enabled ?? false);
    setQuietHoursStart(settings.quiet_hours_start ?? "22:30");
    setQuietHoursEnd(settings.quiet_hours_end ?? "08:30");
    setRetryAttempts(String(settings.delivery_retry_attempts ?? 2));
    setDedupeMinutes(String(settings.delivery_dedupe_minutes ?? 30));
  }, [settings]);

  const enabledChannels = useMemo(
    () => channels.filter((channel) => channel.enabled),
    [channels]
  );

  const openCreate = () => {
    setEditingChannel(null);
    setChannelName("");
    setChannelType("bark");
    setChannelEnabled(true);
    setBarkServerUrl("https://api.day.app");
    setBarkDeviceKey("");
    setBarkGroup("");
    setBarkSound("");
    setWebhookUrl("");
    setFormError(null);
    setDialogOpen(true);
  };

  const openEdit = (channel: MonitorNotificationChannelRecord) => {
    setEditingChannel(channel);
    setChannelName(channel.name);
    setChannelType(channel.type);
    setChannelEnabled(channel.enabled);
    setBarkServerUrl(channel.bark_server_url || "https://api.day.app");
    setBarkDeviceKey(channel.bark_device_key || "");
    setBarkGroup(channel.bark_group || "");
    setBarkSound(channel.bark_sound || "");
    setWebhookUrl(channel.webhook_url || "");
    setFormError(null);
    setDialogOpen(true);
  };

  const saveChannel = async () => {
    try {
      setFormError(null);
      if (!channelName.trim()) {
        throw new Error("请输入通知渠道名称");
      }
      const payload = {
        name: channelName.trim(),
        type: channelType,
        enabled: channelEnabled,
        bark_server_url: barkServerUrl.trim() || null,
        bark_device_key: barkDeviceKey.trim() || null,
        bark_group: barkGroup.trim() || null,
        bark_sound: barkSound.trim() || null,
        webhook_url: webhookUrl.trim() || null,
      };
      if (editingChannel) {
        await updateChannelAsync({ id: editingChannel.id, data: payload });
        toast.success("通知渠道已更新");
      } else {
        await createChannelAsync(payload);
        toast.success("通知渠道已创建");
      }
      setDialogOpen(false);
    } catch (error) {
      const message = error instanceof Error ? error.message : "保存通知渠道失败";
      setFormError(message);
      toast.error(message);
    }
  };

  const saveSettings = async () => {
    try {
      const retry = Number(retryAttempts);
      const dedupe = Number(dedupeMinutes);
      if (!Number.isInteger(retry) || retry < 1 || retry > 5) {
        throw new Error("失败重试次数需要是 1 到 5 之间的整数");
      }
      if (!Number.isInteger(dedupe) || dedupe < 0 || dedupe > 1440) {
        throw new Error("去重窗口需要是 0 到 1440 之间的整数分钟");
      }
      await updateSettingsAsync({
        default_channel_ids: defaultChannelIds,
        quiet_hours_enabled: quietHoursEnabled,
        quiet_hours_start: quietHoursStart,
        quiet_hours_end: quietHoursEnd,
        delivery_retry_attempts: retry,
        delivery_dedupe_minutes: dedupe,
      });
      toast.success("通知设置已保存");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "保存通知设置失败");
    }
  };

  const handleDelete = async (channel: MonitorNotificationChannelRecord) => {
    if (!window.confirm(`删除通知渠道「${channel.name}」？`)) return;
    try {
      await deleteChannelAsync(channel.id);
      toast.success("通知渠道已删除");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "删除通知渠道失败");
    }
  };

  const handleTest = async (channel: MonitorNotificationChannelRecord) => {
    try {
      const result = await testChannelAsync(channel.id);
      if (result.status === "success") {
        toast.success(`测试消息已发送到 ${channel.name}`);
        return;
      }
      toast.error(result.reason || "测试通知失败");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "测试通知失败");
    }
  };

  const toggleDefaultChannel = (channelId: string) => {
    setDefaultChannelIds((current) =>
      current.includes(channelId)
        ? current.filter((item) => item !== channelId)
        : [...current, channelId]
    );
  };

  return (
    <>
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-3">
            <div>
              <CardTitle>盯盘通知</CardTitle>
              <CardDescription>
                先支持 Bark 和 Webhook，包含默认渠道、规则级渠道覆盖、静默时段、失败重试和去重。
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={openCreate}>
              新增渠道
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-border/60 bg-muted/35 p-4">
              <div className="text-sm font-medium">默认通知渠道</div>
              <div className="mt-1 text-xs text-muted-foreground">
                规则未单独指定渠道时，使用这里的默认选择。
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {enabledChannels.length === 0 ? (
                  <span className="text-sm text-muted-foreground">还没有可用通知渠道</span>
                ) : (
                  enabledChannels.map((channel) => (
                    <Button
                      key={channel.id}
                      type="button"
                      variant={defaultChannelIds.includes(channel.id) ? "secondary" : "outline"}
                      size="sm"
                      onClick={() => toggleDefaultChannel(channel.id)}
                    >
                      {channel.name}
                    </Button>
                  ))
                )}
              </div>
            </div>

            <div className="rounded-xl border border-border/60 bg-muted/35 p-4">
              <div className="text-sm font-medium">静默与发送策略</div>
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <label className="space-y-1 text-sm">
                  <span className="text-muted-foreground">静默时段</span>
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      variant={quietHoursEnabled ? "secondary" : "outline"}
                      size="sm"
                      onClick={() => setQuietHoursEnabled(true)}
                    >
                      启用
                    </Button>
                    <Button
                      type="button"
                      variant={!quietHoursEnabled ? "secondary" : "outline"}
                      size="sm"
                      onClick={() => setQuietHoursEnabled(false)}
                    >
                      关闭
                    </Button>
                  </div>
                </label>
                <label className="space-y-1 text-sm">
                  <span className="text-muted-foreground">失败重试次数</span>
                  <Input type="number" value={retryAttempts} onChange={(event) => setRetryAttempts(event.target.value)} />
                </label>
                <label className="space-y-1 text-sm">
                  <span className="text-muted-foreground">静默开始</span>
                  <Input type="time" value={quietHoursStart} onChange={(event) => setQuietHoursStart(event.target.value)} />
                </label>
                <label className="space-y-1 text-sm">
                  <span className="text-muted-foreground">静默结束</span>
                  <Input type="time" value={quietHoursEnd} onChange={(event) => setQuietHoursEnd(event.target.value)} />
                </label>
                <label className="space-y-1 text-sm md:col-span-2">
                  <span className="text-muted-foreground">去重窗口（分钟）</span>
                  <Input type="number" value={dedupeMinutes} onChange={(event) => setDedupeMinutes(event.target.value)} />
                </label>
              </div>
              <div className="mt-3">
                <Button size="sm" onClick={() => void saveSettings()} disabled={isSavingSettings}>
                  {isSavingSettings ? "保存中..." : "保存通知设置"}
                </Button>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium">通知渠道</div>
              <Badge variant="secondary">{channels.length} 个渠道</Badge>
            </div>
            {isLoading ? (
              <div className="rounded-xl border border-dashed border-border/70 px-4 py-8 text-center text-sm text-muted-foreground">
                正在加载通知配置...
              </div>
            ) : channels.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border/70 px-4 py-8 text-center text-sm text-muted-foreground">
                还没有通知渠道。建议先加一个 Bark 或 Webhook。
              </div>
            ) : (
              <div className="space-y-3">
                {channels.map((channel) => (
                  <div key={channel.id} className="rounded-xl border border-border/70 px-4 py-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-2">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-medium">{channel.name}</span>
                          <Badge variant="outline">{channel.type.toUpperCase()}</Badge>
                          <Badge variant={channel.enabled ? "success" : "secondary"}>
                            {channel.enabled ? "启用中" : "已停用"}
                          </Badge>
                          {defaultChannelIds.includes(channel.id) && (
                            <Badge variant="secondary">默认渠道</Badge>
                          )}
                        </div>
                        <div className="text-xs text-muted-foreground">{channelSummary(channel)}</div>
                        <div className="text-xs text-muted-foreground">
                          更新于 {formatTimestamp(channel.updated_at)}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => void handleTest(channel)}
                          disabled={isTestingChannel || !channel.enabled}
                        >
                          测试
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => openEdit(channel)}>
                          编辑
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => void handleDelete(channel)}
                          disabled={isDeletingChannel}
                        >
                          删除
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-3">
            <div className="text-sm font-medium">最近通知记录</div>
            {deliveries.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border/70 px-4 py-6 text-center text-sm text-muted-foreground">
                还没有通知发送记录。
              </div>
            ) : (
              <div className="space-y-2">
                {deliveries.map((delivery) => (
                  <div key={delivery.id} className="rounded-xl border border-border/60 px-3 py-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-sm font-medium">{delivery.channel_name}</span>
                          <Badge
                            variant={
                              delivery.status === "success"
                                ? "success"
                                : delivery.status === "failed"
                                  ? "destructive"
                                  : "warning"
                            }
                          >
                            {delivery.status}
                          </Badge>
                          {delivery.symbol && <Badge variant="outline">{delivery.symbol}</Badge>}
                        </div>
                        <div className="text-xs text-muted-foreground">{delivery.title}</div>
                        {delivery.reason && (
                          <div className="text-xs text-muted-foreground">{delivery.reason}</div>
                        )}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {formatTimestamp(delivery.created_at)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingChannel ? "编辑通知渠道" : "新增通知渠道"}</DialogTitle>
            <DialogDescription>
              第一版只支持 Bark 和 Webhook。规则可以覆盖默认渠道。
            </DialogDescription>
          </DialogHeader>
          <DialogClose onClose={() => setDialogOpen(false)} />
          <div className="space-y-4 p-5 pt-0">
            <div className="grid gap-3 md:grid-cols-2">
              <label className="space-y-1 text-sm">
                <span className="text-muted-foreground">渠道名称</span>
                <Input value={channelName} onChange={(event) => setChannelName(event.target.value)} />
              </label>
              <label className="space-y-1 text-sm">
                <span className="text-muted-foreground">渠道类型</span>
                <Select
                  value={channelType}
                  onChange={(event) => setChannelType(event.target.value as MonitorNotificationChannelType)}
                  options={CHANNEL_TYPE_OPTIONS}
                />
              </label>
              <label className="space-y-1 text-sm">
                <span className="text-muted-foreground">状态</span>
                <Select
                  value={channelEnabled ? "enabled" : "disabled"}
                  onChange={(event) => setChannelEnabled(event.target.value === "enabled")}
                  options={CHANNEL_STATUS_OPTIONS}
                />
              </label>
            </div>

            {channelType === "bark" ? (
              <div className="grid gap-3 md:grid-cols-2">
                <label className="space-y-1 text-sm md:col-span-2">
                  <span className="text-muted-foreground">Bark Server URL</span>
                  <Input value={barkServerUrl} onChange={(event) => setBarkServerUrl(event.target.value)} />
                </label>
                <label className="space-y-1 text-sm md:col-span-2">
                  <span className="text-muted-foreground">设备 Key</span>
                  <Input value={barkDeviceKey} onChange={(event) => setBarkDeviceKey(event.target.value)} />
                </label>
                <label className="space-y-1 text-sm">
                  <span className="text-muted-foreground">分组（可选）</span>
                  <Input value={barkGroup} onChange={(event) => setBarkGroup(event.target.value)} />
                </label>
                <label className="space-y-1 text-sm">
                  <span className="text-muted-foreground">铃声（可选）</span>
                  <Input value={barkSound} onChange={(event) => setBarkSound(event.target.value)} />
                </label>
              </div>
            ) : (
              <label className="space-y-1 text-sm">
                <span className="text-muted-foreground">Webhook URL</span>
                <Input value={webhookUrl} onChange={(event) => setWebhookUrl(event.target.value)} />
              </label>
            )}

            {formError && (
              <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700">
                {formError}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={() => void saveChannel()} disabled={isSavingChannel}>
              {isSavingChannel ? "保存中..." : "保存渠道"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
