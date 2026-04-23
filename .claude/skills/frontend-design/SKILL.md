---
name: frontend-design
description: Redesign or polish frontend UI in this repo. Use when the user asks to beautify pages/components, redesign dashboards or workbenches, improve layout/hierarchy/visual polish/motion/branding, or says "改好看", "重设计", "优化界面", "做一个 landing page / dashboard / 工作台". Ground decisions in the bundled online design-pattern references instead of generic AI styling.
---

# Frontend Design

为这个仓库生成高质量前端设计时，优先做“有明确方向的产品设计”，不要做模板化、审美中性的网页。

这个技能主要服务于当前仓库的 `Next.js + Tailwind + 数据工作台` 场景，尤其适合：

- 聊天工作台、结果面板、观察列表、设置页、模板页
- 新页面视觉方向定义
- 已有页面的布局重构和精修
- 信息层级、状态设计、空态/错误态、响应式改版

## 先读什么

- 通用视觉与响应式模式：`references/online-design-patterns.md`

如果页面是高密度数据界面、表格、筛选器、三栏工作台，优先同时触发 `data-dense-product-ui`。

## 工作方式

1. 先读当前页面和全局样式约束：
   - `frontend/src/app`
   - `frontend/src/components`
   - `frontend/src/app/globals.css`
   - `frontend/tailwind.config.ts`
2. 用一句话命名这次设计方向，例如“冷静的专业型交易工作台”或“高对比度的研究控制台”。
3. 先改结构，再改装饰：
   - 明确主区、次区、辅助区
   - 调整留白、对齐、密度、分组
   - 最后再补颜色、阴影、边框、动效
4. 统一到一组语义化 token：
   - 背景层级
   - 文本层级
   - 强调色
   - 状态色
5. 只加入少量但有效的动效：
   - 首屏进入
   - 面板切换
   - hover / focus
   - loading 反馈
6. 桌面和移动端都要成立，不能只做桌面截图式布局。

## 设计要求

- 不要默认套用泛紫色渐变、白底圆角卡片、千篇一律的 SaaS 版式。
- 不要把所有内容放成同等视觉权重。
- 重要内容必须先可扫读，再可细读。
- 对这个项目，优先强调“专业、可信、可快速决策”，而不是营销页式炫技。
- 面对中文界面时，注意标题长度、数字宽度、表格对齐、长句换行。

## 交付检查

- 页面是否有明确主任务
- 重要信息是否 3 秒内可扫读
- 空态/加载态/错误态是否存在
- 侧栏、表格、面板在窄屏下是否仍可用
- 颜色是否没有承担唯一的信息表达职责

