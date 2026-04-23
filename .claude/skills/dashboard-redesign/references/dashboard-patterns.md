# Dashboard Patterns

最后整理时间：2026-04-23

## 1. Dashboard 的第一目标是降低扫读成本

优秀后台模板与产品设计系统的共同点是：

- 先给最重要的 summary
- 再给主数据区
- 解释和次级动作放到后面

如果所有区域都一样重，用户就会失去扫描路径。

## 2. Product UI 用 productive typography 更稳

Carbon 区分 productive 与 expressive：

- productive 更适合高密度、任务导向、后台场景
- expressive 更适合营销页和编辑感页面

因此 dashboard 改版时：

- 大部分正文、标签、表头、统计块都应偏 productive
- 只有标题区或关键数字可以适度拉高视觉张力

## 3. 一套好 dashboard 通常有三层信息

推荐层级：

1. Summary：KPI、状态、关键提醒
2. Main area：表格、图表、主流程、主结果
3. Detail / context：解释、筛选、次要信息、历史记录

这与 Vercel 的 admin dashboard 模板和现代产品后台的普遍结构一致。

## 4. 可折叠侧栏和可变内容宽度很有价值

Vercel 社区中的 modern admin/dashboard 模板普遍强调：

- collapsible sidebar
- variable content widths
- theme/layout controls

这类模式很适合当前仓库的工作台，因为：

- 用户有时只想聚焦聊天主流程
- 有时又需要同时看 session 与 result detail

## 5. 间距、token、状态色要像系统，不像手工拼贴

Atlassian foundations 的关键启发：

- spacing 应该来自一套节奏，而不是每个组件自己写数值
- token 是统一视觉语义的基础
- hierarchy 依赖留白、字重、边界和密度共同建立

## 6. Redesign 允许先做视觉原型

如果用户明确要“更高级的视觉”：

- 先做 prototype page 或 isolated view
- 可以先不接全量真实图表和 API
- 优先解决结构、层级、字体、颜色、状态和响应式

## Source Links

- Vercel Admin Dashboard template:
  https://vercel.com/new/templates/next.js/admin-dashboard
- Vercel Next.js & shadcn/ui Admin Dashboard:
  https://vercel.com/templates/next.js/next-js-and-shadcn-ui-admin-dashboard
- Carbon typography overview:
  https://carbondesignsystem.com/elements/typography/overview/
- Carbon type sets:
  https://carbondesignsystem.com/elements/typography/type-sets/
- Atlassian foundations:
  https://atlassian.design/foundations/
- Atlassian spacing:
  https://atlassian.design/foundations/spacing

