# moyuan-wencai

基于问财 Skills、FastAPI、Next.js 和 LangGraph 的个人理财助手，面向 A 股场景，提供自然语言问答、候选池管理、单股分析、模拟持仓联动，以及 GPT 主链路 + MiniMax fallback 的分析增强。

当前版本定位是单用户、本地运行的 Web MVP，不包含实盘交易、多用户权限、完整回测或实时行情推送。

## 1. 项目定位

这个项目的目标不是做一个泛化聊天机器人，而是做一个偏实战的 A 股个人理财助手：

- 用自然语言问股票、板块、财报、题材、资金、持仓。
- 把问财 Skills 的结构化结果收敛成统一前后端 contract。
- 对单股问题输出更像“交易助手”的结果卡，而不是只给机械数据。
- 在规则事实层之上，引入 GPT 分析增强；默认走 `auto` 链路，优先 GPT，失败时回落 MiniMax。
- 在“持仓”“仓位”“怎么处理”类问题上，联动模拟炒股账户和单股快照。

## 2. 当前能力

已实现的核心能力：

- 三栏工作台：
  - 左侧会话列表
  - 中间消息流和输入框
  - 右侧结构化结果面板
- 聊天主链路：
  - `POST /api/chat`
  - `POST /api/chat/follow-up`
  - `POST /api/chat/compare`
- SSE 流式返回
- 用户画像设置页
- 模板中心
- 候选池管理
- 对话内自动加池
- 会话关闭
- 单股操作建议卡
- 单股三周期分析卡
- 问财 facts + GPT 文案增强
- LangGraph agent 编排
- GPT 主链路 + MiniMax fallback
- LLM 账号池适配层

当前关注的重点不是继续堆功能，而是把真实使用体验、回答质量、contract 一致性和配置安全继续收紧。

## 3. 技术栈

前端：

- Next.js 16
- React 18
- TypeScript
- TanStack Query
- Zustand
- Tailwind CSS

后端：

- FastAPI
- Pydantic v2
- LangGraph
- 本地 JSON 存储

运行时：

- Python `3.12.x`
- `uv`
- Node.js + `npm`

## 4. 运行方式

开发端口固定：

- 前端：`3000`
- 后端：`8000`

本项目统一从仓库根目录 `.env` 读取运行时配置：

- 后端读取根 `.env`
- 前端读取根 `.env`
- 启动脚本读取根 `.env`

受支持的配置模板是根目录 [.env.example](.env.example)。

`.env` 不进 Git，`.env.example` 进 Git。

## 5. 快速开始

### 5.1 环境要求

- Linux / macOS 为主
- Python `3.12.x`
- `uv`
- Node.js
- `npm`

### 5.2 初始化配置

```bash
cp .env.example .env
```

然后至少补齐这些配置：

```env
IWENCAI_BASE_URL=https://openapi.iwencai.com
IWENCAI_API_KEY=你的问财密钥

OPENAI_API_KEY=你的GPT密钥
OPENAI_BASE_URL=https://你的OpenAI兼容地址/v1
OPENAI_MODEL=gpt-5.4
OPENAI_MODEL_REASONING_EFFORT=xhigh

ANTHROPIC_BASE_URL=https://你的MiniMax兼容地址
ANTHROPIC_AUTH_TOKEN=你的MiniMax密钥
ANTHROPIC_MODEL=MiniMax-M2.7

NEXT_PUBLIC_API_URL=http://localhost:8000
```

如果你只想先跑通问财，不启用大模型，也可以只配置：

```env
IWENCAI_BASE_URL=https://openapi.iwencai.com
IWENCAI_API_KEY=你的问财密钥
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 5.3 一键启动

```bash
./scripts/dev.sh
```

这个脚本会：

- 从根 `.env` 加载配置
- 启动后端 `:8000`
- 启动前端 `:3000`
- 在任意一个子进程退出时自动清理另一个进程

启动后访问：

- 前端：`http://localhost:3000`
- 或：`http://127.0.0.1:3000`

### 5.4 分别启动前后端

后端：

```bash
./scripts/dev-backend.sh
```

前端：

```bash
./scripts/dev-frontend.sh
```

## 6. 手动启动

如果你不走一键脚本，也可以分别手动启动。

### 6.1 后端

```bash
cd backend
uv sync --python 3.12
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 6.2 前端

```bash
cd frontend
npm ci
npm run dev
```

## 7. 核心环境变量

根目录 `.env` 中当前支持的关键字段如下。

### 7.1 基础运行

```env
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
FRONTEND_PORT=3000
PYTHON_VERSION=3.12
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 7.2 问财配置

```env
IWENCAI_BASE_URL=https://openapi.iwencai.com
IWENCAI_API_KEY=
```

### 7.3 GPT 配置

```env
OPENAI_AUTH_MODE=apikey
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.4
OPENAI_MODEL_REASONING_EFFORT=medium
OPENAI_TIMEOUT_SECONDS=90
OPENAI_ACCOUNT_POOL_JSON=
```

### 7.4 MiniMax fallback 配置

```env
ANTHROPIC_BASE_URL=
ANTHROPIC_AUTH_TOKEN=
ANTHROPIC_MODEL=MiniMax-M2.7
ANTHROPIC_TIMEOUT_SECONDS=90
ANTHROPIC_ACCOUNT_POOL_JSON=
MINIMAX_ACCOUNT_POOL_JSON=
```

### 7.5 LLM 编排配置

```env
LLM_CHAIN_MODE=auto
LLM_ACCOUNT_POOL_ADAPTER=env
LLM_SYSTEM_PROMPT=
LLM_SYSTEM_PROMPT_FILE=backend/prompts/stock-assistant-system-prompt.txt
LLM_SHORT_TERM_PROMPT=
LLM_SHORT_TERM_PROMPT_FILE=backend/prompts/stock-assistant-short-term-prompt.txt
LLM_SWING_PROMPT=
LLM_SWING_PROMPT_FILE=backend/prompts/stock-assistant-swing-prompt.txt
LLM_MID_TERM_VALUE_PROMPT=
LLM_MID_TERM_VALUE_PROMPT_FILE=backend/prompts/stock-assistant-mid-term-value-prompt.txt
```

### 7.6 模拟炒股联动

```env
SIM_TRADING_ACCOUNTS_DIR=
SIM_TRADING_AUTO_OPEN=true
SIM_TRADING_DEPARTMENT_ID=997376
SIM_TRADING_TIMEOUT_SECONDS=15
```

更多字段见 [.env.example](.env.example)。

## 8. LLM 链路说明

当前默认 `LLM_CHAIN_MODE=auto`。

`auto` 链路顺序：

1. OpenAI Responses API
2. OpenAI Chat Completions
3. MiniMax Anthropic 兼容接口

约束：

- GPT 是分析增强层，不是事实数据源
- 规则层和问财结果先执行，再做 LLM 增强
- 只有 OpenAI 和 MiniMax 都失败时，才回落纯规则化结果
- 账号池逻辑通过 `llm_account_pool.py` 统一管理，便于后续新增更多 provider

## 9. 核心技能与数据来源

当前仓库中已经安装并接入了多类问财技能，典型包括：

- 基本资料查询
- 行情数据查询
- 财务数据查询
- 行业数据查询
- 机构研究与评级查询
- 事件数据查询
- 问财选 A 股
- 问财选板块
- 模拟炒股
- 新闻搜索
- 研报搜索
- 公告搜索

此外还包含一批策略/分析辅助技能，例如：

- `stock-selecter`
- `ths-advanced-analysis`
- `ths-financial-data`
- `ths-stock-themes`
- 行业轮动监控
- 量化因子选股

技能代码位于 [skills](skills)。

## 10. 支持的问法方向

典型问法：

- 单股短线：
  - `东阳光今天能买嘛`
  - `翠微股份建议多少价格买入`
- 单股持仓：
  - `翠微股份今天怎么持仓`
- 波段/中线：
  - `北方稀土波段怎么看`
  - `通富微电中线价值如何`
- 数据查询：
  - `给我东阳光的财报和所属板块`
  - `最近主力资金流入靠前的半导体股`
- 对比：
  - `比较北方稀土和包钢股份`
- 候选池：
  - `把通富微电加入候选池`

后端会按问法自动识别模式：

- `short_term`
- `swing`
- `mid_term_value`
- `generic_data_query`
- `compare`
- `follow_up`

## 11. 前端功能概览

主要页面：

- `/`
- `/settings`
- `/templates`
- `/watchlist`

主要交互：

- 会话列表
- 消息流
- 结果概览
- 技能执行轨迹
- 追问建议
- 候选池管理
- 会话关闭

前端所有后端请求统一经 [frontend/src/lib/api.ts](frontend/src/lib/api.ts) 发出，组件不允许直接拼接后端地址。

## 12. 后端 API 概览

健康检查：

- `GET /health`

环境状态：

- `GET /api/meta/status`

会话：

- `GET /api/sessions`
- `POST /api/sessions`
- `GET /api/sessions/{session_id}`
- `DELETE /api/sessions/{session_id}`

聊天：

- `POST /api/chat`
- `POST /api/chat/follow-up`
- `POST /api/chat/compare`

用户画像：

- `GET /api/profile`
- `PUT /api/profile`

模板：

- `GET /api/templates`
- `POST /api/templates`
- `PUT /api/templates/{template_id}`
- `DELETE /api/templates/{template_id}`

候选池：

- `GET /api/watchlist`
- `POST /api/watchlist/resolve`
- `POST /api/watchlist`
- `PATCH /api/watchlist/{item_id}`
- `DELETE /api/watchlist/{item_id}`

聊天支持同步返回和 SSE 流式返回两种链路。

## 13. 结果结构

当前返回结果不是随意文本，而是结构化 contract。

典型结果包含：

- `summary`
- `table`
- `cards`
- `facts`
- `judgements`
- `follow_ups`
- `sources`

单股问题会重点返回：

- `operation_guidance`
- `multi_horizon_analysis`
- `portfolio_context`

其中操作建议卡会尽量拆成四段：

- 现在能不能追
- 更好的买点
- 失效条件
- 止损/观察位

## 14. 仓库结构

```text
.
├── backend/
│   ├── app/
│   │   ├── core/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── prompts/
│   ├── pyproject.toml
│   └── uv.lock
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── stores/
│   │   └── types/
│   ├── package.json
│   └── next.config.mjs
├── docs/
├── scripts/
├── skills/
├── .env.example
├── .gitignore
└── README.md
```

## 15. 关键目录职责

后端：

- [backend/app/main.py](backend/app/main.py)
  FastAPI 入口与路由层
- [backend/app/services/chat_engine.py](backend/app/services/chat_engine.py)
  模式识别、技能路由、结果标准化
- [backend/app/services/langgraph_stock_agent.py](backend/app/services/langgraph_stock_agent.py)
  LangGraph agent 编排
- [backend/app/services/llm_manager.py](backend/app/services/llm_manager.py)
  LLM provider 管理
- [backend/app/services/llm_account_pool.py](backend/app/services/llm_account_pool.py)
  LLM 账号池
- [backend/app/services/openai_client.py](backend/app/services/openai_client.py)
  GPT 分析增强
- [backend/app/services/wencai_client.py](backend/app/services/wencai_client.py)
  问财请求与适配

前端：

- [frontend/src/app/page.tsx](frontend/src/app/page.tsx)
  主工作台
- [frontend/src/components/workbench/MessageFlow.tsx](frontend/src/components/workbench/MessageFlow.tsx)
  消息流与空态
- [frontend/src/components/workbench/ResultPanel.tsx](frontend/src/components/workbench/ResultPanel.tsx)
  结果侧栏
- [frontend/src/lib/api.ts](frontend/src/lib/api.ts)
  唯一 API 出口

文档：

- [docs/wencai-skills-assistant-spec.md](docs/wencai-skills-assistant-spec.md)
  当前实现契约
- [docs/wencai-skills-assistant-architecture.md](docs/wencai-skills-assistant-architecture.md)
  技术结构与模块职责
- [docs/wencai-skills-assistant-roadmap.md](docs/wencai-skills-assistant-roadmap.md)
  迭代顺序与阶段边界
- [docs/wencai-skills-assistant-prd.md](docs/wencai-skills-assistant-prd.md)
  产品背景

## 16. 本地数据与安全

本地运行数据默认落在 `backend/data/`，包括：

- sessions
- messages
- profile
- templates
- watchlist
- 模拟账户数据

这些数据默认不进 Git。

安全约束：

- `.env` 不得提交
- `.env.example` 必须提交
- 真实 API Key 不得写入代码、README、spec 或示例配置
- 前端只能看到“是否已配置”的布尔状态，不能读到真实密钥

## 17. 开发约束

项目当前的强约束：

- Python 必须固定 `3.12.x`
- 后端依赖统一走 `uv`
- 前端、后端端口固定为 `3000/8000`
- 运行时配置统一从根 `.env` 读取
- spec 是 contract 的最高优先级文档
- 变更 schema、type、API、核心交互、视觉风格时，必须同步改 spec

## 18. 常用命令

一键启动：

```bash
./scripts/dev.sh
```

仅后端：

```bash
./scripts/dev-backend.sh
```

仅前端：

```bash
./scripts/dev-frontend.sh
```

后端编译检查：

```bash
uv run --directory backend python -m compileall app
```

前端 TypeScript 检查：

```bash
cd frontend
./node_modules/.bin/tsc --noEmit
```

## 19. 文档优先级

推荐阅读顺序：

1. [README.md](README.md)
2. [docs/wencai-skills-assistant-spec.md](docs/wencai-skills-assistant-spec.md)
3. [docs/wencai-skills-assistant-architecture.md](docs/wencai-skills-assistant-architecture.md)
4. [docs/wencai-skills-assistant-roadmap.md](docs/wencai-skills-assistant-roadmap.md)
5. [docs/wencai-skills-assistant-prd.md](docs/wencai-skills-assistant-prd.md)

如果 README 和 spec 冲突，以 spec 为准。

## 20. 免责声明

本项目是个人理财辅助系统，不构成投资建议，也不保证收益。所有分析结果都应被视为研究辅助信息，而不是交易指令。
