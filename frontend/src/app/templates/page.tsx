"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Select } from "@/components/ui/Select";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
  DialogClose,
} from "@/components/ui/Dialog";
import { useTemplates } from "@/hooks/useTemplates";
import { useChatStore } from "@/stores/chatStore";
import { cn, MODE_LABELS, MODE_COLORS } from "@/lib/utils";
import type { TemplateRecord, TemplateCreate, TemplateUpdate } from "@/types/template";
import type { ChatMode } from "@/types/common";

const MODE_OPTIONS = [
  { value: "short_term", label: "短线" },
  { value: "swing", label: "波段" },
  { value: "mid_term_value", label: "中线价值" },
  { value: "generic_data_query", label: "通用" },
];

const CATEGORY_OPTIONS = [
  { value: "选股", label: "选股" },
  { value: "分析", label: "分析" },
  { value: "比较", label: "比较" },
  { value: "跟踪", label: "跟踪" },
  { value: "其他", label: "其他" },
];

export default function TemplatesPage() {
  const {
    templates,
    isLoading,
    createTemplate,
    updateTemplate,
    deleteTemplate,
    isCreating,
    isUpdating,
  } = useTemplates();
  const router = useRouter();
  const { setInputValue, setModeHint } = useChatStore();
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<TemplateRecord | null>(null);
  const [filterCategory, setFilterCategory] = useState<string>("全部");

  const [formData, setFormData] = useState<TemplateCreate>({
    name: "",
    category: "",
    mode: null,
    content: "",
    default_params: {},
  });

  const categories = ["全部", ...CATEGORY_OPTIONS.map((c) => c.value)];
  const filteredTemplates =
    filterCategory === "全部"
      ? templates
      : templates.filter((t) => t.category === filterCategory);

  const officialTemplates = filteredTemplates.filter(
    (t) => !t.id.startsWith("user_")
  );
  const myTemplates = filteredTemplates.filter((t) => t.id.startsWith("user_"));

  const handleOpenEditor = (template?: TemplateRecord) => {
    if (template) {
      setEditingTemplate(template);
      setFormData({
        name: template.name,
        category: template.category,
        mode: template.mode,
        content: template.content,
        default_params: template.default_params,
      });
    } else {
      setEditingTemplate(null);
      setFormData({
        name: "",
        category: "",
        mode: null,
        content: "",
        default_params: {},
      });
    }
    setIsEditorOpen(true);
  };

  const handleUseTemplate = (template: TemplateRecord) => {
    setInputValue(template.content);
    setModeHint(template.mode);
    router.push("/");
  };

  const handleSave = () => {
    if (editingTemplate && editingTemplate.id.startsWith("user_")) {
      const updateData: TemplateUpdate = {
        name: formData.name,
        category: formData.category,
        mode: formData.mode,
        content: formData.content,
        default_params: formData.default_params,
      };
      updateTemplate({ id: editingTemplate.id, data: updateData });
    } else {
      createTemplate(formData);
    }
    setIsEditorOpen(false);
  };

  const handleDelete = (id: string) => {
    if (confirm("确定要删除这个模板吗？")) {
      deleteTemplate(id);
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">模板中心</h1>
          <p className="text-sm text-muted-foreground">
            管理你的快捷查询模板
          </p>
        </div>
        <Button onClick={() => handleOpenEditor()}>新建模板</Button>
      </div>

      {/* Category Filter */}
      <div className="flex gap-2 mb-6">
        {categories.map((cat) => (
          <Button
            key={cat}
            variant={filterCategory === cat ? "secondary" : "ghost"}
            size="sm"
            onClick={() => setFilterCategory(cat)}
          >
            {cat}
          </Button>
        ))}
      </div>

      {/* Official Templates */}
      <section className="mb-8">
        <h2 className="text-lg font-semibold mb-4">官方模板</h2>
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1, 2].map((i) => (
              <div key={i} className="h-32 bg-muted rounded-lg animate-pulse" />
            ))}
          </div>
        ) : officialTemplates.length === 0 ? (
          <p className="text-sm text-muted-foreground">暂无官方模板</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {officialTemplates.map((template) => (
              <Card key={template.id} className="cursor-pointer hover:bg-muted/50">
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <CardTitle className="text-base">{template.name}</CardTitle>
                    <div className="flex gap-1">
                      {template.mode && (
                        <Badge
                          variant="outline"
                          className={cn("text-xs", MODE_COLORS[template.mode])}
                        >
                          {MODE_LABELS[template.mode]}
                        </Badge>
                      )}
                      <Badge variant="secondary" className="text-xs">
                        {template.category}
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {template.content}
                  </p>
                  <div className="mt-3 flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-xs h-7"
                      onClick={() => handleUseTemplate(template)}
                    >
                      使用
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>

      {/* My Templates */}
      <section>
        <h2 className="text-lg font-semibold mb-4">我的模板</h2>
        {myTemplates.length === 0 ? (
          <p className="text-sm text-muted-foreground">暂无自定义模板</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {myTemplates.map((template) => (
              <Card key={template.id} className="cursor-pointer hover:bg-muted/50">
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <CardTitle className="text-base">{template.name}</CardTitle>
                    <div className="flex gap-1">
                      {template.mode && (
                        <Badge
                          variant="outline"
                          className={cn("text-xs", MODE_COLORS[template.mode])}
                        >
                          {MODE_LABELS[template.mode]}
                        </Badge>
                      )}
                      <Badge variant="secondary" className="text-xs">
                        {template.category}
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {template.content}
                  </p>
                  <div className="mt-3 flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="text-xs h-7"
                      onClick={() => handleOpenEditor(template)}
                    >
                      编辑
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-xs h-7 text-red-500"
                      onClick={() => handleDelete(template.id)}
                    >
                      删除
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>

      {/* Template Editor Dialog */}
      <Dialog open={isEditorOpen} onOpenChange={setIsEditorOpen}>
        <DialogContent>
          <DialogClose onClose={() => setIsEditorOpen(false)} />
          <DialogHeader>
            <DialogTitle>
              {editingTemplate ? "编辑模板" : "新建模板"}
            </DialogTitle>
            <DialogDescription>
              创建一个快捷查询模板，方便快速发起常用查询
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-1 block">模板名称</label>
              <Input
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                placeholder="例如: 短线强势股筛选"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-1 block">分类</label>
                <Select
                  options={CATEGORY_OPTIONS}
                  value={formData.category}
                  onChange={(e) =>
                    setFormData({ ...formData, category: e.target.value })
                  }
                  placeholder="选择分类"
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">模式</label>
                <Select
                  options={MODE_OPTIONS}
                  value={formData.mode || ""}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      mode: (e.target.value || null) as ChatMode | null,
                    })
                  }
                  placeholder="选择模式"
                />
              </div>
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">模板内容</label>
              <Textarea
                value={formData.content}
                onChange={(e) =>
                  setFormData({ ...formData, content: e.target.value })
                }
                placeholder="输入模板内容..."
                className="min-h-[120px]"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditorOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSave} disabled={isCreating || isUpdating}>
              {isCreating || isUpdating ? "保存中..." : "保存"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
