# 问财 Skills 个人助手 Spec

最后更新：2026-04-23

## 1. 文档定位

这份 spec 是当前仓库的实现契约，不是方向性方案。若本文件和 PRD、架构规划、路线图存在冲突，以本文件为准。

相关背景文档：

- `docs/wencai-skills-assistant-prd.md`
- `docs/wencai-skills-assistant-architecture.md`
- `docs/wencai-skills-assistant-roadmap.md`

强约束规则：

- 修改后端 Pydantic schema、API 路由、前端 TypeScript type、核心交互、视觉风格时，必须同步更新本 spec。
- `backend/app/schemas/*.py` 和 `frontend/src/types/*.ts` 必须保持字段、枚举、nullable 语义一致。
- 前端 API 封装必须只从 `frontend/src/lib/api.ts` 暴露，不允许组件直接拼接后端地址。
- 会话、消息、结果、候选池等跨端数据结构不得在组件内临时扩字段。需要新增字段时，先改 spec，再改 Pydantic，再改 TypeScript。
- UI 风格必须服从第 10 节视觉约束。新增页面和组件不得随意引入另一套颜色、圆角、阴影、按钮尺寸或布局语言。
- 运行时配置只能来自项目根目录 `.env`。代码和脚本不得再读取 `backend/.env`、`frontend/.env.local` 等分散 env 文件。
- `.env` 不得提交，`.env.example` 必须提交，且字段集合必须与实际代码读取的配置项保持同步。

## 2. 当前实现边界

当前版本是单用户、本地 Web MVP：

- 前端：Next.js、TypeScript、TanStack Query、Zustand、Tailwind CSS。
- 后端：FastAPI、Pydantic、本地 JSON 文件存储。
- Python 运行时：必须使用 `uv` 管理，并固定在 `Python 3.12.x`。
- 数据源：问财 OpenAPI、本地已安装 skills、同花顺公开行情页/盘口接口单股补充、统一 LLM 管理下的 GPT 主链路与 MiniMax fallback 分析增强；LLM 编排必须通过 LangGraph agent runtime 执行。
- 运行端口：前端 `3000`，后端 `8000`。
- 不包含实盘交易、多用户权限、完整回测、行情 websocket 推送。

当前仓库路径约束：

| 模块 | 代码位置 |
|---|---|
| 后端入口 | `backend/app/main.py` |
| 后端契约模型 | `backend/app/schemas/*.py` |
| Python 版本锚点 | `.python-version` |
| 后端 uv 依赖入口 | `backend/pyproject.toml` |
| 后端 uv 锁文件 | `backend/uv.lock` |
| 根目录 env 示例 | `.env.example` |
| 统一启动脚本 | `scripts/dev.sh` |
| 后端启动脚本 | `scripts/dev-backend.sh` |
| 前端启动脚本 | `scripts/dev-frontend.sh` |
| 启动脚本 env 加载 | `scripts/load-env.sh` |
| 后端业务编排 | `backend/app/services/chat_engine.py` |
| 运行时技能注册表 | `backend/app/services/skill_registry.py` |
| 运行时技能 adapter | `backend/app/services/skill_adapters.py` |
| 本地单股行情适配 | `backend/app/services/local_market_skill_client.py` |
| LangGraph Agent 编排 | `backend/app/services/langgraph_stock_agent.py` |
| LLM Provider 管理 | `backend/app/services/llm_manager.py` |
| LLM 号池适配 | `backend/app/services/llm_account_pool.py` |
| GPT 分析增强 | `backend/app/services/openai_client.py` |
| 后端数据仓储 | `backend/app/services/repository.py` |
| 后端 JSON 存储 | `backend/app/services/json_store.py` |
| 前端 API 封装 | `frontend/src/lib/api.ts` |
| 前端类型契约 | `frontend/src/types/*.ts` |
| 会话状态 | `frontend/src/stores/chatStore.ts` |
| UI 状态 | `frontend/src/stores/uiStore.ts` |
| 工作台页面 | `frontend/src/app/page.tsx` |
| 会话列表 | `frontend/src/components/workbench/SessionList.tsx` |
| 结果侧栏 | `frontend/src/components/workbench/ResultPanel.tsx` |
| 视觉 token | `frontend/src/app/globals.css` |
| Next 开发配置 | `frontend/next.config.mjs` |

Python / uv 运行强约束：

- 后端后续运行必须基于 `uv`，不能再默认依赖系统 Python 或手工 `pip install`。
- Python 主版本必须锁在 `3.12.x`；若升级到 `3.13+`，必须先同步修改 `.python-version`、`backend/pyproject.toml` 和本 spec。
- 后端依赖的权威入口是 `backend/pyproject.toml`。
- `backend/requirements.txt` 若保留，只能作为兼容导出，内容必须与 `backend/pyproject.toml` 对齐。

## 3. 全局枚举契约

枚举源头：

- 后端：`backend/app/schemas/common.py`
- 前端：`frontend/src/types/common.ts`

任何一端新增、删除、改名枚举值，都必须同步另一端和本 spec。

### 3.1 ChatMode

```ts
type ChatMode =
  | "short_term"
  | "swing"
  | "mid_term_value"
  | "generic_data_query"
  | "compare"
  | "follow_up";
```

中文标签由 `frontend/src/lib/utils.ts` 的 `MODE_LABELS` 约束：

| 值 | 标签 | 使用场景 |
|---|---|---|
| `short_term` | 短线 | 短线、今天、明天、低吸、打板、个股能不能买 |
| `swing` | 波段 | 2 到 4 周、趋势、轮动、未来跟踪 |
| `mid_term_value` | 中线价值 | 估值、财务、ROE、现金流、中线 |
| `generic_data_query` | 通用 | 普通数据查询或兜底 |
| `compare` | 比较 | 比较、对比、排序、打分 |
| `follow_up` | 追问 | 依赖上一轮上下文继续问 |

### 3.2 SkillStrategy

```ts
type SkillStrategy =
  | "screen_then_enrich"
  | "single_source"
  | "compare_existing"
  | "research_expand";
```

策略语义：

- `screen_then_enrich`：先筛选，再补充行业、行情、资金、财务等信息。
- `single_source`：单一数据源查询。
- `compare_existing`：优先复用上一轮结果快照，适用于比较或基于已有表格字段的本地过滤 / 排序追问，不重新跑全量筛选。
- `research_expand`：围绕单股或中线研究扩展多个来源。

### 3.3 状态枚举

```ts
type SkillRunStatus = "pending" | "running" | "success" | "failed";

type ChatResponseStatus =
  | "idle"
  | "analyzing"
  | "running_skills"
  | "partial_ready"
  | "completed"
  | "failed";

type StreamEventType =
  | "analysis_started"
  | "mode_detected"
  | "skill_routing_ready"
  | "skill_started"
  | "skill_finished"
  | "partial_result"
  | "completed"
  | "failed";
```

### 3.4 CardType

```ts
type CardType =
  | "market_overview"
  | "sector_overview"
  | "candidate_summary"
  | "operation_guidance"
  | "portfolio_context"
  | "multi_horizon_analysis"
  | "risk_warning"
  | "research_next_step"
  | "custom";
```

`operation_guidance` 是操作建议卡，属于一等卡片类型。涉及单股购买建议、买入价、止损位的问题时，后端必须优先生成该卡片，前端必须在结果概览中优先展示。

`portfolio_context` 是模拟持仓上下文卡。涉及单股持仓、仓位、加仓、减仓、怎么处理等问题时，若模拟炒股链路可用，后端必须返回该卡片。

`multi_horizon_analysis` 是三周期分析卡。涉及单股咨询且问财返回了价格与技术指标时，后端必须返回该卡片，前端必须在结果概览中与操作建议卡一起优先展示。

### 3.5 WatchBucket

```ts
type WatchBucket =
  | "short_term"
  | "swing"
  | "mid_term_value"
  | "observe"
  | "discard";
```

### 3.6 GptReasoningPolicy

```ts
type GptReasoningPolicy = "auto" | "medium" | "high" | "xhigh";
```

语义：

- `auto`：后端按问法自动分级。
- `medium`：固定中等推理强度。
- `high`：固定高推理强度。
- `xhigh`：固定最高推理强度。

## 4. 数据模型契约

后端所有契约模型继承 `ContractModel`，`extra="forbid"`。请求和响应不得包含未声明字段。

### 4.1 ResultTable

```json
{
  "columns": ["代码", "名称", "最新价", "涨跌幅"],
  "rows": [
    {
      "代码": "600673",
      "名称": "东阳光",
      "最新价": "12.34",
      "涨跌幅": "1.23%"
    }
  ]
}
```

约束：

- `columns` 控制前端展示顺序。
- `rows` 每行是 key-value 对象，key 应优先来自 `columns`。
- 表格值必须是 JSON 可序列化值，不允许函数、日期对象、类实例。
- 数值字段如果需要排序，后端应优先给 number；若带百分号则前端按字符串展示。

### 4.2 ResultCard

```json
{
  "type": "operation_guidance",
  "title": "操作建议卡",
  "content": "现在能不能追：先观察。\n更好的买点：等回踩确认。\n失效条件：跌破计划位。\n止损/观察位：观察承接。",
  "metadata": {
    "subject": "东阳光",
    "observe_low": 11.8,
    "observe_high": 12.1,
    "stop_price": 11.4
  }
}
```

操作建议卡内容格式必须包含四段：

- `现在能不能追：`
- `更好的买点：`
- `失效条件：`
- `止损/观察位：`

若缺少最新价，仍必须返回操作建议卡，但价格相关 metadata 可以为空。

`custom` 卡当前允许用于规则层单股补充信息，已落地标题只有：

- `同花顺盘口补充`
- `同花顺题材补充`
- `财报与基本面`

前端不得把这些标题改成另一套别名；若新增新的 `custom` 卡标题，必须先更新本 spec。

### 4.3 StructuredResult

```json
{
  "summary": "一句话结论",
  "table": null,
  "cards": [],
  "facts": [],
  "judgements": [],
  "follow_ups": [],
  "sources": []
}
```

约束：

- `facts` 只放事实和来源。
- `judgements` 只放系统判断、风险解释、条件假设。
- 投资建议类回答必须保留风险边界，不能只给“买/不买”的结论。
- `sources` 里的 `skill` 和 `query` 必须可追溯到实际调用或实际使用的快照。
- 单股补充场景下，`sources.skill` 允许出现 `同花顺行情快照`、`同花顺盘口分析`、`同花顺题材补充`。
- 若 GPT 分析增强已启用，只允许增强 `summary`、`judgements`、`follow_ups` 和 `operation_guidance` 卡片文案。
- GPT 增强不得改写 `table`、`facts`、`sources`、卡片 `metadata`，不得新增未由问财或规则层提供的价格、新闻、指标。

### 4.3.1 UserVisibleError

```json
{
  "code": "iwencai_auth_failed",
  "severity": "error",
  "title": "问财鉴权失败",
  "message": "问财鉴权失败，请检查后端 IWENCAI_API_KEY 后重试。",
  "retryable": false
}
```

约束：

- `severity` 当前只允许 `warning` 或 `error`。
- `message` 必须直接可展示给终端用户，不能塞 Python 异常栈、traceback 或实现细节。
- `retryable=true` 只表示适合稍后重试，不保证当前环境配置一定正确。
- `user_visible_error` 可以出现在 `ChatResponse` 和 `ChatMessageRecord` 中，用于表示“本轮有明确可见的失败或降级提示”。
- 即使 `status="completed"`，也允许携带 `user_visible_error`；这表示本轮返回了可展示 fallback 结果，但需要明确告诉用户外部数据或能力存在失败。
- 当 `status="completed"` 且 `user_visible_error` 仅用于表达“本轮已降级返回 fallback 结果”时，`severity` 应优先使用 `warning`；真正的请求失败再使用 `error`。

### 4.4 SessionSummary

```json
{
  "id": "s_001",
  "title": "东阳光建议多少价格买入",
  "mode": "short_term",
  "archived": false,
  "created_at": "2026-04-23T01:00:00Z",
  "updated_at": "2026-04-23T01:10:00Z"
}
```

约束：

- `archived` 是会话关闭状态，不是硬删除状态。
- `GET /api/sessions` 永远不返回 `archived=true` 的会话。
- 已归档会话的详情查询必须返回 `404`。

### 4.5 ChatMessageRecord

```json
{
  "id": "m_001",
  "session_id": "s_001",
  "parent_message_id": null,
  "role": "assistant",
  "content": "总结文本",
  "mode": "short_term",
  "rewritten_query": "东阳光 最新价 涨跌幅 换手率 成交额 主力资金净流入 所属行业 所属概念",
  "skills_used": [],
  "result_snapshot": null,
  "status": "completed",
  "user_visible_error": null,
  "created_at": "2026-04-23T01:00:00Z"
}
```

约束：

- `role` 当前只允许业务使用 `user` 和 `assistant`。
- assistant 消息必须尽量保存 `result_snapshot`，用于比较和追问。
- 用户消息的 `parent_message_id` 可以为空。
- assistant 消息的 `parent_message_id` 应指向触发它的用户消息。
- assistant 消息若 `status="failed"`，必须同时持久化 `user_visible_error`，不能只在前端内存里显示一次。

## 5. API 契约

API 实现在 `backend/app/main.py`。前端只通过 `frontend/src/lib/api.ts` 调用。

### 5.1 Health

`GET /health`

响应：

```json
{
  "ok": true,
  "version": "0.1.0"
}
```

### 5.2 环境状态

`GET /api/meta/status`

响应：

```json
{
  "api_base_url": "https://openapi.iwencai.com",
  "api_key_configured": true,
  "skill_count": 20,
  "runtime_skills": [
    {
      "skill_id": "wencai.stock_screen",
      "display_name": "问财选A股",
      "adapter_kind": "wencai_query",
      "default_channel": null,
      "asset_path": "skills/stock-selecter",
      "asset_meta": {
        "slug": "stock-selecter",
        "version": "3.3.2",
        "owner_id": "kn7012q6c9jjgkq7dqwzkpgbt982y51v",
        "published_at": 1775992983412,
        "meta_path": "skills/stock-selecter/_meta.json"
      },
      "enabled": true
    }
  ],
  "llm_chain_mode": "auto",
  "llm_agent_runtime": "langgraph",
  "llm_enabled": true,
  "llm_account_pool_adapter": "env",
  "llm_system_prompt_source": "file",
  "llm_system_prompt_role": "你是问财 Skills 个人助手中的 A 股炒股助手。",
  "openai_base_url": "https://w.ciykj.cn/v1",
  "openai_api_key_configured": true,
  "openai_model": "gpt-5.4",
  "openai_reasoning_effort": "xhigh",
  "openai_enabled": true,
  "openai_account_count": 1,
  "anthropic_base_url": "https://api.minimaxi.com/anthropic",
  "anthropic_auth_token_configured": true,
  "anthropic_model": "MiniMax-M2.7",
  "anthropic_enabled": true,
  "anthropic_account_count": 1,
  "version": "0.1.0"
}
```

约束：

- `api_key_configured` 只能表示是否已配置，不能返回明文 key。
- `openai_api_key_configured` 只能表示是否已配置，不能返回明文 key。
- `anthropic_auth_token_configured` 只能表示是否已配置，不能返回明文 token。
- `llm_chain_mode` 当前支持 `auto`、`openai`、`minimax`；默认必须是 `auto`。
- `llm_agent_runtime` 当前固定为 `langgraph`。
- `llm_enabled` 表示至少有一个 provider 可用于大模型增强。
- `llm_account_pool_adapter` 当前默认 `env`。
- `llm_system_prompt_source` 当前支持 `env`、`file`。
- `llm_system_prompt_role` 必须返回当前系统 prompt 的首条角色定位，不返回完整长 prompt。
- `openai_account_count`、`anthropic_account_count` 必须返回当前 provider 真实可用账号数，而不是简单看 env 字段是否存在。
- `openai_enabled` 必须表示 GPT provider 至少有一个真实可用账号，可来自单账号 env 或 `OPENAI_ACCOUNT_POOL_JSON`。
- `anthropic_enabled` 必须表示 MiniMax provider 至少有一个真实可用账号，可来自单账号 env 或 `ANTHROPIC_ACCOUNT_POOL_JSON` / `MINIMAX_ACCOUNT_POOL_JSON`。
- `skill_count` 来源于 `skills/.skills_store_lock.json`。
- `runtime_skills` 必须来自后端 runtime registry，而不是简单遍历 `skills/` 目录。
- `runtime_skills[*].asset_meta` 允许为 `null`；这表示该 runtime skill 当前没有可读取的 `_meta.json`，不能视为接口错误。
- `runtime_skills[*].asset_meta` 若存在，只能暴露静态安装元数据，例如 `slug`、`version`、`owner_id`、`published_at`、`meta_path`。
- `runtime_skills[*].asset_meta` 不能反向决定 runtime 执行行为；前端也不能把它当成启用/禁用依据。

### 5.3 会话接口

#### `GET /api/sessions`

返回未归档会话列表，按 `updated_at` 倒序。

```json
[
  {
    "id": "s_001",
    "title": "短线盘前候选",
    "mode": "short_term",
    "archived": false,
    "created_at": "2026-04-23T01:00:00Z",
    "updated_at": "2026-04-23T01:10:00Z"
  }
]
```

#### `POST /api/sessions`

创建新会话，无请求体。

响应必须是 `SessionSummary`，默认：

- `title="新会话"`
- `mode=null`
- `archived=false`

#### `GET /api/sessions/{session_id}`

返回 `SessionDetail`。未知会话或已归档会话必须返回：

```json
{
  "detail": "Session not found"
}
```

HTTP status 必须是 `404`。

#### `DELETE /api/sessions/{session_id}`

关闭会话，语义是归档隐藏，不是物理删除。

成功响应：

```json
{
  "ok": true
}
```

约束：

- 后端必须调用 `Repository.archive_session()`。
- 后端必须将 `archived` 写为 `true`，并刷新 `updated_at`。
- 重复关闭、关闭未知会话、关闭已归档会话都返回 `404`。
- 关闭后 `GET /api/sessions` 不再出现该会话。
- 关闭后 `GET /api/sessions/{session_id}` 返回 `404`。
- 未来如果要做硬删除，必须新增独立语义，不允许复用当前 close contract。

### 5.4 Chat

#### `POST /api/chat`

请求：

```json
{
  "session_id": "s_001",
  "message": "东阳光建议多少价格买入",
  "mode_hint": "short_term",
  "stream": true
}
```

字段约束：

- `session_id` 可为 `null` 或省略。省略时后端创建新会话。
- `message` 必填，最小长度 1。
- `mode_hint` 可为 `ChatMode` 或 `null`。
- `stream` 可省略，后端默认 `false`；前端当前显式传 boolean。

非流式响应：

```json
{
  "session_id": "s_001",
  "message_id": "m_001",
  "mode": "short_term",
  "skills_used": [
    {
      "name": "个股快照",
      "status": "success",
      "latency_ms": 1200,
      "reason": "获取个股当日交易画像"
    }
  ],
  "summary": "如果你问的是买入价，东阳光不建议直接追。",
  "table": null,
  "cards": [],
  "facts": [],
  "judgements": [],
  "follow_ups": [],
  "sources": [],
  "status": "completed",
  "user_visible_error": null
}
```

#### 流式响应

当 `stream=true` 时，返回 `text/event-stream`。当前实现使用 data-only SSE，每段格式为：

```text
data: {"event":"mode_detected","emitted_at":"2026-04-23T01:00:00Z","mode":"short_term","confidence":0.84,"source":"single_security_rule"}
```

约束：

- 当前实现不使用单独的 `event:` 行。
- 前端解析时必须读取 JSON 内的 `event` 字段。
- 前端必须在 `completed` 之前就消费 `skill_routing_ready`、`skill_started`、`skill_finished`，并把这些事件增量写回当前 assistant 占位消息的 `skills_used`，不能只在最终 `completed` 时一次性更新。
- `completed` 事件的数据必须能还原为 `ChatResponse`。
- 当 `stream=true` 且规则层已产出结构化结果时，后端必须先发送 `partial_result` 和 `completed`，不能让 `completed` 被 LLM 增强阻塞。
- 若后续 LLM 增强产出的结果和已完成结果不同，后端可以继续追加 `result_enhanced` 事件；其 payload 必须仍可还原为 `ChatResponse`，并复用同一条 assistant `message_id`。
- `failed` 事件必须返回 `status="failed"`，并携带可直接展示的 `user_visible_error`。
- 当前前端必须把 SSE `failed` 事件和 HTTP 非 200 都转换成一条稳定的 assistant 失败消息，并额外给出 Toast；不能只停止 loading。
- HTTP 非 `200` 若返回的是 FastAPI 校验错误数组，前端也必须尽量归一成可读文案，不能直接把 `[object Object]` 或整段原始 JSON 暴露给用户。
- 当查询成功但命中 0 条时，返回的提示必须说明“未命中可展示数据”，不能误报为 API Key 问题。
- 只有鉴权失败、未配置 key 或明确的接口失败时，才允许返回检查 `IWENCAI_API_KEY` 或接口失败相关提示。
- 当问财主查询全部失败、但后端仍返回 fallback 表格时，`ChatResponse.status` 允许保持 `completed`，但必须通过 `user_visible_error` 明确告诉前端这是一轮带降级的结果。
- LLM provider 的读超时，包括 `TimeoutError` 和 `socket.timeout`，必须被归一成 provider 错误并按 fail-open 处理；已有基础结果时，不能把整轮请求升级成 `failed`。

#### `POST /api/chat/follow-up`

请求：

```json
{
  "session_id": "s_001",
  "parent_message_id": "m_001",
  "message": "把刚才那3只按风险排序",
  "stream": false
}
```

约束：

- 优先读取 `parent_message_id` 对应消息。
- 若父消息不存在，回退到该会话最新 assistant 消息。
- `message` 命中“对比 / 比较 / 打分 / 比一下”这类比较意图时，响应 `mode` 为 `compare`，允许直接基于上一轮 `result_snapshot` 做本地比较，不重新执行全量 skill。
- `message` 命中“只保留 / 去掉 / 剔除 / 按风险排序 / 按财务质量排序 / 只保留趋势更稳的 / 只保留 A 股标的”这类过滤或排序追问，且父结果表已包含所需字段时，后端允许直接基于上一轮 `result_snapshot.table` 做本地 refinement，不重新执行外部 skill。
- 当前本地 refinement 只允许使用上一轮结果表里已有字段，例如 `涨跌幅`、`技术面`、`基本面`、`风险点`、`代码`；若条件依赖快照里不存在的字段，例如市值、股息、最新公告日期，必须退回上下文继承 + 重路由，而不是伪造本地筛选结果。
- 其他追问必须结合父 assistant 的 `result_snapshot`、`rewritten_query` 和父消息 / 会话模式做上下文继承，然后重新执行 `detect_mode()`、`build_route()`、`execute_plan()`，不能统一退化成 `compare_from_snapshot()`。
- 追问重路由分支的响应 `mode` 仍固定为 `follow_up`，但 `skills_used`、`rewritten_query`、`sources` 必须记录本次真实执行结果。
- 追问本地 refinement 分支的响应 `mode` 也固定为 `follow_up`，`skills_used` 允许为空；`sources` 必须明确表明使用了上一轮结果快照。
- 若父消息对应单股结果且当前追问未显式写股票名称或代码，后端必须优先从卡片 `metadata.subject` 或单行结果表中继承标的主体。
- 若父消息上下文不足以继承标的或筛选条件，后端应回退为基于原始 `message` 和当前会话模式继续分析，而不是直接失败。
- 当 `stream=true` 且进入追问本地 refinement 分支时，后端至少要返回 `analysis_started`、`mode_detected`、`skill_routing_ready`、`partial_result`、`completed`；其中 `skill_routing_ready.strategy` 应为 `compare_existing`，`skills` 可以为空数组。
- 当 `stream=true` 且进入追问重路由分支时，SSE 事件序列必须与 `/api/chat` 主链路一致，至少包含 `analysis_started`、`mode_detected`、`skill_routing_ready`、`skill_started`、`skill_finished`、`partial_result`、`completed`；若事后 LLM 增强改写了结果，可额外补发 `result_enhanced`。
- 追问重路由分支里，`mode_detected` 事件中的 `mode` 表示本次实际执行用的处理模式；`completed` 事件里的 `ChatResponse.mode` 仍为 `follow_up`。

#### `POST /api/chat/compare`

请求：

```json
{
  "session_id": "s_001",
  "parent_message_id": "m_001",
  "symbols": [],
  "message": "比较上一轮结果",
  "stream": false
}
```

约束：

- `parent_message_id` 可为空。为空时使用该会话最新 assistant 消息。
- 当前 `symbols` 已进入契约但业务实现主要依赖快照和 `message`。

### 5.5 用户画像

`GET /api/profile`

`PUT /api/profile`

模型：

```json
{
  "capital": null,
  "position_limit_pct": 20,
  "max_drawdown_pct": 8,
  "holding_horizon": "2-4w",
  "risk_style": "balanced",
  "preferred_sectors": [],
  "default_mode": "swing",
  "default_result_size": 5,
  "gpt_enhancement_enabled": true,
  "gpt_reasoning_policy": "auto"
}
```

约束：

- `position_limit_pct` 和 `max_drawdown_pct` 范围是 0 到 100。
- `default_result_size` 范围是 1 到 100。
- `gpt_enhancement_enabled=false` 时，后端必须完全跳过 GPT 文案增强。
- `gpt_reasoning_policy=auto` 时，后端必须按问法自动选择 `medium/high/xhigh`。
- `UserProfileUpdate` 字段均可选。

### 5.6 模板

接口：

- `GET /api/templates`
- `POST /api/templates`
- `PUT /api/templates/{template_id}`
- `DELETE /api/templates/{template_id}`

`TemplateRecord`：

```json
{
  "id": "official_short_term",
  "name": "短线观察股",
  "category": "选股",
  "mode": "short_term",
  "content": "今天适合做什么方向？给我 5 只短线观察股，并说明催化、资金和风险。",
  "default_params": {},
  "created_at": "2026-04-23T01:00:00Z"
}
```

删除响应：

```json
{
  "ok": true
}
```

### 5.7 候选池

接口：

- `GET /api/watchlist`
- `POST /api/watchlist/resolve`
- `POST /api/watchlist`
- `PATCH /api/watchlist/{item_id}`
- `DELETE /api/watchlist/{item_id}`

`WatchStockResolveRequest`：

```json
{
  "query": "东阳光"
}
```

`WatchStockCandidate`：

```json
{
  "symbol": "600673.SH",
  "name": "东阳光",
  "latest_price": 33.9,
  "change_pct": -2.75,
  "industry": "元器件、半导体",
  "concepts": ["算力租赁", "数据中心"],
  "source_query": "东阳光 最新价 涨跌幅 所属行业 所属概念"
}
```

`WatchItemCreate`：

```json
{
  "query": "600673",
  "symbol": null,
  "name": null,
  "bucket": "observe",
  "tags": ["算力", "回踩"],
  "note": "等 MA20 回踩确认",
  "source_session_id": null
}
```

约束：

- `query`、`symbol`、`name` 三者至少要能提供一个有效值。
- `POST /api/watchlist/resolve` 必须支持股票名称、6 位代码、带交易所后缀代码。
- `POST /api/watchlist` 在 `symbol` 或 `name` 缺失时，后端必须自动走解析链路补全。
- `POST /api/watchlist/backfill` 必须提供一次性批量补齐能力，用于给旧候选项回填缺失的标签和备注。
- 解析完成后，后端必须统一返回标准化 `symbol`，例如 `600673.SH`。
- 候选池去重键是 `symbol`。若同一股票已存在，`POST /api/watchlist` 必须返回 `409 Conflict`。
- `tags` 必须在后端去空白、去重。
- `note` 必须在后端 trim；空字符串应转为 `null`。
- `query` 只作为创建时的临时输入，不得写入 `WatchItemRecord` 或存储文件。
- 允许直接传 `symbol + name` 创建，这条链路用于结果表 `☆` 一键入池。
- 结果表 `☆` 一键入池时，前端应优先补齐自动标签和备注后再调用 `POST /api/watchlist`：
  - 标签至少覆盖 `行业 / 题材 / 模式` 三类中的可用部分
  - 备注优先取当前这轮 assistant 的一句摘要或核心判断
- `POST /api/watchlist/backfill` 只补缺失内容：
  - 不覆盖已有 `tags`
  - 不覆盖已有 `note`
  - 可新增自动标签
  - 仅在 `note` 为空时尝试补一句自动备注

`WatchItemRecord`：

```json
{
  "id": "w_001",
  "symbol": "600673.SH",
  "name": "东阳光",
  "bucket": "short_term",
  "tags": ["观察"],
  "note": "等回踩确认",
  "source_session_id": "s_001",
  "created_at": "2026-04-23T01:00:00Z",
  "updated_at": "2026-04-23T01:00:00Z"
}
```

删除响应：

```json
{
  "ok": true
}
```

## 6. 后端行为契约

### 6.1 模式识别

函数：`detect_mode()`，位置：`backend/app/services/chat_engine.py`。

优先级：

1. `mode_hint`。
2. “刚才、上面、这几只、那几只、对比、比较”等追问或比较强规则。
3. 单股咨询规则。
4. 短线、波段、中线价值关键词规则。
5. 当前会话模式。
6. 通用查询和 fallback。

单股咨询必须覆盖以下口语：

- `东阳光今天能买嘛`
- `给我东阳光的购买建议`
- `东阳光建议多少价格买入`
- `东阳光什么价可以买`
- `翠微股份今天怎么持仓`
- `北方稀土建议买吗`
- `通富微电财报和K线怎么看`
- `通富微电属于什么板块`
- `我持有通富微电，帮我看具体情况`
- 股票代码形式，如 `600673 今天能不能买`

涉及买入价、价位、位置、低吸、上车的问题，必须设置 `entry_price_focus=true`，并生成更直接的买点总结。
涉及 `怎么持仓`、`怎么操作`、`怎么处理`、`建议买吗` 这类口语时，也必须识别为单股咨询，而不是退回市场级筛选。
涉及 `持仓`、`持有`、`仓位`、`加仓`、`减仓`、`清仓`、`止盈`、`止损`、`怎么拿` 这类问题时，必须额外设置 `holding_context_focus=true`。
- 单股主体提取前必须先做空白归一化；像 `帮我看 北方稀土 的 k线和财报`、`帮我看 中国平安 的 行业和概念` 这类带空格或并列主题的问法，必须识别出真实标的是 `北方稀土`、`中国平安`，不能把 `k线和`、`行业和` 误识别成 `subject`。

候选池动作识别：

- `/api/chat` 必须识别“把东阳光加入候选池”“把它加入候选池”“把这几只加入候选池”这类动作型问法。
- 若消息命中候选池添加意图，后端必须优先执行候选池写入，而不是走普通问财分析链路。
- 若问法只引用上下文代词如“它”“这只”“这几只”，后端必须优先尝试从当前会话最新 assistant `result_snapshot` 中提取股票。
- 单只上下文提取优先级：
  1. `result_snapshot.table.rows[0]`
  2. 卡片 metadata 里的 `subject`
- 多只上下文提取默认来自 `result_snapshot.table.rows`
- 若上下文里没有可解析股票，响应必须明确提示用户直接补股票名称或代码。
- 候选池动作响应也必须写入会话消息，不能只改数据不回消息。

### 6.2 路由策略

函数：`build_route()`。

运行时约束：

- `build_route()` 当前仍然输出固定编排的 `RoutePlan`，不直接从 `skills/` 目录动态发现可执行技能。
- `RoutePlan.skills[*]` 的最小运行时字段必须包括：`skill_id`、`name`、`query`、`reason`。
- `skill_id` 是后端运行时主键，用于交给 `backend/app/services/skill_registry.py` 查找技能元数据。
- `name` 仍是用户可见标签，用于 SSE `skill_started / skill_finished` 和前端 Skills 面板展示。
- `execute_plan()` 必须先根据 `skill_id` 查询 registry，再按 registry 里的 `adapter_kind` 调用 `backend/app/services/skill_adapters.py`，不能继续在主循环里直接写死各种 `plan.kind` / `plan.channel` 分支。
- `skills/` 目录仍是已安装 skill 的资产落盘位置，不是后端 runtime source of truth；是否启用、走哪类 adapter、默认 search channel 等运行时语义，以 registry 为准。
- 若某个 runtime skill 配置了 `asset_path`，registry 应允许 best-effort 读取 `asset_path/_meta.json`，补充 `slug`、`version`、`ownerId`、`publishedAt` 这类静态安装元数据。
- `_meta.json` 只能补充静态资产信息，不能反向覆盖 `display_name`、`adapter_kind`、`default_channel`、`enabled` 等 runtime 语义。

短线普通筛选：

- `问财选板块`：判断短线主线。
- `问财选A股`：筛选短线候选股。
- `行情数据查询`：补充资金承接。

波段普通筛选：

- `问财选A股`：筛选趋势候选。
- `行业数据查询`：补充行业轮动。
- `财务数据查询`：补充基本面质量。

中线价值：

- `财务数据查询`：筛选财务和估值质量。
- `公司股东股本查询`：补充筹码和股东结构。
- `研报搜索`：补充机构观点。

单股咨询：

- `个股价格量能`：获取价格、涨跌幅、振幅、量比、换手率、成交额和主力资金净流入。
- `个股技术指标`：获取均线、MACD、DIF、DEA、RSI、KDJ 和布林带。
- `个股行业题材`：补充所属行业、概念、上市板块、上市地点和市净率。
- `财报核心指标`：补充最新财报里的营收、利润、毛利率、资产负债率和经营活动现金流净额。
- `估值现金流补充`：补充市盈率、ROE、净资产收益率、增速和经营现金流。
- `同花顺行情快照`：补充最新价、开高低、成交额、换手率、量比、委比、委差等实时字段。
- `同花顺盘口分析`：补充五档盘口和最近逐笔成交。
- `同花顺题材补充`：补充所属地域、涉及概念、主营业务。
- 短线和波段补 `新闻搜索`、`公告搜索`。
- 中线补 `研报搜索`、`公告搜索`。
- 单股执行顺序必须满足：`个股价格量能`、`个股技术指标`、`个股行业题材` 在前，`财报核心指标`、`估值现金流补充` 紧随其后，本地补充链路早于新闻/公告/研报补充。
- 若用户输入的不是 6 位代码，系统允许在本地补充链路里先做股票名称到代码的解析。
- 若单股问财子查询失败，但本地代码解析成功且 `同花顺行情快照` 可用，后端仍必须生成单股结果，不能直接退回“暂无数据”。

单股持仓问题：

- 必须走 `模拟炒股 + 单股问财快照` 双链路。
- `模拟炒股` 负责提供真实模拟账户里的持仓数量、可用数量、成本、浮盈亏、账户仓位。
- 单股问财快照阶段负责提供现价、涨跌幅、换手率、资金、行业概念和技术指标。
- 若本地单股补充链路可用，持仓回答还应额外吸收盘口和题材补充。
- 若 `模拟炒股` 链路失败，不能让整轮失败；必须降级为仅基于单股问财快照的建议，并明确说明模拟持仓未读取成功。
- `模拟炒股` 当前仍属于 `chat_engine.py` 内的单股后处理分支，第一版 skill registry / adapter 改造不要求把它注册进 runtime registry。

### 6.3 操作建议卡

函数：`_single_security_action_card()`。

单股咨询结果必须包含：

- `summary`：用自然语言直接回应用户问题。
- `facts`：当前价格、涨跌幅、换手率、资金等事实。
- `judgements`：追价风险、失效逻辑等判断。
- `cards`：至少一个 `operation_guidance` 卡。
- `cards`：至少一个 `multi_horizon_analysis` 卡。
- `follow_ups`：围绕该标的继续深挖的三个建议。

若问财或财报补充返回了财务字段，还必须尽量包含：

- `财报与基本面` 自定义卡。
- `facts` 中至少一条财报事实，例如财报期、营收、归母净利润、经营现金流、ROE、毛利率、资产负债率中的任意组合。
- `facts` 中至少一条板块/上市地/行业归属事实。

若本地单股补充成功，还应尽量包含：

- `同花顺盘口补充` 自定义卡。
- `同花顺题材补充` 自定义卡。

若 `holding_context_focus=true` 且模拟持仓可用，还必须包含：

- 一个 `portfolio_context` 卡。
- `facts` 中至少一条模拟持仓事实。
- `judgements` 中至少一条结合成本或仓位的处理判断。

单股回答内容约束：

- `summary` 不能只给“先观察”这类空话，必须至少带一个数据锚点，如价格、涨跌幅、资金、近5日或近20日表现。
- `summary` 或 `judgements` 必须明确覆盖短线、中线、长线中的至少两个周期。
- 若财务字段可用，`summary`、`facts` 或 `judgements` 至少一处必须落财报锚点，优先使用财报期、营收同比、归母净利润同比、ROE、经营现金流中的任意一项。
- 若 `新闻搜索补充` 或 `公告搜索补充` 已有标题，`facts` 或 `judgements` 至少要落一个可跟踪的催化或风险线索。
- `judgements` 应优先解释“为什么现在不适合追 / 为什么更适合等承接”，而不是重复结论。
- 若 `同花顺盘口分析` 已成功，`summary`、`judgements` 或操作建议卡至少一处必须引用盘口承接、委比/委差、买一到买三、逐笔买卖倾向中的任一锚点。
- 若 `同花顺盘口分析` 已成功，规则层允许用买一到买三承接区间收紧 `observe_low` / `observe_high`。
- 若 `同花顺题材补充` 已成功，`facts` 至少应落一条地域、概念或主营业务事实。
- 若存在模拟持仓，上述回答必须优先回答“已有仓位该怎么处理”，而不是只回答“现在能不能买”。
- 若问财返回了 K 线和技术指标，`facts` 或 `judgements` 至少要引用一项技术锚点，例如开高低收、MA5/MA20/MA60、MACD、RSI、KDJ、布林带、量比。
- 若问财返回了 `上市板块` 或 `上市地点`，`facts` 至少应落一条相关事实。

三周期分析卡内容格式必须包含三段：

- `短线：`
- `中线：`
- `长线：`

单股快照查询字段约束：

- 单股问财快照必须拆成多条更窄的 query，不能再把价格、均线、MACD、布林带、行业、估值一次塞进同一条 `query2data`。
- `个股价格量能` 必须覆盖 `最新价`、`涨跌幅`、`近5日涨跌幅`、`近20日涨跌幅`、`开盘价`、`最高价`、`最低价`、`振幅`、`量比`、`换手率`、`成交额`、`主力资金净流入`。
- `个股技术指标` 必须覆盖 `5日均线`、`10日均线`、`20日均线`、`60日均线`、`MACD`、`DIF`、`DEA`、`RSI`、`KDJ`、`布林带上轨`、`布林带中轨`、`布林带下轨`。
- `个股行业题材` 必须覆盖 `所属同花顺行业` 或 `所属行业`、`所属概念`、`上市板块`、`上市地点`，并可附带 `市净率`。
- `财报核心指标` 必须覆盖 `营业收入`、`营业收入同比增长率`、`归母净利润`、`归母净利润同比增长率`、`扣非归母净利润`、`经营活动产生的现金流量净额`、`销售毛利率`、`资产负债率`。
- `估值现金流补充` 必须覆盖 `市盈率`、`ROE`、`净资产收益率`、`营收增速`、`净利润增速`、`经营现金流`，并可补充 `经营活动产生的现金流量净额`。
- `mid_term_value` 的单股链路在上述拆分基础上仍必须请求估值或财务字段，不能退化成只有价格和技术指标。
- 问财 `query2data` / `comprehensive_search` 命中非 0 `status_code` 时，后端应至少做一次轻量重试，再决定是否记为失败。
- 当问财 `query2data` 返回非 0 `status_code` 时，后端产出的失败原因必须直接带上 `status_code`，若上游返回了 `chunks_info`，也必须一并带上，不能只保留“问财接口返回错误”。

价格计算约束：

- `observe_high` 默认约为最新价的 0.99。
- 短线 `observe_low` 默认约为最新价的 0.97，非短线默认约为 0.96。
- 短线 `stop_price` 默认约为最新价的 0.95，非短线默认约为 0.93。
- 若短线存在前收盘价，应避免给出高于合理回踩确认的位置。

这些价格是辅助观察位，不是交易指令。文案必须避免承诺收益。

### 6.4 GPT 分析增强

服务位置：`backend/app/services/openai_client.py`。
Agent 编排位置：`backend/app/services/langgraph_stock_agent.py`。
Provider 管理位置：`backend/app/services/llm_manager.py`。
号池适配位置：`backend/app/services/llm_account_pool.py`。

配置来源：

- 项目根目录 `.env`。
- `LLM_CHAIN_MODE`，默认 `auto`。
- `LLM_ACCOUNT_POOL_ADAPTER`，默认 `env`。
- `LLM_SYSTEM_PROMPT`，可选；若存在，直接作为项目级系统 prompt。
- `LLM_SYSTEM_PROMPT_FILE`，可选；若未配置 `LLM_SYSTEM_PROMPT`，则从该文件读取项目级系统 prompt。当前默认文件为 `backend/prompts/stock-assistant-system-prompt.txt`。
- `LLM_SHORT_TERM_PROMPT`，可选；若存在，直接作为 `short_term` 模式子 prompt。
- `LLM_SHORT_TERM_PROMPT_FILE`，可选；若未配置 `LLM_SHORT_TERM_PROMPT`，则从该文件读取 `short_term` 模式子 prompt。
- `LLM_SWING_PROMPT`，可选；若存在，直接作为 `swing` 模式子 prompt。
- `LLM_SWING_PROMPT_FILE`，可选；若未配置 `LLM_SWING_PROMPT`，则从该文件读取 `swing` 模式子 prompt。
- `LLM_MID_TERM_VALUE_PROMPT`，可选；若存在，直接作为 `mid_term_value` 模式子 prompt。
- `LLM_MID_TERM_VALUE_PROMPT_FILE`，可选；若未配置 `LLM_MID_TERM_VALUE_PROMPT`，则从该文件读取 `mid_term_value` 模式子 prompt。
- `SIM_TRADING_ACCOUNTS_DIR`，可选；模拟炒股账户文件目录。默认优先读 skill 旧目录，找不到则落到 `backend/data/user_accounts`。
- `SIM_TRADING_AUTO_OPEN`，默认 `true`；若无模拟账户时是否自动开户。
- `SIM_TRADING_DEPARTMENT_ID`，默认 `997376`。
- `SIM_TRADING_TIMEOUT_SECONDS`，默认 `15`。
- `OPENAI_BASE_URL`，默认 `https://api.openai.com/v1`。
- `OPENAI_API_KEY`。
- `OPENAI_MODEL`，当前默认 `gpt-5.4`。
- `OPENAI_MODEL_REASONING_EFFORT`，当前可配置为 `xhigh`。
- `OPENAI_ACCOUNT_POOL_JSON`，可选；若存在，定义 GPT provider 的多账号池。
- `ANTHROPIC_BASE_URL`，MiniMax Anthropic 兼容接口地址。
- `ANTHROPIC_AUTH_TOKEN`。
- `ANTHROPIC_MODEL`，当前默认 `MiniMax-M2.7`。
- `ANTHROPIC_ACCOUNT_POOL_JSON` 或 `MINIMAX_ACCOUNT_POOL_JSON`，可选；若存在，定义 MiniMax provider 的多账号池。

行为约束：

- LLM / skill 编排必须通过 LangGraph graph 执行，不允许在 API 层直接手写 if/else 把 GPT 增强和 skill 调用串起来。
- LangGraph agent 当前至少要包含两个阶段节点：
  - `call_skills`：调用规则层 skill 执行器，产出结构化结果、skills_used 和 rewritten_query
  - `llm_enhance`：仅在存在成功 skill 时执行 LLM 增强
- 当 `stream=true` 时，API 层可以先消费 `call_skills` 阶段结果并立即返回 `partial_result` / `completed`，再通过 LangGraph 的增强阶段做 best-effort 补丁；但基础执行和增强执行都必须仍通过 `backend/app/services/langgraph_stock_agent.py` 暴露的 runtime 能力完成。
- LangGraph agent 的职责是编排，不改动前后端 chat contract；`/api/chat`、`/api/chat/follow-up`、`ChatResponse`、`StructuredResult` 的对外格式必须保持兼容。
- LangGraph agent 可以把当前整组问财 / 本地补充 skill 执行视为一个执行节点；后续若要细拆成逐 skill node，不能破坏当前 contract。
- GPT 只作为问财结构化结果后的分析增强层，不作为事实数据源。
- 当增强阶段失败、超时或 provider 不可用时，LangGraph runtime 必须返回未增强的基础结果，而不是把已有结构化结果整轮打成失败。
- 系统 prompt 必须体现“基于问财的 A 股炒股助手”定位，默认语气偏实战、直接、可执行，而不是泛化投资顾问。
- 项目级系统 prompt、模式子 prompt 与任务级增强约束必须三层分离：
  - 项目级系统 prompt：定义整体角色和通用风格
  - 模式子 prompt：按 `short_term`、`swing`、`mid_term_value` 细化关注点和语气
  - 任务级增强约束：定义 JSON 输出、可改字段和事实边界
- 若同时配置 `LLM_SYSTEM_PROMPT` 和 `LLM_SYSTEM_PROMPT_FILE`，必须优先使用 `LLM_SYSTEM_PROMPT`。
- 若同时配置模式 inline prompt 和对应 prompt file，必须优先使用 inline prompt。
- 若 `LLM_SYSTEM_PROMPT_FILE` 不存在或为空，服务必须在启动阶段直接报错，不能等到首个请求才失败。
- 三个模式子 prompt file 若不存在或为空，服务也必须在启动阶段直接报错。
- `short_term` 模式必须自动拼接 `LLM_SHORT_TERM_PROMPT` 或其文件内容。
- `swing` 模式必须自动拼接 `LLM_SWING_PROMPT` 或其文件内容。
- `mid_term_value` 模式必须自动拼接 `LLM_MID_TERM_VALUE_PROMPT` 或其文件内容。
- 默认 `LLM_CHAIN_MODE=auto`，按统一 provider 管理链路执行。
- `auto` 链路顺序必须是：
  - OpenAI Responses API `/responses`
  - OpenAI Chat Completions `/chat/completions`
  - MiniMax Anthropic `/v1/messages`
- `LLM_ACCOUNT_POOL_ADAPTER` 当前内建值只有 `env`；若配置未知 adapter，服务必须在启动阶段直接报错，不能静默回退到别的实现。
- `openai` 链路只允许走 GPT provider。
- `minimax` 链路只允许走 MiniMax provider。
- 若某个 provider 配置了账号池，provider 内部必须先做账号级轮询和失败切换，再决定是否切到下一个 provider。
- 账号池适配必须独立于 provider 实现，方便后续切换到数据库、配置中心或外部号池服务。
- 账号池模块必须提供 adapter factory / registry，后续新增数据库、配置中心、外部号池服务时，只新增 adapter 并在工厂注册，不允许把 provider 逻辑改成分支判断各种账号来源。
- 只有 OpenAI 和 MiniMax fallback 都失败时，才静默降级为规则化结果；不能让 `/api/chat` 因 GPT 失败整体失败。
- 新增 provider 时，必须先接入统一 provider 管理层，再给业务增强层使用。
- GPT 输出只能覆盖 `summary`、`judgements`、`follow_ups` 和 `operation_guidance` 文案。
- 操作建议卡经 GPT 改写后仍必须保留四段固定前缀和规则层生成的价格数字。
- 若单股结果已经包含三周期分析卡，GPT 改写后的 `summary` 或 `judgements` 仍必须保留多周期视角，且至少引用一个技术指标锚点。
- `skills_used` 不记录 GPT，因为 GPT 不是问财 skill；来源追溯仍以 `sources` 为准。
- `gpt_enhancement_enabled` 读取自 `UserProfile`，允许前端设置页动态关闭。
- `gpt_reasoning_policy` 默认 `auto`。自动分级规则：
  - 普通筛选、通用数据查询优先使用 `medium`
  - 单股建议、波段、中线价值分析优先使用 `high`
  - 买点价位、止损位、估值、财报、ROE、现金流等更重判断问题优先使用 `xhigh`

### 6.5 模拟炒股联动

服务位置：`backend/app/services/sim_trading_client.py`。

行为约束：

- 只有 `holding_context_focus=true` 的单股问题，才接入模拟炒股链路。
- 模拟炒股链路默认只读：当前阶段只允许开户、读取账户、读取持仓和账户仓位，不允许在 `/api/chat` 内自动触发买卖委托。
- 若本地无模拟账户且 `SIM_TRADING_AUTO_OPEN=true`，系统允许自动创建模拟账户。
- 账户信息必须存成单独 JSON 文件，默认文件名 `default.json`。
- 账户文件目录优先级必须是：
  1. `SIM_TRADING_ACCOUNTS_DIR`
  2. skill 旧目录 `/workspace/projects/workspace/user_accounts`
  3. `backend/data/user_accounts`
- 若模拟账户当前未持有该股，回答必须明确说明“未持有”，不能伪装成已持仓建议。
- `skills_used` 必须记录 `模拟炒股`，`sources` 必须可追溯到 `当前模拟持仓`。
- `facts` 必须包含 `同花顺问财模拟炒股服务` 的来源说明。
- 模拟炒股链路失败时，必须保留个股快照链路结果，并在 `facts` 中写明失败原因。

### 6.6 会话仓储

仓储位置：`backend/app/services/repository.py`。

当前实现使用 JSON 文件：

- `backend/app/data/profile.json`
- `backend/app/data/sessions.json`
- `backend/app/data/messages.json`
- `backend/app/data/templates.json`
- `backend/app/data/watchlist.json`

约束：

- 写入必须通过 `JsonFileStore.update()` 或 `JsonFileStore.write()`，保持原子替换。
- 不得在业务代码中直接读写这些 JSON 文件。
- 会话关闭只能改 `archived`，不得删除对应消息。
- `ensure_session()` 必须忽略已归档会话。若传入已归档 `session_id`，应创建新会话。

## 7. 前端行为契约

### 7.1 页面结构

当前页面：

- `/`：工作台。
- `/templates`：模板中心。
- `/watchlist`：候选池。
- `/settings`：设置。

工作台必须保持三栏结构：

- 左栏：会话列表，宽度 `w-60`。
- 中栏：消息流和输入框，自适应宽度。
- 右栏：结果侧栏，宽度 `w-[480px]`。

全局外壳：

- `AppShell` 使用 `h-screen overflow-hidden bg-background`。
- `Sidebar` 使用 `w-60 border-r bg-card`。
- 主内容区域内部滚动，不允许页面整体无控制滚动。

### 7.2 会话列表

组件：`frontend/src/components/workbench/SessionList.tsx`。

必须包含：

- `+ 新建会话` 按钮。
- 搜索框，占位文案 `搜索会话...`。
- 未匹配状态 `没有匹配的会话`。
- 空状态 `暂无会话记录`。
- 会话标题、模式 badge、相对更新时间。
- 每条会话的 `关闭` 按钮。

选择会话：

- 点击会话内容区域时调用 `setCurrentSession(session.id)`。
- 切换会话时先 `clearMessages()`，再由 `useSession()` 加载详情。

新建会话：

- 调用 `createSession()`。
- 成功后设为当前会话。
- 清空当前消息和结果。

关闭会话：

- 调用 `useSessions().closeSession(id)`。
- 前端 API 函数名必须是 `closeSession`，不得命名为 `deleteSession`，避免误导为硬删除。
- UI 按钮文案是 `关闭`。
- `aria-label` 必须包含会话标题，格式类似 `关闭会话：{title}`。
- 关闭按钮不能嵌套在会话选择 `<button>` 内，必须是同级按钮，避免无效 HTML 和误触。
- 点击关闭按钮不能触发会话选择。
- mutation 成功后必须 `invalidateQueries(["sessions"])`。
- mutation 成功后必须 `removeQueries(["session", closedSessionId])`。
- 如果关闭的是当前会话，必须 `setCurrentSession(null)` 并 `clearMessages()`。

视觉约束：

- 会话行容器使用 `group flex items-start gap-1 rounded-lg transition-colors`。
- 当前会话背景为 `bg-primary/10`。
- 非当前会话 hover 为 `hover:bg-muted`。
- 桌面端关闭按钮默认可隐藏，hover 或 focus 时出现；移动端必须常显。

### 7.3 ChatComposer

组件：`frontend/src/components/workbench/ChatComposer.tsx`。

输入框约束：

- 占位文案：`输入你的问题... (Enter发送, Shift+Enter换行)`。
- `Enter` 发送。
- `Shift + Enter` 换行。
- 发送期间禁用输入和发送按钮。
- 发送前必须 trim 输入。
- 发送后立即清空输入，并进入 loading。

追问判定：

- 如果当前存在 `currentSessionId`、最新 assistant 消息，并且输入命中推荐追问或包含追问关键词，走 `/api/chat/follow-up`。
- 否则走 `/api/chat`。
- 候选池动作问法默认走 `/api/chat`，由后端自行识别和执行，不要求前端单独分流。
- 用户点击 `追问` tab 里的推荐追问时，前端必须直接发起一次新请求，而不是只把文案填回输入框等待用户二次发送。
- 推荐追问被点击后，前端必须立即在消息流里插入该追问对应的 user message，并进入流式执行态；这是“顺滑追问”的一部分，不是可选体验。

快捷模板：

- `短线选股`
- `波段候选`
- `估值筛选`

### 7.4 MessageFlow

组件：`frontend/src/components/workbench/MessageFlow.tsx`。

空状态必须显示：

- `开始你的第一个问题吧`
- 示例：`今天适合做什么方向？给我5只短线观察股`

消息气泡：

- 用户消息右对齐，使用 `bg-primary text-primary-foreground`。
- assistant 消息左对齐，使用 `bg-muted`。
- assistant 消息必须展示模式 badge。
- 消息内容保留换行，使用 `whitespace-pre-wrap`。
- assistant 消息若携带 `user_visible_error`，消息气泡内必须直接展示错误/降级提示块。
- assistant 消息若 `status="failed"`，消息气泡视觉上必须和普通 completed 消息区分开，不能看起来像一条普通成功回复。

### 7.5 ResultPanel

组件：`frontend/src/components/workbench/ResultPanel.tsx`。

Tab 固定为：

- `结果概览`
- `Skills (n)`
- `追问 (n)`

结果概览顺序：

1. `ResultSummary`
2. 优先卡片
3. 表格视图或卡片视图

约束：

- assistant 主回复 `summary` 只在消息气泡中展示，右侧 `结果概览` 不得重复渲染同一段 `summary`。
- `ResultSummary` 只承载补充信息：`user_visible_error`、`judgements`；右栏默认不再渲染 `facts`。
- 优先卡片当前固定包括：
  - `operation_guidance`
  - `multi_horizon_analysis`
  - `portfolio_context`
  - 标题为 `财报与基本面` 的 `custom` 卡
- 这些优先卡片必须先于普通 cards 展示。
- 在 `卡片` 视图，若当前存在结构化 cards，右栏首屏应优先展示 `user_visible_error` 和结构化 cards；`judgements` 应后置，不能把结构化卡片压到首屏以下。
- 表格和卡片切换按钮只在表格和普通 cards 两种视图都可用时出现；若当前只有一种视图，前端必须直接展示该视图，不能切到空白态。
- 默认 `resultViewMode` 是 `table`。
- `Skills` tab 使用最新 assistant 消息的 `skills_used`。
- 当当前轮处于流式执行中时，`Skills` tab 必须实时反映 `pending -> running -> success/failed` 的变化，不能等整轮 `completed` 后再刷新。
- `追问` tab 使用 `currentResult.follow_ups`。
- 点击 `追问` tab 里的 suggestion 后，前端应立即切回 `结果概览` 或消息主视区，并直接自动发送该追问。
- 若表格支持收藏回调，`ResultPanel` 必须把 `onFavorite` 接到候选池创建 API，而不是留空。
- 结果侧栏应允许显示最近一次“加入候选池”成功或失败反馈。
- 聊天主链路若收到 `user_visible_error`，结果区或消息气泡里必须有稳定可见提示；Toast 只能作为补充，不能代替主界面状态。
- `ResultSummary` 顶部必须优先展示当前 latest assistant 的 `user_visible_error`，并在 `retryable=true` 时明确显示“可重试”语义。
- 若右侧当前没有错误提示、judgements、优先卡片、普通卡片或表格，则显示 `暂无分析结果`；不能因为消息气泡已有主回复就再造一个重复摘要占位。

### 7.6 ResultTable

组件：`frontend/src/components/results/ResultTable.tsx`。

约束：

- 支持全局搜索。
- 支持点击表头排序。
- 支持行点击回调。
- 支持收藏按钮回调。
- `☆` 收藏按钮语义是“加入候选池”。
- 若行里有 `代码` 和 `名称`，点击 `☆` 后必须调用 `POST /api/watchlist`。
- 收藏列必须固定在表格右侧，不能要求用户先横向滚动到最右边才能看到或点击 `☆`。
- 结果表 `☆` 入池前，前端应优先尝试用行内字段或 `POST /api/watchlist/resolve` 补齐 `行业 / 题材 / 模式` 标签。
- 结果表 `☆` 入池时，前端应自动带上一句当前轮 assistant 的摘要或核心判断作为 `note`；若行内已有 `核心逻辑`，优先使用行内逻辑。
- 收藏成功或失败的反馈必须回传到使用它的上层组件。
- 收藏态必须以后端 `watchlist` 真值为准，不能只靠组件局部点击状态假装成功。
- 若某行对应股票已经在候选池中，前端必须直接显示“已收藏”态或等价状态，并在再次点击时给出“已在候选池中”提示，而不是重新发起一轮看似成功的本地 toggle。
- 空表格显示 `暂无表格数据`。
- 底部显示 `共 n 条结果`。

### 7.7 ResultCards

组件：`frontend/src/components/results/ResultCards.tsx`。

卡片风格必须沿用当前类型映射：

| type | 背景 | 标签 |
|---|---|---|
| `market_overview` | `bg-blue-50 border-blue-200` | 市场概览 |
| `sector_overview` | `bg-purple-50 border-purple-200` | 板块概览 |
| `candidate_summary` | `bg-green-50 border-green-200` | 候选摘要 |
| `operation_guidance` | `bg-amber-50 border-amber-200` | 操作建议 |
| `risk_warning` | `bg-red-50 border-red-200` | 风险提示 |
| `research_next_step` | `bg-cyan-50 border-cyan-200` | 研究建议 |
| `custom` | `bg-gray-50 border-gray-200` | 自定义 |

特殊标题样式约束：

- 标题为 `财报与基本面` 的 `custom` 卡必须使用 `bg-emerald-50 border-emerald-200`，图标文案为 `财`。
- 对 `operation_guidance`、`multi_horizon_analysis`、`财报与基本面`、`同花顺盘口补充`、`同花顺题材补充` 这些固定单股卡型，前端必须优先消费 `metadata` 并渲染成结构化指标块、标签区或分栏区块，不能只把 `content` 当一整段纯文本打印。
- `operation_guidance` 应拆成四段可扫描区块，并把 `observe_low`、`observe_high`、`stop_price` 呈现成独立价格指标。
- `multi_horizon_analysis` 应至少拆成 `短线`、`中线`、`长线` 三个视觉区块，并结合 `metadata` 展示均线相对位置、量比、资金、MACD/RSI、估值或增速等核心锚点。
- `财报与基本面` 应按“财报期/归属信息/增长与盈利/估值质量”分组展示，避免把营收、利润、ROE、负债率继续拼成自然语言长段落。
- 未命中上述固定卡型时，前端才回退到通用纯文本卡片渲染。

### 7.8 WatchlistPage

组件：`frontend/src/app/watchlist/page.tsx`。

添加股票交互约束：

- 添加弹窗必须优先使用单输入框，标签为 `股票代码或名称`。
- 添加弹窗必须以居中浮层真实渲染，打开后内容、按钮和输入框必须可见且可点击，不能出现“DOM 已打开但界面不可操作”的状态。
- 输入框占位文案必须支持名称、6 位代码、带交易所后缀代码三种示例。
- 添加弹窗必须提供 `识别` 按钮。
- 若识别成功，必须展示标准化代码、股票名称，以及可用时的价格、涨跌幅、行业、概念预览。
- 手动添加时，一旦识别成功，前端必须自动预填标签，来源至少包括：
  - `行业`
  - `题材 / 概念`
  - 当前选择的 `bucket` 对应模式标签
- 用户仍可手动增删这些自动标签，但不应要求用户从空白开始自己补行业/题材/模式。
- 若识别失败，错误信息必须在弹窗内直接展示，不能静默失败。
- 保存时若还没有标准化 `symbol/name`，前端必须先调用 `POST /api/watchlist/resolve` 或直接调用 `POST /api/watchlist` 让后端完成补全，不能要求用户手填两项。
- 编辑已有候选股时，不允许修改股票本体，只允许修改 `bucket`、`tags`、`note`。
- 后端返回 `409` 时，前端必须把“已在候选池中”的错误直接展示给用户。
- 添加成功、更新成功、删除成功都必须有稳定可见反馈；当前实现允许用 Toast。

## 8. 前端状态和缓存契约

### 8.1 Query Keys

固定 query key：

- `["sessions"]`
- `["session", id]`
- `["meta-status"]`
- `["templates"]`
- `["watchlist"]`

会话关闭必须同时处理列表缓存和详情缓存。

### 8.2 Chat Store

`useChatStore` 必须持有：

- `currentSessionId`
- `messages`
- `inputValue`
- `modeHint`
- `autoDetectedMode`
- `streamingStatus`
- `currentResult`
- `partialSummary`

`clearMessages()` 必须同时清空：

- `messages`
- `currentResult`
- `partialSummary`

### 8.3 UI Store

`useUIStore` 默认值：

- `resultViewMode="table"`
- `resultTab="overview"`
- `leftPanelCollapsed=false`
- `rightPanelCollapsed=false`
- `sessionSearchQuery=""`

## 9. 开发和运行契约

### 9.1 端口和地址

前端：

- `http://localhost:3000`
- `http://127.0.0.1:3000`

后端：

- `http://127.0.0.1:8000`
- `http://localhost:8000`

统一配置文件：

```text
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
FRONTEND_PORT=3000
NEXT_PUBLIC_API_URL=http://localhost:8000
```

约束：

- 前端、后端和根目录启动脚本都必须从项目根目录 `.env` 读取运行时配置。
- `frontend/.env.local`、`backend/.env` 不再属于受支持的配置入口。
- `.env` 只允许本地存在，不得提交；`.env.example` 必须作为唯一可提交的配置模板保留在仓库根目录。

后端 CORS 当前允许：

- `http://localhost:3000`
- `http://127.0.0.1:3000`

Next 开发态必须允许 `127.0.0.1` 访问 dev resource：

```js
const nextConfig = {
  allowedDevOrigins: ["127.0.0.1"],
  reactStrictMode: true,
};
```

### 9.2 启动命令

统一一键启动：

```bash
./scripts/dev.sh
```

单独启动后端：

```bash
./scripts/dev-backend.sh
```

单独启动前端：

```bash
./scripts/dev-frontend.sh
```

后端：

```bash
cd backend
uv sync --python 3.12
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

前端：

```bash
cd frontend
PORT=3000 npm run dev
```

脚本约束：

- `scripts/dev-backend.sh` 必须先执行 `uv sync --python 3.12`，再启动 `uvicorn`。
- `scripts/dev-frontend.sh` 负责确保前端依赖已安装；`node_modules` 缺失时允许自动执行 `npm ci` 或 `npm install`。
- 启动脚本在拉起服务前应尽量做端口占用或现有 dev 进程预检，并给出直接可读的失败信息。
- `scripts/dev.sh` 必须并行拉起前后端，并在任一子进程退出时回收另一端。

### 9.3 验收命令

后端 Python 版本验收：

```bash
cd backend
uv run python -V
```

输出必须为 `Python 3.12.x`。

前端构建：

```bash
cd frontend
npm run build
```

会话关闭 API 验收：

```bash
created=$(curl -s -X POST http://127.0.0.1:8000/api/sessions)
session_id=$(node -e "const s=JSON.parse(process.argv[1]); console.log(s.id)" "$created")
curl -s -X DELETE "http://127.0.0.1:8000/api/sessions/$session_id"
curl -s -o /tmp/session.out -w "%{http_code}" "http://127.0.0.1:8000/api/sessions/$session_id"
```

最后一条必须输出 `404`。

## 10. 视觉和交互风格约束

### 10.1 全局视觉方向

当前产品是轻量、理性、数据工作台风格：

- 默认浅色主题。
- 背景是浅灰蓝：`--background: 220 20% 97%`。
- 卡片是白色：`--card: 0 0% 100%`。
- 主色是稳定蓝：`--primary: 221 83% 53%`。
- 圆角统一来自 `--radius: 0.5rem`。
- 边框使用 `--border: 214 32% 91%`。

不得随意引入：

- 大面积深色主题。
- 大面积紫色主视觉。
- 玻璃拟态、强阴影、强渐变背景。
- 与当前工作台不一致的营销页式视觉语言。

### 10.2 组件风格

新增按钮、输入框、卡片、badge 必须优先复用：

- `frontend/src/components/ui/Button.tsx`
- `frontend/src/components/ui/Input.tsx`
- `frontend/src/components/ui/Textarea.tsx`
- `frontend/src/components/ui/Badge.tsx`
- `frontend/src/components/ui/Card.tsx`

新增 className 时必须通过 `cn()` 合并，不允许手写冲突 Tailwind 类后不处理。

尺寸约束：

- 小按钮使用 `size="sm"`。
- 图标按钮使用 `size="icon"`。
- 列表项主要文字使用 `text-sm`。
- 辅助信息使用 `text-xs` 或 `text-[10px]`。
- 搜索输入框高度使用 `h-8`。

### 10.3 模式颜色

模式颜色由 `MODE_COLORS` 统一约束：

| mode | class |
|---|---|
| `short_term` | `bg-orange-100 text-orange-700 border-orange-200` |
| `swing` | `bg-violet-100 text-violet-700 border-violet-200` |
| `mid_term_value` | `bg-cyan-100 text-cyan-700 border-cyan-200` |
| `generic_data_query` | `bg-gray-100 text-gray-700 border-gray-200` |
| `compare` | `bg-blue-100 text-blue-700 border-blue-200` |
| `follow_up` | `bg-green-100 text-green-700 border-green-200` |

不得在业务组件里重新定义同一 mode 的另一套颜色。

### 10.4 文案风格

投资相关结论必须遵守：

- 先给结论，再给条件。
- 明确区分事实、判断、操作建议。
- 避免只输出“可以买”或“不能买”。
- 必须给出失效条件或风险提醒。
- 不承诺收益，不替代用户做最终交易决定。

单股买点类回答的推荐结构：

```text
如果你问的是买入价，{name}不建议在 {latest} 直接追。
更合适的是等 {observe_low}-{observe_high} 元区间承接稳定再看，
跌破 {stop_price} 元这笔交易计划就要重算。
```

### 10.5 可访问性和可测试性

- 操作按钮必须有可识别文本或 `aria-label`。
- 关闭、删除、收藏等图标或短文案按钮必须提供 `title` 或 `aria-label`。
- 重要空状态必须有稳定中文文案，方便浏览器回归定位。
- 不允许依赖纯颜色表达状态，必须同时有文字或图标。

## 11. 回归验收清单

改动合入前至少满足：

- `cd frontend && npm run build` 通过。
- `GET /health` 返回 `{"ok": true}`。
- `GET /api/meta/status` 不泄露 API Key。
- `GET /api/meta/status` 能返回 GPT 配置状态，且不泄露 `OPENAI_API_KEY`。
- `POST /api/chat` 能创建会话并返回 `ChatResponse`。
- `stream=true` 时能收到 `completed` SSE 数据。
- 会话列表能加载历史会话。
- 点击会话能加载消息和结果快照。
- 点击关闭当前会话后，会话从左栏消失，中栏恢复空状态，右栏无旧结果。
- 关闭后的会话详情接口返回 `404`。
- `localhost:3000` 和 `127.0.0.1:3000` 都能正常加载工作台。
- 单股买点问题，如 `东阳光建议多少价格买入`，必须返回操作建议卡。

## 12. 后续变更规则

新增能力时按以下顺序执行：

1. 更新本 spec 的模型、API、行为和视觉约束。
2. 更新 `backend/app/schemas/*.py`。
3. 更新 `frontend/src/types/*.ts`。
4. 更新后端实现。
5. 更新 `frontend/src/lib/api.ts` 和 hooks。
6. 更新 UI。
7. 跑构建和关键浏览器回归。

禁止做法：

- 先在 UI 里临时拼字段，后面再补模型。
- 只改 Pydantic 不改 TypeScript。
- 只改 TypeScript 不改 Pydantic。
- API 语义变化但不更新本 spec。
- UI 视觉变化但不更新第 10 节。
