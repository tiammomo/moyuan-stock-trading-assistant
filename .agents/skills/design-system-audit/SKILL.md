---
name: design-system-audit
description: Audit or define a design system for a frontend codebase. Use when the user asks to梳理设计系统, 统一组件风格, 做 UI audit, 收敛 token, 规范 typography/spacing/color, 盘点组件变体, or wants a concrete report on visual inconsistency and design debt.
---

# Design System Audit

这个技能用于“查问题”和“立规则”。目标不是直接重画所有页面，而是识别视觉与交互系统的断裂点，给出一套可执行的统一方案。

## 先读什么

- `references/design-system-audit-patterns.md`

## 审查范围

- 颜色 token
- 字体与字号层级
- spacing / radius / shadow
- 组件变体
- 状态色与反馈模式
- 交互语义与 accessibility
- 页面级布局惯例

## 审查流程

1. 盘点基础 token 是否成体系
2. 盘点组件是否有重复变体与隐形分叉
3. 盘点页面是否共享一致的布局规则
4. 找出高频断裂点
5. 产出最小统一方案，而不是理想化大重构

## 建议输出格式

1. 现状摘要
2. 最高优先级问题
3. token 层建议
4. 组件层建议
5. 页面层建议
6. 迁移顺序

## 特别注意

- 不要只说“风格不统一”，要明确是哪个 token、哪个组件、哪个页面模式出了问题
- 不要一上来建议完整重做 design system，优先给最小可落地方案
- 报告里要区分视觉债务、交互债务、可访问性债务

