---
name: data-dense-product-ui
description: Design or refactor dense product UI such as dashboards, tables, result panels, sidebars, filter bars, watchlists, compare views, or multi-panel workbenches. Use when the user asks for dashboard/table/workbench/result-panel/watchlist/filter UX, or when a page has too much data and needs clearer scanability and hierarchy.
---

# Data-Dense Product UI

这个技能处理“信息很多，但用户要很快做判断”的界面，适合当前仓库的：

- 会话列表
- 消息流 + 结果面板
- 观察列表
- 模板与设置页
- 表格、卡片、对比视图

## 先读什么

- `references/data-dense-patterns.md`

## 设计原则

1. 先识别用户的主任务：
   - 找结论
   - 找异常
   - 比较对象
   - 执行动作
2. 不要同时强调所有信息。
3. 用“摘要 -> 明细 -> 深钻”三层结构组织内容。
4. 表格、卡片、筛选器、状态提示必须互相配合，而不是各自独立。

## 推荐布局

- 左侧：导航、对象列表、筛选上下文
- 中间：主流程、主要内容、当前任务
- 右侧：详情、解释、结构化结果、后续动作

如果空间不足：

- 先保主流程
- 再保当前上下文
- 最后保辅助详情

## 表格与结果面板规则

- 数字右对齐，文本左对齐。
- 默认排序要体现最重要字段。
- 表格上方提供筛选、排序、批量动作或视图切换。
- 长内容不要直接撑爆单元格，优先截断、换行或展开查看。
- 不要只靠颜色表达涨跌、风险、状态，配合图标、标签或文案。
- 结果卡片用于摘要，表格用于比较，详情面板用于解释。

## 检查项

- 3 秒内能否扫到最关键的结论
- 空态、无结果、异常态是否明确
- 长数字、长公司名、长中文文案是否破版
- 各面板是否有稳定的宽度和收起策略
- 键盘与触屏是否都能完成关键操作

