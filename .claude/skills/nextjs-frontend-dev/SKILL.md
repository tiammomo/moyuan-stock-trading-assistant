---
name: nextjs-frontend-dev
description: Build frontend features in this repo's stack: Next.js App Router, TypeScript, Tailwind, React Query, and Zustand. Use when the user asks to add pages/components/hooks/stores/API wiring, refactor frontend structure, or implement interactions in the current frontend folder.
---

# Next.js Frontend Dev

这个技能约束“怎么在这个仓库里实现前端功能”，避免写出和现有结构不一致的代码。

## 仓库约定

- 路由页面：`frontend/src/app`
- 复用组件：`frontend/src/components`
- hooks：`frontend/src/hooks`
- store：`frontend/src/stores`
- API：`frontend/src/lib/api.ts`
- 类型：`frontend/src/types`

## 先读什么

- `references/implementation-patterns.md`

## 实现规则

1. 先判断是不是必须 `use client`
   - 只有交互、状态、本地事件、浏览器 API 才下沉到 Client Component
2. Server data 和 UI state 分开
   - React Query：服务端数据、缓存、失效、异步状态
   - Zustand：本地 UI 状态、临时交互状态、跨组件共享的客户端状态
3. 类型先行
   - API 入参与返回值先在 `src/types` 明确
   - 再写 `src/lib/api.ts`
   - 再接 hooks / store / component
4. 页面尽量薄
   - 页面负责装配
   - 复杂视图逻辑下沉到组件和 hooks
5. Tailwind 优先使用已有 token 和语义颜色，不随手新增零散色值

## 典型实现顺序

1. 定义类型
2. 接 API
3. 写 query / mutation hook
4. 必要时补 store
5. 组合到页面和组件
6. 检查 loading / empty / error / success

## 这个仓库里尤其注意

- `useChatStore` 与 React Query 的职责边界
- 会话、观察列表、模板等列表型资源的失效刷新
- 多面板布局下的收起、切换和同步状态
- 中文界面下的长文本与数字展示

