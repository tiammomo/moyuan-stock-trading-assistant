# Testing Patterns

最后整理时间：2026-04-23

## 1. Reconnaissance, then action

Anthropic 官方 `webapp-testing` skill 的核心模式：

1. 打开页面
2. 等待页面稳定
3. 截图或检查渲染后的 DOM
4. 再决定选择器和动作

不要在页面尚未稳定时就猜测 DOM 结构。

## 2. 动态应用先等网络与渲染完成

对于工作台式应用：

- 初次进入可能有查询请求
- 切换 session 可能触发重新拉取
- 展开结果面板和 tabs 可能导致延迟渲染

因此测试时要区分：

- 首屏加载完成
- 异步数据回来后的稳定态
- 用户交互后的稳定态

## 3. 验收不是只看 happy path

至少覆盖：

- 页面首次加载
- 空数据
- 接口失败
- 一次完整成功流程
- 窄屏或中等宽度下的布局变化

## Source Links

- Anthropic `webapp-testing` skill:
  https://github.com/anthropics/skills/tree/main/skills/webapp-testing
