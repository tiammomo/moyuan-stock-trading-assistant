from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import math
import re
from typing import Any, Dict, Iterable, List, Optional

from app.schemas import (
    CardType,
    ChatMessageRecord,
    ChatMode,
    ChatResponse,
    ChatResponseStatus,
    GptReasoningPolicy,
    ResultCard,
    ResultTable,
    SkillRunStatus,
    SkillStrategy,
    SkillUsage,
    SourceRef,
    StructuredResult,
    UserProfile,
    UserVisibleError,
    UserVisibleErrorSeverity,
)
from .skill_adapters import (
    LocalOrderBookAdapterResult,
    LocalRealheadAdapterResult,
    LocalThemeAdapterResult,
    WencaiQueryAdapterResult,
    WencaiSearchAdapterResult,
    get_skill_adapter,
)
from .skill_registry import (
    SKILL_LOCAL_ORDERBOOK,
    SKILL_LOCAL_REALHEAD,
    SKILL_LOCAL_THEME,
    SKILL_SEARCH_ANNOUNCEMENT,
    SKILL_SEARCH_NEWS,
    SKILL_SEARCH_REPORT,
    SKILL_WENCAI_FINANCIAL_QUERY,
    SKILL_WENCAI_INDUSTRY_QUERY,
    SKILL_WENCAI_MARKET_QUERY,
    SKILL_WENCAI_SECTOR_SCREEN,
    SKILL_WENCAI_SHAREHOLDER_QUERY,
    SKILL_WENCAI_SINGLE_SECURITY_FUNDAMENTAL,
    SKILL_WENCAI_SINGLE_SECURITY_SNAPSHOT,
    SKILL_WENCAI_STOCK_SCREEN,
    SkillAdapterKind,
    skill_registry,
)

from .local_market_skill_client import (
    LocalMarketContext,
    LocalMarketSkillError,
    LocalOrderBookSnapshot,
    LocalThemeSnapshot,
    local_market_skill_client,
)
from .langgraph_stock_agent import langgraph_stock_agent
from .wencai_client import WencaiClientError, wencai_client
from .openai_client import OpenAIClientError, openai_analysis_client
from .sim_trading_client import SimTradingClientError, SimTradingHoldingContext, sim_trading_client


@dataclass
class SkillPlan:
    skill_id: str
    name: str
    query: str
    reason: str


@dataclass
class ModeDetection:
    mode: ChatMode
    confidence: float
    source: str


@dataclass
class RoutePlan:
    mode: ChatMode
    strategy: SkillStrategy
    skills: List[SkillPlan]
    subject: Optional[str] = None
    single_security: bool = False
    entry_price_focus: bool = False
    holding_context_focus: bool = False


@dataclass
class TechnicalSnapshot:
    close: Optional[float] = None
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    five_day_change: Optional[float] = None
    twenty_day_change: Optional[float] = None
    turnover: Optional[float] = None
    amount: Optional[float] = None
    money_flow: Optional[float] = None
    volume_ratio: Optional[float] = None
    amplitude: Optional[float] = None
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma60: Optional[float] = None
    macd: Optional[float] = None
    diff: Optional[float] = None
    dea: Optional[float] = None
    rsi: Optional[float] = None
    kdj: Optional[float] = None
    boll_upper: Optional[float] = None
    boll_mid: Optional[float] = None
    boll_lower: Optional[float] = None
    pb: Optional[float] = None
    pe: Optional[float] = None
    roe: Optional[float] = None
    revenue_growth: Optional[float] = None
    profit_growth: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    revenue: Optional[float] = None
    net_profit: Optional[float] = None
    deduct_net_profit: Optional[float] = None
    gross_margin: Optional[float] = None
    debt_ratio: Optional[float] = None


def _skill_plan(
    skill_id: str,
    query: str,
    reason: str,
    *,
    name: Optional[str] = None,
) -> SkillPlan:
    spec = skill_registry.require(skill_id)
    return SkillPlan(skill_id=skill_id, name=name or spec.display_name, query=query, reason=reason)


SINGLE_SECURITY_PRICE_FIELDS = (
    "最新价 涨跌幅 近5日涨跌幅 近20日涨跌幅 "
    "开盘价 最高价 最低价 振幅 量比 换手率 成交额 主力资金净流入"
)

SINGLE_SECURITY_TECHNICAL_FIELDS = (
    "5日均线 10日均线 20日均线 60日均线 "
    "MACD DIF DEA RSI KDJ 布林带上轨 布林带中轨 布林带下轨"
)

SINGLE_SECURITY_THEME_FIELDS = "市净率 所属同花顺行业 所属行业 所属概念 上市板块 上市地点"

SINGLE_SECURITY_FUNDAMENTAL_CORE_FIELDS = (
    "最新财报 营业收入 营业收入同比增长率 "
    "归母净利润 归母净利润同比增长率 扣非归母净利润 "
    "经营活动产生的现金流量净额 毛利率 销售毛利率 资产负债率"
)

SINGLE_SECURITY_VALUATION_CASHFLOW_FIELDS = (
    "最新财报 市盈率 ROE 净资产收益率 "
    "营收增速 净利润增速 经营现金流 经营活动产生的现金流量净额"
)


SECURITY_ADVISORY_PATTERNS = (
    r"(?:我(?:目前)?(?:持有|拿着)|持有)(?P<subject>[A-Za-z0-9\u4e00-\u9fff]{2,12})(?:，|,|。|今天|今日|现在|目前|的|怎么|如何|$)",
    r"(?:给我|帮我看|请问|想问|看看|分析下|分析一下|说说)?(?P<subject>[A-Za-z0-9\u4e00-\u9fff]{2,12}?)(?:的|是|属于|对应)?(?:什么|哪个|哪些)?(?:财报|基本面|所属板块|板块|行业|概念|K线|k线|技术指标|技术面|走势|财务情况|具体情况)",
    r"(?:给我|帮我看|请问|想问|看看|分析下|分析一下|说说)?(?P<subject>[A-Za-z0-9\u4e00-\u9fff]{2,12}?)(?:今天|今日)?(?:能买嘛|能买吗|买嘛|能不能买|值不值得买)",
    r"(?:给我|帮我看|请问|想问|看看|分析下|分析一下|说说)?(?P<subject>[A-Za-z0-9\u4e00-\u9fff]{2,12}?)的(?:购买建议|买入建议|投资建议|短线建议|走势分析|诊断|建议)",
    r"(?:给我|帮我看|请问|想问|看看|分析下|分析一下|说说)?(?P<subject>[A-Za-z0-9\u4e00-\u9fff]{2,12}?)(?:今天|今日)?(?:怎么持仓|如何持仓|怎么操作|如何操作|怎么处理|如何处理|怎么拿|如何拿)",
    r"(?:给我|帮我看|请问|想问|看看|分析下|分析一下|说说)?(?P<subject>[A-Za-z0-9\u4e00-\u9fff]{2,12}?)(?:建议)?(?:买(?:吗|嘛)|买入(?:吗|嘛)|要不要买|该不该买|建议买吗)",
    r"(?:给我|帮我看|请问|想问|看看|分析下|分析一下|说说)?(?P<subject>[A-Za-z0-9\u4e00-\u9fff]{2,12}?)(?:建议)?(?:多少|什么|哪个)?(?:价格|价位|位置)(?:买入|介入|上车)",
    r"(?:给我|帮我看|请问|想问|看看|分析下|分析一下|说说)?(?P<subject>[A-Za-z0-9\u4e00-\u9fff]{2,12}?)(?:多少价|什么价|哪个价)(?:可以买|买入|介入)",
)

SECURITY_SUBJECT_STOPWORDS = {
    "a股",
    "A股",
    "大盘",
    "指数",
    "板块",
    "今天",
    "今日",
    "明天",
    "现在",
    "给我",
    "帮我看",
    "请问",
    "想问",
    "看看",
    "分析下",
    "分析一下",
    "说说",
    "这个",
    "这只",
    "个股",
    "股票",
    "的股票",
}

SECURITY_SUBJECT_PREFIXES = tuple(sorted(SECURITY_SUBJECT_STOPWORDS, key=len, reverse=True))

FOLLOW_UP_COMPARE_KEYWORDS = ("对比", "比较", "打分", "比一下", "比一比")


def detect_mode(
    message: str,
    *,
    mode_hint: Optional[ChatMode] = None,
    session_mode: Optional[ChatMode] = None,
) -> ModeDetection:
    text = message.lower()
    if mode_hint:
        return ModeDetection(mode_hint, 1.0, "mode_hint")

    if any(key in message for key in ("刚才", "上面", "这几只", "那几只", "对比", "比较")):
        if any(key in message for key in ("对比", "比较", "排序", "打分")):
            return ModeDetection(ChatMode.COMPARE, 0.95, "rule")
        return ModeDetection(ChatMode.FOLLOW_UP, 0.9, "rule")

    if _extract_security_subject(message):
        if any(key in message for key in ("中线", "价值", "估值", "财务", "财报", "基本面", "roe", "现金流")):
            return ModeDetection(ChatMode.MID_TERM_VALUE, 0.84, "single_security_rule")
        if any(key in message for key in ("波段", "趋势", "2周", "4周", "未来")):
            return ModeDetection(ChatMode.SWING, 0.84, "single_security_rule")
        return ModeDetection(ChatMode.SHORT_TERM, 0.84, "single_security_rule")

    if any(key in message for key in ("短线", "打板", "连板", "涨停", "明天", "今天", "盘前", "盘中", "低吸")):
        return ModeDetection(ChatMode.SHORT_TERM, 0.9, "rule")

    if any(key in message for key in ("波段", "2周", "4周", "趋势", "轮动", "未来", "跟踪")):
        return ModeDetection(ChatMode.SWING, 0.86, "rule")

    if any(key in message for key in ("中线", "价值", "估值", "roe", "pe", "pb", "现金流", "分红", "财务质量")):
        return ModeDetection(ChatMode.MID_TERM_VALUE, 0.88, "rule")

    if session_mode:
        return ModeDetection(session_mode, 0.65, "session_mode")

    if "?" in text or "？" in text or any(key in message for key in ("查询", "多少", "有哪些")):
        return ModeDetection(ChatMode.GENERIC_DATA_QUERY, 0.72, "rule")

    return ModeDetection(ChatMode.GENERIC_DATA_QUERY, 0.5, "fallback")


def _looks_like_specific_query(message: str) -> bool:
    return any(
        key in message
        for key in (
            "涨跌幅",
            "主力资金",
            "ROE",
            "roe",
            "市盈率",
            "营收",
            "净利润",
            "财报",
            "基本面",
            "K线",
            "k线",
            "技术指标",
            "技术面",
            "公告",
            "研报",
            "行业",
            "板块",
            "趋势",
            "只保留",
            "去掉",
            "剔除",
            "过滤",
            "筛选条件",
            "高股息",
        )
    )


def _extract_security_subject(message: str) -> Optional[str]:
    normalized_message = re.sub(r"\s+", "", message)
    code_match = re.search(r"([0368]\d{5}(?:\.(?:SH|SZ|BJ))?)", normalized_message, re.IGNORECASE)
    if code_match:
        return code_match.group(1).upper()

    for pattern in SECURITY_ADVISORY_PATTERNS:
        match = re.search(pattern, normalized_message)
        if not match:
            continue
        subject = match.group("subject").strip(" ，。！？?？")
        for stopword in SECURITY_SUBJECT_PREFIXES:
            subject = subject.removeprefix(stopword)
        subject = re.sub(r"(今天|今日)$", "", subject)
        subject = subject.strip()
        if 2 <= len(subject) <= 12 and subject not in SECURITY_SUBJECT_STOPWORDS:
            return subject
    return None


def _is_entry_price_question(message: str) -> bool:
    price_keywords = ("价格", "价位", "位置", "多少价", "什么价", "哪个价")
    action_keywords = ("买入", "介入", "上车", "低吸", "买")
    return any(price in message for price in price_keywords) and any(
        action in message for action in action_keywords
    )


def _is_holding_question(message: str) -> bool:
    keywords = (
        "持仓",
        "仓位",
        "加仓",
        "减仓",
        "清仓",
        "止盈",
        "止损",
        "怎么拿",
        "如何拿",
        "持有",
        "拿着",
        "怎么处理",
        "如何处理",
        "怎么操作",
        "如何操作",
        "要不要走",
        "要不要卖",
    )
    return any(keyword in message for keyword in keywords)


def _build_single_security_snapshot_plans(subject: str, mode: ChatMode) -> List[SkillPlan]:
    return [
        _skill_plan(
            SKILL_WENCAI_SINGLE_SECURITY_SNAPSHOT,
            f"{subject} {SINGLE_SECURITY_PRICE_FIELDS}",
            "获取价格、涨跌、量比、换手和资金快照",
            name="个股价格量能",
        ),
        _skill_plan(
            SKILL_WENCAI_SINGLE_SECURITY_SNAPSHOT,
            f"{subject} {SINGLE_SECURITY_TECHNICAL_FIELDS}",
            "获取均线、MACD、RSI、KDJ和布林带技术指标",
            name="个股技术指标",
        ),
        _skill_plan(
            SKILL_WENCAI_SINGLE_SECURITY_SNAPSHOT,
            f"{subject} {SINGLE_SECURITY_THEME_FIELDS}",
            "补充行业、概念、板块、上市地和市净率",
            name="个股行业题材",
        ),
    ]


def _build_single_security_fundamental_plans(subject: str) -> List[SkillPlan]:
    return [
        _skill_plan(
            SKILL_WENCAI_SINGLE_SECURITY_FUNDAMENTAL,
            f"{subject} {SINGLE_SECURITY_FUNDAMENTAL_CORE_FIELDS}",
            "补充最新财报核心指标",
            name="财报核心指标",
        ),
        _skill_plan(
            SKILL_WENCAI_SINGLE_SECURITY_FUNDAMENTAL,
            f"{subject} {SINGLE_SECURITY_VALUATION_CASHFLOW_FIELDS}",
            "补充估值、ROE、增速和现金流指标",
            name="估值现金流补充",
        ),
    ]


def _single_security_route(
    subject: str,
    mode: ChatMode,
    *,
    entry_price_focus: bool = False,
    holding_context_focus: bool = False,
) -> RoutePlan:
    snapshot_plans = _build_single_security_snapshot_plans(subject, mode)
    fundamental_plans = _build_single_security_fundamental_plans(subject)
    local_plans = [
        _skill_plan(SKILL_LOCAL_REALHEAD, subject, "补充最新价、量比、换手和盘口基础数据"),
        _skill_plan(SKILL_LOCAL_ORDERBOOK, subject, "补充五档盘口和逐笔成交"),
        _skill_plan(SKILL_LOCAL_THEME, subject, "补充地域、概念和主营业务"),
    ]
    if mode == ChatMode.MID_TERM_VALUE:
        return RoutePlan(
            mode=mode,
            strategy=SkillStrategy.RESEARCH_EXPAND,
            subject=subject,
            single_security=True,
            entry_price_focus=entry_price_focus,
            holding_context_focus=holding_context_focus,
            skills=[
                *snapshot_plans,
                *fundamental_plans,
                *local_plans,
                _skill_plan(SKILL_SEARCH_REPORT, f"{subject} 研究报告", "补充机构观点"),
                _skill_plan(SKILL_SEARCH_ANNOUNCEMENT, f"{subject} 公告", "补充最新公告"),
            ],
        )

    if mode == ChatMode.SWING:
        return RoutePlan(
            mode=mode,
            strategy=SkillStrategy.RESEARCH_EXPAND,
            subject=subject,
            single_security=True,
            entry_price_focus=entry_price_focus,
            holding_context_focus=holding_context_focus,
            skills=[
                *snapshot_plans,
                *fundamental_plans,
                *local_plans,
                _skill_plan(SKILL_SEARCH_NEWS, f"{subject} 新闻", "补充近期新闻催化"),
                _skill_plan(SKILL_SEARCH_ANNOUNCEMENT, f"{subject} 公告", "补充最新公告"),
            ],
        )

    return RoutePlan(
        mode=mode,
        strategy=SkillStrategy.RESEARCH_EXPAND,
        subject=subject,
        single_security=True,
        entry_price_focus=entry_price_focus,
        holding_context_focus=holding_context_focus,
        skills=[
            *snapshot_plans,
            *fundamental_plans,
            *local_plans,
            _skill_plan(SKILL_SEARCH_NEWS, f"{subject} 新闻", "补充近期新闻催化"),
            _skill_plan(SKILL_SEARCH_ANNOUNCEMENT, f"{subject} 公告", "补充最新公告"),
        ],
    )


def build_route(message: str, mode: ChatMode, profile: UserProfile) -> RoutePlan:
    limit = profile.default_result_size or 5
    subject = _extract_security_subject(message)
    entry_price_focus = _is_entry_price_question(message)
    holding_context_focus = _is_holding_question(message)
    if subject and mode in {ChatMode.SHORT_TERM, ChatMode.SWING, ChatMode.MID_TERM_VALUE}:
        return _single_security_route(
            subject,
            mode,
            entry_price_focus=entry_price_focus,
            holding_context_focus=holding_context_focus,
        )

    if mode == ChatMode.SHORT_TERM:
        stock_query = message if _looks_like_specific_query(message) else f"今日A股涨跌幅前{max(limit, 5)}的股票"
        return RoutePlan(
            mode=mode,
            strategy=SkillStrategy.SCREEN_THEN_ENRICH,
            skills=[
                _skill_plan(SKILL_WENCAI_SECTOR_SCREEN, f"今日A股涨跌幅前{max(limit, 5)}的板块", "判断短线市场主线"),
                _skill_plan(SKILL_WENCAI_STOCK_SCREEN, stock_query, "筛选短线候选股"),
                _skill_plan(SKILL_WENCAI_MARKET_QUERY, f"今日主力资金净流入前{max(limit, 5)}的A股", "补充资金承接"),
            ],
        )

    if mode == ChatMode.SWING:
        stock_query = message if _looks_like_specific_query(message) else f"近20日涨幅前{max(limit * 2, 10)}且今日主力资金净流入的A股"
        return RoutePlan(
            mode=mode,
            strategy=SkillStrategy.SCREEN_THEN_ENRICH,
            skills=[
                _skill_plan(SKILL_WENCAI_STOCK_SCREEN, stock_query, "筛选波段趋势候选"),
                _skill_plan(SKILL_WENCAI_INDUSTRY_QUERY, "近20日涨幅前10的A股板块", "补充行业轮动状态"),
                _skill_plan(SKILL_WENCAI_FINANCIAL_QUERY, "近一年净利润增长且ROE较高的A股", "补充基本面质量"),
            ],
        )

    if mode == ChatMode.MID_TERM_VALUE:
        finance_query = message if _looks_like_specific_query(message) else "市盈率低且ROE高且经营现金流为正的A股"
        return RoutePlan(
            mode=mode,
            strategy=SkillStrategy.RESEARCH_EXPAND,
            skills=[
                _skill_plan(SKILL_WENCAI_FINANCIAL_QUERY, finance_query, "筛选财务和估值质量"),
                _skill_plan(SKILL_WENCAI_SHAREHOLDER_QUERY, "股东户数下降且前十大股东持股稳定的A股", "补充筹码和股东结构"),
                _skill_plan(SKILL_SEARCH_REPORT, "A股 低估值 高ROE 研究报告", "补充机构观点"),
            ],
        )

    if mode == ChatMode.COMPARE:
        return RoutePlan(mode, SkillStrategy.COMPARE_EXISTING, [])

    return RoutePlan(
        mode=mode,
        strategy=SkillStrategy.SINGLE_SOURCE,
        skills=[_skill_plan(SKILL_WENCAI_STOCK_SCREEN, message, "按原始问句查询问财数据")],
    )


def _find_value(row: Dict[str, Any], exact: Iterable[str], contains: Iterable[str]) -> Any:
    for key in exact:
        if key in row:
            return row.get(key)
        lowered = key.lower()
        for row_key, value in row.items():
            if row_key.lower() == lowered:
                return value
    for key, value in row.items():
        lowered_key = key.lower()
        if any(part in key or part.lower() in lowered_key for part in contains):
            return value
    return None


def _metric_key_matches(key: str, contains: Iterable[str], excludes: Iterable[str] = ()) -> bool:
    lowered_key = key.lower()
    contains_match = any(part in key or part.lower() in lowered_key for part in contains)
    excludes_match = any(part in key or part.lower() in lowered_key for part in excludes)
    return contains_match and not excludes_match


def _find_metric_value(
    row: Dict[str, Any],
    contains: Iterable[str],
    excludes: Iterable[str] = (),
) -> Any:
    for key, value in row.items():
        if _metric_key_matches(key, contains, excludes):
            return value
    return None


def _safe_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and math.isfinite(value):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace("%", "").replace(",", "")
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _compact_metric_fields(row: Dict[str, Any], excluded: set[str], limit: int = 3) -> str:
    items = []
    for key, value in row.items():
        if key in excluded:
            continue
        if isinstance(value, (dict, list)):
            continue
        text = str(value)
        if len(text) > 32:
            text = text[:32] + "..."
        items.append(f"{key}: {text}")
        if len(items) >= limit:
            break
    return "；".join(items)


def _build_logic(mode: ChatMode, change: Optional[float], metric_text: str) -> str:
    if mode == ChatMode.SHORT_TERM:
        return f"短线强势或资金关注；{metric_text}" if metric_text else "短线强势或资金关注"
    if mode == ChatMode.SWING:
        return f"趋势和资金条件入选；{metric_text}" if metric_text else "趋势和资金条件入选"
    if mode == ChatMode.MID_TERM_VALUE:
        return f"估值/财务质量维度入选；{metric_text}" if metric_text else "估值/财务质量维度入选"
    return metric_text or "匹配当前查询条件"


def _build_risk(mode: ChatMode, change: Optional[float]) -> str:
    if change is not None and change >= 9.5:
        return "短期涨幅较大，注意追高和次日分歧"
    if mode == ChatMode.MID_TERM_VALUE:
        return "需继续核对财报质量、估值陷阱和行业景气"
    if mode == ChatMode.SWING:
        return "趋势失效或板块退潮时需要止损"
    return "需关注量能持续性和题材退潮"


def normalize_table(datas: List[Dict[str, Any]], mode: ChatMode, source_skill: str, limit: int) -> ResultTable:
    include_technical = any(_build_row_technical_brief(raw) for raw in datas[:limit])
    include_fundamental = any(_build_row_fundamental_brief(raw) for raw in datas[:limit])
    columns = ["代码", "名称", "最新价", "涨跌幅"]
    if include_technical:
        columns.append("技术面")
    if include_fundamental:
        columns.append("基本面")
    columns.extend(["核心逻辑", "风险点", "数据来源"])
    rows: List[Dict[str, Any]] = []
    for raw in datas[:limit]:
        code = _find_value(raw, ("股票代码", "指数代码", "代码"), ("代码",))
        name = _find_value(raw, ("股票简称", "指数简称", "名称", "股票名称"), ("简称", "名称"))
        latest = _find_value(raw, ("最新价",), ("最新价",))
        change = _safe_float(_find_value(raw, ("最新涨跌幅",), ("涨跌幅",)))
        excluded = {k for k in raw if any(part in k for part in ("代码", "简称", "名称", "最新价", "涨跌幅"))}
        metric_text = _compact_metric_fields(raw, excluded)
        row = {
            "代码": code or "-",
            "名称": name or "-",
            "最新价": latest if latest is not None else "-",
            "涨跌幅": f"{change:.2f}%" if change is not None else "-",
            "核心逻辑": _build_logic(mode, change, metric_text),
            "风险点": _build_risk(mode, change),
            "数据来源": source_skill,
        }
        if include_technical:
            row["技术面"] = _build_row_technical_brief(raw) or "-"
        if include_fundamental:
            row["基本面"] = _build_row_fundamental_brief(raw) or "-"
        rows.append(row)
    return ResultTable(columns=columns, rows=rows)


def _skill_success(name: str, latency_ms: Optional[int], reason: str) -> SkillUsage:
    return SkillUsage(name=name, status=SkillRunStatus.SUCCESS, latency_ms=latency_ms, reason=reason)


def _skill_failed(name: str, reason: str) -> SkillUsage:
    return SkillUsage(name=name, status=SkillRunStatus.FAILED, latency_ms=None, reason=reason)


def _execution_user_visible_error(failure_reasons: List[str]) -> UserVisibleError:
    first_reason = next((reason for reason in failure_reasons if reason), "")
    if not first_reason:
        return UserVisibleError(
            code="iwencai_upstream_error",
            severity=UserVisibleErrorSeverity.WARNING,
            title="问财接口调用失败",
            message="问财接口暂时不可用，请稍后重试。",
            retryable=True,
        )

    if "API_KEY 未配置" in first_reason or "HTTP 401" in first_reason or "HTTP 403" in first_reason:
        return UserVisibleError(
            code="iwencai_auth_failed",
            severity=UserVisibleErrorSeverity.WARNING,
            title="问财鉴权失败",
            message="问财鉴权失败，请检查后端 IWENCAI_API_KEY 后重试。",
            retryable=False,
        )

    if "网络错误" in first_reason:
        return UserVisibleError(
            code="iwencai_network_error",
            severity=UserVisibleErrorSeverity.WARNING,
            title="问财接口网络异常",
            message="问财接口网络异常，请稍后重试。",
            retryable=True,
        )

    return UserVisibleError(
        code="iwencai_upstream_error",
        severity=UserVisibleErrorSeverity.WARNING,
        title="问财接口调用失败",
        message=first_reason[:120],
        retryable=True,
    )


def _primary_skill_priority(plan: SkillPlan, mode: ChatMode) -> int:
    spec = skill_registry.require(plan.skill_id)
    if spec.adapter_kind != SkillAdapterKind.WENCAI_QUERY:
        if spec.adapter_kind == SkillAdapterKind.LOCAL_REALHEAD:
            return 95
        return -1
    if plan.skill_id in {SKILL_WENCAI_STOCK_SCREEN, SKILL_WENCAI_SINGLE_SECURITY_SNAPSHOT}:
        return 100
    if mode == ChatMode.MID_TERM_VALUE and plan.skill_id == SKILL_WENCAI_FINANCIAL_QUERY:
        return 90
    if plan.skill_id == SKILL_WENCAI_MARKET_QUERY:
        return 80
    if plan.skill_id in {SKILL_WENCAI_FINANCIAL_QUERY, SKILL_WENCAI_SHAREHOLDER_QUERY}:
        return 70
    if "板块" in plan.name or "行业" in plan.name:
        return 20
    return 50


def _extract_security_code(value: Any) -> Optional[str]:
    text = str(value or "").strip().upper()
    matched = re.search(r"([0368]\d{5})", text)
    if not matched:
        return None
    return matched.group(1)


def _extract_security_code_from_raw(raw: Optional[Dict[str, Any]]) -> Optional[str]:
    if not raw:
        return None
    return _extract_security_code(_find_value(raw, ("股票代码", "代码"), ("代码",)))


def _extract_security_name_from_raw(raw: Optional[Dict[str, Any]]) -> Optional[str]:
    if not raw:
        return None
    value = _find_value(raw, ("股票简称", "名称", "股票名称"), ("简称", "名称"))
    text = str(value or "").strip()
    return text or None


def _select_single_security_row(
    datas: List[Dict[str, Any]],
    subject: Optional[str],
) -> Optional[Dict[str, Any]]:
    if not datas:
        return None
    subject_text = str(subject or "").strip()
    subject_code = _extract_security_code(subject_text)
    for row in datas:
        row_code = _extract_security_code_from_raw(row)
        if subject_code and row_code == subject_code:
            return row
    for row in datas:
        row_name = _extract_security_name_from_raw(row)
        if row_name and subject_text and row_name == subject_text:
            return row
    return datas[0]


def _merge_raw_fields(
    base: Optional[Dict[str, Any]],
    overlay: Dict[str, Any],
    *,
    overwrite: bool,
) -> Dict[str, Any]:
    merged = dict(base or {})
    for key, value in overlay.items():
        if value is None or value == "" or value == []:
            continue
        current = merged.get(key)
        current_missing = current is None or current == "" or current == [] or current == "--"
        if overwrite or key not in merged or current_missing:
            merged[key] = value
    return merged


def _refresh_primary_table(raw: Dict[str, Any], mode: ChatMode, source_skill: str) -> ResultTable:
    return normalize_table([raw], mode, source_skill, 1)


def _append_source_label(current: str, incoming: str) -> str:
    if not current:
        return incoming
    if incoming in current:
        return current
    return f"{current} + {incoming}"


def _format_book_volume(value: Optional[float]) -> Optional[str]:
    if value is None:
        return None
    if value >= 10000:
        return f"{value / 10000:.2f}万股"
    if float(value).is_integer():
        return f"{int(value)}股"
    return f"{value:.0f}股"


def _format_order_book_side(
    label: str,
    prices: List[Optional[float]],
    volumes: List[Optional[float]],
    *,
    depth: int = 3,
) -> Optional[str]:
    items: List[str] = []
    for idx, price in enumerate(prices[:depth], start=1):
        if price is None:
            continue
        volume = volumes[idx - 1] if idx - 1 < len(volumes) else None
        volume_text = _format_book_volume(volume)
        if volume_text:
            items.append(f"{label}{idx} {price:.2f}/{volume_text}")
        else:
            items.append(f"{label}{idx} {price:.2f}")
    if not items:
        return None
    return "，".join(items)


def _local_support_zone(local_market: Optional[LocalMarketContext]) -> tuple[Optional[float], Optional[float]]:
    if not local_market or not local_market.order_book:
        return None, None
    return local_market.order_book.support_zone(depth=3)


def _local_trade_balance(local_market: Optional[LocalMarketContext]) -> Optional[str]:
    if not local_market or not local_market.trades:
        return None
    buy_volume = sum((trade.volume or 0.0) for trade in local_market.trades if trade.direction == "buy")
    sell_volume = sum((trade.volume or 0.0) for trade in local_market.trades if trade.direction == "sell")
    if buy_volume <= 0 and sell_volume <= 0:
        return None
    if buy_volume > sell_volume * 1.2:
        return f"最近逐笔买盘更主动（买 { _format_book_volume(buy_volume) }，卖 { _format_book_volume(sell_volume) }）"
    if sell_volume > buy_volume * 1.2:
        return f"最近逐笔卖盘更重（卖 { _format_book_volume(sell_volume) }，买 { _format_book_volume(buy_volume) }）"
    return f"最近逐笔买卖接近均衡（买 { _format_book_volume(buy_volume) }，卖 { _format_book_volume(sell_volume) }）"


def _local_orderbook_bias(local_market: Optional[LocalMarketContext]) -> Optional[str]:
    if not local_market or not local_market.order_book:
        return None
    order_book = local_market.order_book
    trade_balance = _local_trade_balance(local_market)
    if order_book.weibi is not None:
        if order_book.weibi >= 10:
            return (
                f"盘口委比 {order_book.weibi:.2f}% 偏强，"
                + (trade_balance or "买盘承接略占优")
            )
        if order_book.weibi <= -10:
            return (
                f"盘口委比 {order_book.weibi:.2f}% 偏弱，"
                + (trade_balance or "卖盘更重")
            )
    support_low, support_high = order_book.support_zone(depth=3)
    if support_low is not None and support_high is not None:
        support_text = f"买一到买三大致在 {support_low:.2f}-{support_high:.2f} 元"
        if trade_balance:
            return f"{support_text}，{trade_balance}"
        return support_text
    return trade_balance


def _local_orderbook_card(subject: Optional[str], local_market: Optional[LocalMarketContext]) -> Optional[ResultCard]:
    if not local_market or not local_market.order_book:
        return None
    order_book = local_market.order_book
    lines = [
        _format_order_book_side("买", order_book.bid_prices, order_book.bid_volumes),
        _format_order_book_side("卖", order_book.ask_prices, order_book.ask_volumes),
    ]
    if order_book.weibi is not None or order_book.weicha is not None:
        metrics = _join_parts(
            [
                f"委比 {order_book.weibi:.2f}%" if order_book.weibi is not None else None,
                f"委差 {order_book.weicha:.0f}" if order_book.weicha is not None else None,
                f"外盘 {_format_book_volume(order_book.waipan)}" if order_book.waipan is not None else None,
                f"内盘 {_format_book_volume(order_book.neipan)}" if order_book.neipan is not None else None,
            ]
        )
        if metrics:
            lines.append(metrics)
    trade_balance = _local_trade_balance(local_market)
    if trade_balance:
        lines.append(trade_balance)

    content = "\n".join(line for line in lines if line)
    if not content:
        return None

    support_low, support_high = order_book.support_zone(depth=3)
    return ResultCard(
        type=CardType.CUSTOM,
        title="同花顺盘口补充",
        content=content,
        metadata={
            "subject": subject,
            "code": order_book.code,
            "support_low": round(support_low, 2) if support_low is not None else None,
            "support_high": round(support_high, 2) if support_high is not None else None,
            "weibi": round(order_book.weibi, 2) if order_book.weibi is not None else None,
            "weicha": round(order_book.weicha, 2) if order_book.weicha is not None else None,
        },
    )


def _local_theme_card(subject: Optional[str], theme: Optional[LocalThemeSnapshot]) -> Optional[ResultCard]:
    if not theme:
        return None
    lines = [
        f"所属地域：{theme.region}" if theme.region else None,
        f"涉及概念：{'、'.join(theme.themes[:8])}" if theme.themes else None,
        f"主营业务：{theme.business}" if theme.business else None,
    ]
    content = "\n".join(line for line in lines if line)
    if not content:
        return None
    return ResultCard(
        type=CardType.CUSTOM,
        title="同花顺题材补充",
        content=content,
        metadata={
            "subject": subject,
            "code": theme.code,
            "region": theme.region,
            "themes": theme.themes[:8],
        },
    )


def _ensure_local_resolved_security(
    route: RoutePlan,
    plan: SkillPlan,
    primary_raw_row: Optional[Dict[str, Any]],
    local_market: LocalMarketContext,
):
    if local_market.resolved is not None:
        return local_market.resolved

    candidate = _extract_security_code_from_raw(primary_raw_row) or route.subject or plan.query
    resolved = local_market_skill_client.resolve_security(str(candidate or "").strip())
    if not resolved.name:
        resolved.name = _extract_security_name_from_raw(primary_raw_row) or (
            route.subject if route.subject and not _extract_security_code(route.subject) else None
        )
    local_market.resolved = resolved
    return resolved


def _extract_numeric_metric(raw: Optional[Dict[str, Any]], *contains: str) -> Optional[float]:
    if not raw:
        return None
    value = _find_value(raw, (), contains)
    return _safe_float(value)


def _extract_numeric_metric_filtered(
    raw: Optional[Dict[str, Any]],
    contains: Iterable[str],
    excludes: Iterable[str] = (),
) -> Optional[float]:
    if not raw:
        return None
    value = _find_metric_value(raw, contains, excludes)
    return _safe_float(value)


def _extract_text_metric(raw: Optional[Dict[str, Any]], *contains: str) -> Optional[str]:
    if not raw:
        return None
    value = _find_value(raw, (), contains)
    if value is None:
        return None
    if isinstance(value, list):
        parts = [str(item).strip() for item in value if str(item).strip()]
        return "、".join(parts[:4]) if parts else None
    text = str(value).strip()
    return text or None


def _extract_change_by_span(
    raw: Optional[Dict[str, Any]],
    *,
    min_days: int,
    max_days: int,
) -> Optional[float]:
    if not raw:
        return None
    candidates: List[tuple[int, float]] = []
    for key, value in raw.items():
        if "涨跌幅[" not in key or "-" not in key:
            continue
        matched = re.search(r"\[(\d{8})-(\d{8})\]", key)
        if not matched:
            continue
        try:
            started_at = datetime.strptime(matched.group(1), "%Y%m%d")
            ended_at = datetime.strptime(matched.group(2), "%Y%m%d")
        except ValueError:
            continue
        span_days = (ended_at - started_at).days
        if min_days <= span_days <= max_days:
            numeric = _safe_float(value)
            if numeric is not None:
                candidates.append((span_days, numeric))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def _extract_latest_metric_date(
    raw: Optional[Dict[str, Any]],
    *contains: str,
) -> Optional[str]:
    if not raw:
        return None
    dates: List[str] = []
    for key in raw:
        if not _metric_key_matches(key, contains):
            continue
        matched = re.search(r"\[(\d{8})\]", key)
        if matched:
            dates.append(matched.group(1))
    if not dates:
        return None
    latest = max(dates)
    return f"{latest[0:4]}-{latest[4:6]}-{latest[6:8]}"


def _extract_card_titles(cards: List[ResultCard], card_title: str, *, limit: int = 2) -> List[str]:
    titles: List[str] = []
    for card in cards:
        if card.title != card_title:
            continue
        for raw_line in card.content.splitlines():
            line = raw_line.strip()
            if line.startswith("- "):
                line = line[2:].strip()
            if not line:
                continue
            titles.append(line)
            if len(titles) >= limit:
                return titles
    return titles


def _extract_technical_snapshot(raw: Optional[Dict[str, Any]]) -> TechnicalSnapshot:
    return TechnicalSnapshot(
        close=_extract_numeric_metric(raw, "最新价", "收盘价"),
        open=_extract_numeric_metric(raw, "开盘价"),
        high=_extract_numeric_metric(raw, "最高价"),
        low=_extract_numeric_metric(raw, "最低价"),
        five_day_change=_extract_change_by_span(raw, min_days=4, max_days=8),
        twenty_day_change=_extract_change_by_span(raw, min_days=18, max_days=35),
        turnover=_extract_numeric_metric(raw, "换手率"),
        amount=_extract_numeric_metric(raw, "成交额"),
        money_flow=_extract_numeric_metric(raw, "主力资金", "资金流向"),
        volume_ratio=_extract_numeric_metric(raw, "量比"),
        amplitude=_extract_numeric_metric(raw, "振幅"),
        ma5=_extract_numeric_metric(raw, "ma5"),
        ma10=_extract_numeric_metric(raw, "ma10"),
        ma20=_extract_numeric_metric(raw, "ma20"),
        ma60=_extract_numeric_metric(raw, "ma60"),
        macd=_extract_numeric_metric(raw, "macd"),
        diff=_extract_numeric_metric(raw, "diff"),
        dea=_extract_numeric_metric(raw, "dea"),
        rsi=_extract_numeric_metric(raw, "rsi"),
        kdj=_extract_numeric_metric(raw, "kdj"),
        boll_upper=_extract_numeric_metric(raw, "boll_upper"),
        boll_mid=_extract_numeric_metric(raw, "boll_mid"),
        boll_lower=_extract_numeric_metric(raw, "boll_lower"),
        pb=_extract_numeric_metric(raw, "市净率"),
        pe=_extract_numeric_metric(raw, "市盈率"),
        roe=_extract_numeric_metric(raw, "ROE", "roe", "净资产收益率", "加权净资产收益率"),
        revenue_growth=_extract_numeric_metric(raw, "营收增速", "营业收入同比增长率", "营业总收入同比增长率"),
        profit_growth=_extract_numeric_metric(raw, "净利润增速", "归母净利润同比增长率", "净利润同比增长率"),
        operating_cash_flow=_extract_numeric_metric(raw, "经营现金流", "经营活动产生的现金流量净额"),
        revenue=_extract_numeric_metric_filtered(raw, ("营业收入",), ("同比", "增长率", "增速")),
        net_profit=_extract_numeric_metric_filtered(
            raw,
            ("归母净利润", "归属于母公司所有者的净利润"),
            ("同比", "增长率", "扣非"),
        ),
        deduct_net_profit=_extract_numeric_metric_filtered(
            raw,
            ("扣非归母净利润", "扣除非经常性损益后的归母净利润"),
        ),
        gross_margin=_extract_numeric_metric(raw, "销售毛利率", "毛利率"),
        debt_ratio=_extract_numeric_metric(raw, "资产负债率"),
    )


def _pct_distance(price: Optional[float], anchor: Optional[float]) -> Optional[float]:
    if price is None or anchor is None or not anchor:
        return None
    return (price - anchor) / anchor * 100


def _price_vs_anchor(price: Optional[float], anchor: Optional[float], label: str) -> Optional[str]:
    diff_pct = _pct_distance(price, anchor)
    if diff_pct is None:
        return None
    direction = "站上" if diff_pct >= 0 else "低于"
    return f"{direction}{label} {abs(diff_pct):.1f}%"


def _join_parts(parts: List[Optional[str]], sep: str = "，") -> str:
    return sep.join(part for part in parts if part)


def _normalize_text_for_dedupe(text: str) -> str:
    compact = " ".join(str(text or "").split()).strip()
    compact = compact.strip("，。！？；：、,.!?;: ")
    return re.sub(r"[\s，。！？；：、,.!?;:（）()“”\"'《》<>·\-]+", "", compact.lower())


def _is_near_duplicate_text(left: str, right: str) -> bool:
    normalized_left = _normalize_text_for_dedupe(left)
    normalized_right = _normalize_text_for_dedupe(right)
    if not normalized_left or not normalized_right:
        return False
    if normalized_left == normalized_right:
        return True
    shorter = min(len(normalized_left), len(normalized_right))
    longer = max(len(normalized_left), len(normalized_right))
    if shorter < 10:
        return False
    if (normalized_left in normalized_right or normalized_right in normalized_left) and shorter >= 18:
        return True
    return (
        (normalized_left in normalized_right or normalized_right in normalized_left)
        and shorter / longer >= 0.55
    )


def _dedupe_string_list(
    items: List[str],
    *,
    against: Optional[List[str]] = None,
    limit: Optional[int] = None,
) -> List[str]:
    deduped: List[str] = []
    baseline = list(against or [])
    for raw_item in items:
        item = " ".join(str(raw_item or "").split()).strip()
        if not item:
            continue
        if any(_is_near_duplicate_text(item, existing) for existing in baseline + deduped):
            continue
        deduped.append(item)
        if limit is not None and len(deduped) >= limit:
            break
    return deduped


def _normalize_structured_result_output(result: StructuredResult) -> StructuredResult:
    summary = " ".join(result.summary.split()).strip()
    facts = _dedupe_string_list(result.facts)
    judgements = _dedupe_string_list(result.judgements, against=[summary], limit=5)
    follow_ups = _dedupe_string_list(result.follow_ups, limit=3)
    return StructuredResult(
        summary=summary,
        table=result.table,
        cards=result.cards,
        facts=facts,
        judgements=judgements,
        follow_ups=follow_ups,
        sources=result.sources,
    )


def _intraday_close_bias(snapshot: TechnicalSnapshot) -> Optional[str]:
    if snapshot.high is None or snapshot.low is None or snapshot.close is None:
        return None
    span = snapshot.high - snapshot.low
    if span <= 0:
        return None
    close_ratio = (snapshot.close - snapshot.low) / span
    if close_ratio >= 0.75:
        return "收在日内高位"
    if close_ratio <= 0.25:
        return "收在日内低位"
    return "收在日内中部"


def _macd_state(snapshot: TechnicalSnapshot) -> Optional[str]:
    if snapshot.macd is None:
        return None
    if snapshot.macd > 0:
        return "MACD转为红柱"
    return "MACD仍在绿柱区"


def _rsi_state(snapshot: TechnicalSnapshot) -> Optional[str]:
    if snapshot.rsi is None:
        return None
    if snapshot.rsi <= 30:
        return f"RSI {snapshot.rsi:.1f}，接近超卖"
    if snapshot.rsi >= 70:
        return f"RSI {snapshot.rsi:.1f}，接近过热"
    return f"RSI {snapshot.rsi:.1f}"


def _volume_ratio_state(snapshot: TechnicalSnapshot) -> Optional[str]:
    if snapshot.volume_ratio is None:
        return None
    if snapshot.volume_ratio >= 1.2:
        return f"量比 {snapshot.volume_ratio:.2f}，放量"
    if snapshot.volume_ratio <= 0.85:
        return f"量比 {snapshot.volume_ratio:.2f}，偏缩量"
    return f"量比 {snapshot.volume_ratio:.2f}"


def _build_row_technical_brief(raw: Optional[Dict[str, Any]]) -> str:
    snapshot = _extract_technical_snapshot(raw)
    if all(
        value is None
        for value in (snapshot.ma5, snapshot.ma20, snapshot.macd, snapshot.rsi, snapshot.volume_ratio)
    ):
        return ""

    parts: List[Optional[str]] = []
    ma_bits = _join_parts(
        [
            _price_vs_anchor(snapshot.close, snapshot.ma5, "MA5"),
            _price_vs_anchor(snapshot.close, snapshot.ma20, "MA20"),
        ],
        "、",
    )
    if ma_bits:
        parts.append(ma_bits)
    parts.append(_macd_state(snapshot))
    parts.append(_rsi_state(snapshot))
    parts.append(_volume_ratio_state(snapshot))
    return "；".join(part for part in parts if part)


def _build_row_fundamental_brief(raw: Optional[Dict[str, Any]]) -> str:
    snapshot = _extract_technical_snapshot(raw)
    parts = [
        f"PE {snapshot.pe:.2f}" if snapshot.pe is not None else None,
        f"PB {snapshot.pb:.2f}" if snapshot.pb is not None else None,
        f"ROE {snapshot.roe:.2f}%" if snapshot.roe is not None else None,
        f"营收同比 {snapshot.revenue_growth:.2f}%" if snapshot.revenue_growth is not None else None,
        f"归母同比 {snapshot.profit_growth:.2f}%" if snapshot.profit_growth is not None else None,
        (
            f"经营现金流 {_format_money_value(snapshot.operating_cash_flow)}"
            if snapshot.operating_cash_flow is not None
            else None
        ),
    ]
    return "；".join(part for part in parts if part)


def _format_signed_pct(value: Optional[float]) -> Optional[str]:
    if value is None:
        return None
    return f"{value:+.2f}%"


def _format_pct(value: Optional[float]) -> Optional[str]:
    if value is None:
        return None
    return f"{value:.2f}%"


def _format_money_flow(value: Optional[float]) -> Optional[str]:
    if value is None:
        return None
    amount = abs(value)
    if amount >= 100000000:
        text = f"{amount / 100000000:.2f}亿"
    elif amount >= 10000:
        text = f"{amount / 10000:.2f}万"
    else:
        text = f"{amount:.0f}"
    direction = "净流入" if value >= 0 else "净流出"
    return f"{direction}{text}"


def _format_money_value(value: Optional[float]) -> Optional[str]:
    if value is None:
        return None
    amount = abs(value)
    sign = "-" if value < 0 else ""
    if amount >= 100000000:
        return f"{sign}{amount / 100000000:.2f}亿"
    if amount >= 10000:
        return f"{sign}{amount / 10000:.2f}万"
    return f"{value:.2f}"


def _format_signed_money(value: Optional[float]) -> Optional[str]:
    if value is None:
        return None
    sign = "+" if value >= 0 else "-"
    amount = abs(value)
    if amount >= 100000000:
        text = f"{amount / 100000000:.2f}亿"
    elif amount >= 10000:
        text = f"{amount / 10000:.2f}万"
    else:
        text = f"{amount:.2f}元"
    if text.endswith("元"):
        return f"{sign}{text}"
    return f"{sign}{text}"


def _format_share_count(value: int) -> str:
    return f"{value}股"


def _portfolio_context_card(
    subject: str,
    holding_context: SimTradingHoldingContext,
) -> ResultCard:
    matched = holding_context.matched_position
    lines = [holding_context.note]
    metadata: Dict[str, Any] = {
        "subject": subject,
        "opened_now": holding_context.opened_now,
        "total_positions": holding_context.total_positions,
    }
    if matched:
        lines.append(f"当前持仓：{matched.name} {_format_share_count(matched.quantity)}（可用 {_format_share_count(matched.available_quantity)}）")
        if matched.cost_price is not None:
            lines.append(f"持仓成本：{matched.cost_price:.2f} 元")
            metadata["cost_price"] = round(matched.cost_price, 2)
        if matched.market_value is not None:
            lines.append(f"持仓市值：{matched.market_value:.2f}")
            metadata["market_value"] = round(matched.market_value, 2)
        pnl_text = _format_signed_money(matched.float_profit)
        pnl_pct_text = _format_signed_pct(matched.profit_rate_pct)
        if pnl_text:
            line = f"浮盈亏：{pnl_text}"
            if pnl_pct_text:
                line += f"（{pnl_pct_text}）"
            lines.append(line)
        metadata.update(
            {
                "holding_qty": matched.quantity,
                "available_qty": matched.available_quantity,
                "code": matched.code,
            }
        )
    elif holding_context.total_positions == 0:
        lines.append(f"模拟账户当前未持有 {subject}，账户里也没有其他持仓。")
    else:
        lines.append(f"模拟账户当前未持有 {subject}。")
        lines.append(f"账户里还有 {holding_context.total_positions} 只其他持仓。")

    if holding_context.portfolio_position_pct is not None:
        lines.append(f"账户总仓位：{holding_context.portfolio_position_pct:.2f}%")
        metadata["portfolio_position_pct"] = round(holding_context.portfolio_position_pct, 2)
    if holding_context.total_assets is not None:
        lines.append(f"账户总资产：{holding_context.total_assets:.2f}")
        metadata["total_assets"] = round(holding_context.total_assets, 2)

    return ResultCard(
        type=CardType.PORTFOLIO_CONTEXT,
        title="模拟持仓上下文",
        content="\n".join(lines),
        metadata=metadata,
    )


def _format_price_zone(observe_low: Optional[float], observe_high: Optional[float]) -> Optional[str]:
    if observe_low is None or observe_high is None:
        return None
    return f"{observe_low:.2f}-{observe_high:.2f} 元"


def _build_short_horizon_line(
    snapshot: TechnicalSnapshot,
    *,
    observe_low: Optional[float],
    observe_high: Optional[float],
) -> str:
    kline_bits = _join_parts(
        [
            _intraday_close_bias(snapshot),
            _price_vs_anchor(snapshot.close, snapshot.ma5, "MA5"),
            _price_vs_anchor(snapshot.close, snapshot.ma10, "MA10"),
        ]
    )
    indicator_bits = _join_parts(
        [
            _macd_state(snapshot),
            _rsi_state(snapshot),
            _volume_ratio_state(snapshot),
            _format_money_flow(snapshot.money_flow),
        ]
    )
    price_zone_text = _format_price_zone(observe_low, observe_high)

    weakness_score = sum(
        1
        for cond in (
            snapshot.close is not None and snapshot.ma5 is not None and snapshot.close < snapshot.ma5,
            snapshot.close is not None and snapshot.ma10 is not None and snapshot.close < snapshot.ma10,
            snapshot.macd is not None and snapshot.macd < 0,
            snapshot.money_flow is not None and snapshot.money_flow < 0,
            snapshot.volume_ratio is not None and snapshot.volume_ratio < 1,
        )
        if cond
    )

    if weakness_score >= 3:
        conclusion = f"短线先看 {price_zone_text} 承接，不建议追。" if price_zone_text else "短线先观察承接，不建议追。"
    elif snapshot.money_flow is not None and snapshot.money_flow > 0 and snapshot.close is not None and snapshot.ma5 is not None and snapshot.close >= snapshot.ma5:
        conclusion = "短线可继续跟踪，但更适合轻仓试错，不适合重仓追价。"
    else:
        conclusion = "短线偏中性，等量价和承接进一步确认。"

    body = "；".join(part for part in (kline_bits, indicator_bits) if part)
    return _join_parts([body, conclusion], " ")


def _build_mid_horizon_line(snapshot: TechnicalSnapshot) -> str:
    trend_bits = _join_parts(
        [
            _price_vs_anchor(snapshot.close, snapshot.ma20, "MA20"),
            _price_vs_anchor(snapshot.close, snapshot.boll_mid, "布林中轨"),
            f"近20日 {_format_signed_pct(snapshot.twenty_day_change)}" if snapshot.twenty_day_change is not None else None,
        ]
    )
    indicator_bits = _join_parts(
        [
            _macd_state(snapshot),
            f"DIF {snapshot.diff:.3f}/DEA {snapshot.dea:.3f}" if snapshot.diff is not None and snapshot.dea is not None else None,
        ]
    )

    if (
        snapshot.close is not None
        and snapshot.ma20 is not None
        and snapshot.close >= snapshot.ma20
        and snapshot.macd is not None
        and snapshot.macd >= 0
    ):
        conclusion = "中线趋势在修复，可以继续跟踪回踩后的延续。"
    elif (
        snapshot.close is not None
        and snapshot.ma20 is not None
        and snapshot.close < snapshot.ma20
    ):
        conclusion = "中线趋势还没修复，先看能否重新站回 MA20。"
    else:
        conclusion = "中线先看趋势确认，不要只按一天涨跌做结论。"

    body = "；".join(part for part in (trend_bits, indicator_bits) if part)
    return _join_parts([body, conclusion], " ")


def _build_long_horizon_line(
    snapshot: TechnicalSnapshot,
    *,
    industry: Optional[str],
    concept: Optional[str],
) -> str:
    long_bits = _join_parts(
        [
            _price_vs_anchor(snapshot.close, snapshot.ma60, "MA60"),
            f"市盈率 {snapshot.pe:.2f}" if snapshot.pe is not None else None,
            f"市净率 {snapshot.pb:.2f}" if snapshot.pb is not None else None,
            f"ROE {snapshot.roe:.2f}%" if snapshot.roe is not None else None,
            f"营收增速 {snapshot.revenue_growth:.2f}%" if snapshot.revenue_growth is not None else None,
            f"净利润增速 {snapshot.profit_growth:.2f}%" if snapshot.profit_growth is not None else None,
            (
                f"经营现金流 {_format_money_value(snapshot.operating_cash_flow)}"
                if snapshot.operating_cash_flow is not None
                else None
            ),
            f"资产负债率 {snapshot.debt_ratio:.2f}%" if snapshot.debt_ratio is not None else None,
        ]
    )
    industry_hint = industry or concept
    if snapshot.operating_cash_flow is not None and snapshot.operating_cash_flow < 0:
        conclusion = "长线先警惕经营现金流承压，基本面验证要放在技术反弹前面。"
    elif snapshot.close is not None and snapshot.ma60 is not None and snapshot.close < snapshot.ma60:
        conclusion = "长线仍没转强，更适合作为跟踪标的，别只按题材冲动加仓。"
    elif snapshot.roe is not None or snapshot.revenue_growth is not None or snapshot.profit_growth is not None:
        conclusion = "长线可以继续看基本面验证，但要把行业景气和估值一起核对。"
    else:
        conclusion = "长线角度还缺更完整财务验证，先别把短线波动硬解释成长逻辑。"
    if industry_hint:
        conclusion += f" 行业/题材上主要看 {industry_hint}。"

    return _join_parts(["；".join(part for part in (long_bits,) if part), conclusion], " ")


def _build_fundamental_brief(
    snapshot: TechnicalSnapshot,
    *,
    report_period: Optional[str],
) -> Optional[str]:
    lines = [
        f"最新财报期 {report_period}" if report_period else None,
        (
            f"营收 { _format_money_value(snapshot.revenue) } / 同比 {snapshot.revenue_growth:.2f}%"
            if snapshot.revenue is not None and snapshot.revenue_growth is not None
            else None
        ),
        (
            f"归母净利润 { _format_money_value(snapshot.net_profit) } / 同比 {snapshot.profit_growth:.2f}%"
            if snapshot.net_profit is not None and snapshot.profit_growth is not None
            else None
        ),
        f"ROE {snapshot.roe:.2f}%" if snapshot.roe is not None else None,
        (
            f"经营现金流 { _format_money_value(snapshot.operating_cash_flow) }"
            if snapshot.operating_cash_flow is not None
            else None
        ),
    ]
    text = "；".join(line for line in lines if line)
    return text or None


def _build_fundamental_judgement(snapshot: TechnicalSnapshot) -> Optional[str]:
    if (
        snapshot.roe is not None
        and snapshot.profit_growth is not None
        and snapshot.operating_cash_flow is not None
        and snapshot.roe >= 8
        and snapshot.profit_growth >= 15
        and snapshot.operating_cash_flow > 0
    ):
        return "财报端表现不弱，盈利增速和现金流能支撑中长期跟踪，但仍要看估值和行业景气。"
    if snapshot.operating_cash_flow is not None and snapshot.operating_cash_flow < 0:
        return "财报端最大的约束在经营现金流，哪怕短线反弹，也要防止基本面跟不上。"
    if snapshot.debt_ratio is not None and snapshot.debt_ratio >= 70:
        return "资产负债率偏高，做中长线判断时要把财务杠杆风险一起算进去。"
    if snapshot.roe is not None or snapshot.revenue_growth is not None or snapshot.profit_growth is not None:
        return "财报端至少能给出盈利和增速锚点，后续要继续核对利润兑现和现金流质量。"
    return None


def _fundamental_card(subject: str, raw: Optional[Dict[str, Any]]) -> Optional[ResultCard]:
    if not raw:
        return None
    snapshot = _extract_technical_snapshot(raw)
    report_period = _extract_latest_metric_date(
        raw,
        "净资产收益率",
        "营业收入",
        "归母净利润",
        "经营活动产生的现金流量净额",
        "销售毛利率",
        "资产负债率",
    )
    industry = _extract_text_metric(raw, "所属同花顺行业", "所属行业")
    concept = _extract_text_metric(raw, "所属概念", "涉及概念")
    listing_board = _extract_text_metric(raw, "上市板块")
    listing_place = _extract_text_metric(raw, "上市地点")

    lines = [
        f"最新财报期：{report_period}" if report_period else None,
        _join_parts(
            [
                f"上市板块：{listing_board}" if listing_board else None,
                f"上市地点：{listing_place}" if listing_place else None,
            ]
        ),
        _join_parts(
            [
                f"所属行业：{industry}" if industry else None,
                f"核心概念：{concept}" if concept else None,
            ]
        ),
        _join_parts(
            [
                f"营业收入：{_format_money_value(snapshot.revenue)}" if snapshot.revenue is not None else None,
                f"同比：{snapshot.revenue_growth:.2f}%" if snapshot.revenue_growth is not None else None,
            ]
        ),
        _join_parts(
            [
                f"归母净利润：{_format_money_value(snapshot.net_profit)}" if snapshot.net_profit is not None else None,
                f"同比：{snapshot.profit_growth:.2f}%" if snapshot.profit_growth is not None else None,
            ]
        ),
        _join_parts(
            [
                (
                    f"扣非归母净利润：{_format_money_value(snapshot.deduct_net_profit)}"
                    if snapshot.deduct_net_profit is not None
                    else None
                ),
                (
                    f"经营现金流：{_format_money_value(snapshot.operating_cash_flow)}"
                    if snapshot.operating_cash_flow is not None
                    else None
                ),
            ]
        ),
        _join_parts(
            [
                f"ROE：{snapshot.roe:.2f}%" if snapshot.roe is not None else None,
                f"毛利率：{snapshot.gross_margin:.2f}%" if snapshot.gross_margin is not None else None,
                f"资产负债率：{snapshot.debt_ratio:.2f}%" if snapshot.debt_ratio is not None else None,
            ]
        ),
        _join_parts(
            [
                f"PE(TTM)：{snapshot.pe:.2f}" if snapshot.pe is not None else None,
                f"PB：{snapshot.pb:.2f}" if snapshot.pb is not None else None,
            ]
        ),
    ]
    content = "\n".join(line for line in lines if line)
    if not content:
        return None

    metadata: Dict[str, Any] = {
        "subject": subject,
        "report_period": report_period,
        "listing_board": listing_board,
        "listing_place": listing_place,
        "industry": industry,
        "concept": concept,
        "pe": snapshot.pe,
        "pb": snapshot.pb,
        "roe": snapshot.roe,
        "revenue_growth": snapshot.revenue_growth,
        "profit_growth": snapshot.profit_growth,
        "operating_cash_flow": snapshot.operating_cash_flow,
        "revenue": snapshot.revenue,
        "net_profit": snapshot.net_profit,
        "deduct_net_profit": snapshot.deduct_net_profit,
        "gross_margin": snapshot.gross_margin,
        "debt_ratio": snapshot.debt_ratio,
    }
    metadata = {key: value for key, value in metadata.items() if value is not None}

    return ResultCard(
        type=CardType.CUSTOM,
        title="财报与基本面",
        content=content,
        metadata=metadata,
    )


def _multi_horizon_analysis_card(
    route: RoutePlan,
    row: Dict[str, Any],
    raw: Optional[Dict[str, Any]],
    *,
    observe_low: Optional[float],
    observe_high: Optional[float],
) -> ResultCard:
    snapshot = _extract_technical_snapshot(raw)
    industry = _extract_text_metric(raw, "所属同花顺行业", "所属行业")
    concept = _extract_text_metric(raw, "所属概念", "涉及概念")
    report_period = _extract_latest_metric_date(
        raw,
        "净资产收益率",
        "营业收入",
        "归母净利润",
        "经营活动产生的现金流量净额",
        "销售毛利率",
        "资产负债率",
    )
    listing_board = _extract_text_metric(raw, "上市板块")
    listing_place = _extract_text_metric(raw, "上市地点")

    content = "\n".join(
        [
            f"短线：{_build_short_horizon_line(snapshot, observe_low=observe_low, observe_high=observe_high)}",
            f"中线：{_build_mid_horizon_line(snapshot)}",
            f"长线：{_build_long_horizon_line(snapshot, industry=industry, concept=concept)}",
        ]
    )

    metadata: Dict[str, Any] = {
        "subject": route.subject or row.get("名称"),
        "close": snapshot.close,
        "open": snapshot.open,
        "high": snapshot.high,
        "low": snapshot.low,
        "five_day_change": snapshot.five_day_change,
        "twenty_day_change": snapshot.twenty_day_change,
        "turnover": snapshot.turnover,
        "amount": snapshot.amount,
        "money_flow": snapshot.money_flow,
        "volume_ratio": snapshot.volume_ratio,
        "amplitude": snapshot.amplitude,
        "ma5": snapshot.ma5,
        "ma10": snapshot.ma10,
        "ma20": snapshot.ma20,
        "ma60": snapshot.ma60,
        "macd": snapshot.macd,
        "diff": snapshot.diff,
        "dea": snapshot.dea,
        "rsi": snapshot.rsi,
        "kdj": snapshot.kdj,
        "boll_upper": snapshot.boll_upper,
        "boll_mid": snapshot.boll_mid,
        "boll_lower": snapshot.boll_lower,
        "pb": snapshot.pb,
        "pe": snapshot.pe,
        "roe": snapshot.roe,
        "revenue_growth": snapshot.revenue_growth,
        "profit_growth": snapshot.profit_growth,
        "operating_cash_flow": snapshot.operating_cash_flow,
        "revenue": snapshot.revenue,
        "net_profit": snapshot.net_profit,
        "deduct_net_profit": snapshot.deduct_net_profit,
        "gross_margin": snapshot.gross_margin,
        "debt_ratio": snapshot.debt_ratio,
        "report_period": report_period,
        "listing_board": listing_board,
        "listing_place": listing_place,
        "industry": industry,
        "concept": concept,
    }
    metadata = {key: value for key, value in metadata.items() if value is not None}

    return ResultCard(
        type=CardType.MULTI_HORIZON_ANALYSIS,
        title="三周期分析",
        content=content,
        metadata=metadata,
    )


def _single_security_verdict(mode: ChatMode, change: Optional[float], money_flow: Optional[float]) -> str:
    if mode == ChatMode.SHORT_TERM:
        if change is not None and change >= 7:
            return "不适合当下追高，更适合等分歧后的承接"
        if change is not None and change <= -3:
            return "先以观察为主，等止跌信号更稳"
        if money_flow is not None and money_flow > 0:
            return "可以轻仓跟踪，但前提是量能和承接继续维持"
        return "更偏向观察，不建议仓促下手"
    if mode == ChatMode.SWING:
        if money_flow is not None and money_flow > 0:
            return "更适合作为波段跟踪标的"
        return "暂时更适合继续观察趋势是否修复"
    if money_flow is not None and money_flow > 0:
        return "可以继续做中线跟踪，但还要核对财务和行业景气"
    return "结论偏中性，建议先补财务和行业验证"


def _single_security_summary(
    route: RoutePlan,
    row: Dict[str, Any],
    raw: Optional[Dict[str, Any]],
    cards: List[ResultCard],
    holding_context: Optional[SimTradingHoldingContext] = None,
    local_market: Optional[LocalMarketContext] = None,
) -> tuple[str, List[str], List[str], List[str], List[ResultCard]]:
    name = str(row.get("名称") or route.subject or "该标的")
    latest = row.get("最新价", "-")
    latest_float = _safe_float(latest)
    change_text = str(row.get("涨跌幅", "-"))
    change = _safe_float(change_text.replace("%", ""))
    snapshot = _extract_technical_snapshot(raw)
    turnover = snapshot.turnover
    money_flow = snapshot.money_flow
    money_flow_text = _format_money_flow(snapshot.money_flow)
    industry = _extract_text_metric(raw, "所属同花顺行业", "所属行业")
    concept = _extract_text_metric(raw, "所属概念", "涉及概念")
    listing_board = _extract_text_metric(raw, "上市板块")
    listing_place = _extract_text_metric(raw, "上市地点")
    report_period = _extract_latest_metric_date(
        raw,
        "净资产收益率",
        "营业收入",
        "归母净利润",
        "经营活动产生的现金流量净额",
        "销售毛利率",
        "资产负债率",
    )
    region = _extract_text_metric(raw, "所属地域")
    business = _extract_text_metric(raw, "主营业务")
    five_day_change = snapshot.five_day_change
    twenty_day_change = snapshot.twenty_day_change
    news_titles = _extract_card_titles(cards, "新闻搜索补充")
    announcement_titles = _extract_card_titles(cards, "公告搜索补充")
    verdict = _single_security_verdict(route.mode, change, money_flow)
    holding_position = holding_context.matched_position if holding_context else None
    action_card = _single_security_action_card(
        route,
        row,
        raw,
        holding_context=holding_context,
        local_market=local_market,
    )
    observe_low = action_card.metadata.get("observe_low")
    observe_high = action_card.metadata.get("observe_high")
    stop_price = action_card.metadata.get("stop_price")
    price_zone_text = _format_price_zone(observe_low, observe_high) or "更低的承接区间"
    catalyst_hint = news_titles[0] if news_titles else announcement_titles[0] if announcement_titles else None
    orderbook_bias = _local_orderbook_bias(local_market)
    short_horizon_line = _build_short_horizon_line(snapshot, observe_low=observe_low, observe_high=observe_high)
    mid_horizon_line = _build_mid_horizon_line(snapshot)
    long_horizon_line = _build_long_horizon_line(snapshot, industry=industry, concept=concept)
    fundamental_brief = _build_fundamental_brief(snapshot, report_period=report_period)
    fundamental_judgement = _build_fundamental_judgement(snapshot)
    listing_brief = _join_parts(
        [
            f"上市板块 {listing_board}" if listing_board else None,
            f"上市地点 {listing_place}" if listing_place else None,
            f"所属行业 {industry}" if industry else None,
        ]
    )
    horizon_card = _multi_horizon_analysis_card(
        route,
        row,
        raw,
        observe_low=observe_low if isinstance(observe_low, (int, float)) else None,
        observe_high=observe_high if isinstance(observe_high, (int, float)) else None,
    )
    finance_card = _fundamental_card(route.subject or name, raw)

    if route.holding_context_focus and holding_position:
        cost_text = _format_price(holding_position.cost_price)
        pnl_text = _format_signed_money(holding_position.float_profit)
        pnl_pct_text = _format_signed_pct(holding_position.profit_rate_pct)
        holding_bits = [f"你模拟账户里当前持有{name} {_format_share_count(holding_position.quantity)}"]
        if holding_position.cost_price is not None:
            holding_bits.append(f"成本 {cost_text} 元")
        if pnl_text:
            pnl_part = f"浮盈亏 {pnl_text}"
            if pnl_pct_text:
                pnl_part += f"（{pnl_pct_text}）"
            holding_bits.append(pnl_part)
        market_bits = [f"现价 {latest}", f"今日 {change_text}"]
        if money_flow_text:
            market_bits.append(f"主力资金 {money_flow_text}")
        summary = "，".join(holding_bits) + "；" + "，".join(market_bits[:3]) + "。"
        if change is not None and change < 0:
            summary += f" 今天更偏向持仓观察，不建议逆势加仓，先看 {price_zone_text} 承接。"
        else:
            summary += f" 先看 {price_zone_text} 一带能否稳住，再决定继续拿还是做加减仓。"
        ma20_hint = _price_vs_anchor(snapshot.close, snapshot.ma20, "MA20")
        ma60_hint = _price_vs_anchor(snapshot.close, snapshot.ma60, "MA60")
        if ma20_hint or ma60_hint:
            summary += f" 中线看 {ma20_hint or '趋势修复'}，长线看 {ma60_hint or '基本面验证'}。"
        if listing_brief:
            summary += f" 归属上看，{listing_brief}。"
        if fundamental_brief:
            summary += f" 财报上看，{fundamental_brief}。"
        if catalyst_hint:
            summary += f" 催化上先盯「{catalyst_hint}」。"
    elif route.holding_context_focus:
        if holding_context is None:
            summary = f"这轮没成功读到你的模拟持仓，只能先按个股快照给出处理建议。"
        elif holding_context.total_positions == 0:
            if holding_context.opened_now:
                summary = f"已自动创建模拟账户，当前还没持有{name}，这轮先按未持仓视角判断。"
            else:
                summary = f"模拟账户当前空仓，未持有{name}，这轮先按未持仓视角判断。"
        else:
            count_text = holding_context.total_positions if holding_context else 0
            summary = f"模拟账户当前未持有{name}"
            if count_text:
                summary += f"，但账户里还有 {count_text} 只其他股票"
            summary += "；这轮先按未持仓视角处理。"
        summary += f" 现价 {latest}、今日涨跌幅 {change_text}。"
        if money_flow_text:
            summary += f" 眼下主力资金 {money_flow_text}。"
        if observe_low and observe_high:
            summary += f" 更适合等 {price_zone_text} 一带承接确认后再看。"
        summary += f" 短线看 {short_horizon_line} 中线看 {mid_horizon_line}"
        if listing_brief:
            summary += f" 归属上看，{listing_brief}。"
        if fundamental_brief:
            summary += f" 财报上看，{fundamental_brief}。"
        if catalyst_hint:
            summary += f" 催化上先盯「{catalyst_hint}」。"
    elif route.entry_price_focus and observe_low and observe_high and stop_price:
        if route.mode == ChatMode.SHORT_TERM:
            summary = (
                f"{name} 短线不建议在 {latest} 直接追，优先等 {observe_low:.2f}-{observe_high:.2f} 元区间承接稳定再看。"
                f"跌破 {stop_price:.2f} 元，这个买点就先失效。"
            )
        elif route.mode == ChatMode.SWING:
            summary = (
                f"{name} 更适合等 {observe_low:.2f}-{observe_high:.2f} 元区间的回踩确认，"
                f"不建议在 {latest} 附近直接追。失效位参考 {stop_price:.2f} 元。"
            )
        else:
            summary = (
                f"{name} 中线更适合分批看 {observe_low:.2f}-{observe_high:.2f} 元区间，"
                f"不建议单笔追高到 {latest}。失效位参考 {stop_price:.2f} 元。"
            )
        summary += f" 从技术面看，{short_horizon_line} 中线看 {mid_horizon_line} 长线看 {long_horizon_line}"
        if money_flow_text:
            summary += f" 眼下资金侧还是 {money_flow_text}。"
        if listing_brief:
            summary += f" 归属上看，{listing_brief}。"
        if fundamental_brief:
            summary += f" 财报上看，{fundamental_brief}。"
    else:
        summary = (
            f"{name} 当前更偏向“{verdict}”，现价 {latest}、今日涨跌幅 {change_text}。"
            f" 短线看 {short_horizon_line} 中线看 {mid_horizon_line} 长线看 {long_horizon_line}"
        )
        if listing_brief:
            summary += f" 归属上看，{listing_brief}。"
        if fundamental_brief:
            summary += f" 财报上看，{fundamental_brief}。"
        if catalyst_hint:
            summary += f" 催化上先盯「{catalyst_hint}」是不是实质利好。"
    if orderbook_bias:
        summary += f" 盘口上{orderbook_bias}。"

    facts = [f"{name} 当前价格 {latest}，今日涨跌幅 {change_text}。"]
    if route.holding_context_focus and holding_context:
        facts.append("模拟持仓上下文来自同花顺问财模拟炒股服务。")
        if holding_position:
            facts.append(
                f"模拟账户当前持有 {name} {_format_share_count(holding_position.quantity)}，"
                f"可用数量 {_format_share_count(holding_position.available_quantity)}。"
            )
            if holding_position.cost_price is not None:
                facts.append(f"模拟持仓成本约 {holding_position.cost_price:.2f} 元。")
            pnl_text = _format_signed_money(holding_position.float_profit)
            pnl_pct_text = _format_signed_pct(holding_position.profit_rate_pct)
            if pnl_text:
                pnl_line = f"当前模拟仓浮盈亏 {pnl_text}"
                if pnl_pct_text:
                    pnl_line += f"，收益率 {pnl_pct_text}"
                pnl_line += "。"
                facts.append(pnl_line)
        elif holding_context.total_positions == 0:
            facts.append("模拟账户当前没有任何持仓。")
        else:
            facts.append(f"模拟账户当前未持有 {name}，但还持有 {holding_context.total_positions} 只其他股票。")
        if holding_context.portfolio_position_pct is not None:
            facts.append(f"模拟账户总仓位约 {holding_context.portfolio_position_pct:.2f}%。")
        if holding_context.total_assets is not None:
            facts.append(f"模拟账户总资产约 {holding_context.total_assets:.2f}。")
    if turnover is not None:
        facts.append(f"当前换手率约 {turnover:.2f}%，说明市场交易活跃度已被纳入观察。")
    if money_flow_text:
        facts.append(f"主力资金口径当前为 {money_flow_text}。")
    if local_market and local_market.realhead and local_market.realhead.update_time:
        facts.append(f"同花顺实时行情更新时间：{local_market.realhead.update_time}。")
    if orderbook_bias:
        facts.append(f"盘口补充：{orderbook_bias}。")
    if five_day_change is not None and route.mode != ChatMode.MID_TERM_VALUE:
        trend_bits = [f"近5日 {_format_signed_pct(five_day_change)}"]
        if twenty_day_change is not None:
            trend_bits.append(f"近20日 {_format_signed_pct(twenty_day_change)}")
        facts.append(f"{name} 近期趋势表现：{'，'.join(trend_bits)}。")
    kline_bits = _join_parts(
        [
            f"日K开 {snapshot.open:.2f}" if snapshot.open is not None else None,
            f"高 {snapshot.high:.2f}" if snapshot.high is not None else None,
            f"低 {snapshot.low:.2f}" if snapshot.low is not None else None,
            f"收 {snapshot.close:.2f}" if snapshot.close is not None else None,
            _intraday_close_bias(snapshot),
        ]
    )
    if kline_bits:
        facts.append(f"{name} 今日 K 线：{kline_bits}。")
    indicator_bits = _join_parts(
        [
            f"MA5 {snapshot.ma5:.2f}" if snapshot.ma5 is not None else None,
            f"MA20 {snapshot.ma20:.2f}" if snapshot.ma20 is not None else None,
            f"MA60 {snapshot.ma60:.2f}" if snapshot.ma60 is not None else None,
            f"MACD {snapshot.macd:.3f}" if snapshot.macd is not None else None,
            f"RSI {snapshot.rsi:.2f}" if snapshot.rsi is not None else None,
            f"KDJ {snapshot.kdj:.2f}" if snapshot.kdj is not None else None,
            f"布林中轨 {snapshot.boll_mid:.2f}" if snapshot.boll_mid is not None else None,
            f"量比 {snapshot.volume_ratio:.2f}" if snapshot.volume_ratio is not None else None,
        ]
    )
    if indicator_bits:
        facts.append(f"{name} 技术指标：{indicator_bits}。")
    if listing_board or listing_place:
        listing_bits = _join_parts(
            [
                f"上市板块 {listing_board}" if listing_board else None,
                f"上市地点 {listing_place}" if listing_place else None,
            ]
        )
        facts.append(f"{name} {listing_bits}。")
    if industry or concept:
        industry_text = f"所属行业 {industry}" if industry else ""
        concept_text = f"所属概念 {concept}" if concept else ""
        joiner = "；" if industry_text and concept_text else ""
        facts.append(f"{name} {industry_text}{joiner}{concept_text}。".strip())
    if report_period and (
        snapshot.revenue is not None
        or snapshot.net_profit is not None
        or snapshot.operating_cash_flow is not None
    ):
        finance_bits = _join_parts(
            [
                f"营收 {_format_money_value(snapshot.revenue)}" if snapshot.revenue is not None else None,
                (
                    f"营收同比 {snapshot.revenue_growth:.2f}%"
                    if snapshot.revenue_growth is not None
                    else None
                ),
                f"归母净利润 {_format_money_value(snapshot.net_profit)}" if snapshot.net_profit is not None else None,
                (
                    f"归母同比 {snapshot.profit_growth:.2f}%"
                    if snapshot.profit_growth is not None
                    else None
                ),
                (
                    f"经营现金流 {_format_money_value(snapshot.operating_cash_flow)}"
                    if snapshot.operating_cash_flow is not None
                    else None
                ),
            ]
        )
        facts.append(f"{name} 最新财报期 {report_period}：{finance_bits}。")
    quality_bits = _join_parts(
        [
            f"ROE {snapshot.roe:.2f}%" if snapshot.roe is not None else None,
            f"毛利率 {snapshot.gross_margin:.2f}%" if snapshot.gross_margin is not None else None,
            f"资产负债率 {snapshot.debt_ratio:.2f}%" if snapshot.debt_ratio is not None else None,
            f"PE(TTM) {snapshot.pe:.2f}" if snapshot.pe is not None else None,
            f"PB {snapshot.pb:.2f}" if snapshot.pb is not None else None,
        ]
    )
    if quality_bits:
        facts.append(f"{name} 基本面指标：{quality_bits}。")
    if region:
        facts.append(f"{name} 所属地域为 {region}。")
    if business:
        facts.append(f"{name} 主营业务摘要：{business}。")
    if catalyst_hint:
        facts.append(f"近期可跟踪的催化线索：{catalyst_hint}。")
    if announcement_titles:
        facts.append(f"公告侧最近的重点是：{announcement_titles[0]}。")

    judgements = []
    if route.holding_context_focus and holding_position:
        if latest_float is not None and holding_position.cost_price is not None:
            if latest_float < holding_position.cost_price:
                judgements.append(
                    f"当前价格已经回到你的模拟成本下方，处理上更该先守观察位，而不是情绪化补仓。"
                )
            else:
                judgements.append(
                    f"当前价格仍在你的模拟成本上方，先看承接是否成立，再决定继续拿还是做保护利润。"
                )
        else:
            judgements.append("既然已经有仓，今天更重要的是处理持仓节奏，而不是重新追买。")
        if holding_position.available_quantity < holding_position.quantity:
            judgements.append("可用数量低于总持仓，说明部分仓位可能是当日新开，处理上要注意可卖数量限制。")
        if holding_context.portfolio_position_pct is not None and holding_context.portfolio_position_pct >= 70:
            judgements.append("模拟账户整体仓位已经不低，若继续走弱，优先考虑控仓而不是加仓。")
    elif route.mode == ChatMode.SHORT_TERM:
        judgements.append(short_horizon_line)
        if five_day_change is not None and five_day_change > 5 and change is not None and change < 0:
            judgements.append(f"如果前面已经有一段拉升，今天更像强势股分歧，后手追价容易被动。")
        if concept:
            judgements.append(f"{name} 还会受 {concept} 题材情绪影响，最好结合板块强弱一起看。")
    elif route.mode == ChatMode.SWING:
        judgements.append(mid_horizon_line)
        if twenty_day_change is not None:
            judgements.append(f"近20日 {_format_signed_pct(twenty_day_change)}，说明趋势判断要结合回踩后的延续性。")
    else:
        judgements.append(long_horizon_line)

    if fundamental_judgement:
        judgements.append(fundamental_judgement)

    if catalyst_hint:
        judgements.append(f"近期催化可以看「{catalyst_hint}」，但别只按标题交易，先确认是不是实质变化。")
    if orderbook_bias:
        judgements.append(f"短线执行上要盯盘口变化：{orderbook_bias}。")
    judgements.append(f"当前核心风险是：{row.get('风险点', '需继续核对风险点')}。")
    judgements = judgements[:5]

    if route.holding_context_focus and holding_position:
        cost_text = _format_price(holding_position.cost_price)
        follow_ups = [
            f"按 {cost_text} 元成本和 {stop_price:.2f} 元失效位给我拆减仓预案" if stop_price else f"按 {cost_text} 元成本给我拆减仓预案",
            f"如果 {name} 回踩到 {price_zone_text}，加仓条件是什么",
            f"结合我当前模拟仓位，给我{name}的持仓节奏建议",
        ]
    elif route.mode == ChatMode.SHORT_TERM:
        follow_ups = [
            f"按 MA5、MA20、MA60 给我拆 {name} 的三周期计划",
            f"补充{name}最新财报和板块归属",
            f"看看{name}主力资金什么时候算转强",
        ]
    elif route.mode == ChatMode.SWING:
        follow_ups = [f"补充{name}行业、板块和趋势位置", f"看看{name}重新站回 MA20 需要什么条件", f"给我{name}波段买卖计划"]
    else:
        follow_ups = [f"补充{name}最新财报", f"看看{name}估值、ROE和现金流", f"按长线视角给我{name}跟踪清单"]

    leading_cards = [action_card, horizon_card]
    if finance_card:
        leading_cards.append(finance_card)
    orderbook_card = _local_orderbook_card(route.subject or name, local_market)
    theme_card = _local_theme_card(route.subject or name, local_market.theme if local_market else None)
    if orderbook_card:
        leading_cards.append(orderbook_card)
    if theme_card:
        leading_cards.append(theme_card)
    return summary, facts, judgements, follow_ups, leading_cards


def _format_price(value: Optional[float]) -> str:
    if value is None:
        return "-"
    return f"{value:.2f}"


def _single_security_action_card(
    route: RoutePlan,
    row: Dict[str, Any],
    raw: Optional[Dict[str, Any]],
    *,
    holding_context: Optional[SimTradingHoldingContext] = None,
    local_market: Optional[LocalMarketContext] = None,
) -> ResultCard:
    latest = _safe_float(row.get("最新价"))
    change = _safe_float(str(row.get("涨跌幅", "")).replace("%", ""))
    snapshot = _extract_technical_snapshot(raw)
    prev_close = _extract_numeric_metric(raw, "收盘价")
    money_flow = snapshot.money_flow
    holding_position = holding_context.matched_position if holding_context else None

    if latest is None:
        return ResultCard(
            type=CardType.OPERATION_GUIDANCE,
            title="操作建议卡",
            content="现在能不能追：先观察。\n更好的买点：等更清晰的量价和资金信号。\n失效条件：逻辑无法被数据验证。\n止损/观察位：先看下一轮行情确认。",
        )

    observe_high = latest * 0.99
    observe_low = latest * (0.97 if route.mode == ChatMode.SHORT_TERM else 0.96)
    stop_price = latest * (0.95 if route.mode == ChatMode.SHORT_TERM else 0.93)
    support_low, support_high = _local_support_zone(local_market)
    if support_low is not None and support_high is not None:
        observe_low = support_low
        observe_high = min(support_high, latest * 1.005)
        stop_ratio = 0.985 if route.mode == ChatMode.SHORT_TERM else 0.97
        stop_price = min(stop_price, observe_low * stop_ratio)
        if observe_low > observe_high:
            observe_low = observe_high

    if prev_close is not None and route.mode == ChatMode.SHORT_TERM:
        observe_high = min(observe_high, max(prev_close, latest * 0.985))
        observe_low = min(observe_low, observe_high)

    book_bias = _local_orderbook_bias(local_market)

    if route.holding_context_focus and holding_position:
        holding_qty = _format_share_count(holding_position.quantity)
        if change is not None and change <= -2:
            chase = f"你当前模拟持有 {holding_qty}，今天更偏向持仓观察，不建议逆势继续加仓。"
        elif money_flow is not None and money_flow > 0 and snapshot.close is not None and snapshot.ma5 is not None and snapshot.close >= snapshot.ma5:
            chase = f"你当前模拟持有 {holding_qty}，可以继续拿，但新加仓别急，先看承接是否持续。"
        else:
            chase = f"你当前模拟持有 {holding_qty}，先按计划拿着看承接，别把持仓问题做成追涨问题。"
        better = (
            f"更好的买点：若要继续加仓，优先等回踩 {_format_price(observe_low)}-{_format_price(observe_high)} 元区间有承接，"
            "而不是在情绪波动时硬加。"
        )
        invalidation = f"失效条件：跌破 {_format_price(stop_price)} 元，或主力资金持续转弱并且 K 线继续压在短期均线下方。"
        stop_watch = (
            f"止损/观察位：先看 {_format_price(observe_high)} 元附近能否稳住；若失守 {_format_price(stop_price)} 元，"
            "持仓优先减到更舒服的仓位。"
        )
    elif route.mode == ChatMode.SHORT_TERM:
        short_ma_hint = _price_vs_anchor(snapshot.close, snapshot.ma5, "MA5")
        if change is not None and change >= 7:
            chase = "不建议现在直接追，位置已经偏热。"
            better = f"更好的买点：等回踩 {_format_price(observe_low)}-{_format_price(observe_high)} 元区间、且承接没有明显转弱时再看。"
        elif money_flow is not None and money_flow > 0 and snapshot.close is not None and snapshot.ma5 is not None and snapshot.close >= snapshot.ma5:
            chase = "可以轻仓跟踪，但不适合重仓追价。"
            better = f"更好的买点：更理想的是靠近 {_format_price(observe_high)} 元附近承接稳定时再介入。"
        else:
            chase = "先观察更稳，别急着下手。"
        better = f"更好的买点：等重新走强或回踩 {_format_price(observe_low)} 元附近出现放量承接。"
        if short_ma_hint:
            chase += f" 当前 K 线 {short_ma_hint}。"
        invalidation = f"失效条件：跌破 {_format_price(stop_price)} 元，或主力资金转弱并出现冲高回落，且 MACD 没有修复。"
        stop_watch = f"止损/观察位：观察 {_format_price(observe_high)} 元附近承接，止损参考 {_format_price(stop_price)} 元。"
    elif route.mode == ChatMode.SWING:
        ma20_hint = _price_vs_anchor(snapshot.close, snapshot.ma20, "MA20")
        chase = "不建议只看今天一根K线追入，先确认趋势延续。"
        if ma20_hint:
            chase += f" 当前价格 {ma20_hint}。"
        better = f"更好的买点：回踩 {_format_price(observe_low)}-{_format_price(observe_high)} 元区间守住时，或重新站回 MA20 后再分批。"
        invalidation = f"失效条件：跌破 {_format_price(stop_price)} 元且资金持续走弱，或布林中轨继续失守。"
        stop_watch = f"止损/观察位：先看 {_format_price(observe_high)} 元附近能否稳住，止损参考 {_format_price(stop_price)} 元。"
    else:
        ma60_hint = _price_vs_anchor(snapshot.close, snapshot.ma60, "MA60")
        chase = "中线更适合分批跟踪，不要把单日波动当成唯一买点。"
        if ma60_hint:
            chase += f" 当前价格 {ma60_hint}。"
        better = f"更好的买点：等财务或行业催化确认后分批布局，价格上更理想是 {_format_price(observe_low)}-{_format_price(observe_high)} 元附近。"
        invalidation = f"失效条件：跌破 {_format_price(stop_price)} 元且基本面逻辑被破坏，或长周期均线继续走弱。"
        stop_watch = f"止损/观察位：观察 {_format_price(observe_high)} 元附近的企稳情况，止损参考 {_format_price(stop_price)} 元。"

    if book_bias:
        chase += f" 盘口上{book_bias}。"

    content = "\n".join(
        [
            f"现在能不能追：{chase}",
            better,
            invalidation,
            stop_watch,
        ]
    )

    return ResultCard(
        type=CardType.OPERATION_GUIDANCE,
        title="操作建议卡",
        content=content,
        metadata={
            "subject": route.subject,
            "observe_low": round(observe_low, 2),
            "observe_high": round(observe_high, 2),
            "stop_price": round(stop_price, 2),
        },
    )


def _card_type_value(card: ResultCard) -> str:
    return card.type.value if isinstance(card.type, CardType) else str(card.type)


def _apply_gpt_enhancement(
    route: RoutePlan,
    result: StructuredResult,
    *,
    user_message: str,
    profile: UserProfile,
) -> StructuredResult:
    if not openai_analysis_client.enabled or not profile.gpt_enhancement_enabled:
        return result

    reasoning_effort = _resolve_gpt_reasoning_effort(route, user_message, profile)

    try:
        enhancement = openai_analysis_client.enhance_result(
            user_message=user_message,
            mode=route.mode,
            result=result,
            subject=route.subject,
            entry_price_focus=route.entry_price_focus,
            reasoning_effort=reasoning_effort,
        )
    except OpenAIClientError:
        return result

    if enhancement is None:
        return result

    cards: List[ResultCard] = []
    for card in result.cards:
        if (
            _card_type_value(card) == CardType.OPERATION_GUIDANCE.value
            and enhancement.operation_guidance_content
        ):
            cards.append(
                ResultCard(
                    type=card.type,
                    title=card.title,
                    content=enhancement.operation_guidance_content,
                    metadata=card.metadata,
                )
            )
            continue
        cards.append(card)

    return _normalize_structured_result_output(StructuredResult(
        summary=enhancement.summary or result.summary,
        table=result.table,
        cards=cards,
        facts=result.facts,
        judgements=enhancement.judgements or result.judgements,
        follow_ups=enhancement.follow_ups or result.follow_ups,
        sources=result.sources,
    ))


def _resolve_gpt_reasoning_effort(
    route: RoutePlan,
    user_message: str,
    profile: UserProfile,
) -> str:
    policy = profile.gpt_reasoning_policy
    if policy != GptReasoningPolicy.AUTO:
        return policy.value

    text = user_message.lower()
    xhigh_keywords = (
        "多少价格",
        "什么价",
        "哪个价",
        "买点",
        "卖点",
        "止损",
        "止盈",
        "仓位",
        "估值",
        "财报",
        "现金流",
        "roe",
        "pe",
        "pb",
    )
    high_keywords = (
        "能买吗",
        "能买嘛",
        "值不值得买",
        "购买建议",
        "操作建议",
        "走势分析",
        "诊断",
        "波段",
        "中线",
        "公告",
        "研报",
    )

    if route.entry_price_focus or any(keyword in text for keyword in xhigh_keywords):
        return GptReasoningPolicy.XHIGH.value
    if route.mode == ChatMode.MID_TERM_VALUE:
        return GptReasoningPolicy.HIGH.value
    if route.single_security or any(keyword in user_message for keyword in high_keywords):
        return GptReasoningPolicy.HIGH.value
    return GptReasoningPolicy.MEDIUM.value


def _execute_plan_core(
    route: RoutePlan,
    profile: UserProfile,
    user_message: str = "",
) -> tuple[StructuredResult, List[SkillUsage], str, Optional[UserVisibleError]]:
    limit = profile.default_result_size or 5
    skills_used: List[SkillUsage] = []
    sources: List[SourceRef] = []
    facts: List[str] = []
    judgements: List[str] = []
    cards: List[ResultCard] = []
    primary_table: Optional[ResultTable] = None
    primary_query = route.skills[0].query if route.skills else ""
    primary_source_skill = ""
    primary_priority = -1
    collected_names: List[str] = []
    primary_raw_row: Optional[Dict[str, Any]] = None
    failure_reasons: List[str] = []
    fallback_summary: Optional[str] = None
    user_visible_error: Optional[UserVisibleError] = None
    holding_context: Optional[SimTradingHoldingContext] = None
    local_market = LocalMarketContext()
    used_wencai_source = False
    used_local_market_source = False

    for plan in route.skills:
        spec = skill_registry.require(plan.skill_id)
        adapter = get_skill_adapter(spec.adapter_kind)
        try:
            if spec.adapter_kind == SkillAdapterKind.WENCAI_SEARCH:
                adapter_result = adapter.execute(spec, query=plan.query, limit=3)
                if not isinstance(adapter_result, WencaiSearchAdapterResult):
                    raise TypeError(f"{plan.skill_id} returned unexpected adapter result")
                titles = adapter_result.titles
                if titles:
                    cards.append(
                        ResultCard(
                            type=CardType.RESEARCH_NEXT_STEP,
                            title=f"{plan.name}补充",
                            content="\n".join(f"- {title}" for title in titles),
                        )
                    )
                skills_used.append(_skill_success(plan.name, adapter_result.latency_ms, plan.reason))
                sources.append(SourceRef(skill=plan.name, query=plan.query))
                used_wencai_source = True
                continue

            if spec.adapter_kind == SkillAdapterKind.LOCAL_REALHEAD:
                resolved = _ensure_local_resolved_security(route, plan, primary_raw_row, local_market)
                adapter_result = adapter.execute(spec, code=resolved.code)
                if not isinstance(adapter_result, LocalRealheadAdapterResult):
                    raise TypeError(f"{plan.skill_id} returned unexpected adapter result")
                realhead = adapter_result.snapshot
                if not realhead.name and resolved.name:
                    realhead.name = resolved.name
                if not resolved.name and realhead.name:
                    resolved.name = realhead.name
                local_market.realhead = realhead
                skills_used.append(_skill_success(plan.name, adapter_result.latency_ms, plan.reason))
                sources.append(SourceRef(skill=plan.name, query=resolved.symbol or resolved.code))
                facts.append(f"{plan.name} 已补充 {realhead.name or resolved.name or resolved.code} 的实时行情快照。")
                used_local_market_source = True

                raw_overlay = realhead.to_raw_fields()
                if resolved.name:
                    raw_overlay["股票简称"] = resolved.name
                    raw_overlay["名称"] = resolved.name
                primary_raw_row = _merge_raw_fields(primary_raw_row, raw_overlay, overwrite=True)
                primary_source_skill = _append_source_label(primary_source_skill, plan.name)
                primary_table = _refresh_primary_table(primary_raw_row, route.mode, primary_source_skill)
                primary_query = route.subject or plan.query
                primary_priority = max(primary_priority, _primary_skill_priority(plan, route.mode))
                collected_names = [
                    str(row.get("名称") or "")
                    for row in primary_table.rows
                    if str(row.get("名称") or "") and str(row.get("名称") or "") != "-"
                ]
                continue

            if spec.adapter_kind == SkillAdapterKind.LOCAL_ORDERBOOK:
                resolved = _ensure_local_resolved_security(route, plan, primary_raw_row, local_market)
                adapter_result = adapter.execute(
                    spec,
                    code=resolved.code,
                    realhead=local_market.realhead,
                )
                if not isinstance(adapter_result, LocalOrderBookAdapterResult):
                    raise TypeError(f"{plan.skill_id} returned unexpected adapter result")
                local_market.order_book = adapter_result.order_book
                local_market.trades = adapter_result.trades
                skills_used.append(_skill_success(plan.name, adapter_result.latency_ms, plan.reason))
                sources.append(SourceRef(skill=plan.name, query=resolved.symbol or resolved.code))
                facts.append(f"{plan.name} 已补充五档盘口和最近逐笔成交。")
                used_local_market_source = True
                continue

            if spec.adapter_kind == SkillAdapterKind.LOCAL_THEME:
                resolved = _ensure_local_resolved_security(route, plan, primary_raw_row, local_market)
                adapter_result = adapter.execute(spec, code=resolved.code)
                if not isinstance(adapter_result, LocalThemeAdapterResult):
                    raise TypeError(f"{plan.skill_id} returned unexpected adapter result")
                theme = adapter_result.snapshot
                if not theme.name and resolved.name:
                    theme.name = resolved.name
                if not resolved.name and theme.name:
                    resolved.name = theme.name
                local_market.theme = theme
                skills_used.append(_skill_success(plan.name, adapter_result.latency_ms, plan.reason))
                sources.append(SourceRef(skill=plan.name, query=resolved.symbol or resolved.code))
                facts.append(f"{plan.name} 已补充地域、概念和主营业务。")
                used_local_market_source = True
                if primary_raw_row is not None:
                    primary_raw_row = _merge_raw_fields(primary_raw_row, theme.to_raw_fields(), overwrite=False)
                    primary_source_skill = _append_source_label(primary_source_skill, plan.name)
                    primary_table = _refresh_primary_table(primary_raw_row, route.mode, primary_source_skill)
                continue

            if spec.adapter_kind != SkillAdapterKind.WENCAI_QUERY:
                raise TypeError(f"Unsupported adapter kind: {spec.adapter_kind.value}")

            adapter_result = adapter.execute(spec, query=plan.query, limit=max(limit, 5))
            if not isinstance(adapter_result, WencaiQueryAdapterResult):
                raise TypeError(f"{plan.skill_id} returned unexpected adapter result")
            datas = adapter_result.rows
            skills_used.append(_skill_success(plan.name, adapter_result.latency_ms, plan.reason))
            sources.append(SourceRef(skill=plan.name, query=plan.query))
            facts.append(f"{plan.name} 查询 `{plan.query}` 命中 {adapter_result.code_count} 条，当前取 {len(datas)} 条。")
            used_wencai_source = True

            if route.single_security and plan.skill_id in {
                SKILL_WENCAI_SINGLE_SECURITY_SNAPSHOT,
                SKILL_WENCAI_SINGLE_SECURITY_FUNDAMENTAL,
            } and datas:
                selected_raw = _select_single_security_row(datas, route.subject)
                if selected_raw is not None:
                    primary_raw_row = _merge_raw_fields(primary_raw_row, selected_raw, overwrite=False)
                    primary_source_skill = _append_source_label(primary_source_skill, plan.name)
                    primary_table = _refresh_primary_table(primary_raw_row, route.mode, primary_source_skill)
                    primary_query = route.subject or primary_query or plan.query
                    primary_priority = max(primary_priority, _primary_skill_priority(plan, route.mode))
                    code = _extract_security_code_from_raw(primary_raw_row)
                    name = _extract_security_name_from_raw(primary_raw_row)
                    if code:
                        local_market.resolved = local_market.resolved or local_market_skill_client.resolve_security(code)
                        if name and not local_market.resolved.name:
                            local_market.resolved.name = name
                    collected_names = [
                        str(row.get("名称") or "")
                        for row in primary_table.rows
                        if str(row.get("名称") or "") and str(row.get("名称") or "") != "-"
                    ]
                continue

            plan_priority = _primary_skill_priority(plan, route.mode)
            use_as_primary = bool(datas) and plan_priority > primary_priority

            if use_as_primary:
                primary_table = normalize_table(datas, route.mode, plan.name, limit)
                primary_query = plan.query
                primary_source_skill = plan.name
                primary_priority = plan_priority
                primary_raw_row = _select_single_security_row(datas, route.subject) if route.single_security else (datas[0] if datas else None)
                if route.single_security and primary_raw_row is not None:
                    code = _extract_security_code_from_raw(primary_raw_row)
                    name = _extract_security_name_from_raw(primary_raw_row)
                    if code:
                        local_market.resolved = local_market.resolved or local_market_skill_client.resolve_security(code)
                        if name and not local_market.resolved.name:
                            local_market.resolved.name = name
                collected_names = []
                for row in primary_table.rows:
                    name = str(row.get("名称") or "")
                    if name and name != "-":
                        collected_names.append(name)
            else:
                names = [
                    str(_find_value(row, ("股票简称", "指数简称", "名称", "股票名称"), ("简称", "名称")) or "")
                    for row in datas[:5]
                ]
                names = [name for name in names if name]
                if names:
                    cards.append(
                        ResultCard(
                            type=CardType.SECTOR_OVERVIEW if "板块" in plan.name or "行业" in plan.name else CardType.CANDIDATE_SUMMARY,
                            title=plan.name,
                            content="、".join(names),
                        )
                    )
        except WencaiClientError as exc:
            skills_used.append(_skill_failed(plan.name, str(exc)))
            facts.append(f"{plan.name} 调用失败：{exc}")
            failure_reasons.append(str(exc))
        except LocalMarketSkillError as exc:
            skills_used.append(_skill_failed(plan.name, str(exc)))
            facts.append(f"{plan.name} 调用失败：{exc}")
            failure_reasons.append(str(exc))

    if route.single_security and route.holding_context_focus and route.subject:
        try:
            holding_context = sim_trading_client.query_holding_context(route.subject)
            skills_used.append(_skill_success("模拟炒股", holding_context.latency_ms, "读取当前模拟持仓上下文"))
            sources.append(SourceRef(skill="模拟炒股", query=f"{route.subject} 当前模拟持仓"))
            cards.append(_portfolio_context_card(route.subject, holding_context))
        except SimTradingClientError as exc:
            skills_used.append(_skill_failed("模拟炒股", str(exc)))
            facts.append(f"模拟炒股 持仓上下文获取失败：{exc}")

    if primary_table is None:
        fallback_tip = "本次查询未命中可展示数据"
        if route.single_security:
            fallback_suggestion = "可以补充“最新价、涨跌幅、公告、新闻、资金”这类更具体条件再试。"
        else:
            fallback_suggestion = "可以补充股票名、代码、时间范围或更具体筛选条件后重试。"

        if skills_used and all(skill.status == SkillRunStatus.FAILED for skill in skills_used):
            first_reason = failure_reasons[0] if failure_reasons else ""
            user_visible_error = _execution_user_visible_error(failure_reasons)
            fallback_tip = "问财接口调用失败"
            if "API_KEY 未配置" in first_reason or "HTTP 401" in first_reason or "HTTP 403" in first_reason:
                fallback_suggestion = "问财鉴权失败，请检查后端 IWENCAI_API_KEY 后重试。"
            elif "网络错误" in first_reason:
                fallback_suggestion = "问财接口网络异常，请稍后重试。"
            elif first_reason:
                fallback_suggestion = first_reason[:120]
            else:
                fallback_suggestion = "请稍后重试。"
            fallback_summary = "这次没有成功拿到问财结果。"
        else:
            fallback_summary = "这次查询没有命中可展示结果。"

        primary_table = ResultTable(
            columns=["提示", "建议"],
            rows=[{"提示": fallback_tip, "建议": fallback_suggestion}],
        )

    if route.single_security and primary_raw_row is not None and primary_table.rows:
        summary, extra_facts, extra_judgements, follow_ups, leading_cards = _single_security_summary(
            route,
            primary_table.rows[0],
            primary_raw_row,
            cards,
            holding_context,
            local_market,
        )
        facts.extend(extra_facts)
        judgements.extend(extra_judgements)
        cards = leading_cards + cards
    elif route.mode == ChatMode.SHORT_TERM:
        summary = fallback_summary or "短线模式已完成：优先观察强势板块、涨跌幅和资金承接。"
        judgements.append("短线结果更适合做观察池，不建议把涨幅榜直接等同于买入清单。")
        follow_ups = ["把这几只按胜率排序", "补充最近7天公告", "去掉今日涨幅过大的"]
    elif route.mode == ChatMode.SWING:
        summary = fallback_summary or "波段模式已完成：重点看趋势延续、行业轮动和基本面质量。"
        judgements.append("波段候选需要结合趋势失效条件，不能只看近20日强弱。")
        follow_ups = ["只保留趋势更稳的", "补充财务质量对比", "按回撤风险排序"]
    elif route.mode == ChatMode.MID_TERM_VALUE:
        summary = fallback_summary or "中线价值模式已完成：重点看估值、ROE、现金流和后续验证项。"
        judgements.append("低估值需要排除价值陷阱，建议继续核对主营、现金流和股东变化。")
        follow_ups = ["对Top3做财务体检", "补充最新研报和公告", "只保留高股息标的"]
    else:
        summary = fallback_summary or "通用查询已完成。"
        follow_ups = ["把结果做成比较表", "补充公告和新闻", "只保留A股标的"]

    if collected_names and not route.single_security:
        cards.insert(
            0,
            ResultCard(
                type=CardType.CANDIDATE_SUMMARY,
                title="候选摘要",
                content="、".join(collected_names[:limit]),
            ),
        )

    source_facts: List[str] = []
    if used_wencai_source:
        source_facts.append("数据来源：同花顺问财。")
    if used_local_market_source:
        source_facts.append("单股实时补充来自同花顺公开行情页、盘口接口和题材页。")
    facts = source_facts + facts

    risk_content = "以上为基于同花顺问财数据的辅助筛选和规则化整理，不构成投资建议。"
    if used_wencai_source and used_local_market_source:
        risk_content = "以上为基于同花顺问财与同花顺公开行情页补充的辅助整理，不构成投资建议。"
    elif used_local_market_source:
        risk_content = "以上为基于同花顺公开行情页和盘口补充的辅助整理，不构成投资建议。"
    cards.append(
        ResultCard(
            type=CardType.RISK_WARNING,
            title="使用边界",
            content=risk_content,
        )
    )

    structured = _normalize_structured_result_output(StructuredResult(
        summary=summary,
        table=primary_table,
        cards=cards,
        facts=facts,
        judgements=judgements,
        follow_ups=follow_ups,
        sources=sources,
    ))
    return structured, skills_used, primary_query, user_visible_error


def _enhance_result_with_llm(
    route: RoutePlan,
    result: StructuredResult,
    profile: UserProfile,
    user_message: str = "",
) -> StructuredResult:
    return _apply_gpt_enhancement(
        route,
        result,
        user_message=user_message or route.subject or "",
        profile=profile,
    )


def execute_plan(
    route: RoutePlan,
    profile: UserProfile,
    user_message: str = "",
) -> tuple[StructuredResult, List[SkillUsage], str, Optional[UserVisibleError]]:
    return langgraph_stock_agent.invoke(
        route=route,
        profile=profile,
        user_message=user_message,
        skill_executor=_execute_plan_core,
        result_enhancer=_enhance_result_with_llm,
    )


def execute_plan_base(
    route: RoutePlan,
    profile: UserProfile,
    user_message: str = "",
) -> tuple[StructuredResult, List[SkillUsage], str, Optional[UserVisibleError], bool]:
    state = langgraph_stock_agent.invoke_base(
        route=route,
        profile=profile,
        user_message=user_message,
        skill_executor=_execute_plan_core,
    )
    return (
        state["result"],
        state.get("skills_used", []),
        state.get("rewritten_query", ""),
        state.get("user_visible_error"),
        state.get("should_enhance", False),
    )


def enhance_plan_result(
    route: RoutePlan,
    result: StructuredResult,
    profile: UserProfile,
    *,
    user_message: str = "",
    should_enhance: bool = True,
    user_visible_error: Optional[UserVisibleError] = None,
) -> StructuredResult:
    return langgraph_stock_agent.enhance(
        route=route,
        profile=profile,
        user_message=user_message,
        result=result,
        result_enhancer=_enhance_result_with_llm,
        should_enhance=should_enhance,
        user_visible_error=user_visible_error,
    )


def compare_from_snapshot(snapshot: Optional[StructuredResult], message: str) -> StructuredResult:
    if not snapshot or not snapshot.table or not snapshot.table.rows:
        return StructuredResult(
            summary="没有找到可比较的上一轮结构化结果。",
            table=ResultTable(columns=["提示"], rows=[{"提示": "请先完成一次选股或查询"}]),
            follow_ups=["重新筛选短线候选", "重新筛选波段候选"],
        )

    rows = snapshot.table.rows[:3]
    compare_rows = []
    for idx, row in enumerate(rows, start=1):
        change = _safe_float(str(row.get("涨跌幅", "")).replace("%", ""))
        risk = 8 if change is not None and change > 9 else 5
        compare_rows.append(
            {
                "排序": idx,
                "代码": row.get("代码", "-"),
                "名称": row.get("名称", "-"),
                "胜率": max(5, 9 - risk // 2),
                "赔率": 7 if idx == 1 else 6,
                "催化确定性": 6,
                "回撤风险": risk,
                "结论": "优先跟踪" if idx == 1 else "备选观察",
            }
        )

    return StructuredResult(
        summary="已基于上一轮结果做本地比较。评分是规则化辅助判断，仍需结合实时数据复核。",
        table=ResultTable(
            columns=["排序", "代码", "名称", "胜率", "赔率", "催化确定性", "回撤风险", "结论"],
            rows=compare_rows,
        ),
        facts=["比较对象来自上一轮结构化结果。"],
        judgements=["如要提高准确度，可继续补调公告、研报和财务数据。"],
        follow_ups=["补充最近7天公告", "只保留风险最低的", "重新按财务质量排序"],
        sources=snapshot.sources,
    )


def _row_text_value(row: Dict[str, Any], key: str) -> str:
    value = row.get(key)
    if value is None:
        return ""
    return str(value).strip()


def _row_change_pct(row: Dict[str, Any]) -> Optional[float]:
    return _safe_float(_row_text_value(row, "涨跌幅").replace("%", ""))


def _keyword_score(text: str, rules: Dict[str, int]) -> int:
    score = 0
    lowered = text.lower()
    for keyword, weight in rules.items():
        if keyword.lower() in lowered:
            score += weight
    return score


def _row_risk_score(row: Dict[str, Any]) -> int:
    change = _row_change_pct(row)
    technical = _row_text_value(row, "技术面")
    fundamental = _row_text_value(row, "基本面")
    logic = _row_text_value(row, "核心逻辑")
    risk = _row_text_value(row, "风险点")

    score = 45
    if change is not None:
        if change >= 9.5:
            score += 24
        elif change >= 6:
            score += 12
        elif change <= -5:
            score += 10
        elif -2 <= change <= 4:
            score -= 4

    score += _keyword_score(
        risk,
        {
            "追高": 16,
            "分歧": 10,
            "退潮": 14,
            "止损": 8,
            "价值陷阱": 16,
            "失效": 8,
        },
    )
    score += _keyword_score(
        technical,
        {
            "低于MA20": 12,
            "低于MA5": 6,
            "绿柱": 10,
            "超卖": 4,
        },
    )
    score += _keyword_score(
        fundamental,
        {
            "现金流承压": 12,
            "负债率": 6,
        },
    )
    score -= _keyword_score(
        technical,
        {
            "高于MA20": 10,
            "高于MA5": 6,
            "红柱": 8,
            "趋势修复": 6,
        },
    )
    score -= _keyword_score(
        logic,
        {
            "低估值": 4,
            "财务质量": 4,
            "资金条件入选": 3,
        },
    )
    return max(0, min(score, 100))


def _row_trend_score(row: Dict[str, Any]) -> int:
    change = _row_change_pct(row)
    technical = _row_text_value(row, "技术面")
    logic = _row_text_value(row, "核心逻辑")
    risk = _row_text_value(row, "风险点")

    score = 50
    if change is not None:
        if 0 <= change <= 7:
            score += 6
        elif change >= 9.5:
            score -= 8
        elif change <= -5:
            score -= 10

    score += _keyword_score(
        technical,
        {
            "高于MA20": 14,
            "高于MA5": 8,
            "红柱": 10,
            "趋势修复": 8,
            "放量": 4,
        },
    )
    score += _keyword_score(
        logic,
        {
            "趋势和资金条件入选": 8,
            "短线强势或资金关注": 5,
        },
    )
    score -= _keyword_score(
        technical,
        {
            "低于MA20": 14,
            "低于MA5": 8,
            "绿柱": 10,
            "超卖": 4,
        },
    )
    score -= _keyword_score(
        risk,
        {
            "分歧": 8,
            "退潮": 10,
            "止损": 6,
        },
    )
    return max(0, min(score, 100))


def _row_fundamental_score(row: Dict[str, Any]) -> int:
    fundamental = _row_text_value(row, "基本面")
    logic = _row_text_value(row, "核心逻辑")
    risk = _row_text_value(row, "风险点")

    if not fundamental and not logic:
        return 0

    score = 40
    score += _keyword_score(
        f"{fundamental} {logic}",
        {
            "ROE": 14,
            "现金流": 12,
            "净利润": 8,
            "营收": 6,
            "PE": 4,
            "PB": 4,
            "低估值": 10,
            "财务质量": 10,
            "高股息": 10,
            "分红": 8,
        },
    )
    score -= _keyword_score(
        f"{fundamental} {risk}",
        {
            "价值陷阱": 16,
            "现金流承压": 12,
            "负债率": 8,
            "风险": 4,
        },
    )
    return max(0, min(score, 100))


def _is_a_share_row(row: Dict[str, Any]) -> bool:
    code = _row_text_value(row, "代码").upper()
    return code.endswith((".SH", ".SZ", ".BJ"))


def _snapshot_refine_keep_count(total: int) -> int:
    if total <= 1:
        return total
    return min(3, max(1, math.ceil(total / 2)))


def refine_follow_up_from_snapshot(
    snapshot: Optional[StructuredResult],
    message: str,
    *,
    parent_mode: Optional[ChatMode] = None,
) -> Optional[StructuredResult]:
    if snapshot is None or snapshot.table is None or not snapshot.table.rows:
        return None

    text = " ".join(message.strip().split())
    lowered = text.lower()
    rows = [dict(row) for row in snapshot.table.rows]
    original_count = len(rows)
    refined_rows: List[Dict[str, Any]] = rows
    action = ""
    explanation = ""
    local_field_hint = ""

    if "只保留趋势更稳" in text or "趋势更稳" in text:
        action = "filter_trend"
        ranked = sorted(rows, key=_row_trend_score, reverse=True)
        keep_count = _snapshot_refine_keep_count(len(ranked))
        refined_rows = ranked[:keep_count]
        explanation = "趋势稳定度优先参考技术面中的均线位置、MACD 状态、涨跌幅和风险点。"
        local_field_hint = "技术面 / 涨跌幅 / 风险点"
    elif "只保留风险最低" in text or "只保留低风险" in text:
        action = "filter_low_risk"
        ranked = sorted(rows, key=_row_risk_score)
        keep_count = _snapshot_refine_keep_count(len(ranked))
        refined_rows = ranked[:keep_count]
        explanation = "风险高低优先参考涨跌幅、风险点文案和技术面里的均线 / MACD 状态。"
        local_field_hint = "涨跌幅 / 技术面 / 风险点"
    elif ("按" in text and "风险排序" in text) or "按回撤风险排序" in text:
        action = "sort_risk"
        refined_rows = sorted(rows, key=_row_risk_score)
        explanation = "这次按回撤风险从低到高重排，越靠前表示规则化风险越低。"
        local_field_hint = "涨跌幅 / 技术面 / 风险点"
    elif "财务质量排序" in text or "按财务质量排序" in text:
        action = "sort_fundamental"
        ranked = sorted(rows, key=_row_fundamental_score, reverse=True)
        if _row_fundamental_score(ranked[0]) <= 0:
            return None
        refined_rows = ranked
        explanation = "财务质量排序只使用当前结果表已有的基本面摘要，不补调新财报。"
        local_field_hint = "基本面 / 核心逻辑 / 风险点"
    elif (
        "涨幅过大" in text
        and any(keyword in text for keyword in ("去掉", "剔除", "排除", "不要", "别要"))
    ):
        action = "drop_overextended"
        threshold = 9.5 if parent_mode == ChatMode.SHORT_TERM else 12.0
        refined_rows = [
            row for row in rows if (_row_change_pct(row) is None or _row_change_pct(row) < threshold)
        ]
        explanation = f"“涨幅过大”当前按涨跌幅 >= {threshold:.1f}% 视为过热处理。"
        local_field_hint = "涨跌幅 / 风险点"
    elif "只保留a股" in lowered or "只保留A股" in text:
        action = "filter_a_share"
        refined_rows = [row for row in rows if _is_a_share_row(row)]
        explanation = "A 股识别当前按代码后缀 .SH / .SZ / .BJ 判断。"
        local_field_hint = "代码"
    else:
        return None

    if not refined_rows:
        return StructuredResult(
            summary="按这条追问条件过滤后，上一轮结果里没有保留下来的标的。",
            table=ResultTable(
                columns=["提示", "建议"],
                rows=[{"提示": "本地过滤结果为空", "建议": "可以放宽条件，或补查更完整字段后再筛。"}],
            ),
            cards=[
                ResultCard(
                    type=CardType.CANDIDATE_SUMMARY,
                    title="追问筛选",
                    content=f"条件：{text}\n结果：本地过滤后没有命中标的。",
                )
            ],
            facts=[
                "这次追问直接基于上一轮结构化结果做本地过滤，没有重新调用外部数据。",
                f"本地过滤使用字段：{local_field_hint}。",
            ],
            judgements=[explanation],
            follow_ups=["放宽这轮过滤条件", "补充最近7天公告", "重新跑一轮更完整筛选"],
            sources=[*snapshot.sources, SourceRef(skill="上一轮结果快照", query=text)],
        )

    retained_names = [
        _row_text_value(row, "名称") or _row_text_value(row, "代码")
        for row in refined_rows[:3]
    ]
    retained_preview = "、".join(name for name in retained_names if name) or "当前结果"

    if action == "filter_trend":
        summary = f"已基于上一轮结果保留趋势更稳的 {len(refined_rows)} 只，优先看 {retained_preview}。"
    elif action == "filter_low_risk":
        summary = f"已基于上一轮结果保留风险更低的 {len(refined_rows)} 只，当前更靠前的是 {retained_preview}。"
    elif action == "sort_risk":
        summary = f"已按回撤风险从低到高重排上一轮结果，当前更靠前的是 {retained_preview}。"
    elif action == "sort_fundamental":
        summary = f"已按结果表里的财务质量线索重排上一轮结果，当前更靠前的是 {retained_preview}。"
    elif action == "drop_overextended":
        summary = (
            f"已从上一轮结果里去掉涨幅过大的标的，剩下 {len(refined_rows)} 只，优先看 {retained_preview}。"
        )
    else:
        summary = f"已按追问条件保留 {len(refined_rows)} 只标的，当前更靠前的是 {retained_preview}。"

    card_lines = [
        f"条件：{text}",
        f"原始数量：{original_count}",
        f"当前数量：{len(refined_rows)}",
        f"优先关注：{retained_preview}",
    ]
    if action == "sort_risk":
        card_lines.append("排序方式：风险从低到高")
    elif action == "sort_fundamental":
        card_lines.append("排序方式：财务质量从强到弱")

    follow_ups = _dedupe_string_list(
        [
            "补充最近7天公告",
            "按回撤风险排序" if action != "sort_risk" else "只保留风险最低的",
            "重新按财务质量排序" if action != "sort_fundamental" else "只保留趋势更稳的",
            "去掉最近涨幅过大的" if action != "drop_overextended" else "只保留趋势更稳的",
        ],
        limit=3,
    )

    result = StructuredResult(
        summary=summary,
        table=ResultTable(columns=snapshot.table.columns, rows=refined_rows),
        cards=[
            ResultCard(
                type=CardType.CANDIDATE_SUMMARY,
                title="追问筛选",
                content="\n".join(card_lines),
                metadata={
                    "action": action,
                    "original_count": original_count,
                    "current_count": len(refined_rows),
                },
            )
        ],
        facts=[
            "这次追问直接基于上一轮结构化结果做本地过滤/排序，没有重新调用问财或外部行情。",
            f"本地 refinement 使用字段：{local_field_hint}。",
        ],
        judgements=[explanation],
        follow_ups=follow_ups,
        sources=[*snapshot.sources, SourceRef(skill="上一轮结果快照", query=text)],
    )
    return _normalize_structured_result_output(result)


def is_compare_follow_up(message: str) -> bool:
    return any(keyword in message for keyword in FOLLOW_UP_COMPARE_KEYWORDS)


def _looks_like_single_security_snapshot(snapshot: Optional[StructuredResult]) -> bool:
    if snapshot is None:
        return False

    for card in snapshot.cards:
        if _card_type_value(card) in {
            CardType.OPERATION_GUIDANCE.value,
            CardType.MULTI_HORIZON_ANALYSIS.value,
            CardType.PORTFOLIO_CONTEXT.value,
        }:
            return True
        subject = card.metadata.get("subject")
        if isinstance(subject, str) and subject.strip():
            return True

    if snapshot.table and len(snapshot.table.rows) == 1:
        row = snapshot.table.rows[0]
        return any(key in row for key in ("名称", "股票简称", "代码", "股票代码"))

    return False


def _snapshot_subject(snapshot: Optional[StructuredResult]) -> Optional[str]:
    if snapshot is None:
        return None

    for card in snapshot.cards:
        subject = card.metadata.get("subject")
        if isinstance(subject, str):
            text = subject.strip()
            if text:
                return text

    if snapshot.table and snapshot.table.rows:
        row = snapshot.table.rows[0]
        for key in ("名称", "股票简称", "股票名称", "代码", "股票代码"):
            value = row.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text and text != "-":
                return text

    return None


def _snapshot_candidate_names(snapshot: Optional[StructuredResult], *, limit: int = 3) -> List[str]:
    if snapshot is None or snapshot.table is None:
        return []

    names: List[str] = []
    seen: set[str] = set()
    for row in snapshot.table.rows:
        for key in ("名称", "股票简称", "股票名称", "代码", "股票代码"):
            value = row.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if not text or text == "-" or text in seen:
                continue
            seen.add(text)
            names.append(text)
            break
        if len(names) >= limit:
            break
    return names


def rewrite_follow_up_message(
    message: str,
    parent_message: Optional[ChatMessageRecord],
) -> str:
    text = " ".join(message.strip().split())
    if not text or parent_message is None:
        return text

    if _extract_security_subject(text):
        return text

    snapshot = parent_message.result_snapshot
    if _looks_like_single_security_snapshot(snapshot):
        subject = _snapshot_subject(snapshot)
        if subject:
            return f"{subject} {text}"

    context_parts: List[str] = []
    candidate_names = _snapshot_candidate_names(snapshot)
    if candidate_names and any(marker in text for marker in ("刚才", "上面", "上一轮", "这几只", "那几只", "这些", "Top3", "top3")):
        context_parts.append(f"上一轮候选：{'、'.join(candidate_names)}")
    previous_query = " ".join((parent_message.rewritten_query or "").strip().split())
    if "上一轮筛选条件：" in previous_query:
        previous_query = previous_query.rsplit("上一轮筛选条件：", maxsplit=1)[-1].strip("； ")
    if previous_query:
        context_parts.append(f"上一轮筛选条件：{previous_query}")

    if not context_parts:
        return text
    return f"{text}；{'；'.join(context_parts)}"


def plan_follow_up_route(
    message: str,
    parent_message: Optional[ChatMessageRecord],
    *,
    session_mode: Optional[ChatMode],
    profile: UserProfile,
) -> tuple[ModeDetection, RoutePlan, str]:
    contextual_message = rewrite_follow_up_message(message, parent_message)
    parent_mode = (
        parent_message.mode
        if parent_message is not None and parent_message.mode not in {ChatMode.COMPARE, ChatMode.FOLLOW_UP}
        else None
    )
    effective_session_mode = parent_mode or session_mode
    detection = detect_mode(contextual_message, session_mode=effective_session_mode)

    if detection.mode in {ChatMode.COMPARE, ChatMode.FOLLOW_UP}:
        fallback_mode = effective_session_mode or ChatMode.GENERIC_DATA_QUERY
        detection = ModeDetection(
            mode=fallback_mode,
            confidence=detection.confidence,
            source=f"{detection.source}_follow_up_context",
        )

    snapshot = parent_message.result_snapshot if parent_message is not None else None
    subject = _snapshot_subject(snapshot) if _looks_like_single_security_snapshot(snapshot) else None
    if subject and detection.mode in {ChatMode.SHORT_TERM, ChatMode.SWING, ChatMode.MID_TERM_VALUE}:
        route = _single_security_route(
            subject,
            detection.mode,
            entry_price_focus=_is_entry_price_question(contextual_message),
            holding_context_focus=_is_holding_question(contextual_message),
        )
        return detection, route, contextual_message

    route = build_route(contextual_message, detection.mode, profile)
    return detection, route, contextual_message


def result_to_chat_response(
    *,
    session_id: str,
    message_id: str,
    mode: ChatMode,
    result: StructuredResult,
    skills_used: List[SkillUsage],
    status: ChatResponseStatus = ChatResponseStatus.COMPLETED,
    user_visible_error: Optional[UserVisibleError] = None,
) -> ChatResponse:
    return ChatResponse(
        session_id=session_id,
        message_id=message_id,
        mode=mode,
        skills_used=skills_used,
        summary=result.summary,
        table=result.table,
        cards=result.cards,
        facts=result.facts,
        judgements=result.judgements,
        follow_ups=result.follow_ups,
        sources=result.sources,
        status=status,
        user_visible_error=user_visible_error,
    )


def to_plain_json(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [to_plain_json(item) for item in value]
    if isinstance(value, dict):
        return {key: to_plain_json(item) for key, item in value.items()}
    return value
