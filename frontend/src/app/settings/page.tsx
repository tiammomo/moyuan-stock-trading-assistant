"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { useMetaStatus } from "@/hooks/useMetaStatus";
import { useProfile } from "@/hooks/useProfile";
import type { UserProfileUpdate } from "@/types/profile";
import type { ChatMode, GptReasoningPolicy } from "@/types/common";
import type { RuntimeSkillStatus } from "@/types/meta";

const RISK_STYLE_OPTIONS = [
  { value: "conservative", label: "保守" },
  { value: "balanced", label: "平衡" },
  { value: "aggressive", label: "激进" },
];

const HOLDING_HORIZON_OPTIONS = [
  { value: "1w", label: "1周内" },
  { value: "2-4w", label: "2-4周" },
  { value: "1-3m", label: "1-3个月" },
  { value: "3-6m", label: "3-6个月" },
  { value: "6m+", label: "6个月以上" },
];

const MODE_OPTIONS = [
  { value: "short_term", label: "短线" },
  { value: "swing", label: "波段" },
  { value: "mid_term_value", label: "中线价值" },
  { value: "generic_data_query", label: "通用" },
];

const GPT_REASONING_POLICY_OPTIONS = [
  { value: "auto", label: "自动分级" },
  { value: "medium", label: "固定 medium" },
  { value: "high", label: "固定 high" },
  { value: "xhigh", label: "固定 xhigh" },
];

const SECTOR_OPTIONS = [
  { value: "科技", label: "科技" },
  { value: "医药", label: "医药" },
  { value: "消费", label: "消费" },
  { value: "金融", label: "金融" },
  { value: "新能源", label: "新能源" },
  { value: "半导体", label: "半导体" },
  { value: "军工", label: "军工" },
  { value: "地产", label: "地产" },
];

export default function SettingsPage() {
  const { profile, isLoading, updateProfile, isUpdating } = useProfile();
  const { status: metaStatus, isError: isMetaError } = useMetaStatus();

  const [formData, setFormData] = useState<UserProfileUpdate>({});
  const [hasChanges, setHasChanges] = useState(false);

  const handleChange = (field: keyof UserProfileUpdate, value: unknown) => {
    setFormData({ ...formData, [field]: value });
    setHasChanges(true);
  };

  const handleSave = () => {
    updateProfile(formData);
    setHasChanges(false);
  };

  const handleReset = () => {
    setFormData({});
    setHasChanges(false);
  };

  if (isLoading) {
    return (
      <div className="p-6 max-w-3xl mx-auto">
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 bg-muted rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">设置</h1>
          <p className="text-sm text-muted-foreground">管理你的投资偏好</p>
        </div>
        {hasChanges && (
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleReset}>
              重置
            </Button>
            <Button onClick={handleSave} disabled={isUpdating}>
              {isUpdating ? "保存中..." : "保存更改"}
            </Button>
          </div>
        )}
      </div>

      {/* User Profile Settings */}
      <section className="mb-8">
        <Card>
          <CardHeader>
            <CardTitle>投资偏好</CardTitle>
            <CardDescription>
              设置你的投资风格和偏好，系统会根据这些信息提供更精准的推荐
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-2 gap-6">
              <div>
                <label className="text-sm font-medium mb-1 block">
                  总资金 (元)
                </label>
                <Input
                  type="number"
                  value={formData.capital ?? profile?.capital ?? ""}
                  onChange={(e) =>
                    handleChange(
                      "capital",
                      e.target.value ? Number(e.target.value) : null
                    )
                  }
                  placeholder="例如: 300000"
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">
                  单票仓位上限 (%)
                </label>
                <Input
                  type="number"
                  value={
                    formData.position_limit_pct ??
                    profile?.position_limit_pct ??
                    ""
                  }
                  onChange={(e) =>
                    handleChange(
                      "position_limit_pct",
                      e.target.value ? Number(e.target.value) : null
                    )
                  }
                  placeholder="例如: 20"
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">
                  最大回撤容忍 (%)
                </label>
                <Input
                  type="number"
                  value={
                    formData.max_drawdown_pct ??
                    profile?.max_drawdown_pct ??
                    ""
                  }
                  onChange={(e) =>
                    handleChange(
                      "max_drawdown_pct",
                      e.target.value ? Number(e.target.value) : null
                    )
                  }
                  placeholder="例如: 8"
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">
                  默认持股周期
                </label>
                <Select
                  options={HOLDING_HORIZON_OPTIONS}
                  value={formData.holding_horizon ?? profile?.holding_horizon ?? ""}
                  onChange={(e) => handleChange("holding_horizon", e.target.value)}
                  placeholder="选择持股周期"
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">
                  风险偏好
                </label>
                <Select
                  options={RISK_STYLE_OPTIONS}
                  value={formData.risk_style ?? profile?.risk_style ?? ""}
                  onChange={(e) => handleChange("risk_style", e.target.value)}
                  placeholder="选择风险偏好"
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">
                  默认模式
                </label>
                <Select
                  options={MODE_OPTIONS}
                  value={formData.default_mode ?? profile?.default_mode ?? ""}
                  onChange={(e) =>
                    handleChange("default_mode", (e.target.value || null) as ChatMode | null)
                  }
                  placeholder="选择默认模式"
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">
                  默认返回条数
                </label>
                <Input
                  type="number"
                  value={
                    formData.default_result_size ??
                    profile?.default_result_size ??
                    5
                  }
                  onChange={(e) =>
                    handleChange(
                      "default_result_size",
                      e.target.value ? Number(e.target.value) : null
                    )
                  }
                  placeholder="例如: 5"
                />
              </div>
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">偏好行业</label>
              <div className="flex flex-wrap gap-2">
                {SECTOR_OPTIONS.map((sector) => {
                  const selected =
                    formData.preferred_sectors ??
                    profile?.preferred_sectors ??
                    [];
                  const isSelected = selected.includes(sector.value);
                  return (
                    <Button
                      key={sector.value}
                      variant={isSelected ? "secondary" : "outline"}
                      size="sm"
                      onClick={() => {
                        const newSectors = isSelected
                          ? selected.filter((s) => s !== sector.value)
                          : [...selected, sector.value];
                        handleChange("preferred_sectors", newSectors);
                      }}
                    >
                      {sector.label}
                    </Button>
                  );
                })}
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="mb-8">
        <Card>
          <CardHeader>
            <CardTitle>GPT 辅助分析</CardTitle>
            <CardDescription>
              控制 GPT 是否参与结果润色；系统整体默认按 A 股炒股助手定位组织回答
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-2 gap-6">
              <div>
                <label className="text-sm font-medium mb-2 block">
                  GPT 增强开关
                </label>
                <div className="flex gap-2">
                  <Button
                    variant={
                      (formData.gpt_enhancement_enabled ??
                        profile?.gpt_enhancement_enabled ??
                        true)
                        ? "secondary"
                        : "outline"
                    }
                    size="sm"
                    onClick={() => handleChange("gpt_enhancement_enabled", true)}
                  >
                    启用
                  </Button>
                  <Button
                    variant={
                      (formData.gpt_enhancement_enabled ??
                        profile?.gpt_enhancement_enabled ??
                        true) === false
                        ? "secondary"
                        : "outline"
                    }
                    size="sm"
                    onClick={() => handleChange("gpt_enhancement_enabled", false)}
                  >
                    关闭
                  </Button>
                </div>
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">
                  推理强度策略
                </label>
                <Select
                  options={GPT_REASONING_POLICY_OPTIONS}
                  value={
                    formData.gpt_reasoning_policy ??
                    profile?.gpt_reasoning_policy ??
                    "auto"
                  }
                  onChange={(e) =>
                    handleChange(
                      "gpt_reasoning_policy",
                      (e.target.value || "auto") as GptReasoningPolicy
                    )
                  }
                  placeholder="选择推理强度"
                />
              </div>
            </div>

            <div className="rounded-lg border bg-muted/40 p-4 text-sm text-muted-foreground space-y-2">
              <div className="flex items-center justify-between">
                <span>当前生效状态</span>
                <Badge
                  variant={
                    (profile?.gpt_enhancement_enabled ?? true) &&
                    metaStatus?.llm_enabled
                      ? "success"
                      : "secondary"
                  }
                  className="text-xs"
                >
                  {(profile?.gpt_enhancement_enabled ?? true) &&
                  metaStatus?.llm_enabled
                    ? "增强已生效"
                    : "增强未生效"}
                </Badge>
              </div>
              <p>
                自动分级规则：普通筛选和通用查询优先走 <code>medium</code>，单股建议、
                波段/中线分析优先走 <code>high</code>，买点价位、止损位、估值财报这类更重判断的问题优先走 <code>xhigh</code>。
              </p>
              <p>
                当前系统角色：<code>{metaStatus?.llm_system_prompt_role || "-"}</code>
              </p>
              {!metaStatus?.llm_enabled && (
                <p className="text-amber-700">
                  当前后端环境未启用任何大模型 provider。即使这里打开增强，仍会退回规则化结果。
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Environment Status */}
      <section>
        <Card>
          <CardHeader>
            <CardTitle>环境状态</CardTitle>
            <CardDescription>检查系统配置和连接状态</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between py-2 border-b">
                <span className="text-sm">前端 API 地址</span>
                <code className="text-xs bg-muted px-2 py-1 rounded">
                  {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
                </code>
              </div>
              <div className="flex items-center justify-between py-2 border-b">
                <span className="text-sm">API 状态</span>
                <Badge
                  variant={isMetaError ? "destructive" : "success"}
                  className="text-xs"
                >
                  {isMetaError ? "未连接" : "已连接"}
                </Badge>
              </div>
              <div className="flex items-center justify-between py-2 border-b">
                <span className="text-sm">问财 Base URL</span>
                <code className="text-xs bg-muted px-2 py-1 rounded">
                  {metaStatus?.api_base_url || "-"}
                </code>
              </div>
              <div className="flex items-center justify-between py-2 border-b">
                <span className="text-sm">问财 API Key</span>
                <Badge
                  variant={metaStatus?.api_key_configured ? "success" : "destructive"}
                  className="text-xs"
                >
                  {metaStatus?.api_key_configured ? "已配置" : "未配置"}
                </Badge>
              </div>
              <div className="flex items-center justify-between py-2 border-b">
                <span className="text-sm">可用 Skills</span>
                <Badge variant="secondary" className="text-xs">
                  {metaStatus?.skill_count ?? "-"} 个
                </Badge>
              </div>
              <div className="flex items-center justify-between py-2 border-b">
                <span className="text-sm">LLM 链路</span>
                <Badge
                  variant={metaStatus?.llm_enabled ? "success" : "destructive"}
                  className="text-xs"
                >
                  {metaStatus?.llm_chain_mode || "-"}
                </Badge>
              </div>
              <div className="flex items-center justify-between py-2 border-b">
                <span className="text-sm">Agent Runtime</span>
                <Badge variant="secondary" className="text-xs">
                  {metaStatus?.llm_agent_runtime || "-"}
                </Badge>
              </div>
              <div className="flex items-center justify-between py-2 border-b">
                <span className="text-sm">号池适配器</span>
                <Badge variant="secondary" className="text-xs">
                  {metaStatus?.llm_account_pool_adapter || "-"}
                </Badge>
              </div>
              <div className="flex items-center justify-between py-2 border-b gap-4">
                <span className="text-sm">系统 Prompt</span>
                <code className="text-xs bg-muted px-2 py-1 rounded text-right">
                  {metaStatus?.llm_system_prompt_role || "-"}
                </code>
              </div>
              <div className="flex items-center justify-between py-2 border-b">
                <span className="text-sm">Prompt 来源</span>
                <Badge variant="secondary" className="text-xs">
                  {metaStatus?.llm_system_prompt_source || "-"}
                </Badge>
              </div>
              <div className="flex items-center justify-between py-2 border-b">
                <span className="text-sm">GPT Base URL</span>
                <code className="text-xs bg-muted px-2 py-1 rounded">
                  {metaStatus?.openai_base_url || "-"}
                </code>
              </div>
              <div className="flex items-center justify-between py-2 border-b">
                <span className="text-sm">GPT API Key</span>
                <Badge
                  variant={metaStatus?.openai_api_key_configured ? "success" : "destructive"}
                  className="text-xs"
                >
                  {metaStatus?.openai_api_key_configured ? "已配置" : "未配置"}
                </Badge>
              </div>
              <div className="flex items-center justify-between py-2 border-b">
                <span className="text-sm">GPT 模型</span>
                <code className="text-xs bg-muted px-2 py-1 rounded">
                  {metaStatus?.openai_model || "-"}
                </code>
              </div>
              <div className="flex items-center justify-between py-2 border-b">
                <span className="text-sm">推理强度</span>
                <Badge
                  variant={metaStatus?.openai_enabled ? "success" : "secondary"}
                  className="text-xs"
                >
                  {metaStatus?.openai_reasoning_effort || "-"}
                </Badge>
              </div>
              <div className="flex items-center justify-between py-2 border-b">
                <span className="text-sm">GPT 增强</span>
                <Badge
                  variant={metaStatus?.openai_enabled ? "success" : "destructive"}
                  className="text-xs"
                >
                  {metaStatus?.openai_enabled ? "已启用" : "未启用"}
                </Badge>
              </div>
              <div className="flex items-center justify-between py-2 border-b">
                <span className="text-sm">GPT 账号数</span>
                <Badge variant="secondary" className="text-xs">
                  {metaStatus?.openai_account_count ?? "-"}
                </Badge>
              </div>
              <div className="flex items-center justify-between py-2 border-b">
                <span className="text-sm">MiniMax Base URL</span>
                <code className="text-xs bg-muted px-2 py-1 rounded">
                  {metaStatus?.anthropic_base_url || "-"}
                </code>
              </div>
              <div className="flex items-center justify-between py-2 border-b">
                <span className="text-sm">MiniMax Token</span>
                <Badge
                  variant={metaStatus?.anthropic_auth_token_configured ? "success" : "destructive"}
                  className="text-xs"
                >
                  {metaStatus?.anthropic_auth_token_configured ? "已配置" : "未配置"}
                </Badge>
              </div>
              <div className="flex items-center justify-between py-2 border-b">
                <span className="text-sm">MiniMax 模型</span>
                <code className="text-xs bg-muted px-2 py-1 rounded">
                  {metaStatus?.anthropic_model || "-"}
                </code>
              </div>
              <div className="flex items-center justify-between py-2 border-b">
                <span className="text-sm">MiniMax 兜底</span>
                <Badge
                  variant={metaStatus?.anthropic_enabled ? "success" : "secondary"}
                  className="text-xs"
                >
                  {metaStatus?.anthropic_enabled ? "已启用" : "未启用"}
                </Badge>
              </div>
              <div className="flex items-center justify-between py-2 border-b">
                <span className="text-sm">MiniMax 账号数</span>
                <Badge variant="secondary" className="text-xs">
                  {metaStatus?.anthropic_account_count ?? "-"}
                </Badge>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-sm">版本</span>
                <span className="text-sm text-muted-foreground">
                  {metaStatus?.version || "-"}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="mb-8">
        <Card>
          <CardHeader>
            <CardTitle>运行时 Skills</CardTitle>
            <CardDescription>
              展示当前后端 registry 已接入的 runtime skill，以及安装目录里的静态版本信息
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {(metaStatus?.runtime_skills || []).map((skill) => (
                <div
                  key={skill.skill_id}
                  className="rounded-xl border border-border/50 bg-muted/20 px-4 py-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="text-sm font-medium">{skill.display_name}</div>
                      <div className="mt-1 text-[11px] text-muted-foreground break-all">
                        {skill.skill_id}
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center justify-end gap-2 shrink-0">
                      <Badge variant={skill.enabled ? "success" : "secondary"} className="text-[11px]">
                        {skill.enabled ? "enabled" : "disabled"}
                      </Badge>
                      <Badge variant="secondary" className="text-[11px]">
                        {skill.adapter_kind}
                      </Badge>
                      <Badge
                        variant={skill.asset_meta?.version ? "secondary" : "outline"}
                        className="text-[11px]"
                      >
                        {skill.asset_meta?.version ? `v${skill.asset_meta.version}` : "无 _meta"}
                      </Badge>
                    </div>
                  </div>
                  <div className="mt-3 grid gap-2 text-[11px] text-muted-foreground md:grid-cols-2">
                    <div>
                      安装目录：
                      <code className="ml-1 rounded bg-muted px-1.5 py-0.5 text-[10px]">
                        {skill.asset_path || "-"}
                      </code>
                    </div>
                    <div>
                      资源标识：
                      <code className="ml-1 rounded bg-muted px-1.5 py-0.5 text-[10px]">
                        {skill.asset_meta?.slug || "-"}
                      </code>
                    </div>
                    <div>
                      元数据文件：
                      <code className="ml-1 rounded bg-muted px-1.5 py-0.5 text-[10px]">
                        {skill.asset_meta?.meta_path || "-"}
                      </code>
                    </div>
                    <div>
                      发布时间：
                      <span className="ml-1">{formatPublishedAt(skill)}</span>
                    </div>
                  </div>
                </div>
              ))}
              {(metaStatus?.runtime_skills?.length || 0) === 0 && (
                <div className="rounded-xl border border-dashed border-border/60 px-4 py-6 text-sm text-muted-foreground">
                  当前没有可展示的 runtime skill 元数据。
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

function formatPublishedAt(skill: RuntimeSkillStatus): string {
  const timestamp = skill.asset_meta?.published_at;
  if (!timestamp) return "-";
  return new Date(timestamp).toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}
