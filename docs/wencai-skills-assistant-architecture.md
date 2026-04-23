# 问财 Skills 个人助手技术架构

最后更新：2026-04-23

## 1. 文档定位

这份文档说明当前仓库的技术结构、模块职责、运行方式和后续演进边界。

优先级规则：

- API 字段、模型字段、前端行为和视觉约束，以 `docs/wencai-skills-assistant-spec.md` 为准。
- 本文不再维护独立的一套 request / response 字段定义，避免和 spec 冲突。
- 本文只回答 4 个问题：
  - 当前系统是怎么搭的
  - 每个模块负责什么
  - 一条核心链路怎么走
  - 未来在什么条件下才升级技术方案

## 2. 当前架构结论

当前项目不是“预留完整企业架构”的空壳，而是已经可运行的个人使用型 MVP：

- 前端：`Next.js + TypeScript + TanStack Query + Zustand + Tailwind CSS`
- 后端：`FastAPI + Pydantic`
- Python 运行时：`uv + Python 3.12.x`
- 存储：本地 JSON 文件
- 数据源：问财 OpenAPI、本地已安装 skills 的能力映射，以及统一 LLM provider 管理下的 GPT 主链路 + MiniMax fallback 分析增强
- 交互：同步请求 + SSE 流式返回
- 启动方式：根目录脚本统一拉起，后端固定走 `uv`

当前明确不做：

- 多用户鉴权
- Redis 依赖
- SQLAlchemy / ORM 层
- PostgreSQL 持久化
- 微服务拆分
- 前端直连问财接口

这些不是“永远不做”，而是当前版本没有必要。

## 3. 运行时拓扑

```text
[Browser]
    |
    v
[Next.js Frontend @ :3000]
    |
    v
[FastAPI Backend @ :8000]
    |
    +--> [chat_engine.py]
    |       |--> 模式识别
    |       |--> skill 路由
    |       |--> 单股买点/操作建议卡生成
    |       |--> 结果标准化
    |
    +--> [openai_client.py]
    |       |--> summary / judgement / follow_up 文案增强
    |
    +--> [llm_manager.py]
    |       |--> provider 注册与统一管理
    |       |--> auto / openai / minimax 链路选择
    |       |--> GPT 优先、MiniMax fallback
    |       |--> 未来新增 LLM 的统一接入点
    |
    +--> [llm_account_pool.py]
    |       |--> LLM 账号池适配
    |       |--> 单账号 env 兼容
    |       |--> 多账号 JSON 池解析
    |       |--> 账号级轮询和失败切换
    |
    +--> [repository.py]
    |       |--> sessions.json
    |       |--> messages.json
    |       |--> profile.json
    |       |--> templates.json
    |       |--> watchlist.json
    |
    +--> [wencai_client.py]
            |--> OpenAPI / skill 结果适配
```

地址约束：

- 前端开发地址：`http://localhost:3000`、`http://127.0.0.1:3000`
- 后端开发地址：`http://127.0.0.1:8000`、`http://localhost:8000`
- 统一运行时配置入口是项目根目录 `.env`
- `.env` 不得提交，`.env.example` 必须提交且与实际读取字段同步
- 前端、后端和 `scripts/dev*.sh` 都必须读取根 `.env`，不再依赖 `frontend/.env.local` 或 `backend/.env`
- `frontend/next.config.mjs` 必须保留 `allowedDevOrigins: ["127.0.0.1"]`
- 统一启动入口：`scripts/dev.sh`
- 后端单独入口：`scripts/dev-backend.sh`
- 前端单独入口：`scripts/dev-frontend.sh`

## 4. 前端架构

### 4.1 目录角色

| 路径 | 角色 |
|---|---|
| `frontend/src/app` | 页面和应用外壳 |
| `frontend/src/components/layout` | 全局布局 |
| `frontend/src/components/workbench` | 工作台核心交互 |
| `frontend/src/components/results` | 结果展示组件 |
| `frontend/src/components/ui` | 可复用基础 UI 组件 |
| `frontend/src/lib/api.ts` | 唯一 API 请求出口 |
| `frontend/src/lib/utils.ts` | 文案、颜色、格式化映射 |
| `frontend/src/stores/chatStore.ts` | 当前会话和消息状态 |
| `frontend/src/stores/uiStore.ts` | 面板、tab、搜索等 UI 状态 |
| `frontend/src/hooks` | 基于 TanStack Query 的数据访问层 |
| `frontend/src/types` | 后端契约的 TypeScript 镜像 |

### 4.2 页面结构

当前主工作台是稳定的三栏布局：

- 左栏：会话列表
- 中栏：消息流 + 输入框
- 右栏：结果概览 / Skills / 追问

这不是可随意改动的临时布局，而是后续所有体验优化的基本骨架。

### 4.3 状态划分

前端状态分两层：

1. 服务端数据缓存：TanStack Query
2. 本地交互态：Zustand

TanStack Query 负责：

- `["sessions"]`
- `["session", id]`
- `["meta-status"]`
- `["templates"]`
- `["watchlist"]`

Zustand 负责：

- 当前会话 id
- 当前消息流
- 输入框内容
- streaming status
- 当前结构化结果
- 左右面板和 tab 状态

原则：

- 与后端同步的数据，优先交给 Query。
- 只属于当前页面交互的临时态，交给 Zustand。
- 不允许在业务组件里自己维护一份平行的会话或结果副本。

### 4.4 API 边界

前端只能通过 `frontend/src/lib/api.ts` 调用后端。

原因：

- 保证 URL、header、错误处理、返回类型一致。
- 保证 TypeScript 类型在一个入口集中绑定。
- 避免组件直接调用 `fetch("/api/...")` 导致 contract 漂移。

## 5. 后端架构

### 5.1 模块角色

| 路径 | 角色 |
|---|---|
| `backend/app/main.py` | FastAPI 入口、路由层 |
| `backend/app/schemas/*.py` | Pydantic 契约模型 |
| `backend/app/services/chat_engine.py` | 模式识别、路由、结果生成主链路 |
| `backend/app/services/openai_client.py` | GPT 分析增强和 OpenAI 兼容请求 |
| `backend/app/services/llm_manager.py` | LLM provider 注册、链路管理、失败切换 |
| `backend/app/services/llm_account_pool.py` | LLM 账号池 adapter factory、账号级轮询和失败切换 |
| `backend/app/services/sim_trading_client.py` | 模拟炒股账户、持仓上下文和只读联动 |
| `backend/app/services/watchlist_resolver.py` | 候选池股票解析、代码标准化和去重前校验 |
| `backend/app/services/repository.py` | 用户画像、会话、消息、模板、候选池仓储 |
| `backend/app/services/json_store.py` | 原子 JSON 文件存储 |
| `backend/app/services/wencai_client.py` | 问财请求和返回适配 |
| `backend/app/core/config.py` | 环境配置和 CORS |

### 5.2 路由层职责

`main.py` 只负责：

- 校验请求
- 调用服务层
- 把失败转成 HTTP 状态码
- 输出 JSON 或 SSE
- 协调候选池解析和重复冲突响应

它不应该承担：

- 复杂模式识别
- 技能路由策略
- 结果标准化细节
- 数据持久化细节

### 5.3 编排层职责

`chat_engine.py` 是当前后端核心，负责：

- `detect_mode()`：模式识别
- `build_route()`：技能路由
- `execute_plan()`：逐步执行技能计划
- `result_to_chat_response()`：把结构化结果包装成 `ChatResponse`
- 单股咨询分支：
  - `_extract_security_subject()`
  - `_is_entry_price_question()`
  - `_single_security_route()`
  - `_single_security_action_card()`
  - `_multi_horizon_analysis_card()`
  - `_extract_technical_snapshot()`

`openai_client.py` 负责：

- 读取项目级系统 prompt
- 按 `short_term`、`swing`、`mid_term_value` 拼接对应模式子 prompt
- 最后叠加任务级增强约束
- 只增强 `summary`、`judgements`、`follow_ups`、操作建议卡文案

`llm_manager.py` 负责：

- 读取系统级 LLM 配置
- 维护 provider 注册表
- 默认走 `auto` 链路
- 统一管理 GPT 优先、MiniMax fallback
- 为后续新增 provider 提供单一接入点

`llm_account_pool.py` 负责：

- 将单账号 env 配置适配成账号池
- 按 `LLM_ACCOUNT_POOL_ADAPTER` 选择具体 adapter 实现
- 维护账号池 adapter factory / registry
- 解析 `OPENAI_ACCOUNT_POOL_JSON`、`ANTHROPIC_ACCOUNT_POOL_JSON`、`MINIMAX_ACCOUNT_POOL_JSON`
- 为 provider 提供有序账号列表
- 在 provider 内部支持账号级轮询
- 后续如需接数据库、配置中心、外部号池服务，只替换 adapter，不改 provider 和业务增强层

`sim_trading_client.py` 负责：

- 读取或创建模拟炒股账户
- 查询当前模拟持仓和账户仓位
- 将模拟炒股原始结果归一化为后端内部持仓上下文
- 只做只读查询，不在聊天链路里直接下单

这意味着当前系统的“智能感”来自两层：

- 第一层：规则编排，负责事实边界和价格位
- 第二层：GPT 增强，负责在“炒股助手”角色下按短线、波段、中线价值三套子 prompt 组织表达

单股链路还必须额外输出“三周期 + 技术面”结构：

- 短线：日 K、MA5/MA10、量比、主力资金和承接。
- 中线：MA20、近 20 日表现、MACD、布林中轨和趋势修复。
- 长线：MA60、估值或财务字段，以及行业/题材是否能支撑更长周期。

### 5.4 仓储层职责

`repository.py` 是当前唯一业务存储层，负责：

- 用户画像读写
- 会话创建、读取、归档
- 消息写入和会话快照
- 模板 CRUD
- 候选池 CRUD

约束：

- 业务代码不得绕开 `repository` 直接写 JSON 文件。
- 关闭会话只能通过 `archive_session()`，不能删记录。
- 已归档会话对外表现为“不存在”。
- GPT 开关和推理强度策略也属于用户画像的一部分，通过 `/api/profile` 持久化。

### 5.5 存储层职责

`json_store.py` 提供一个很小但明确的能力：

- 读取 JSON
- 失败时回退默认值
- 写临时文件后原子替换
- `RLock` 保证单进程内访问安全

它解决的是“本地单用户 MVP 的可靠性”，不是“高并发数据库事务”。

## 6. 核心链路

### 6.1 主问答链路

```text
用户输入问题
-> ChatComposer 判断走 /api/chat
-> backend/main.py 接收 ChatRequest
-> repository 读取用户画像 / 会话摘要
-> 若命中“加入候选池”动作，优先走候选池动作链路
-> chat_engine.detect_mode()
-> chat_engine.build_route()
-> repository.ensure_session()
-> repository.add_message(user)
-> chat_engine.execute_plan()
-> 如已启用 GPT，则 openai_client 做文案增强
-> repository.add_message(assistant + result_snapshot)
-> 返回 ChatResponse 或 SSE completed
```

当前支持两种响应形态：

- 非流式 JSON
- SSE 流式事件

### 6.1.1 候选池动作链路

```text
用户输入“把东阳光加入候选池”或“把这几只加入候选池”
-> backend/main.py 识别候选池动作意图
-> 若是上下文代词，则读取当前 session 最新 assistant result_snapshot
-> watchlist_resolver / context rows 解析股票
-> repository.find_watch_item_by_symbol() 去重
-> repository.create_watch_item() 写入候选池
-> assistant 返回候选池更新结果
```

### 6.2 追问 / 比较链路

```text
用户输入追问
-> ChatComposer 判断走 /api/chat/follow-up
-> 后端读取 parent_message_id 对应消息
-> 若缺失则回退该 session 最新 assistant 消息
-> compare_from_snapshot()
-> 写入 user / assistant 消息
-> 返回 follow_up 或 compare 结果
```

当前设计重点：

- 优先复用 `result_snapshot`
- 避免每次追问都重查外部数据

### 6.3 关闭会话链路

```text
用户点击左栏“关闭”
-> useSessions.closeSession(id)
-> DELETE /api/sessions/{id}
-> repository.archive_session(id)
-> sessions 列表缓存失效
-> 移除 session 详情缓存
-> 如果关闭的是当前会话，则清空当前消息和结果
```

语义说明：

- 关闭 = 归档隐藏
- 不是物理删除
- 现阶段没有恢复 UI

### 6.4 单股买点链路

这是当前业务里最有辨识度的一条链路，必须保留：

```text
用户问“东阳光建议多少价格买入”
-> detect_mode() 识别为单股短线问题
-> build_route() 走 single security route
-> execute_plan() 获取个股快照、K 线、均线和技术指标，并补充新闻/公告
-> _single_security_action_card() 计算 observe_low / observe_high / stop_price
-> _multi_horizon_analysis_card() 生成短线 / 中线 / 长线三周期分析
-> openai_client 在不改价格位的前提下润色 summary / card content
-> summary + facts + judgements + operation_guidance card + multi_horizon_analysis card
-> 前端 ResultPanel 优先显示操作建议卡和三周期分析卡
```

这个链路说明当前架构不是单纯“表格查数”，而是“规则定边界 + GPT 做表达增强”的组合系统。

### 6.5 单股持仓双链路

```text
用户问“翠微股份今天怎么持仓”
-> detect_mode() 识别为单股短线 + holding_context_focus
-> build_route() 走 single security route
-> execute_plan() 获取个股快照、新闻、公告
-> execute_plan() 再读取模拟炒股持仓上下文
-> 若命中该股持仓，则把数量、成本、浮盈亏、账户仓位拼进 summary / facts / judgements
-> 返回 operation_guidance + portfolio_context 两张卡
-> 若模拟炒股失败，则降级为仅个股快照建议
```

### 6.6 GPT 强度决策链路

```text
用户在设置页保存 gpt_enhancement_enabled / gpt_reasoning_policy
-> /api/profile 持久化到 profile.json
-> /api/chat 时后端读取 UserProfile
-> 若 gpt_enhancement_enabled=false，则跳过 GPT
-> 若 gpt_reasoning_policy=auto，则按问法分为 medium / high / xhigh
-> llm_manager 按 `LLM_CHAIN_MODE` 选择 provider 链
-> provider 先从 llm_account_pool 取账号池并轮询可用账号
-> 默认 `auto`：GPT 账号池优先，失败再 MiniMax 账号池
```

## 7. 数据与契约策略

### 7.1 单一契约源

契约顺序必须是：

1. `docs/wencai-skills-assistant-spec.md`
2. `backend/app/schemas/*.py`
3. `frontend/src/types/*.ts`
4. `frontend/src/lib/api.ts`
5. hooks / store / 组件

禁止出现：

- 后端 schema 已改，前端类型没改
- 前端临时拼字段，后端没有定义
- spec 还没改，代码已经先漂移

### 7.2 为什么先用 Pydantic + TypeScript 镜像

当前选择不是 codegen，而是手工双端同步，原因很现实：

- 模型规模还不大
- 演化速度快
- 现阶段更需要明确审阅和控制字段语义

何时考虑自动 codegen：

- 契约文件数继续增长
- 双端字段变更频率高
- 已出现多次手工同步遗漏

### 7.3 会话模型的关键语义

`SessionSummary` / `SessionDetail` 的关键字段是 `archived`。

架构层语义：

- `archived=false`：对用户可见
- `archived=true`：对外不可见，但保留内部历史

因此：

- 关闭操作不影响历史消息存储
- 未来若做“恢复会话”，直接基于 `archived` 实现
- 若未来要做“彻底删除”，必须新增单独语义和审计策略

## 8. 当前为什么不用数据库和 Redis

旧版架构文档里把 `SQLite / PostgreSQL / Redis / SQLAlchemy` 写成了默认推荐，这和当前实现冲突，现改为条件触发式演进。

当前不引入它们的原因：

- 单用户、本地运行
- 数据量很小
- 没有复杂筛选和跨会话聚合查询
- 没有并发写入压力
- 没有缓存击穿或分布式部署需求

JSON 存储的代价：

- 不适合复杂查询
- 不适合多人并发
- 不适合精细索引

但在当前阶段它的收益更高：

- 简单
- 可读
- 迁移成本低
- 排错直观

## 9. 演进触发条件

后续技术升级必须由触发条件驱动，而不是先上复杂基础设施。

### 9.1 何时引入 SQLite / PostgreSQL

满足任一条件再考虑：

- 会话量和消息量增大，JSON 读写明显拖慢页面加载
- 候选池需要复杂筛选、排序、聚合
- 需要多端同步或更稳定的数据恢复
- 需要可靠迁移、备份、审计

优先顺序：

1. 先 SQLite
2. 再视需要迁移 PostgreSQL

当前不建议直接为这个项目引入 SQLAlchemy。

### 9.2 何时引入 Redis

满足任一条件再考虑：

- 外部查询耗时稳定偏高
- 相同查询重复率高
- 需要跨进程共享缓存
- 需要队列、限流或短期状态保存

在这些条件没出现前，保留无 Redis 设计。

### 9.3 何时拆 Adapter 层

当前 `chat_engine.py` 仍然承担了较多编排和结果生成逻辑。只有在以下情况出现时，才值得继续拆分：

- skill 类型明显增多
- 单股咨询、筛选类、搜索类的标准化逻辑差异过大
- 文件体积和变更频率已经影响维护

届时优先拆成：

- `mode_detector.py`
- `router.py`
- `normalizers/`
- `adapters/`
- `followup.py`

而不是一开始就拆很多空模块。

## 10. 安全与运行约束

当前安全边界：

- `IWENCAI_API_KEY` 只在后端环境中使用
- 前端只能看到 `api_key_configured: boolean`
- 后端通过 CORS 只允许本地前端地址

运行约束：

- 后端解释器和依赖必须统一走 `uv`，并固定在 `Python 3.12.x`
- 前端和后端端口固定
- `localhost` 与 `127.0.0.1` 都要可用
- 前端构建必须保持通过
- 浏览器回归至少覆盖：
  - 会话列表加载
  - 切换会话
  - 关闭会话
  - 单股买点回答

## 11. 当前架构的边界结论

当前这套架构的目标不是“面向未来十个团队的通用平台”，而是：

- 把问财 skills 变成一套自己能稳定每天用的工作台
- 用尽量少的层次解决实际问题
- 先把 contract、交互和结果表达做稳

所以当前的架构原则是：

1. contract 先于抽象
2. 规则编排先于大模型自治，GPT 只能做增强不能接管事实源
3. 本地可靠性先于分布式复杂度
4. 演进按触发条件升级，不预支复杂性
