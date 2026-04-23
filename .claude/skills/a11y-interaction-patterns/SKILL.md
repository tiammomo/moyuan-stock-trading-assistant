---
name: a11y-interaction-patterns
description: Implement or review accessible interactive UI patterns such as dialogs, tabs, comboboxes, disclosures, keyboard navigation, and focus management. Use when the user asks for modal, tab, dropdown, command menu, searchable select, accordion, or accessibility fixes in frontend components.
---

# A11y Interaction Patterns

这个技能用于交互组件的结构正确性，而不是表面样式。

适用场景：

- Modal / Dialog
- Tabs
- Combobox / searchable select
- Disclosure / accordion / 可展开导航
- 键盘导航
- 焦点管理

## 先读什么

- `references/aria-patterns.md`

## 工作规则

1. 能用原生元素就先用原生元素。
2. 再考虑 ARIA role，不要一上来就手写复杂语义。
3. 键盘路径要和视觉路径一致。
4. `focus-visible`、关闭逻辑、Esc、Tab 循环要明确。
5. 不要用“看起来像菜单”的导航就套 `menu` role；很多站点导航更适合 disclosure 模式。

## 对这个仓库的重点

- 侧栏折叠与展开
- 结果面板 tabs
- 搜索/选择型输入
- 模态设置面板
- 会话列表键盘操作

## 交付检查

- 打开组件时焦点是否落在正确位置
- 关闭组件时焦点是否回到触发源
- 键盘是否可完成核心流程
- ARIA 属性是否和真实行为匹配
- 交互说明是否没有只依赖颜色

