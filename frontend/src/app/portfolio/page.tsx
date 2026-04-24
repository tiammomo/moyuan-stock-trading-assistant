"use client";

import { ChangeEvent, useMemo, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/Dialog";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { toast } from "@/components/ui/Toast";
import { usePortfolio } from "@/hooks/usePortfolio";
import { cn, formatDateTime, formatTimestamp } from "@/lib/utils";
import type {
  PortfolioAccountView,
  PortfolioBrokerTemplate,
  PortfolioPositionView,
  PortfolioScreenshotImportResponse,
  TradingStyle,
} from "@/types/portfolio";

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
    isMutating,
  } = usePortfolio();

  const accounts = summary?.accounts ?? [];
  const [accountDialogOpen, setAccountDialogOpen] = useState(false);
  const [positionDialogOpen, setPositionDialogOpen] = useState(false);
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [editingAccount, setEditingAccount] = useState<PortfolioAccountView | null>(null);
  const [editingPosition, setEditingPosition] = useState<PortfolioPositionView | null>(null);
  const [importPreviewResult, setImportPreviewResult] = useState<PortfolioScreenshotImportResponse | null>(null);
  const [targetAccountId, setTargetAccountId] = useState("");

  const [accountName, setAccountName] = useState("");
  const [availableFunds, setAvailableFunds] = useState("0");
  const [accountEnabled, setAccountEnabled] = useState(true);

  const [positionAccountId, setPositionAccountId] = useState("");
  const [symbol, setSymbol] = useState("");
  const [stockName, setStockName] = useState("");
  const [costPrice, setCostPrice] = useState("");
  const [quantity, setQuantity] = useState("");
  const [tradingStyle, setTradingStyle] = useState<TradingStyle>("swing");
  const [note, setNote] = useState("");
  const [importAccountId, setImportAccountId] = useState("");
  const [importFileName, setImportFileName] = useState("");
  const [importImageDataUrl, setImportImageDataUrl] = useState("");
  const [importBrokerTemplate, setImportBrokerTemplate] = useState<PortfolioBrokerTemplate>("auto");

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
    setTargetAccountId(accountId ?? defaultAccountId);
    setPositionAccountId(accountId ?? defaultAccountId);
    setSymbol("");
    setStockName("");
    setCostPrice("");
    setQuantity("");
    setTradingStyle("swing");
    setNote("");
    setPositionDialogOpen(true);
  };

  const openImportDialog = (accountId?: string) => {
    const resolvedAccountId = accountId ?? defaultAccountId;
    setImportAccountId(resolvedAccountId);
    setImportFileName("");
    setImportImageDataUrl("");
    setImportBrokerTemplate("auto");
    setImportPreviewResult(null);
    setImportDialogOpen(true);
  };

  const openEditPosition = (position: PortfolioPositionView) => {
    setEditingPosition(position);
    setTargetAccountId(position.account_id);
    setPositionAccountId(position.account_id);
    setSymbol(position.symbol);
    setStockName(position.name);
    setCostPrice(String(position.cost_price));
    setQuantity(String(position.quantity));
    setTradingStyle(position.trading_style);
    setNote(position.note ?? "");
    setPositionDialogOpen(true);
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
        await updateAccountAsync({ id: editingAccount.id, data: { name, available_funds: funds, enabled: accountEnabled } });
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
    const price = Number(costPrice);
    const qty = Number(quantity);
    if (!positionAccountId) {
      toast.error("请选择账户");
      return;
    }
    if (!normalizedSymbol) {
      toast.error("请输入股票代码");
      return;
    }
    if (!Number.isFinite(price) || price <= 0) {
      toast.error("成本价需要大于 0");
      return;
    }
    if (!Number.isInteger(qty) || qty <= 0) {
      toast.error("数量需要是正整数");
      return;
    }
    try {
      if (editingPosition) {
        await updatePositionAsync({
          id: editingPosition.id,
          data: {
            account_id: positionAccountId,
            symbol: normalizedSymbol,
            name: stockName.trim() || null,
            cost_price: price,
            quantity: qty,
            trading_style: tradingStyle,
            note: note.trim() || null,
          },
        });
        toast.success("持仓已更新");
      } else {
        await createPositionAsync({
          account_id: positionAccountId,
          symbol: normalizedSymbol,
          name: stockName.trim() || null,
          cost_price: price,
          quantity: qty,
          trading_style: tradingStyle,
          note: note.trim() || null,
        });
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

  const handleConfirmImport = async () => {
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
      setImportDialogOpen(false);
      setImportPreviewResult(null);
      setImportFileName("");
      setImportImageDataUrl("");
      toast.success(`截图导入完成：新增 ${result.imported_count}，更新 ${result.updated_count}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "截图导入失败");
    }
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">持仓账户</h1>
          <p className="text-sm text-muted-foreground">
            支持手动维护和手机截图导入。交易时段按 10 秒自动刷新行情、市值、盈亏和日内损益，持仓成本保持手工录入值不被覆盖。
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="secondary">{marketSchedule?.market_phase === "open" ? "交易中" : "休市中"}</Badge>
            <span>最近行情刷新：{lastSummaryRefreshLabel}</span>
            <span>{marketRefreshLabel}</span>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={openCreateAccount}>新增账户</Button>
          <Button variant="outline" onClick={() => openImportDialog()} disabled={accounts.length === 0}>截图导入</Button>
          <Button onClick={() => openCreatePosition()} disabled={accounts.length === 0}>新增持仓</Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2"><CardDescription>总成本</CardDescription></CardHeader>
          <CardContent className="text-2xl font-semibold">¥{money(summary?.total_cost ?? 0)}</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardDescription>总市值</CardDescription></CardHeader>
          <CardContent className="text-2xl font-semibold">¥{money(summary?.total_market_value ?? 0)}</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardDescription>累计盈亏</CardDescription></CardHeader>
          <CardContent className={cn("text-2xl font-semibold", signedClass(summary?.total_pnl))}>
            ¥{money(summary?.total_pnl ?? 0)} <span className="text-sm">{pct(summary?.total_pnl_pct ?? 0)}</span>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardDescription>日内盈亏</CardDescription></CardHeader>
          <CardContent className={cn("text-2xl font-semibold", signedClass(summary?.total_daily_pnl))}>
            ¥{money(summary?.total_daily_pnl ?? 0)}
          </CardContent>
        </Card>
      </div>

      {summary?.quote_error_count ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-700">
          有 {summary.quote_error_count} 条持仓行情刷新失败，请稍后重试或检查代码。
        </div>
      ) : null}

      {isLoading ? (
        <Card><CardContent className="p-8 text-center text-sm text-muted-foreground">正在加载持仓...</CardContent></Card>
      ) : accounts.length === 0 ? (
        <Card>
          <CardContent className="p-10 text-center">
            <div className="text-lg font-medium">还没有账户</div>
            <p className="mt-2 text-sm text-muted-foreground">先创建一个账户，再录入股票成本和数量。</p>
            <Button className="mt-4" onClick={openCreateAccount}>创建第一个账户</Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {accounts.map((account) => (
            <Card key={account.id}>
              <CardHeader>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <CardTitle>{account.name}</CardTitle>
                      <Badge variant="outline">{account.enabled ? "启用" : "停用"}</Badge>
                      <Badge variant="secondary">{account.positions.length} 只持仓</Badge>
                    </div>
                    <CardDescription>
                      可用资金 ¥{money(account.available_funds)} · 账户维护于 {formatTimestamp(account.updated_at)}
                    </CardDescription>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" onClick={() => openImportDialog(account.id)}>截图导入</Button>
                    <Button variant="outline" size="sm" onClick={() => openCreatePosition(account.id)}>加持仓</Button>
                    <Button variant="ghost" size="sm" onClick={() => openEditAccount(account)}>编辑账户</Button>
                    <Button variant="ghost" size="sm" onClick={() => void removeAccount(account)}>删除</Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="mb-4 grid gap-3 md:grid-cols-4">
                  <div className="rounded-xl bg-muted/35 p-3"><div className="text-xs text-muted-foreground">成本</div><div className="font-semibold">¥{money(account.total_cost)}</div></div>
                  <div className="rounded-xl bg-muted/35 p-3"><div className="text-xs text-muted-foreground">市值</div><div className="font-semibold">¥{money(account.total_market_value)}</div></div>
                  <div className="rounded-xl bg-muted/35 p-3"><div className="text-xs text-muted-foreground">盈亏</div><div className={cn("font-semibold", signedClass(account.total_pnl))}>¥{money(account.total_pnl)} {pct(account.total_pnl_pct)}</div></div>
                  <div className="rounded-xl bg-muted/35 p-3"><div className="text-xs text-muted-foreground">日内</div><div className={cn("font-semibold", signedClass(account.total_daily_pnl))}>¥{money(account.total_daily_pnl)}</div></div>
                </div>

                {account.positions.length === 0 ? (
                  <div className="rounded-xl border border-dashed border-border/70 p-6 text-center text-sm text-muted-foreground">
                    这个账户还没有持仓。
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="text-xs text-muted-foreground">
                        <tr className="border-b">
                          <th className="py-2 text-left">股票</th>
                          <th className="py-2 text-right">成本/数量</th>
                          <th className="py-2 text-right">现价/涨跌</th>
                          <th className="py-2 text-right">市值</th>
                          <th className="py-2 text-right">盈亏</th>
                          <th className="py-2 text-right">操作</th>
                        </tr>
                      </thead>
                      <tbody>
                        {account.positions.map((position) => (
                          <tr key={position.id} className="border-b border-border/50 last:border-0">
                            <td className="py-3">
                              <div className="font-medium">{position.name}</div>
                              <div className="text-xs text-muted-foreground">
                                {position.symbol} · {STYLE_LABELS[position.trading_style]}
                              </div>
                              {position.quote_error && <div className="text-xs text-amber-600">行情失败</div>}
                            </td>
                            <td className="py-3 text-right font-mono">
                              <div>{money(position.cost_price)}</div>
                              <div className="text-xs text-muted-foreground">{position.quantity} 股</div>
                            </td>
                            <td className="py-3 text-right font-mono">
                              <div>{money(position.latest_price)}</div>
                              <div className={cn("text-xs", signedClass(position.change_pct))}>{pct(position.change_pct)}</div>
                            </td>
                            <td className="py-3 text-right font-mono">¥{money(position.market_value)}</td>
                            <td className={cn("py-3 text-right font-mono", signedClass(position.pnl))}>
                              <div>¥{money(position.pnl)}</div>
                              <div className="text-xs">{pct(position.pnl_pct)}</div>
                            </td>
                            <td className="py-3 text-right">
                              <Button variant="ghost" size="sm" onClick={() => openEditPosition(position)}>编辑</Button>
                              <Button variant="ghost" size="sm" onClick={() => void removePosition(position)}>删除</Button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={accountDialogOpen} onOpenChange={setAccountDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingAccount ? "编辑账户" : "新增账户"}</DialogTitle>
            <DialogDescription>账户只存储在本地 JSON，不会连接真实券商。</DialogDescription>
          </DialogHeader>
          <DialogClose onClose={() => setAccountDialogOpen(false)} />
          <div className="space-y-4 p-5 pt-0">
            <label className="space-y-1 text-sm"><span className="text-muted-foreground">账户名称</span><Input value={accountName} onChange={(event) => setAccountName(event.target.value)} placeholder="例如：主账户" /></label>
            <label className="space-y-1 text-sm"><span className="text-muted-foreground">可用资金</span><Input type="number" value={availableFunds} onChange={(event) => setAvailableFunds(event.target.value)} /></label>
            <label className="space-y-1 text-sm"><span className="text-muted-foreground">状态</span><Select value={accountEnabled ? "true" : "false"} onChange={(event) => setAccountEnabled(event.target.value === "true")} options={[{ value: "true", label: "启用" }, { value: "false", label: "停用" }]} /></label>
          </div>
          <DialogFooter><Button variant="ghost" onClick={() => setAccountDialogOpen(false)}>取消</Button><Button disabled={isMutating} onClick={() => void saveAccount()}>{isMutating ? "保存中..." : "保存"}</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={positionDialogOpen} onOpenChange={setPositionDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingPosition ? "编辑持仓" : "新增持仓"}</DialogTitle>
            <DialogDescription>输入股票代码、成本价和数量，股票名称可留空自动补全。</DialogDescription>
          </DialogHeader>
          <DialogClose onClose={() => setPositionDialogOpen(false)} />
          <div className="grid gap-4 p-5 pt-0 md:grid-cols-2">
            <label className="space-y-1 text-sm md:col-span-2"><span className="text-muted-foreground">账户</span><Select value={positionAccountId || targetAccountId} onChange={(event) => setPositionAccountId(event.target.value)} options={accounts.map((account) => ({ value: account.id, label: account.name }))} /></label>
            <label className="space-y-1 text-sm"><span className="text-muted-foreground">股票代码</span><Input value={symbol} onChange={(event) => setSymbol(event.target.value)} placeholder="600519 或 600519.SH" /></label>
            <label className="space-y-1 text-sm"><span className="text-muted-foreground">股票名称（可选）</span><Input value={stockName} onChange={(event) => setStockName(event.target.value)} placeholder="留空自动尝试补全" /></label>
            <label className="space-y-1 text-sm"><span className="text-muted-foreground">成本价</span><Input type="number" value={costPrice} onChange={(event) => setCostPrice(event.target.value)} /></label>
            <label className="space-y-1 text-sm"><span className="text-muted-foreground">数量</span><Input type="number" value={quantity} onChange={(event) => setQuantity(event.target.value)} /></label>
            <label className="space-y-1 text-sm"><span className="text-muted-foreground">交易风格</span><Select value={tradingStyle} onChange={(event) => setTradingStyle(event.target.value as TradingStyle)} options={STYLE_OPTIONS} /></label>
            <label className="space-y-1 text-sm md:col-span-2"><span className="text-muted-foreground">备注</span><Input value={note} onChange={(event) => setNote(event.target.value)} placeholder="买入理由、计划止损等" /></label>
          </div>
          <DialogFooter><Button variant="ghost" onClick={() => setPositionDialogOpen(false)}>取消</Button><Button disabled={isMutating} onClick={() => void savePosition()}>{isMutating ? "保存中..." : "保存"}</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={importDialogOpen} onOpenChange={setImportDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>截图导入持仓</DialogTitle>
            <DialogDescription>
              上传券商 App 的持仓列表截图，系统会识别股票名称、持仓数量和成本价，并直接写入当前账户。
            </DialogDescription>
          </DialogHeader>
          <DialogClose onClose={() => setImportDialogOpen(false)} />
          <div className="space-y-4 p-5 pt-0">
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
                        <th className="py-2 text-right">持仓/可用</th>
                        <th className="py-2 text-right">成本/现价</th>
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
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setImportDialogOpen(false)}>取消</Button>
            <Button variant="outline" disabled={isMutating || !importImageDataUrl} onClick={() => void handlePreviewScreenshot()}>
              {isMutating ? "处理中..." : "预览识别"}
            </Button>
            <Button disabled={isMutating || !importPreviewResult} onClick={() => void handleConfirmImport()}>
              {isMutating ? "导入中..." : "确认导入"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
