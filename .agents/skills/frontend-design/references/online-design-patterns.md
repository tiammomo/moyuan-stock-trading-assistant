# Online Design Patterns

最后整理时间：2026-04-23

这份参考不是原文搬运，而是把线上成熟设计系统里的共性模式压缩成 Claude 可直接执行的规则。

## 1. 先选一个鲜明方向，不要做默认款

来自 Anthropic 官方 `frontend-design` skill 的核心思想：

- 先定义产品语气和视觉立场，再开始写代码。
- 字体、颜色、空间、动效、背景应该服务同一个概念方向。
- “精致极简”和“高张力强视觉”都可以，但必须一致。
- 避免泛化的 AI 审美：无差异字体、紫白渐变、到处都是卡片、装饰多但层级弱。

落地到这个仓库：

- 工作台页面优先做“可信赖的分析工具”而不是“炫酷 landing page”。
- 允许更高密度，但必须配合更清楚的层级、对齐、留白和状态设计。

## 2. 响应式先解决层级，再解决栅格

结合 Material 的 responsive UI 模式：

- 小屏优先保留一个主要任务，不要在手机上强行同时展示 summary 和 detail。
- 宽屏再逐步揭示第二层、第三层信息，例如左侧会话列表 + 中间主流程 + 右侧详情。
- 侧栏可以分为三类：
  - permanent：始终存在
  - persistent：可切换，但出现后不遮挡主要交互逻辑
  - temporary：小屏临时抽屉
- 面板扩展时优先使用 reveal、divide、reflow，而不是简单堆更多卡片。

对这个仓库的直接启发：

- 小屏下优先保聊天主流程，结果面板改为切换或抽屉。
- 宽屏保留三栏工作台，但每栏都要有清楚边界和收起策略。

## 3. 空态要解释“为什么空”和“下一步做什么”

结合 Atlassian 和 Material 的空态模式：

- 标题要短、可扫读、能说明当前状态。
- 正文控制在 1 到 2 句，解释原因并给出下一步。
- CTA 用动作词，避免模糊按钮文案。
- 空态可以出现在整页、面板、表格、搜索结果里；不同容器的语气和篇幅应不同。
- 对频繁出现的空态，文案要更克制；对首次使用的 blank slate，可以多一点引导。

适用于这个仓库的空态：

- 首次会话
- 无观察股
- 无模板
- 搜索/筛选无结果
- 后端未连接或技能未配置

## 4. 视觉层级应围绕决策速度设计

高密度产品界面里，优先级通常是：

1. 当前最重要的判断或结果
2. 可执行动作
3. 关键上下文
4. 明细和扩展信息

因此：

- 标题区不要承担过多视觉重量。
- 关键摘要、状态、数字、结论要更接近视线起点。
- 次级说明放到折叠区、标签页或辅助列。

## 5. 动效只用于解释变化

- 面板展开/收起：帮助理解布局关系。
- 数据刷新：提示状态变化，不要造成跳动。
- hover/focus：明确交互边界。
- 避免为每个元素都加动画。

## Source Links

- Anthropic `frontend-design` skill:
  https://github.com/anthropics/skills/tree/main/skills/frontend-design
- Material Design responsive UI:
  https://m1.material.io/layout/responsive-ui.html
- Material Design empty states:
  https://m1.material.io/patterns/empty-states.html
- Atlassian empty state guidance:
  https://atlassian.design/foundations/content/designing-messages/empty-state

