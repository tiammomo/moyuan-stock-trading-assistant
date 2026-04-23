---
name: frontend-webapp-testing
description: Verify frontend behavior locally with browser-based checks. Use when the user asks to test pages, reproduce UI bugs, verify interactions, inspect screenshots, check responsive regressions, or validate flows after frontend changes in this repo.
---

# Frontend Webapp Testing

这个技能用于前端改动后的本地验收，重点是“先观察，再操作”，避免凭想象写选择器和断言。

## 先读什么

- `references/testing-patterns.md`

## 适用场景

- 改完页面后做回归检查
- 定位 UI bug
- 验证抽屉、弹窗、tabs、表格、筛选、表单
- 检查桌面与移动端布局

## 执行原则

1. 先启动相关服务，再做浏览器检查。
2. 先截图、看 DOM、确认加载完成，再交互。
3. 优先用 role、label、text 等更稳定的选择器。
4. 每次改动后至少检查：
   - loading
   - empty
   - error
   - happy path
5. 发现视觉问题时，记录是在：
   - 布局层
   - 状态层
   - 组件交互层
   - 数据返回层

## 对这个仓库的重点

- 左中右三栏布局在不同宽度下是否破版
- 聊天输入、消息流、结果面板是否同步
- watchlist / templates / settings 页是否存在空态与错误态
- 长文本、长数字、中文文案是否溢出

