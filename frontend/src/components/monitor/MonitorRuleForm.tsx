"use client";

import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/Button";
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
import type {
  MonitorRuleCondition,
  MonitorRuleConditionOperator,
  MonitorRuleConditionType,
  MonitorRuleCreate,
  MonitorRuleRecord,
  MonitorRuleUpdate,
  WatchItemRecord,
} from "@/types/watchlist";

type ConditionRowState = {
  type: MonitorRuleConditionType;
  op: MonitorRuleConditionOperator;
  value: string;
  value2: string;
};

interface MonitorRuleFormProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  watchlist: WatchItemRecord[];
  initialRule?: MonitorRuleRecord | null;
  onCreate: (payload: MonitorRuleCreate) => Promise<void>;
  onUpdate: (ruleId: string, payload: MonitorRuleUpdate) => Promise<void>;
  isSubmitting: boolean;
}

const METRIC_OPTIONS: Array<{ value: MonitorRuleConditionType; label: string }> = [
  { value: "latest_price", label: "现价" },
  { value: "change_pct", label: "涨跌幅" },
  { value: "volume_ratio", label: "量比" },
  { value: "weibi", label: "委比" },
  { value: "amount", label: "成交额" },
  { value: "volume", label: "成交量" },
  { value: "turnover_pct", label: "换手率" },
  { value: "amplitude_pct", label: "振幅" },
  { value: "waipan", label: "外盘" },
  { value: "neipan", label: "内盘" },
  { value: "weicha", label: "委差" },
  { value: "pb", label: "市净率" },
  { value: "pe_dynamic", label: "动态市盈率" },
  { value: "total_market_value", label: "总市值" },
  { value: "float_market_value", label: "流通市值" },
];

const OPERATOR_OPTIONS: Array<{ value: MonitorRuleConditionOperator; label: string }> = [
  { value: ">=", label: ">=" },
  { value: "<=", label: "<=" },
  { value: ">", label: ">" },
  { value: "<", label: "<" },
  { value: "between", label: "区间" },
];

const SEVERITY_OPTIONS = [
  { value: "info", label: "普通" },
  { value: "warning", label: "重点" },
];

const ENABLED_OPTIONS = [
  { value: "enabled", label: "启用" },
  { value: "disabled", label: "停用" },
];

const GROUP_OPTIONS = [
  { value: "or", label: "任一满足" },
  { value: "and", label: "全部满足" },
];

const MARKET_HOURS_OPTIONS = [
  { value: "trading_only", label: "仅交易时段" },
  { value: "always", label: "全天生效" },
];

const REPEAT_OPTIONS = [
  { value: "repeat", label: "重复触发" },
  { value: "once", label: "仅触发一次" },
];

function toDatetimeLocalValue(value?: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

function fromDatetimeLocalValue(value: string): string | null {
  if (!value.trim()) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toISOString();
}

function emptyCondition(): ConditionRowState {
  return {
    type: "change_pct",
    op: ">=",
    value: "3",
    value2: "",
  };
}

function toConditionRows(rule?: MonitorRuleRecord | null): ConditionRowState[] {
  if (!rule || rule.condition_group.items.length === 0) {
    return [emptyCondition()];
  }
  return rule.condition_group.items.map((condition) => {
    const isBetween = condition.op === "between";
    const rangeValue = Array.isArray(condition.value) ? condition.value : [];
    return {
      type: condition.type,
      op: condition.op,
      value: isBetween ? String(rangeValue[0] ?? "") : String(condition.value ?? ""),
      value2: isBetween ? String(rangeValue[1] ?? "") : "",
    };
  });
}

export function MonitorRuleForm({
  open,
  onOpenChange,
  watchlist,
  initialRule,
  onCreate,
  onUpdate,
  isSubmitting,
}: MonitorRuleFormProps) {
  const isEdit = Boolean(initialRule);
  const defaultItemId = useMemo(() => watchlist[0]?.id ?? "", [watchlist]);

  const [itemId, setItemId] = useState("");
  const [ruleName, setRuleName] = useState("默认异动提醒");
  const [enabled, setEnabled] = useState(true);
  const [severity, setSeverity] = useState<"info" | "warning">("info");
  const [groupOp, setGroupOp] = useState<"and" | "or">("or");
  const [marketHoursMode, setMarketHoursMode] = useState<"trading_only" | "always">("trading_only");
  const [repeatMode, setRepeatMode] = useState<"repeat" | "once">("repeat");
  const [expireAt, setExpireAt] = useState("");
  const [cooldownMinutes, setCooldownMinutes] = useState("15");
  const [maxTriggersPerDay, setMaxTriggersPerDay] = useState("5");
  const [conditions, setConditions] = useState<ConditionRowState[]>([emptyCondition()]);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    if (initialRule) {
      setItemId(initialRule.item_id);
      setRuleName(initialRule.rule_name);
      setEnabled(initialRule.enabled);
      setSeverity(initialRule.severity);
      setGroupOp(initialRule.condition_group.op);
      setMarketHoursMode(initialRule.market_hours_mode ?? "trading_only");
      setRepeatMode(initialRule.repeat_mode ?? "repeat");
      setExpireAt(toDatetimeLocalValue(initialRule.expire_at));
      setCooldownMinutes(String(initialRule.cooldown_minutes));
      setMaxTriggersPerDay(String(initialRule.max_triggers_per_day));
      setConditions(toConditionRows(initialRule));
      setFormError(null);
      return;
    }
    setItemId(defaultItemId);
    setRuleName("默认异动提醒");
    setEnabled(true);
    setSeverity("info");
    setGroupOp("or");
    setMarketHoursMode("trading_only");
    setRepeatMode("repeat");
    setExpireAt("");
    setCooldownMinutes("15");
    setMaxTriggersPerDay("5");
    setConditions([emptyCondition()]);
    setFormError(null);
  }, [defaultItemId, initialRule, open]);

  const selectedItem = useMemo(
    () => watchlist.find((item) => item.id === itemId) ?? null,
    [itemId, watchlist]
  );

  const handleConditionChange = (
    index: number,
    patch: Partial<ConditionRowState>
  ) => {
    setConditions((current) =>
      current.map((condition, idx) => {
        if (idx !== index) return condition;
        const next = { ...condition, ...patch };
        if (patch.op && patch.op !== "between") {
          next.value2 = "";
        }
        return next;
      })
    );
  };

  const handleAddCondition = () => {
    setConditions((current) => [...current, emptyCondition()]);
  };

  const handleRemoveCondition = (index: number) => {
    setConditions((current) => current.filter((_, idx) => idx !== index));
  };

  const buildConditions = (): MonitorRuleCondition[] => {
    return conditions.map((condition, index) => {
      const numeric = Number(condition.value);
      if (!Number.isFinite(numeric)) {
        throw new Error(`第 ${index + 1} 条条件的数值无效`);
      }
      if (condition.op === "between") {
        const upper = Number(condition.value2);
        if (!Number.isFinite(upper)) {
          throw new Error(`第 ${index + 1} 条条件的区间上限无效`);
        }
        return {
          type: condition.type,
          op: condition.op,
          value: [numeric, upper],
        };
      }
      return {
        type: condition.type,
        op: condition.op,
        value: numeric,
      };
    });
  };

  const handleSubmit = async () => {
    try {
      setFormError(null);
      const normalizedName = ruleName.trim();
      if (!normalizedName) {
        throw new Error("请输入规则名称");
      }
      if (!itemId && !initialRule) {
        throw new Error("请选择要绑定的股票");
      }
      if (conditions.length === 0) {
        throw new Error("至少保留一条触发条件");
      }

      const cooldown = Number(cooldownMinutes);
      const maxPerDay = Number(maxTriggersPerDay);
      if (!Number.isInteger(cooldown) || cooldown < 0 || cooldown > 1440) {
        throw new Error("冷却时间需要是 0 到 1440 之间的整数分钟");
      }
      if (!Number.isInteger(maxPerDay) || maxPerDay < 0 || maxPerDay > 999) {
        throw new Error("每日上限需要是 0 到 999 之间的整数");
      }

      const conditionItems = buildConditions();
      const normalizedExpireAt = fromDatetimeLocalValue(expireAt);
      if (isEdit && initialRule) {
        await onUpdate(initialRule.id, {
          rule_name: normalizedName,
          enabled,
          severity,
          market_hours_mode: marketHoursMode,
          repeat_mode: repeatMode,
          expire_at: normalizedExpireAt,
          cooldown_minutes: cooldown,
          max_triggers_per_day: maxPerDay,
          condition_group: {
            op: groupOp,
            items: conditionItems,
          },
        });
      } else {
        await onCreate({
          item_id: itemId,
          rule_name: normalizedName,
          enabled,
          severity,
          market_hours_mode: marketHoursMode,
          repeat_mode: repeatMode,
          expire_at: normalizedExpireAt,
          cooldown_minutes: cooldown,
          max_triggers_per_day: maxPerDay,
          condition_group: {
            op: groupOp,
            items: conditionItems,
          },
        });
      }
      onOpenChange(false);
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "保存规则失败");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? "编辑提醒规则" : "新增提醒规则"}</DialogTitle>
          <DialogDescription>
            绑定单只候选股，支持多指标组合、交易时段、过期时间和重复模式。
          </DialogDescription>
        </DialogHeader>
        <DialogClose onClose={() => onOpenChange(false)} />
        <div className="space-y-4 p-5 pt-0">
          <div className="grid gap-3 md:grid-cols-2">
            <label className="space-y-1 text-sm">
              <span className="text-muted-foreground">股票</span>
              {isEdit ? (
                <div className="rounded-lg border border-border/60 bg-muted/35 px-3 py-2 text-sm">
                  {initialRule?.name} ({initialRule?.symbol})
                </div>
              ) : (
                <Select
                  value={itemId}
                  onChange={(event) => setItemId(event.target.value)}
                  options={watchlist.map((item) => ({
                    value: item.id,
                    label: `${item.name} (${item.symbol})`,
                  }))}
                />
              )}
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-muted-foreground">规则名称</span>
              <Input value={ruleName} onChange={(event) => setRuleName(event.target.value)} />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-muted-foreground">触发逻辑</span>
              <Select
                value={groupOp}
                onChange={(event) => setGroupOp(event.target.value as "and" | "or")}
                options={GROUP_OPTIONS}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-muted-foreground">状态</span>
              <Select
                value={enabled ? "enabled" : "disabled"}
                onChange={(event) => setEnabled(event.target.value === "enabled")}
                options={ENABLED_OPTIONS}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-muted-foreground">严重级别</span>
              <Select
                value={severity}
                onChange={(event) => setSeverity(event.target.value as "info" | "warning")}
                options={SEVERITY_OPTIONS}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-muted-foreground">冷却时间（分钟）</span>
              <Input
                type="number"
                min={0}
                max={1440}
                value={cooldownMinutes}
                onChange={(event) => setCooldownMinutes(event.target.value)}
              />
            </label>
            <label className="space-y-1 text-sm md:col-span-2">
              <span className="text-muted-foreground">每日触发上限</span>
              <Input
                type="number"
                min={0}
                max={999}
                value={maxTriggersPerDay}
                onChange={(event) => setMaxTriggersPerDay(event.target.value)}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-muted-foreground">生效时段</span>
              <Select
                value={marketHoursMode}
                onChange={(event) => setMarketHoursMode(event.target.value as "trading_only" | "always")}
                options={MARKET_HOURS_OPTIONS}
              />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-muted-foreground">重复模式</span>
              <Select
                value={repeatMode}
                onChange={(event) => setRepeatMode(event.target.value as "repeat" | "once")}
                options={REPEAT_OPTIONS}
              />
            </label>
            <label className="space-y-1 text-sm md:col-span-2">
              <span className="text-muted-foreground">过期时间（可选）</span>
              <Input
                type="datetime-local"
                value={expireAt}
                onChange={(event) => setExpireAt(event.target.value)}
              />
            </label>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium">触发条件</div>
                <div className="text-xs text-muted-foreground">
                  {selectedItem ? `当前绑定：${selectedItem.name}（${selectedItem.symbol}）` : "请先选择股票"}
                </div>
              </div>
              <Button variant="outline" size="sm" type="button" onClick={handleAddCondition}>
                添加条件
              </Button>
            </div>
            <div className="space-y-3">
              {conditions.map((condition, index) => (
                <div
                  key={`${condition.type}-${index}`}
                  className="rounded-xl border border-border/60 bg-muted/25 px-3 py-3"
                >
                  <div className="grid gap-3 md:grid-cols-[1.1fr_0.9fr_1fr_1fr_auto]">
                    <Select
                      value={condition.type}
                      onChange={(event) =>
                        handleConditionChange(index, {
                          type: event.target.value as MonitorRuleConditionType,
                        })
                      }
                      options={METRIC_OPTIONS}
                    />
                    <Select
                      value={condition.op}
                      onChange={(event) =>
                        handleConditionChange(index, {
                          op: event.target.value as MonitorRuleConditionOperator,
                        })
                      }
                      options={OPERATOR_OPTIONS}
                    />
                    <Input
                      type="number"
                      value={condition.value}
                      onChange={(event) =>
                        handleConditionChange(index, { value: event.target.value })
                      }
                      placeholder="数值"
                    />
                    {condition.op === "between" ? (
                      <Input
                        type="number"
                        value={condition.value2}
                        onChange={(event) =>
                          handleConditionChange(index, { value2: event.target.value })
                        }
                        placeholder="上限"
                      />
                    ) : (
                      <div className="flex items-center text-xs text-muted-foreground">
                        单值条件
                      </div>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      type="button"
                      disabled={conditions.length === 1}
                      onClick={() => handleRemoveCondition(index)}
                    >
                      删除
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {formError && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700">
              {formError}
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="ghost" type="button" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button type="button" onClick={() => void handleSubmit()} disabled={isSubmitting}>
            {isSubmitting ? "保存中..." : isEdit ? "保存规则" : "创建规则"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
