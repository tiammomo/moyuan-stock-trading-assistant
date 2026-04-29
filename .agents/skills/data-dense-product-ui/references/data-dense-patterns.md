# Data-Dense Patterns

最后整理时间：2026-04-23

## 1. 表格不是孤立组件，而是决策容器

综合 Material 和 Atlassian 的表格模式：

- 表格应该自带排序、分页、筛选或重排行为，而不是只显示静态数据。
- 默认排序要指向最重要字段。
- 表格常常需要嵌入在卡片或面板内，与工具栏和批量操作区一起工作。
- 数值列右对齐，文本列左对齐，可显著提升扫读效率。

适合这个仓库的用法：

- 结果面板顶部放筛选与视图切换
- 中间是表格/卡片主视图
- 下方或右侧放解释、来源、后续动作

## 2. 摘要与明细应同时存在，但不必同时展开

Material 的 responsive 模式强调：

- 窄屏只保一个主层级
- 宽屏再显示 summary + detail
- 面板可以 reveal、divide、reflow

对工作台最实用的模式：

- 宽屏：会话列表 + 主消息流 + 结果详情
- 中屏：列表收窄，详情改标签页
- 小屏：主流程单列，详情抽屉化

## 3. 空态和无结果态属于主流程设计

Atlassian 与 Shopify Polaris 的共性：

- 空态常出现在列表、表格、图表和整页中
- 必须解释当前为什么没有数据
- 必须给下一步动作
- CTA 用明确动词，不要用空泛按钮

对这个仓库的典型空态：

- 还没有创建会话
- 暂无观察股
- 没有命中模板
- 当前筛选条件下无结果

## 4. 高密度界面优先保障“扫读路径”

推荐顺序：

1. 顶部摘要或状态条
2. 关键操作区
3. 主数据区
4. 解释性附加信息

如果一屏信息太多：

- 降低装饰，增强分组
- 合并重复标签
- 把不影响决策的说明放到二级区域

## 5. 视觉信号要稳定

- 成功、警告、错误、信息四类状态颜色保持一致
- 同一类 badge/lozenge 不要在不同页面换含义
- 选中态、hover 态、focus 态要可预期

## Source Links

- Atlassian Dynamic Table:
  https://atlassian.design/components/dynamic-table/
- Atlassian Empty State:
  https://atlassian.design/components/empty-state/
- Material Design data tables:
  https://m1.material.io/components/data-tables.html
- Material Design responsive UI:
  https://m1.material.io/layout/responsive-ui.html
- Shopify Polaris empty state:
  https://shopify.dev/docs/api/app-home/patterns/compositions/empty-state
- Shopify Polaris IndexTable:
  https://polaris-react.shopify.com/components/tables/index-table?example=index-table-without-checkboxes

