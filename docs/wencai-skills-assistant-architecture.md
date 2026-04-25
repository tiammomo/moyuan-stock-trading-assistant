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

其中主回答文案以中栏 assistant 消息气泡为准，右栏 `结果概览` 只承载结构化补充信息，不重复渲染同一段 `summary`。
对于单股固定卡型，右栏还应优先按 `metadata` 渲染成结构化指标卡，而不是继续把 `card.content` 原样堆成大段文字。
当用户切到 `卡片` 视图时，右栏首屏应优先露出结构化 cards，本来作为补充信息的 `judgements` 需要后置，避免把关键卡片压到滚动容器下半区；`facts` 默认不在右栏结果概览中单独渲染。
右栏 `追问` tab 里的 suggestion 属于直接执行入口，不是输入框草稿；点击后应直接复用聊天流式主链路发起下一轮 follow-up。

这不是可随意改动的临时布局，而是后续所有体验优化的基本骨架。

### 4.3 状态划分

前端状态分两层：

1. 服务端数据缓存：TanStack Query
2. 本地交互态：Zustand

TanStack Query 负责：

- `["sessions"]`
- `["session", id]`
- `["meta-status"]`
- `["watch-monitor", "status"]`
- `["watch-monitor", "events"]`
- `["templates"]`
- `["watchlist"]`

其中 `["watchlist"]` 还是结果表收藏态和候选池页面的统一真值来源；前端不能只靠局部组件 state 判断某只股票是否已入池。
结果表 `☆` 入池和候选池手动添加共用一套自动填充规则：优先从 resolver 或行内字段推导 `行业 / 题材 / 模式` 标签；结果表入池还要自动带一条当前轮 assistant 的摘要或核心判断作为备注。
对于历史遗留的空标签 / 空备注候选项，后端提供一次性 `watchlist backfill` 入口做幂等补齐：只补缺，不覆盖已有手填内容。
`["watch-monitor", "status"]` 和 `["watch-monitor", "events"]` 属于后台盯盘 runtime 的只读展示层缓存，不允许前端自己维护一份平行事件流。

Zustand 负责：

- 当前会话 id
- 当前消息流
- 输入框内容
- streaming status
- 当前结构化结果
- 当前 assistant 占位消息上的实时 skill trace
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
| `backend/app/services/skill_registry.py` | 运行时 skill 元数据注册表，维护 `skill_id -> adapter_kind` |
| `backend/app/services/skill_adapters.py` | 运行时 skill adapter 层，隔离问财 / 搜索 / 本地行情调用 |
| `backend/app/services/openai_client.py` | GPT 分析增强和 OpenAI 兼容请求 |
| `backend/app/services/llm_manager.py` | LLM provider 注册、链路管理、失败切换 |
| `backend/app/services/llm_account_pool.py` | LLM 账号池 adapter factory、账号级轮询和失败切换 |
| `backend/app/services/sim_trading_client.py` | 模拟炒股账户、持仓上下文和只读联动 |
| `backend/app/services/watchlist_resolver.py` | 候选池股票解析、代码标准化和去重前校验 |
| `backend/app/services/watch_monitor.py` | 候选池驱动的分钟级盯盘 runtime、事件门禁和本地事件流 |
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

### 5.4 盯盘 Runtime

第一版实时盯盘不复刻 PanWatch 的整套多账户 Agent 平台，而是落成一个更轻量的 runtime：

- 股票来源：直接复用 `watchlist`
- 数据源：复用 `local_market_skill_client` 的实时快照
- 门禁：每只股票的声明式规则组 `watch_rules.json`
- 持久化：
  - `watch_rules.json`：规则声明
  - `watch_monitor_events.json`：事件流
  - `watch_monitor_state.json`：runtime 状态、symbol 最近快照、rule 冷却/日上限状态
- 输出：`/api/monitor/status`、`/api/monitor/rules`、`/api/monitor/events`、`/api/monitor/scan`

这样做的原因：

- 先把“候选池 -> 后台扫描 -> 事件流 -> 页面可见”闭环跑通
- 不在当前阶段引入第二套监控股票池
- 不提前把项目推进到 SQLAlchemy / APScheduler；通知渠道保持轻量 JSON 配置和 HTTP 推送适配
- 结果聚合、主表选择、卡片生成和失败兜底
- 单股咨询分支：
  - `_extract_security_subject()`
  - `_is_entry_price_question()`
  - `_single_security_route()`
  - `_single_security_action_card()`
  - `_multi_horizon_analysis_card()`
  - `_extract_technical_snapshot()`

`_extract_security_subject()` 当前还承担单股口语的预清洗职责：在正则提取前先移除问句中的空白字符，避免 `帮我看 北方稀土 的 k线和财报` 这类问法被错解析成 `k线和`、`行业和` 之类主题词。

单股问财模板已拆成更窄的子查询阶段：

- `个股价格量能`
- `个股技术指标`
- `个股行业题材`
- `财报核心指标`
- `估值现金流补充`

这些阶段在 runtime 上仍复用 `wencai.single_security_snapshot` / `wencai.single_security_fundamental` 两个 skill_id，但通过不同 `SkillPlan.name + query` 拆开执行，再在 `execute_plan()` 内合并成同一条单股主结果。

`skill_registry.py` 负责：

- 维护 `skill_id -> SkillSpec`
- 为每个运行时 skill 声明展示名、`adapter_kind`、默认 search channel、可选 `asset_path`
- 若 `asset_path/_meta.json` 存在，则 best-effort 吸收 `slug`、`version`、`ownerId`、`publishedAt` 这类静态安装元数据
- 为 `/api/meta/status` 提供 runtime skill 元数据，供设置页展示已安装版本
- 作为后端 runtime source of truth；`skills/` 目录只是安装资产目录，不直接驱动后端执行

`skill_adapters.py` 负责：

- 按 `adapter_kind` 封装问财 query、问财综合搜索、本地行情快照、本地盘口、本地题材补充
- 把外部调用细节和耗时采集从 `chat_engine.py` 中抽离
- 保持 `execute_plan()` 的主职责仍是“编排和结果聚合”，而不是“了解每一种 skill 怎么调”

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
-> 非流式：在 LangGraph 内完成规则执行 + GPT 增强，再写入 assistant
-> 流式：先消费 LangGraph `call_skills` 阶段结果
      -> 先返回 `partial_result` + `completed`
      -> repository.add_message(assistant + result_snapshot)
      -> 再 best-effort 执行 LangGraph `llm_enhance`
      -> 若增强结果有变化，则 repository.update_message(assistant) 并补发 `result_enhanced`
-> 若本轮存在可展示 fallback，但外部技能实际失败：
      -> completed ChatResponse / SSE completed 仍返回结构化结果
      -> 同时挂 `user_visible_error`
      -> 这类 completed 降级提示前端应按 warning 语义展示，而不是和 failed 共用 error 态
      -> 前端在消息气泡和结果概览顶部稳定展示该提示，Toast 只做补充提醒
-> 若主链路发生未兜住异常：
      -> repository.add_message(assistant failed)
      -> 返回 ChatResponse.failed 或 SSE failed
```

当前支持两种响应形态：

- 非流式 JSON
- SSE 流式事件

流式链路新增一个可选补丁事件：

- `result_enhanced`：`completed` 之后才可能出现，表示 GPT 增强在基础结果返回后又产出了更好的 summary / judgements / follow_ups；前端需要就地更新当前 assistant 消息，而不是新增一条消息。

### 6.1.1 候选池动作链路

```text
用户输入“把东阳光加入候选池”或“把这几只加入候选池”
-> backend/main.py 识别候选池动作意图
-> 若是上下文代词，则读取当前 session 最新 assistant result_snapshot
-> watchlist_resolver / context rows 解析股票
-> 前端基于 resolver 结果 / 当前表格行自动补齐 `行业 / 题材 / 模式` 标签
-> 前端基于当前轮 assistant summary / judgements 或表格行 `核心逻辑` 生成候选池备注
-> repository.find_watch_item_by_symbol() 去重
-> repository.create_watch_item() 写入候选池
-> assistant 返回候选池更新结果
-> 前端以 `["watchlist"]` 刷新后的真实数据驱动星标收藏态，而不是用本地 toggle 假设成功

历史候选池修复链路：
-> backend `/api/watchlist/backfill`
-> 逐条读取现有候选项
-> watchlist_resolver 补行业 / 概念
-> repository.latest_assistant_message() 尝试补一条摘要型备注
-> repository.update_watch_item() 只回填缺失字段
```

### 6.1.2 候选池盯盘链路

```text
应用启动
-> watch_monitor runtime 启动后台循环
-> 定时读取 repository.list_watchlist()
-> watch_rule_store.ensure_default_rules() 补齐默认规则
-> 对每只候选股抓取同花顺实时快照
-> 读取该股票启用中的 monitor rules
-> 对每条规则做条件评估
-> 通过规则级冷却 / 日上限检查
-> 命中时写入本地 monitor events，并更新 rule runtime state
-> 更新 monitor runtime status
-> 前端用 ["watch-monitor", "status"] / ["watch-monitor", "rules"] / ["watch-monitor", "events"] 拉取展示
-> 用户点击“立即扫描”时走 POST /api/monitor/scan 强制执行一轮
```

第一版有意不做的部分：

- 可通过默认通知渠道或规则级覆盖渠道自动发外部通知
- 不自动写入聊天消息
- 不把 watchlist 替换成单独的 holdings / alerts 模型

第一版盯盘区从候选池页拆出，作为独立页面存在：

- 候选池页只负责“看池子 / 管池子”
- 盯盘区页负责“后台扫描状态 + 规则管理 + 事件流”
- 盯盘区页内部保持单列布局：
  - `实时盯盘` 状态卡在上
  - `提醒规则` 在中
  - `最近盯盘事件` 在下

### 6.2 追问 / 比较链路

```text
用户输入追问
-> ChatComposer 判断走 /api/chat/follow-up
-> 后端读取 parent_message_id 对应消息
-> 若缺失则回退该 session 最新 assistant 消息
-> 若是“比较 / 对比 / 打分”类问法：
      -> compare_from_snapshot()
      -> 写入 user / assistant 消息
      -> 返回 compare 结果
-> 若是“只保留 / 去掉 / 按风险排序 / 按财务质量排序 / 趋势更稳”这类本地过滤或排序问法，且父结果表字段足够：
      -> 基于 parent.result_snapshot.table 做本地 refinement
      -> 写入 user / assistant 消息
      -> 返回 follow_up 结果
-> 否则：
      -> 基于 parent.result_snapshot / rewritten_query 做上下文继承
      -> detect_mode() / build_route() / execute_plan()
      -> 流式下先返回基础结果，再补 `result_enhanced`
      -> 写入或更新 user / assistant 消息
      -> 返回 follow_up 结果
```

当前设计重点：

- 比较优先复用 `result_snapshot`
- 过滤 / 排序类追问优先复用上一轮表格已有字段，避免不必要的外部重查
- 真正需要补公告、新闻、财务或单股细节时，再继承上一轮主体、筛选条件和模式做重路由

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
-> execute_plan() 依次获取个股价格量能、个股技术指标、个股行业题材、财报核心指标、估值现金流补充，并补充新闻/公告
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
-> execute_plan() 获取单股问财拆分查询、新闻、公告
-> execute_plan() 再读取模拟炒股持仓上下文
-> 若命中该股持仓，则把数量、成本、浮盈亏、账户仓位拼进 summary / facts / judgements
-> 返回 operation_guidance + portfolio_context 两张卡
-> 若模拟炒股失败，则降级为仅单股问财 + 本地行情建议
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
