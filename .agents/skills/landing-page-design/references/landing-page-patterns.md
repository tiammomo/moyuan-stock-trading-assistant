# Landing Page Patterns

最后整理时间：2026-04-23

## 1. Landing page 不是“后台页面加几段文案”

Vercel 的 SaaS/模板类页面和 Anthropic 的 frontend-design skill 都体现了一个共同点：

- 首屏必须有一个视觉锚点
- 页面节奏要按“吸引 -> 建立信任 -> 解释价值 -> 促成行动”展开
- section 之间不能只有重复卡片和同一层级标题

## 2. Hero 要承担三件事

一个有效 hero 通常同时回答：

- 这是什么
- 为什么值得看
- 下一步做什么

常见有效结构：

- 左文案右装置
- 中央大标题 + 下方产品预览
- 标题区 + 演示终端 / 浏览器框 / 数据板

Vercel Next.js SaaS Starter 明确把 landing page 的 hero 做成带 animated terminal 的首屏，这是一个很典型的“产品感锚点”。

## 3. 营销页排版优先 expressive，后台优先 productive

Carbon 的 typography 指南区分了两类语气：

- productive：更适合产品后台和高密度信息
- expressive：更适合网站页面、编辑感和营销表达

因此：

- landing page 标题可以更大、更有张力
- supporting copy 仍要克制，避免变成海报式堆字
- 可以在页面中混合 expressive hero + productive feature list

## 4. 节奏要有“张”和“弛”

Atlassian 的 spacing 原则很适合做 landing page：

- 用大间距拉开 section 层级
- 用中间距组织卡片和内容组
- 用小间距修正局部对齐

不要让所有区块都同宽、同密度、同边框、同背景。

## 5. 视觉原型允许先假数据、后接线

如果用户主要要“出视觉稿”：

- 优先先做静态高保真页面
- 使用可信的产品示例数据
- 把难点放在版式、类型系统、节奏和氛围，而不是一开始接完整业务链路

## Source Links

- Anthropic `frontend-design` skill:
  https://github.com/anthropics/skills/tree/main/skills/frontend-design
- Vercel Next.js SaaS Starter:
  https://vercel.com/new/vercel/templates/authentication/next-js-saas-starter
- Vercel SaaS template index:
  https://vercel.com/templates/saas
- Carbon typography overview:
  https://carbondesignsystem.com/elements/typography/overview/
- Carbon style strategies:
  https://carbondesignsystem.com/elements/typography/style-strategies/
- Atlassian spacing:
  https://atlassian.design/foundations/spacing

