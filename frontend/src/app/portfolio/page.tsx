"use client";

import { ChangeEvent, useMemo, useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
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
import { Textarea } from "@/components/ui/Textarea";
import { toast } from "@/components/ui/Toast";
import { usePortfolio } from "@/hooks/usePortfolio";
import { useMonitorRules } from "@/hooks/useMonitorRules";
import { useWatchlist } from "@/hooks/useWatchlist";
import { cn, formatDateTime, formatTimestamp } from "@/lib/utils";
import type {
  PortfolioAccountView,
  PortfolioBrokerTemplate,
  PortfolioCsvImportResponse,
  PortfolioPositionView,
  PortfolioScreenshotImportResponse,
  TradingStyle,
} from "@/types/portfolio";
import type { MonitorRuleCreate } from "@/types/watchlist";

const STYLE_OPTIONS: Array<{ value: TradingStyle; label: string }> = [
  { value: "short", label: "短线" },
  { value: "swing", label: "波段" },
  { value: "long", label: "长线" },
];

const STYLE_LABELS: Record<TradingStyle, string> = {
  short: "短线",
  swing: "波段",
  long: "长线",
};

const BROKER_TEMPLATE_OPTIONS: Array<{ value: PortfolioBrokerTemplate; label: string }> = [
  { value: "auto", label: "自动识别" },
  { value: "generic_cn", label: "通用 A 股券商" },
  { value: "guotai_haitong", label: "国泰海通" },
  { value: "tonghuashun", label: "同花顺" },
  { value: "eastmoney", label: "东方财富" },
  { value: "huatai", label: "华泰证券" },
  { value: "pingan", label: "平安证券" },
];

function money(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "--";
  return value.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function pct(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "--";
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(2)}%`;
}

function signedClass(value: number | null | undefined): string {
  if (value === null || value === undefined) return "text-muted-foreground";
  if (value > 0) return "text-red-500";
  if (value < 0) return "text-emerald-500";
  return "text-muted-foreground";
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") {
        resolve(reader.result);
        return;
      }
      reject(new Error("截图读取失败"));
    };
    reader.onerror = () => reject(new Error("截图读取失败"));
    reader.readAsDataURL(file);
  });
}

function readFileAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") {
        resolve(reader.result);
        return;
      }
      reject(new Error("CSV 读取失败"));
    };
    reader.onerror = () => reject(new Error("CSV 读取失败"));
    reader.readAsText(file, "utf-8");
  });
}

export default function PortfolioPage() {
  const {
    summary,
    isLoading,
    summaryUpdatedAt,
    createAccountAsync,
    updateAccountAsync,
    deleteAccountAsync,
    createPositionAsync,
    updatePositionAsync,
    deletePositionAsync,
    importScreenshotAsync,
    importCsvAsync,
    isMutating,
  } = usePortfolio();
  const { createRuleAsync } = useMonitorRules();
  const { watchlist } = useWatchlist();

  const accounts = summary?.accounts ?? [];
  const defaultAccountId = useMemo(() => accounts[0]?.id ?? "", [accounts]);
  const marketSchedule = summary?.market_schedule ?? null;
  const lastSummaryRefreshLabel = summaryUpdatedAt
    ? formatTimestamp(new Date(summaryUpdatedAt).toISOString())
    : "刚刚";
  const marketRefreshLabel = marketSchedule?.market_phase === "open"
    ? "交易中，每 10 秒刷新"
    : marketSchedule?.next_open_at
      ? `按正式交易日历等待开盘：${formatDateTime(marketSchedule.next_open_at)}`
      : "按正式交易日历等待开盘";

  const [accountDialogOpen, setAccountDialogOpen] = useState(false);
  const [positionDialogOpen, setPositionDialogOpen] = useState(false);
  const [screenshotDialogOpen, setScreenshotDialogOpen] = useState(false);
  const [csvDialogOpen, setCsvDialogOpen] = useState(false);

  const [editingAccount, setEditingAccount] = useState<PortfolioAccountView | null>(null);
  const [editingPosition, setEditingPosition] = useState<PortfolioPositionView | null>(null);
  const [importPreviewResult, setImportPreviewResult] = useState<PortfolioScreenshotImportResponse | null>(null);
  const [csvPreviewResult, setCsvPreviewResult] = useState<PortfolioCsvImportResponse | null>(null);

  const [accountName, setAccountName] = useState("");
  const [availableFunds, setAvailableFunds] = useState("0");
  const [accountEnabled, setAccountEnabled] = useState(true);

  const [positionAccountId, setPositionAccountId] = useState("");
  const [symbol, setSymbol] = useState("");
  const [stockName, setStockName] = useState("");
  const [costPrice, setCostPrice] = useState("");
  const [quantity, setQuantity] = useState("");
  const [availableQuantity, setAvailableQuantity] = useState("");
  const [frozenQuantity, setFrozenQuantity] = useState("");
  const [industry, setIndustry] = useState("");
  const [tradingStyle, setTradingStyle] = useState<TradingStyle>("swing");

  const [importAccountId, setImportAccountId] = useState("");
  const [importFileName, setImportFileName] = useState("");
  const [importImageDataUrl, setImportImageDataUrl] = useState("");
  const [importBrokerTemplate, setImportBrokerTemplate] = useState<PortfolioBrokerTemplate>("auto");

  const [csvAccountId, setCsvAccountId] = useState("");
  const [csvFileName, setCsvFileName] = useState("");
  const [csvText, setCsvText] = useState("");

  const openCreateAccount = () => {
    setEditingAccount(null);
    setAccountName("");
    setAvailableFunds("0");
    setAccountEnabled(true);
    setAccountDialogOpen(true);
  };

  const openEditAccount = (account: PortfolioAccountView) => {
    setEditingAccount(account);
    setAccountName(account.name);
    setAvailableFunds(String(account.available_funds));
    setAccountEnabled(account.enabled);
    setAccountDialogOpen(true);
  };

  const openCreatePosition = (accountId?: string) => {
    setEditingPosition(null);
    setPositionAccountId(accountId ?? defaultAccountId);
    setSymbol("");
    setStockName("");
    setCostPrice("");
    setQuantity("");
    setAvailableQuantity("");
    setFrozenQuantity("");
    setIndustry("");
    setTradingStyle("swing");
    setPositionDialogOpen(true);
  };

  const openEditPosition = (position: PortfolioPositionView) => {
    setEditingPosition(position);
    setPositionAccountId(position.account_id);
    setSymbol(position.symbol);
    setStockName(position.name);
    setCostPrice(String(position.cost_price));
    setQuantity(String(position.quantity));
    setAvailableQuantity(String(position.available_quantity));
    setFrozenQuantity(String(position.frozen_quantity));
    setIndustry(position.industry ?? "");
    setTradingStyle(position.trading_style);
    setPositionDialogOpen(true);
  };

  const openScreenshotImportDialog = (accountId?: string) => {
    const resolvedAccountId = accountId ?? defaultAccountId;
    setImportAccountId(resolvedAccountId);
    setImportFileName("");
    setImportImageDataUrl("");
    setImportBrokerTemplate("auto");
    setImportPreviewResult(null);
    setScreenshotDialogOpen(true);
  };

  const openCsvImportDialog = (accountId?: string) => {
    const resolvedAccountId = accountId ?? defaultAccountId;
    setCsvAccountId(resolvedAccountId);
    setCsvFileName("");
    setCsvText("");
    setCsvPreviewResult(null);
    setCsvDialogOpen(true);
  };

  const saveAccount = async () => {
    const name = accountName.trim();
    const funds = Number(availableFunds);
    if (!name) {
      toast.error("请输入账户名称");
      return;
    }
    if (!Number.isFinite(funds)) {
      toast.error("可用资金格式不正确");
      return;
    }
    try {
      if (editingAccount) {
        await updateAccountAsync({
          id: editingAccount.id,
          data: { name, available_funds: funds, enabled: accountEnabled },
        });
        toast.success("账户已更新");
      } else {
        await createAccountAsync({ name, available_funds: funds, enabled: accountEnabled });
        toast.success("账户已创建");
      }
      setAccountDialogOpen(false);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "保存账户失败");
    }
  };

  const savePosition = async () => {
    const normalizedSymbol = symbol.trim();
    if (!positionAccountId) {
      toast.error("请选择账户");
      return;
    }
    if (!normalizedSymbol) {
      toast.error("请输入股票代码");
      return;
    }

    const resolvedQuantity = Number(quantity);
    const resolvedCostPrice = Number(costPrice);
    const resolvedAvailableQuantity = availableQuantity.trim() ? Number(availableQuantity) : null;
    const resolvedFrozenQuantity = frozenQuantity.trim() ? Number(frozenQuantity) : null;

    if (!Number.isInteger(resolvedQuantity) || resolvedQuantity <= 0) {
      toast.error("数量需要是正整数");
      return;
    }
    if (!Number.isFinite(resolvedCostPrice) || resolvedCostPrice <= 0) {
      toast.error("成本价需要大于 0");
      return;
    }
    if (
      resolvedAvailableQuantity !== null &&
      (!Number.isInteger(resolvedAvailableQuantity) || resolvedAvailableQuantity < 0)
    ) {
      toast.error("可用数量需要是非负整数");
      return;
    }
    if (
      resolvedFrozenQuantity !== null &&
      (!Number.isInteger(resolvedFrozenQuantity) || resolvedFrozenQuantity < 0)
    ) {
      toast.error("冻结数量需要是非负整数");
      return;
    }
    if (
      resolvedAvailableQuantity !== null &&
      resolvedFrozenQuantity !== null &&
      resolvedAvailableQuantity + resolvedFrozenQuantity > resolvedQuantity
    ) {
      toast.error("可用数量与冻结数量之和不能超过总持仓数量");
      return;
    }

    try {
      const data = {
        account_id: positionAccountId,
        symbol: normalizedSymbol,
        name: stockName.trim() || null,
        cost_price: resolvedCostPrice,
        quantity: resolvedQuantity,
        available_quantity: resolvedAvailableQuantity,
        frozen_quantity: resolvedFrozenQuantity,
        trading_style: tradingStyle,
        industry: industry.trim() || null,
      };
      if (editingPosition) {
        await updatePositionAsync({ id: editingPosition.id, data });
        toast.success("持仓已更新");
      } else {
        await createPositionAsync(data);
        toast.success("持仓已创建");
      }
      setPositionDialogOpen(false);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "保存持仓失败");
    }
  };

  const removeAccount = async (account: PortfolioAccountView) => {
    if (!window.confirm(`删除账户「${account.name}」？该账户下持仓也会删除。`)) return;
    await deleteAccountAsync(account.id);
    toast.success("账户已删除");
  };

  const removePosition = async (position: PortfolioPositionView) => {
    if (!window.confirm(`删除持仓「${position.name}」？`)) return;
    await deletePositionAsync(position.id);
    toast.success("持仓已删除");
  };

  const createRiskRule = async (position: PortfolioPositionView) => {
    try {
      const watchItem = watchlist.find((item) => item.symbol.toUpperCase() === position.symbol.toUpperCase());
      if (!watchItem) {
        throw new Error("请先把该股票加入候选池，再创建持仓风险规则");
      }
      const lossLine = Number((position.cost_price * 0.95).toFixed(2));
      const payload: MonitorRuleCreate = {
        item_id: watchItem.id,
        rule_name: `持仓风险：跌破成本5%（${position.name}）`,
        enabled: true,
        severity: "warning",
        notify_channel_ids: [],
        market_hours_mode: "trading_only",
        repeat_mode: "repeat",
        expire_at: null,
        cooldown_minutes: 30,
        max_triggers_per_day: 3,
        condition_group: {
          op: "or",
          items: [
            { type: "latest_price", op: "<=", value: lossLine },
            { type: "change_pct", op: "<=", value: -5 },
          ],
        },
      };
      await createRuleAsync(payload);
      toast.success("持仓风险规则已创建");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "创建持仓风险规则失败，请确认该股票已加入候选池");
    }
  };

  const handleImportFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const dataUrl = await readFileAsDataUrl(file);
      setImportFileName(file.name);
      setImportImageDataUrl(dataUrl);
      setImportPreviewResult(null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "截图读取失败");
    } finally {
      event.target.value = "";
    }
  };

  const handlePreviewScreenshot = async () => {
    if (!importAccountId) {
      toast.error("请选择导入账户");
      return;
    }
    if (!importImageDataUrl) {
      toast.error("请选择截图文件");
      return;
    }
    try {
      const result = await importScreenshotAsync({
        account_id: importAccountId,
        image_data_url: importImageDataUrl,
        dry_run: true,
        skip_zero_quantity: true,
        broker_template: importBrokerTemplate,
      });
      setImportPreviewResult(result);
      toast.success(`预览完成：识别 ${result.parsed_count} 行`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "截图预览失败");
    }
  };

  const handleConfirmScreenshotImport = async () => {
    if (!importAccountId || !importPreviewResult) {
      toast.error("请先预览识别结果");
      return;
    }
    try {
      const result = await importScreenshotAsync({
        account_id: importAccountId,
        dry_run: false,
        skip_zero_quantity: true,
        broker_template: importBrokerTemplate,
        broker_name: importPreviewResult.broker_name,
        parsed_rows: importPreviewResult.rows,
      });
      setScreenshotDialogOpen(false);
      setImportPreviewResult(null);
      setImportFileName("");
      setImportImageDataUrl("");
      toast.success(`截图导入完成：新增 ${result.imported_count}，更新 ${result.updated_count}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "截图导入失败");
    }
  };

  const handleCsvFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const text = await readFileAsText(file);
      setCsvFileName(file.name);
      setCsvText(text);
      setCsvPreviewResult(null);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "CSV 读取失败");
    } finally {
      event.target.value = "";
    }
  };

  const handlePreviewCsv = async () => {
    if (!csvAccountId) {
      toast.error("请选择导入账户");
      return;
    }
    if (!csvText.trim()) {
      toast.error("请上传或粘贴 CSV 内容");
      return;
    }
    try {
      const result = await importCsvAsync({
        account_id: csvAccountId,
        csv_text: csvText,
        dry_run: true,
        preserve_existing_note: true,
        default_trading_style: "swing",
      });
      setCsvPreviewResult(result);
      toast.success(`CSV 预览完成：解析 ${result.parsed_count} 行`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "CSV 预览失败");
    }
  };

  const handleConfirmCsvImport = async () => {
    if (!csvAccountId || !csvText.trim()) {
      toast.error("请先上传或粘贴 CSV 内容");
      return;
    }
    try {
      const result = await importCsvAsync({
        account_id: csvAccountId,
        csv_text: csvText,
        dry_run: false,
        preserve_existing_note: true,
        default_trading_style: "swing",
      });
      setCsvDialogOpen(false);
      setCsvPreviewResult(null);
      setCsvFileName("");
      setCsvText("");
      toast.success(`CSV 导入完成：新增 ${result.imported_count}，更新 ${result.updated_count}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "CSV 导入失败");
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">持仓账户</h1>
          <p className="text-sm text-muted-foreground">
            支持手动维护、截图导入和 CSV 导入。交易时段按 10 秒自动刷新行情、市值、盈亏、仓位占比和组合暴露，持仓成本仍以手工或 lot 记录为准。
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="secondary">{marketSchedule?.market_phase === "open" ? "交易中" : "休市中"}</Badge>
            <span>最近行情刷新：{lastSummaryRefreshLabel}</span>
            <span>{marketRefreshLabel}</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={openCreateAccount}>新增账户</Button>
          <Button variant="outline" onClick={() => openScreenshotImportDialog()} disabled={accounts.length === 0}>截图导入</Button>
          <Button variant="outline" onClick={() => openCsvImportDialog()} disabled={accounts.length === 0}>CSV 导入</Button>
          <Button onClick={() => openCreatePosition()} disabled={accounts.length === 0}>新增持仓</Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
        <Card>
          <CardHeader className="pb-2"><CardDescription>可用资金</CardDescription></CardHeader>
          <CardContent className="text-2xl font-semibold">¥{money(summary?.available_funds_total ?? 0)}</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardDescription>总成本</CardDescription></CardHeader>
          <CardContent className="text-2xl font-semibold">¥{money(summary?.total_cost ?? 0)}</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardDescription>总市值</CardDescription></CardHeader>
          <CardContent className="text-2xl font-semibold">¥{money(summary?.total_market_value ?? 0)}</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardDescription>总资产</CardDescription></CardHeader>
          <CardContent className="text-2xl font-semibold">¥{money(summary?.total_assets ?? 0)}</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardDescription>组合仓位</CardDescription></CardHeader>
          <CardContent className="text-2xl font-semibold">{pct(summary?.total_position_ratio_pct ?? 0)}</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardDescription>累计 / 日内</CardDescription></CardHeader>
          <CardContent className={cn("text-2xl font-semibold", signedClass(summary?.total_pnl))}>
            ¥{money(summary?.total_pnl ?? 0)}
            <div className={cn("text-sm", signedClass(summary?.total_daily_pnl))}>
              日内 ¥{money(summary?.total_daily_pnl ?? 0)}
            </div>
          </CardContent>
        </Card>
      </div>

      {summary?.industry_exposures?.length ? (
        <Card>
          <CardHeader>
            <CardTitle>行业暴露</CardTitle>
            <CardDescription>按当前持仓市值统计前 8 个行业暴露。</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {summary.industry_exposures.map((exposure) => (
              <div key={exposure.industry} className="rounded-xl border border-border/60 bg-muted/20 p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="font-medium">{exposure.industry}</div>
                  <Badge variant="outline">{exposure.position_count} 只</Badge>
                </div>
                <div className="mt-2 text-sm text-muted-foreground">
                  市值 ¥{money(exposure.market_value)} · 权重 {pct(exposure.weight_pct)}
                </div>
                <div className="mt-2 text-xs text-muted-foreground">
                  {exposure.symbols.join(" · ")}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}

      {summary?.quote_error_count ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-700">
          有 {summary.quote_error_count} 条持仓行情刷新失败，请稍后重试或检查代码。
        </div>
      ) : null}

      {isLoading ? (
        <Card>
          <CardContent className="p-8 text-center text-sm text-muted-foreground">正在加载持仓...</CardContent>
        </Card>
      ) : accounts.length === 0 ? (
        <Card>
          <CardContent className="p-10 text-center">
            <div className="text-lg font-medium">还没有账户</div>
            <p className="mt-2 text-sm text-muted-foreground">先创建一个账户，再录入股票成本、数量和 lot 记录。</p>
            <Button className="mt-4" onClick={openCreateAccount}>创建第一个账户</Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {accounts.map((account) => {
            const accountPositions = account.positions ?? [];
            const accountIndustryExposures = account.industry_exposures ?? [];

            return (
              <Card key={account.id}>
                <CardHeader>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <CardTitle>{account.name}</CardTitle>
                        <Badge variant="outline">{account.enabled ? "启用" : "停用"}</Badge>
                        <Badge variant="secondary">{accountPositions.length} 只持仓</Badge>
                      </div>
                      <CardDescription>
                        可用资金 ¥{money(account.available_funds)} · 总资产 ¥{money(account.total_assets)} · 仓位 {pct(account.position_ratio_pct)} · 账户维护于 {formatTimestamp(account.updated_at)}
                      </CardDescription>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Button variant="outline" size="sm" onClick={() => openScreenshotImportDialog(account.id)}>截图导入</Button>
                      <Button variant="outline" size="sm" onClick={() => openCsvImportDialog(account.id)}>CSV 导入</Button>
                      <Button variant="outline" size="sm" onClick={() => openCreatePosition(account.id)}>加持仓</Button>
                      <Button variant="ghost" size="sm" onClick={() => openEditAccount(account)}>编辑账户</Button>
                      <Button variant="ghost" size="sm" onClick={() => void removeAccount(account)}>删除</Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="mb-4 grid gap-3 md:grid-cols-6">
                    <div className="rounded-xl bg-muted/35 p-3"><div className="text-xs text-muted-foreground">可用资金</div><div className="font-semibold">¥{money(account.available_funds)}</div></div>
                    <div className="rounded-xl bg-muted/35 p-3"><div className="text-xs text-muted-foreground">成本</div><div className="font-semibold">¥{money(account.total_cost)}</div></div>
                    <div className="rounded-xl bg-muted/35 p-3"><div className="text-xs text-muted-foreground">市值</div><div className="font-semibold">¥{money(account.total_market_value)}</div></div>
                    <div className="rounded-xl bg-muted/35 p-3"><div className="text-xs text-muted-foreground">总资产</div><div className="font-semibold">¥{money(account.total_assets)}</div></div>
                    <div className="rounded-xl bg-muted/35 p-3"><div className="text-xs text-muted-foreground">仓位</div><div className="font-semibold">{pct(account.position_ratio_pct)}</div></div>
                    <div className="rounded-xl bg-muted/35 p-3"><div className="text-xs text-muted-foreground">盈亏 / 日内</div><div className={cn("font-semibold", signedClass(account.total_pnl))}>¥{money(account.total_pnl)} <span className="text-xs">{pct(account.total_pnl_pct)}</span><div className={cn("text-xs", signedClass(account.total_daily_pnl))}>日内 ¥{money(account.total_daily_pnl)}</div></div></div>
                  </div>

                  {accountIndustryExposures.length > 0 && (
                    <div className="mb-4 flex flex-wrap gap-2">
                      {accountIndustryExposures.slice(0, 4).map((exposure) => (
                        <Badge key={exposure.industry} variant="outline">
                          {exposure.industry} · {pct(exposure.weight_pct)}
                        </Badge>
                      ))}
                    </div>
                  )}

                  {accountPositions.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-border/70 p-6 text-center text-sm text-muted-foreground">
                      这个账户还没有持仓。
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full min-w-[1180px] text-sm">
                        <thead className="text-xs text-muted-foreground">
                          <tr className="border-b">
                            <th className="py-2 text-left">股票</th>
                            <th className="py-2 text-right">成本</th>
                            <th className="py-2 text-right">总仓 / 可用 / 冻结</th>
                            <th className="py-2 text-right">现价 / 涨跌</th>
                            <th className="py-2 text-right">市值 / 仓位</th>
                            <th className="py-2 text-right">操作</th>
                          </tr>
                        </thead>
                        <tbody>
                          {accountPositions.map((position) => (
                            <tr key={position.id} className="border-b border-border/50 last:border-0 align-top">
                              <td className="py-3">
                                <div className="flex items-center gap-2">
                                  <div className="font-medium">{position.name}</div>
                                  {position.industry ? <Badge variant="outline">{position.industry}</Badge> : null}
                                </div>
                                <div className="text-xs text-muted-foreground">
                                  {position.symbol} · {STYLE_LABELS[position.trading_style]}
                                </div>
                                {position.quote_error && <div className="text-xs text-amber-600">行情失败：{position.quote_error}</div>}
                                {position.advice?.headline && (
                                  <div className="mt-1 text-xs text-muted-foreground">{position.advice.headline}</div>
                                )}
                              </td>
                              <td className="py-3 text-right font-mono">
                                <div>{money(position.cost_price)}</div>
                              </td>
                              <td className="py-3 text-right font-mono">
                                <div>{position.quantity} 股</div>
                                <div className="text-xs text-muted-foreground">可用 {position.available_quantity ?? 0} / 冻结 {position.frozen_quantity ?? 0}</div>
                                <div className="text-xs text-muted-foreground">可用率 {pct(position.available_ratio_pct ?? 0)}</div>
                              </td>
                              <td className="py-3 text-right font-mono">
                                <div>{money(position.latest_price)}</div>
                                <div className={cn("text-xs", signedClass(position.change_pct))}>{pct(position.change_pct)}</div>
                              </td>
                              <td className="py-3 text-right font-mono">
                                <div>¥{money(position.market_value)}</div>
                                <div className={cn("text-xs", signedClass(position.pnl))}>
                                  累计 ¥{money(position.pnl)} · {pct(position.pnl_pct)}
                                </div>
                                <div className="text-xs text-muted-foreground">仓位 {pct(position.weight_pct)}</div>
                              </td>
                              <td className="py-3 text-right">
                                <div className="flex justify-end gap-1">
                                  <Link href={`/stocks/${encodeURIComponent(position.symbol)}`}>
                                    <Button variant="ghost" size="sm">详情</Button>
                                  </Link>
                                  <Button variant="ghost" size="sm" onClick={() => void createRiskRule(position)}>风险规则</Button>
                                  <Button variant="ghost" size="sm" onClick={() => openEditPosition(position)}>编辑</Button>
                                  <Button variant="ghost" size="sm" onClick={() => void removePosition(position)}>删除</Button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <Dialog open={accountDialogOpen} onOpenChange={setAccountDialogOpen}>
        <DialogHeader>
          <DialogTitle>{editingAccount ? "编辑账户" : "新增账户"}</DialogTitle>
          <DialogDescription>账户只存储在本地 JSON，不会连接真实券商。</DialogDescription>
        </DialogHeader>
        <DialogClose onClose={() => setAccountDialogOpen(false)} />
        <DialogContent className="space-y-4 pt-0">
          <label className="space-y-1 text-sm">
            <span className="text-muted-foreground">账户名称</span>
            <Input value={accountName} onChange={(event) => setAccountName(event.target.value)} placeholder="例如：主账户" />
          </label>
          <label className="space-y-1 text-sm">
            <span className="text-muted-foreground">可用资金</span>
            <Input type="number" value={availableFunds} onChange={(event) => setAvailableFunds(event.target.value)} />
          </label>
          <label className="space-y-1 text-sm">
            <span className="text-muted-foreground">状态</span>
            <Select
              value={accountEnabled ? "true" : "false"}
              onChange={(event) => setAccountEnabled(event.target.value === "true")}
              options={[
                { value: "true", label: "启用" },
                { value: "false", label: "停用" },
              ]}
            />
          </label>
        </DialogContent>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setAccountDialogOpen(false)}>取消</Button>
          <Button disabled={isMutating} onClick={() => void saveAccount()}>{isMutating ? "保存中..." : "保存"}</Button>
        </DialogFooter>
      </Dialog>

      <Dialog open={positionDialogOpen} onOpenChange={setPositionDialogOpen}>
        <DialogHeader>
          <DialogTitle>{editingPosition ? "编辑持仓" : "新增持仓"}</DialogTitle>
          <DialogDescription>维护股票代码、成本、数量、行业和交易风格。</DialogDescription>
        </DialogHeader>
        <DialogClose onClose={() => setPositionDialogOpen(false)} />
        <DialogContent className="space-y-4 pt-0">
          <label className="space-y-1 text-sm">
            <span className="text-muted-foreground">账户</span>
            <Select
              value={positionAccountId || defaultAccountId}
              onChange={(event) => setPositionAccountId(event.target.value)}
              options={accounts.map((account) => ({ value: account.id, label: account.name }))}
            />
          </label>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-1 text-sm">
              <span className="text-muted-foreground">股票代码</span>
              <Input value={symbol} onChange={(event) => setSymbol(event.target.value)} placeholder="600519 或 600519.SH" />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-muted-foreground">股票名称（可选）</span>
              <Input value={stockName} onChange={(event) => setStockName(event.target.value)} placeholder="留空自动尝试补全" />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-muted-foreground">手工成本价</span>
              <Input type="number" value={costPrice} onChange={(event) => setCostPrice(event.target.value)} placeholder="例如：12.34" />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-muted-foreground">持仓数量</span>
              <Input type="number" value={quantity} onChange={(event) => setQuantity(event.target.value)} placeholder="例如：1000" />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-muted-foreground">可用数量</span>
              <Input type="number" value={availableQuantity} onChange={(event) => setAvailableQuantity(event.target.value)} placeholder="默认等于总仓" />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-muted-foreground">冻结数量</span>
              <Input type="number" value={frozenQuantity} onChange={(event) => setFrozenQuantity(event.target.value)} placeholder="默认 0" />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-muted-foreground">交易风格</span>
              <Select value={tradingStyle} onChange={(event) => setTradingStyle(event.target.value as TradingStyle)} options={STYLE_OPTIONS} />
            </label>
            <label className="space-y-1 text-sm">
              <span className="text-muted-foreground">行业</span>
              <Input value={industry} onChange={(event) => setIndustry(event.target.value)} placeholder="例如：有色金属" />
            </label>
          </div>
        </DialogContent>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setPositionDialogOpen(false)}>取消</Button>
          <Button disabled={isMutating} onClick={() => void savePosition()}>{isMutating ? "保存中..." : "保存"}</Button>
        </DialogFooter>
      </Dialog>

      <Dialog open={screenshotDialogOpen} onOpenChange={setScreenshotDialogOpen}>
        <DialogHeader>
          <DialogTitle>截图导入持仓</DialogTitle>
          <DialogDescription>上传券商持仓截图，系统会识别股票、数量、成本和可用数量。</DialogDescription>
        </DialogHeader>
        <DialogClose onClose={() => setScreenshotDialogOpen(false)} />
        <DialogContent className="space-y-4 pt-0">
          <label className="space-y-1 text-sm">
            <span className="text-muted-foreground">导入到账户</span>
            <Select
              value={importAccountId || defaultAccountId}
              onChange={(event) => setImportAccountId(event.target.value)}
              options={accounts.map((account) => ({ value: account.id, label: account.name }))}
            />
          </label>
          <label className="space-y-1 text-sm">
            <span className="text-muted-foreground">券商模板</span>
            <Select
              value={importBrokerTemplate}
              onChange={(event) => setImportBrokerTemplate(event.target.value as PortfolioBrokerTemplate)}
              options={BROKER_TEMPLATE_OPTIONS}
            />
          </label>
          <label className="space-y-1 text-sm">
            <span className="text-muted-foreground">截图文件</span>
            <Input type="file" accept="image/*" onChange={handleImportFileChange} />
            <div className="text-xs text-muted-foreground">
              {importFileName ? `已选择：${importFileName}` : "默认跳过持仓为 0 的已清仓行。先预览，再确认导入。"}
            </div>
          </label>
          {importPreviewResult ? (
            <div className="rounded-xl border border-border/60 bg-muted/20 p-3">
              <div className="flex flex-wrap gap-2 text-xs">
                <Badge variant="secondary">{importPreviewResult.broker_name || "未识别券商"}</Badge>
                <Badge variant="secondary">识别 {importPreviewResult.parsed_count}</Badge>
                <Badge variant="secondary">可导入 {importPreviewResult.rows.filter((row) => row.action === "preview").length}</Badge>
                <Badge variant="secondary">跳过 {importPreviewResult.skipped_count}</Badge>
              </div>
              <div className="mt-3 max-h-72 overflow-auto">
                <table className="w-full text-sm">
                  <thead className="text-xs text-muted-foreground">
                    <tr className="border-b">
                      <th className="py-2 text-left">股票</th>
                      <th className="py-2 text-right">持仓 / 可用</th>
                      <th className="py-2 text-right">成本 / 现价</th>
                      <th className="py-2 text-right">状态</th>
                    </tr>
                  </thead>
                  <tbody>
                    {importPreviewResult.rows.map((row, index) => (
                      <tr key={`${row.name}-${index}`} className="border-b border-border/40 last:border-0">
                        <td className="py-2">
                          <div className="font-medium">{row.name}</div>
                          <div className="text-xs text-muted-foreground">{row.symbol || row.reason || "--"}</div>
                        </td>
                        <td className="py-2 text-right font-mono">
                          <div>{row.quantity}</div>
                          <div className="text-xs text-muted-foreground">{row.available_quantity ?? "--"}</div>
                        </td>
                        <td className="py-2 text-right font-mono">
                          <div>{money(row.cost_price)}</div>
                          <div className="text-xs text-muted-foreground">{money(row.latest_price)}</div>
                        </td>
                        <td className="py-2 text-right">
                          <Badge variant="outline">{row.action}</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}
        </DialogContent>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setScreenshotDialogOpen(false)}>取消</Button>
          <Button variant="outline" disabled={isMutating || !importImageDataUrl} onClick={() => void handlePreviewScreenshot()}>
            {isMutating ? "处理中..." : "预览识别"}
          </Button>
          <Button disabled={isMutating || !importPreviewResult} onClick={() => void handleConfirmScreenshotImport()}>
            {isMutating ? "导入中..." : "确认导入"}
          </Button>
        </DialogFooter>
      </Dialog>

      <Dialog open={csvDialogOpen} onOpenChange={setCsvDialogOpen}>
        <DialogHeader>
          <DialogTitle>CSV 导入持仓</DialogTitle>
          <DialogDescription>
            支持列：`symbol/name/cost_price/quantity/available_quantity/frozen_quantity/industry/trading_style`。
          </DialogDescription>
        </DialogHeader>
        <DialogClose onClose={() => setCsvDialogOpen(false)} />
        <DialogContent className="space-y-4 pt-0">
          <label className="space-y-1 text-sm">
            <span className="text-muted-foreground">导入到账户</span>
            <Select
              value={csvAccountId || defaultAccountId}
              onChange={(event) => setCsvAccountId(event.target.value)}
              options={accounts.map((account) => ({ value: account.id, label: account.name }))}
            />
          </label>
          <label className="space-y-1 text-sm">
            <span className="text-muted-foreground">CSV 文件</span>
            <Input type="file" accept=".csv,text/csv" onChange={handleCsvFileChange} />
            <div className="text-xs text-muted-foreground">
              {csvFileName ? `已选择：${csvFileName}` : "可直接上传文件，也可在下方粘贴 CSV 内容。"}
            </div>
          </label>
          <label className="space-y-1 text-sm">
            <span className="text-muted-foreground">CSV 内容</span>
            <Textarea
              rows={8}
              value={csvText}
              onChange={(event) => {
                setCsvText(event.target.value);
                setCsvPreviewResult(null);
              }}
              placeholder={"symbol,name,cost_price,quantity,available_quantity,industry\n600519.SH,贵州茅台,1680,100,100,白酒"}
            />
          </label>
          {csvPreviewResult ? (
            <div className="rounded-xl border border-border/60 bg-muted/20 p-3">
              <div className="flex flex-wrap gap-2 text-xs">
                <Badge variant="secondary">解析 {csvPreviewResult.parsed_count}</Badge>
                <Badge variant="secondary">可导入 {csvPreviewResult.rows.filter((row) => row.action === "preview").length}</Badge>
                <Badge variant="secondary">跳过 {csvPreviewResult.skipped_count}</Badge>
              </div>
              <div className="mt-3 max-h-72 overflow-auto">
                <table className="w-full text-sm">
                  <thead className="text-xs text-muted-foreground">
                    <tr className="border-b">
                      <th className="py-2 text-left">股票</th>
                      <th className="py-2 text-right">数量</th>
                      <th className="py-2 text-right">成本</th>
                      <th className="py-2 text-left">行业</th>
                      <th className="py-2 text-right">状态</th>
                    </tr>
                  </thead>
                  <tbody>
                    {csvPreviewResult.rows.map((row, index) => (
                      <tr key={`${row.symbol}-${index}`} className="border-b border-border/40 last:border-0">
                        <td className="py-2">
                          <div className="font-medium">{row.name || row.symbol}</div>
                          <div className="text-xs text-muted-foreground">{row.symbol}</div>
                        </td>
                        <td className="py-2 text-right font-mono">
                          <div>{row.quantity}</div>
                          <div className="text-xs text-muted-foreground">可用 {row.available_quantity ?? "--"} / 冻结 {row.frozen_quantity ?? "--"}</div>
                        </td>
                        <td className="py-2 text-right font-mono">{money(row.cost_price)}</td>
                        <td className="py-2 text-xs text-muted-foreground">{row.industry || "--"}</td>
                        <td className="py-2 text-right">
                          <Badge variant="outline">{row.action}</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}
        </DialogContent>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setCsvDialogOpen(false)}>取消</Button>
          <Button variant="outline" disabled={isMutating || !csvText.trim()} onClick={() => void handlePreviewCsv()}>
            {isMutating ? "处理中..." : "预览 CSV"}
          </Button>
          <Button disabled={isMutating || !csvText.trim()} onClick={() => void handleConfirmCsvImport()}>
            {isMutating ? "导入中..." : "确认导入"}
          </Button>
        </DialogFooter>
      </Dialog>
    </div>
  );
}
