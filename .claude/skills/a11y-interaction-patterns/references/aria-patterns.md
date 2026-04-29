# ARIA Interaction Patterns

最后整理时间：2026-04-23

## 1. Modal Dialog

W3C APG 的核心要求：

- 打开时焦点进入弹窗内部
- `Tab` / `Shift+Tab` 在弹窗内部循环
- `Escape` 关闭
- 应有可见的关闭按钮
- 容器使用 `role="dialog"`，并设置可访问名称
- 只有在描述内容较短、线性可读时，才适合使用 `aria-describedby`

工程含义：

- 不要只做视觉遮罩，不做焦点管理
- 不要让背景内容仍然可操作

## 2. Tabs

- 一个 `tablist` 对应多个 `tab`
- 同时只显示一个主要 `tabpanel`
- 选中态必须可感知
- 键盘切换要稳定，尤其是左右箭头或上下箭头行为

适用这里的结果面板与设置页分区。

## 3. Combobox

- 组合框不是普通输入框 + 任意弹层
- 输入区、popup、展开状态、当前激活项必须是同一套交互
- 若 popup 不是 `listbox`，需要匹配对应 `aria-haspopup`

适用于股票选择、模板选择、可搜索下拉。

## 4. Disclosure 优于伪菜单导航

W3C 示例强调：

- 普通站点导航通常不该直接套 `menu` role
- 展开/收起式导航更适合 disclosure 模式

适用于：

- 侧栏折叠组
- 筛选分组
- 高级设置展开区

## 5. Grid / table 的取舍

- 静态表格优先原生 `table`
- 只有需要方向键级别导航、单元格交互、复杂布局时才考虑 `grid`

不要为了“高级”而滥用 ARIA `grid`。

## Source Links

- W3C Dialog (Modal) Pattern:
  https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/
- W3C Tabs Pattern:
  https://www.w3.org/WAI/ARIA/apg/patterns/tabs/
- W3C Combobox Pattern:
  https://www.w3.org/WAI/ARIA/apg/patterns/combobox/
- W3C Pattern Index:
  https://www.w3.org/WAI/ARIA/apg/patterns/
- W3C Disclosure Navigation Example:
  https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/examples/disclosure-navigation/

