"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
  DialogClose,
} from "@/components/ui/Dialog";
import { toast } from "@/components/ui/Toast";
import { useWatchlist } from "@/hooks/useWatchlist";
import { buildAutoWatchTags, mergeWatchTags } from "@/lib/watchlistAutoFill";
import {
  cn,
  BUCKET_LABELS,
  BUCKET_COLORS,
  formatTimestamp,
  normalizeStockSymbol,
} from "@/lib/utils";
import type {
  WatchItemCreate,
  WatchItemUpdate,
  WatchItemRecord,
  WatchStockCandidate,
} from "@/types/watchlist";
import type { WatchBucket } from "@/types/common";

const BUCKET_OPTIONS = [
  { value: "short_term", label: "短线" },
  { value: "swing", label: "波段" },
  { value: "mid_term_value", label: "中线价值" },
  { value: "observe", label: "观察" },
  { value: "discard", label: "丢弃" },
];

export default function WatchlistPage() {
  const {
    watchlist,
    isLoading,
    createItemAsync,
    updateItemAsync,
    deleteItemAsync,
    resolveStockAsync,
    isCreating,
    isResolving,
    isUpdating,
  } = useWatchlist();

  const [filterBucket, setFilterBucket] = useState<string>("全部");
  const [searchQuery, setSearchQuery] = useState("");
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<WatchItemRecord | null>(null);
  const [stockQuery, setStockQuery] = useState("");
  const [resolvedCandidate, setResolvedCandidate] = useState<WatchStockCandidate | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [autoTags, setAutoTags] = useState<string[]>([]);
  const [hiddenAutoTags, setHiddenAutoTags] = useState<string[]>([]);

  const [formData, setFormData] = useState<WatchItemCreate>({
    query: null,
    symbol: null,
    name: null,
    bucket: "observe",
    tags: [],
    note: null,
  });
  const [tagInput, setTagInput] = useState("");
  const visibleAutoTags = useMemo(
    () => autoTags.filter((tag) => !hiddenAutoTags.includes(tag)),
    [autoTags, hiddenAutoTags]
  );
  const mergedTags = useMemo(
    () => (editingItem ? formData.tags : mergeWatchTags(visibleAutoTags, formData.tags)),
    [editingItem, formData.tags, visibleAutoTags]
  );

  const buckets = ["全部", ...BUCKET_OPTIONS.map((b) => b.value)];
  const filteredItems = watchlist.filter((item) => {
    const matchBucket =
      filterBucket === "全部" || item.bucket === filterBucket;
    const matchSearch =
      !searchQuery ||
      item.name.includes(searchQuery) ||
      item.symbol.includes(searchQuery);
    return matchBucket && matchSearch;
  });

  const handleOpenAdd = () => {
    setEditingItem(null);
    setFormData({
      query: null,
      symbol: null,
      name: null,
      bucket: "observe",
      tags: [],
      note: null,
    });
    setStockQuery("");
    setResolvedCandidate(null);
    setFormError(null);
    setAutoTags([]);
    setHiddenAutoTags([]);
    setTagInput("");
    setIsAddDialogOpen(true);
  };

  const handleOpenEdit = (item: WatchItemRecord) => {
    setEditingItem(item);
    setFormData({
      symbol: item.symbol,
      name: item.name,
      bucket: item.bucket,
      tags: [...item.tags],
      note: item.note,
    });
    setStockQuery(item.symbol);
    setResolvedCandidate(null);
    setFormError(null);
    setAutoTags([]);
    setHiddenAutoTags([]);
    setTagInput("");
    setIsAddDialogOpen(true);
  };

  const applyResolvedCandidate = (candidate: WatchStockCandidate, query: string) => {
    setResolvedCandidate(candidate);
    setAutoTags(buildAutoWatchTags({ candidate, bucket: formData.bucket }));
    setHiddenAutoTags([]);
    setFormData((current) => ({
      ...current,
      query,
      symbol: candidate.symbol,
      name: candidate.name,
    }));
  };

  const handleResolveStock = async (input?: string) => {
    const query = (input ?? stockQuery).trim();
    if (!query) {
      setFormError("请输入股票名称或代码");
      return null;
    }

    try {
      setFormError(null);
      const candidate = await resolveStockAsync({ query });
      applyResolvedCandidate(candidate, query);
      return candidate;
    } catch (error) {
      setResolvedCandidate(null);
      setAutoTags([]);
      setHiddenAutoTags([]);
      setFormData((current) => ({
        ...current,
        query,
        symbol: null,
        name: null,
      }));
      setFormError(error instanceof Error ? error.message : "股票识别失败");
      return null;
    }
  };

  const handleSave = async () => {
    try {
      setFormError(null);

      if (editingItem) {
        await updateItemAsync({
          id: editingItem.id,
          data: {
            bucket: formData.bucket,
            tags: formData.tags,
            note: formData.note,
          },
        });
        toast.success(`已更新：${editingItem.name}（${editingItem.symbol}）`);
      } else {
        const query = stockQuery.trim();
        let candidate = resolvedCandidate;
        if (!candidate && query) {
          candidate = await handleResolveStock(query);
        }
        if (!candidate && !(formData.symbol && formData.name)) {
          setFormError("请先识别股票，再保存到候选池");
          return;
        }

        const generatedTags = buildAutoWatchTags({
          candidate,
          bucket: formData.bucket,
        }).filter((tag) => !hiddenAutoTags.includes(tag));

        await createItemAsync({
          query: query || formData.query || null,
          symbol: candidate?.symbol || formData.symbol || null,
          name: candidate?.name || formData.name || null,
          bucket: formData.bucket,
          tags: mergeWatchTags(generatedTags, formData.tags),
          note: formData.note,
        });
        const displayName = candidate?.name || formData.name || query;
        const displaySymbol = normalizeStockSymbol(candidate?.symbol || formData.symbol || null);
        toast.success(`已加入候选池：${displayName}${displaySymbol ? `（${displaySymbol}）` : ""}`);
      }

      setIsAddDialogOpen(false);
    } catch (error) {
      const message = error instanceof Error ? error.message : "保存失败，请稍后重试";
      setFormError(message);
      if (message.includes("已在候选池中")) {
        toast.warning(message);
      } else {
        toast.error(message);
      }
    }
  };

  const handleDelete = async (id: string, name: string, symbol: string) => {
    if (confirm("确定要从候选池移除吗？")) {
      try {
        await deleteItemAsync(id);
        toast.success(`已从候选池移除：${name}（${symbol}）`);
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "移除失败，请稍后重试");
      }
    }
  };

  const addTag = () => {
    const nextTag = tagInput.trim();
    if (nextTag && !mergedTags.includes(nextTag)) {
      setHiddenAutoTags((current) => current.filter((tag) => tag !== nextTag));
      setFormData({ ...formData, tags: [...formData.tags, nextTag] });
      setTagInput("");
    }
  };

  const removeTag = (tag: string) => {
    if (!editingItem && visibleAutoTags.includes(tag) && !formData.tags.includes(tag)) {
      setHiddenAutoTags((current) => (current.includes(tag) ? current : [...current, tag]));
      return;
    }
    setFormData({
      ...formData,
      tags: formData.tags.filter((t) => t !== tag),
    });
  };

  const saveDisabled = editingItem
    ? isUpdating
    : isCreating || isResolving || (!stockQuery.trim() && !(formData.symbol && formData.name));

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">候选池</h1>
          <p className="text-sm text-muted-foreground">
            管理你的股票候选列表
          </p>
        </div>
        <Button onClick={handleOpenAdd}>添加股票</Button>
      </div>

      {/* Filters */}
      <div className="flex gap-4 mb-6">
        <Input
          placeholder="搜索股票..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-64"
        />
        <div className="flex gap-2">
          {buckets.map((bucket) => (
            <Button
              key={bucket}
              variant={filterBucket === bucket ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setFilterBucket(bucket)}
            >
              {bucket === "全部" ? bucket : BUCKET_LABELS[bucket]}
            </Button>
          ))}
        </div>
      </div>

      {/* Watchlist Table */}
      {isLoading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-muted rounded-lg animate-pulse" />
          ))}
        </div>
      ) : filteredItems.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            {watchlist.length === 0
              ? "候选池为空，开始添加股票吧"
              : "没有匹配的股票"}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <div className="divide-y">
            {filteredItems.map((item) => (
              <div
                key={item.id}
                className="flex items-center gap-4 p-4 hover:bg-muted/50"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{item.name}</span>
                    <span className="text-sm text-muted-foreground">
                      {item.symbol}
                    </span>
                    <Badge
                      variant="outline"
                      className={cn("text-xs", BUCKET_COLORS[item.bucket])}
                    >
                      {BUCKET_LABELS[item.bucket]}
                    </Badge>
                  </div>
                  {item.tags.length > 0 && (
                    <div className="flex gap-1 mt-1">
                      {item.tags.map((tag) => (
                        <Badge
                          key={tag}
                          variant="secondary"
                          className="text-[10px] px-1 py-0"
                        >
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}
                  {item.note && (
                    <p className="text-xs text-muted-foreground mt-1 truncate">
                      {item.note}
                    </p>
                  )}
                </div>
                <div className="text-xs text-muted-foreground">
                  {formatTimestamp(item.created_at)}
                </div>
                <div className="flex gap-1">
                  <Link href={`/stocks/${encodeURIComponent(item.symbol)}`}>
                    <Button variant="ghost" size="sm" className="h-7 text-xs">
                      详情
                    </Button>
                  </Link>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => handleOpenEdit(item)}
                  >
                    编辑
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs text-red-500"
                    onClick={() => void handleDelete(item.id, item.name, item.symbol)}
                  >
                    删除
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Add/Edit Dialog */}
      <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
        <DialogContent>
          <DialogClose onClose={() => setIsAddDialogOpen(false)} />
          <DialogHeader>
            <DialogTitle>{editingItem ? "编辑股票" : "添加股票"}</DialogTitle>
            <DialogDescription>
              {editingItem
                ? "修改股票的信息和标签"
                : "输入股票名称或代码，自动识别后加入候选池"}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {!editingItem && (
              <>
                <div>
                  <label className="text-sm font-medium mb-1 block">
                    股票代码或名称
                  </label>
                  <div className="flex gap-2">
                    <Input
                      value={stockQuery}
                      onChange={(e) => {
                        setStockQuery(e.target.value);
                        setResolvedCandidate(null);
                        setFormError(null);
                        setAutoTags([]);
                        setHiddenAutoTags([]);
                        setFormData((current) => ({
                          ...current,
                          query: e.target.value || null,
                          symbol: null,
                          name: null,
                        }));
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          void handleResolveStock();
                        }
                      }}
                      placeholder="例如：东阳光 / 600673 / 600673.SH"
                    />
                    <Button
                      variant="outline"
                      onClick={() => void handleResolveStock()}
                      disabled={!stockQuery.trim() || isResolving}
                    >
                      {isResolving ? "识别中..." : "识别"}
                    </Button>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    支持输入股票名称、6 位代码或带交易所后缀代码
                  </p>
                </div>
                {resolvedCandidate && (
                  <Card className="border-dashed">
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm">识别结果</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2 text-sm">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{resolvedCandidate.name}</span>
                        <span className="text-muted-foreground">
                          {resolvedCandidate.symbol}
                        </span>
                        {typeof resolvedCandidate.change_pct === "number" && (
                          <Badge variant="outline">
                            {resolvedCandidate.change_pct >= 0 ? "+" : ""}
                            {resolvedCandidate.change_pct.toFixed(2)}%
                          </Badge>
                        )}
                      </div>
                      {typeof resolvedCandidate.latest_price === "number" && (
                        <div className="text-muted-foreground">
                          最新价：{resolvedCandidate.latest_price}
                        </div>
                      )}
                      {resolvedCandidate.industry && (
                        <div className="text-muted-foreground">
                          行业：{resolvedCandidate.industry}
                        </div>
                      )}
                      {resolvedCandidate.concepts.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {resolvedCandidate.concepts.map((concept) => (
                            <Badge
                              key={concept}
                              variant="secondary"
                              className="text-[10px] px-1 py-0"
                            >
                              {concept}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}
              </>
            )}
            {editingItem && (
              <div className="rounded-lg border bg-muted/30 px-3 py-2 text-sm">
                <div className="font-medium">{editingItem.name}</div>
                <div className="text-muted-foreground">{editingItem.symbol}</div>
              </div>
            )}
            <div>
              <label className="text-sm font-medium mb-1 block">分类</label>
              <Select
                options={BUCKET_OPTIONS}
                value={formData.bucket}
                onChange={(e) => {
                  const bucket = e.target.value as WatchBucket;
                  setFormData({
                    ...formData,
                    bucket,
                  });
                  if (!editingItem) {
                    setAutoTags(buildAutoWatchTags({ candidate: resolvedCandidate, bucket }));
                  }
                }}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">标签</label>
              <div className="flex gap-2 mb-2">
                <Input
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      addTag();
                    }
                  }}
                  placeholder="输入标签后按Enter添加"
                  className="flex-1"
                />
                <Button variant="outline" onClick={addTag}>
                  添加
                </Button>
              </div>
              <div className="flex flex-wrap gap-1">
                {mergedTags.map((tag) => (
                  <Badge
                    key={tag}
                    variant={visibleAutoTags.includes(tag) && !formData.tags.includes(tag) ? "outline" : "secondary"}
                    className="cursor-pointer"
                    onClick={() => removeTag(tag)}
                  >
                    {tag} ✕
                  </Badge>
                ))}
              </div>
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">备注</label>
              <Input
                value={formData.note || ""}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    note: e.target.value || null,
                  })
                }
                placeholder="添加备注信息..."
              />
            </div>
            {formError && (
              <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">
                {formError}
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAddDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={() => void handleSave()} disabled={saveDisabled}>
              {isCreating || isUpdating ? "保存中..." : "保存"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
