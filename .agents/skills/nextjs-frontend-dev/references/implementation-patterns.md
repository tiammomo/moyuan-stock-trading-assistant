# Implementation Patterns

最后整理时间：2026-04-23

## 1. App Router 结构先对，再写功能

Next.js 官方建议先把路由职责和项目文件职责分开：

- `app` 负责路由和特殊文件约定
- 共享组件、hooks、utils 可以放在 `src` 下独立目录
- 只有存在 `page` 或 `route` 的路径才会成为公开路由

这与当前仓库结构一致，因此新增功能时不要把大量业务逻辑直接堆进 `page.tsx`。

## 2. 默认 Server Component，交互才下沉为 Client Component

Next.js App Router 默认使用 Server Components。

适合做 Client Component 的场景：

- 本地状态
- 浏览器事件
- 交互控件
- context provider

适合留在更高层的场景：

- 静态布局
- 非交互结构
- 可在服务端确定的数据壳层

工程规则：

- `use client` 放在真正需要交互的叶子节点附近
- 不要把整页无脑改成 client

## 3. React Query 负责 server state

TanStack Query 的通用模式：

- `useQuery` 读取远端资源
- `useMutation` 处理写操作
- 写成功后根据资源边界做 invalidation

适合当前仓库：

- sessions
- session detail
- watchlist
- templates
- profile

## 4. Zustand 负责 client state

当前仓库里 Zustand 更适合：

- 当前选中的 session
- 面板展开/收起
- 输入草稿
- 当前视图模式
- 流式中间状态

不要把本来应该被缓存和失效控制的 server data 长期塞进 Zustand。

## 5. 页面必须有四类状态

- loading
- empty
- error
- success

如果只实现 success path，工作台类产品会很快变得脆弱。

## Source Links

- Next.js project structure:
  https://nextjs.org/docs/app/getting-started/project-structure
- Next.js server and client components:
  https://nextjs.org/docs/app/getting-started/server-and-client-components
- TanStack Query invalidations from mutations:
  https://tanstack.com/query/latest/docs/framework/react/guides/invalidations-from-mutations

