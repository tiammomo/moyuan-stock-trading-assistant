# Design System Audit Patterns

最后整理时间：2026-04-23

## 1. 先查 token，再查组件，再查页面

一个高效 audit 的顺序通常是：

1. Foundations / tokens
2. Component variants
3. Page patterns

如果一开始就逐页找问题，很容易把系统问题误判成局部样式问题。

## 2. Token 应该是视觉决策的单一来源

Atlassian foundations 对 token 的定义很实用：

- token 是设计决策的单一来源
- color、spacing、typography、elevation 等都应有稳定命名
- 组件不该频繁绕开 token 直接写原始数值

审查时优先查：

- 是否出现大量零散 hex / rgb / px
- 同一语义是否被多个值表示
- 同一值是否承担多个冲突语义

## 3. 页面类型不同，排版策略也应不同

Carbon 的 typographic strategy 非常适合做 audit：

- 营销/编辑场景可更 expressive
- 产品后台与高密度界面更适合 productive

如果一个仓库里的 landing page 和 dashboard 都用了同一套排版逻辑，通常会显得别扭。

## 4. Spacing 是最常见、也最容易被忽略的系统裂缝

Atlassian spacing 强调：

- 统一间距能建立关系、层级和视觉节奏
- 不同密度场景应使用不同区间的 spacing token
- 少量 optical adjustment 合理，但不能完全无规则

审查重点：

- 卡片内边距是否乱
- 面板与面板之间的距离是否统一
- 表格、列表、表单的密度是否一致

## 5. Accessibility 是系统质量的一部分

W3C APG 提醒我们：

- modal、tabs、combobox、disclosure 都有明确交互语义
- 可访问性不是“最后补几个 aria-label”

因此 audit 时要把这几类问题单独列出：

- 焦点管理缺失
- 键盘路径断裂
- 组件语义与行为不一致

## 6. 输出应该能指导迁移，而不是只做批评

一个好的 audit 结论应当包含：

- 哪些 token 先收敛
- 哪些组件先统一
- 哪些页面模式最值得先改
- 迁移先后顺序与风险

## Source Links

- Atlassian foundations:
  https://atlassian.design/foundations/
- Atlassian design tokens:
  https://atlassian.design/foundations/tokens/design-tokens/
- Atlassian spacing:
  https://atlassian.design/foundations/spacing
- Atlassian typography:
  https://atlassian.design/foundations/typography/applying-typography
- Carbon typography overview:
  https://carbondesignsystem.com/elements/typography/overview/
- Carbon style strategies:
  https://carbondesignsystem.com/elements/typography/style-strategies/
- W3C APG patterns:
  https://www.w3.org/WAI/ARIA/apg/patterns/
