from __future__ import annotations

import re
from typing import Iterable, Optional

from pydantic import Field

from app.schemas import CardType, ResultCard, StructuredResult
from app.schemas.common import ContractModel
from .single_stock_research_harness import extract_deep_research_subject


HIGH_RISK_KEYWORDS = (
    "必涨",
    "稳赚",
    "无风险",
    "保证收益",
    "梭哈",
    "满仓",
)

AMBIGUOUS_STOCK_HINTS = (
    "这只股票",
    "这支股票",
    "这个股票",
    "这票",
    "它",
)

SHORT_TERM_KEYWORDS = (
    "今天能不能买",
    "能不能买",
    "能买吗",
    "能不能追",
    "短线",
    "止损",
    "怎么操作",
    "如何操作",
    "买点",
    "价格分析",
    "价格走势",
    "走势分析",
    "趋势分析",
)

DEEP_RESEARCH_KEYWORDS = (
    "分析",
    "怎么看",
    "小白怎么看",
    "价值",
    "中线",
    "值不值得关注",
    "值得关注吗",
    "值得关注",
    "基本面",
    "估值",
    "财报",
    "风险",
    "主力",
    "散户",
    "资金",
    "筹码",
    "股东",
)

LONG_TERM_KEYWORDS = (
    "长线",
    "长期",
    "长期价值",
    "能不能长期拿",
    "拿三年",
    "拿五年",
    "拿十年",
    "护城河",
    "分红",
    "股东回报",
)

SECTOR_KEYWORDS = (
    "板块",
    "行业",
    "概念",
    "题材",
    "赛道",
    "大盘",
    "a股",
    "A股",
    "沪深",
    "创业板",
    "科创板",
    "新能源",
    "半导体",
    "白酒",
)

EDUCATION_TERMS = (
    "PE",
    "PB",
    "PS",
    "ROE",
    "MACD",
    "RSI",
    "KDJ",
    "布林带",
    "放量",
    "缩量",
    "主力资金",
    "换手率",
)

EDUCATION_ASK_KEYWORDS = (
    "是什么意思",
    "什么是",
    "怎么看",
    "啥意思",
    "怎么理解",
    "什么意思",
)

CHART_TRIGGER_KEYWORDS = (
    "今天能不能买",
    "现在能买吗",
    "现在能买",
    "能不能追",
    "短线怎么看",
    "K线怎么看",
    "k线怎么看",
    "趋势怎么样",
    "止损",
    "要不要止损",
    "放量",
    "缩量",
    "MACD",
    "macd",
    "RSI",
    "rsi",
    "KDJ",
    "kdj",
    "均线",
    "布林带",
    "价格分析",
    "价格走势",
    "走势分析",
    "趋势分析",
)

COMPARE_PATTERN = re.compile(
    r"(?P<left>[A-Za-z0-9\u4e00-\u9fff]{2,12}?)"
    r"(?:和|与|跟|vs|VS|VSVS|对比|比较)"
    r"(?P<right>[A-Za-z0-9\u4e00-\u9fff]{2,12})"
    r"(?:哪个好|谁更好|哪个更好|怎么样|对比|比较|更值得关注|更强)?"
)

OPERATION_SUBJECT_PATTERNS = (
    r"(?P<subject>[A-Za-z0-9\u4e00-\u9fff]{2,12}?)(?:今天能不能买|现在能买吗|能不能买|能买吗|能不能追|要不要止损|短线|止损|怎么操作|如何操作)",
)

GENERIC_STOCK_WORDS = {
    "股票",
    "个股",
    "A股",
    "a股",
    "板块",
    "行业",
    "概念",
    "大盘",
    "今天",
    "明天",
    "现在",
    "小白",
}

ANALYSIS_TOPIC_WORDS = (
    "现金流",
    "财报",
    "财报质量",
    "基本面",
    "估值",
    "分红",
    "回购",
    "护城河",
    "中线",
    "长线",
    "长期",
    "价值",
    "质量",
    "ROE",
    "PE",
    "PB",
    "PS",
    "主力",
    "散户",
    "资金",
    "筹码",
    "股东",
)


class ConversationPlan(ContractModel):
    intent: str
    workflow: str
    stock_names: list[str] = Field(default_factory=list)
    stock_codes: list[str] = Field(default_factory=list)
    time_horizon: str | None = None
    need_clarification: bool = False
    clarification_question: str | None = None
    need_chart: bool = False
    chart_types: list[str] = Field(default_factory=list)
    risk_level: str = "normal"
    reason: str | None = None


def route_message(
    message: str,
    *,
    context_stock_names: Optional[list[str]] = None,
    context_stock_codes: Optional[list[str]] = None,
) -> ConversationPlan:
    text = _compact_text(message)
    context_stock_names = _dedupe(context_stock_names or [])
    context_stock_codes = _dedupe(context_stock_codes or [])

    if _contains_any(text, HIGH_RISK_KEYWORDS):
        return ConversationPlan(
            intent="safety_response",
            workflow="safety_response",
            risk_level="high",
            reason="high_risk_profit_promise",
        )

    stock_codes = _extract_stock_codes(text)
    stock_names = _extract_stock_names(text)

    if _is_missing_subject_capital_structure_question(text) and not stock_names and not stock_codes:
        return ConversationPlan(
            intent="ask_clarification",
            workflow="ask_clarification",
            need_clarification=True,
            clarification_question="请先提供股票名称或股票代码，我再看主力资金、散户筹码、股东户数和持仓变化。",
            risk_level="normal",
            reason="missing_stock_subject_for_capital_structure",
        )

    if _is_ambiguous_stock_question(text) and not stock_names and not stock_codes:
        if len(context_stock_names) == 1:
            stock_names = [context_stock_names[0]]
        elif len(context_stock_codes) == 1:
            stock_codes = [context_stock_codes[0]]
        else:
            return ConversationPlan(
                intent="ask_clarification",
                workflow="ask_clarification",
                need_clarification=True,
                clarification_question="请先提供股票名称或股票代码。",
                risk_level="normal",
                reason="missing_stock_subject",
            )
    elif not stock_names and not stock_codes and _should_inherit_context_stock(text):
        if len(context_stock_names) == 1:
            stock_names = [context_stock_names[0]]
        elif len(context_stock_codes) == 1:
            stock_codes = [context_stock_codes[0]]

    if len(stock_names) + len(stock_codes) >= 2 and _looks_like_compare_question(text):
        return ConversationPlan(
            intent="stock_compare",
            workflow="stock_compare",
            stock_names=stock_names,
            stock_codes=stock_codes,
            time_horizon=_time_horizon(text),
            reason="multi_stock_detected",
        )

    if stock_names or stock_codes:
        if _contains_any(text, SHORT_TERM_KEYWORDS) or _looks_like_directional_short_term(text) or _looks_like_price_window_analysis(text):
            return ConversationPlan(
                intent="short_term_operation",
                workflow="short_term_operation",
                stock_names=stock_names,
                stock_codes=stock_codes,
                time_horizon="short_term",
                need_chart=True if _looks_like_price_window_analysis(text) else _needs_chart(text),
                chart_types=_price_window_chart_types(text)
                if _looks_like_price_window_analysis(text)
                else _directional_short_term_chart_types(text)
                if _looks_like_directional_short_term(text)
                else _chart_types(text),
                reason="single_stock_operation",
            )
        if _contains_any(text, DEEP_RESEARCH_KEYWORDS) or _contains_any(text, LONG_TERM_KEYWORDS) or _looks_like_bare_stock_query(text, stock_names, stock_codes):
            deep_research_chart = _deep_research_chart_types(text)
            return ConversationPlan(
                intent="single_stock_deep_research",
                workflow="single_stock_deep_research",
                stock_names=stock_names,
                stock_codes=stock_codes,
                time_horizon=_time_horizon(text) or "mid_term",
                need_chart=bool(deep_research_chart),
                chart_types=deep_research_chart,
                reason="single_stock_research",
            )

    if _looks_like_sector_question(text):
        return ConversationPlan(
            intent="market_or_sector_analysis",
            workflow="market_or_sector_analysis",
            time_horizon=_time_horizon(text),
            reason="sector_or_market_question",
        )

    if _looks_like_beginner_education(text):
        return ConversationPlan(
            intent="beginner_education",
            workflow="beginner_education",
            reason="concept_explanation",
        )

    return ConversationPlan(
        intent="generic_chat",
        workflow="generic_chat",
        time_horizon=_time_horizon(text),
        reason="fallback",
    )


def direct_response_for_plan(plan: ConversationPlan) -> Optional[StructuredResult]:
    if plan.workflow == "ask_clarification":
        question = plan.clarification_question or "请先提供股票名称或股票代码。"
        return StructuredResult(
            summary=question,
            cards=[
                ResultCard(
                    type=CardType.RESEARCH_NEXT_STEP,
                    title="需要补充标的",
                    content="请先提供股票名称或股票代码，我再按公司画像、行情、技术面、基本面、估值、风险和操作框架继续分析。",
                )
            ],
            judgements=["当前问题缺少明确股票标的，暂时无法判断是否能买或怎么操作。"],
            follow_ups=["补充股票名称", "补充股票代码", "说明你更关心短线还是中线"],
        )

    if plan.workflow == "safety_response":
        return StructuredResult(
            summary="无法保证某只股票明天必涨，也不能提供稳赚、梭哈、满仓这类收益承诺，但可以基于资金、趋势、公告、行业催化和风险做条件化分析。",
            cards=[
                ResultCard(
                    type=CardType.RISK_WARNING,
                    title="收益承诺边界",
                    content="投资判断只能做概率分析，不能把“必涨、稳赚、无风险、梭哈、满仓”当成可执行建议。",
                ),
                ResultCard(
                    type=CardType.RESEARCH_NEXT_STEP,
                    title="建议改问法",
                    content="可以提供具体股票名称或代码，我会从趋势、资金、公告、行业催化和风险维度给出条件化判断。",
                ),
            ],
            judgements=["高风险收益承诺不符合合规边界，后续只能提供概率性和条件性的分析。"],
            follow_ups=["提供具体股票名称", "改问短线风险和条件", "只看公告和催化"],
        )

    return None


def _compact_text(message: str) -> str:
    return re.sub(r"\s+", "", str(message or ""))


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _dedupe(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = str(value or "").strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result


def _extract_stock_codes(text: str) -> list[str]:
    return _dedupe(match.upper() for match in re.findall(r"([0368]\d{5}(?:\.(?:SH|SZ|BJ))?)", text, flags=re.IGNORECASE))


def _extract_stock_names(text: str) -> list[str]:
    names: list[str] = []

    compare_match = COMPARE_PATTERN.search(text)
    if compare_match and not _looks_like_analysis_topic_connector(text):
        names.extend(
            filter(
                None,
                (
                    _clean_stock_candidate(compare_match.group("left")),
                    _clean_stock_candidate(compare_match.group("right")),
                ),
            )
        )

    price_window_match = re.search(
        r"(?P<subject>[A-Za-z0-9\u4e00-\u9fff]{2,12}?)(?:的)?(?:近|最近)(?:\d+|[一二三四五六七八九十]+)(?:日|天|个交易日)"
        r"(?:价格分析|价格走势|走势分析|趋势分析|涨跌|K线|k线)",
        text,
    )
    if price_window_match:
        candidate = _clean_stock_candidate(price_window_match.group("subject"))
        if candidate:
            names.append(candidate)

    deep_subject = _clean_stock_candidate(extract_deep_research_subject(text) or "")
    if deep_subject:
        names.append(deep_subject)

    for pattern in OPERATION_SUBJECT_PATTERNS:
        match = re.search(pattern, text)
        if not match:
            continue
        candidate = _clean_stock_candidate(match.group("subject"))
        if candidate:
            names.append(candidate)

    value_match = re.search(
        r"(?P<subject>[A-Za-z0-9\u4e00-\u9fff]{2,12}?)(?:中线价值|值不值得关注|值得关注吗|值得关注|基本面|估值|现金流|财报|主力|散户|资金|筹码|股东)",
        text,
    )
    if value_match:
        candidate = _clean_stock_candidate(value_match.group("subject"))
        if candidate:
            names.append(candidate)

    long_term_match = re.search(
        r"(?P<subject>[A-Za-z0-9\u4e00-\u9fff]{2,12}?)(?:长线|长期|长期价值|能不能长期拿|适合拿三年|适合拿五年|适合拿十年|拿三年|拿五年|拿十年|护城河|分红|股东回报)",
        text,
    )
    if long_term_match:
        candidate = _clean_stock_candidate(long_term_match.group("subject"))
        if candidate:
            names.append(candidate)

    directional_match = re.search(
        r"(?P<subject>[A-Za-z0-9\u4e00-\u9fff]{2,12}?)(?:\u4eca\u5929|\u660e\u5929|\u73b0\u5728)?"
        r"(?:\u4f1a\u6da8\u5417|\u4f1a\u8dcc\u5417|\u6da8\u5417|\u8dcc\u5417|\u8d70\u52bf\u600e\u4e48\u6837)",
        text,
    )
    if directional_match:
        candidate = _clean_stock_candidate(directional_match.group("subject"))
        if candidate:
            names.append(candidate)

    return _dedupe(names)


def _clean_stock_candidate(candidate: str) -> Optional[str]:
    value = str(candidate or "").strip("，。！？?；:： ")
    value = re.sub(
        r"(?:的)?(?:近|最近)(?:\d+|[一二三四五六七八九十]+)(?:日|天|个交易日)(?:价格分析|价格走势|走势分析|趋势分析|涨跌|K线|k线)?$",
        "",
        value,
    )
    value = re.sub(r"(哪个好|谁更好|哪个更好|怎么样|更值得关注|更强|适合)$", "", value)
    value = re.sub(r"(今天|现在|明天|短线|中线|长线|长期|基本面|估值|财报|风险)$", "", value)
    value = re.sub(r"(的|近|最近)$", "", value)
    value = re.sub(r"^(小白|帮我|请问|想问|看看|分析一下|分析|聊聊)", "", value)
    value = re.sub(r"^(这只|这支|这个|这票|它)", "", value)
    value = re.sub(r"(股票|个股)$", "", value)
    value = value.strip("，。！？?；:： ")
    if not (2 <= len(value) <= 12):
        return None
    if value in GENERIC_STOCK_WORDS:
        return None
    if value in {"这只", "这支", "这个", "这票", "它", "现在"}:
        return None
    if value in {"能买吗", "能不能买", "现在能买", "现在能买吗"}:
        return None
    if any(topic in value for topic in ANALYSIS_TOPIC_WORDS):
        return None
    if any(value.endswith(suffix) for suffix in ("板块", "行业", "概念", "赛道", "大盘")):
        return None
    if value in AMBIGUOUS_STOCK_HINTS:
        return None
    return value


def _should_inherit_context_stock(text: str) -> bool:
    return _is_ambiguous_stock_question(text) or any(hint in text for hint in AMBIGUOUS_STOCK_HINTS)


def _is_ambiguous_stock_question(text: str) -> bool:
    normalized = text.strip("，。！？?；:： ")
    has_ambiguous_hint = any(hint in normalized for hint in AMBIGUOUS_STOCK_HINTS) or normalized in {"能买吗", "能不能买", "现在能买吗"}
    return has_ambiguous_hint and _contains_any(text, SHORT_TERM_KEYWORDS + DEEP_RESEARCH_KEYWORDS)


def _time_horizon(text: str) -> Optional[str]:
    if any(keyword in text for keyword in ("今天", "明天", "短线", "止损", "操作", "追", "价格分析", "价格走势", "走势分析", "趋势分析")) or _looks_like_price_window_analysis(text):
        return "short_term"
    if any(keyword in text for keyword in LONG_TERM_KEYWORDS):
        return "long_term"
    if any(keyword in text for keyword in ("中线", "价值", "估值", "基本面", "财报")):
        return "mid_term"
    return None


def _looks_like_bare_stock_query(text: str, stock_names: list[str], stock_codes: list[str]) -> bool:
    if stock_codes and text.upper() in {code.upper() for code in stock_codes}:
        return True
    if len(stock_names) == 1 and text == stock_names[0]:
        return True
    return False


def _looks_like_sector_question(text: str) -> bool:
    return _contains_any(text, SECTOR_KEYWORDS) and not _extract_stock_names(text) and not _extract_stock_codes(text)


def _looks_like_beginner_education(text: str) -> bool:
    if not _contains_any(text, EDUCATION_TERMS):
        return False
    return _contains_any(text, EDUCATION_ASK_KEYWORDS)


def _looks_like_compare_question(text: str) -> bool:
    if _looks_like_analysis_topic_connector(text):
        return False
    return _contains_any(text, ("和", "与", "跟", "vs", "VS", "对比", "比较", "哪个好", "谁更好", "哪个更好"))


def _looks_like_analysis_topic_connector(text: str) -> bool:
    topic_pairs = (
        "现金流和财报",
        "财报和现金流",
        "估值和现金流",
        "基本面和估值",
        "分红和回购",
        "回购和分红",
        "分红与回购",
        "回购与分红",
        "现金流与财报",
        "财报与现金流",
        "估值与现金流",
        "基本面与估值",
        "主力和散户",
        "散户和主力",
        "主力与散户",
        "散户与主力",
        "资金和筹码",
        "筹码和资金",
        "资金与筹码",
        "筹码与资金",
        "股东和筹码",
        "筹码和股东",
        "股东与筹码",
        "筹码与股东",
    )
    return any(pair in text for pair in topic_pairs)


def _is_missing_subject_capital_structure_question(text: str) -> bool:
    has_capital_topic = any(keyword in text for keyword in ("主力", "散户", "资金", "筹码", "股东户数", "持仓变化"))
    has_question_shape = any(keyword in text for keyword in ("情况", "怎么看", "分析", "如何", "怎么样"))
    return has_capital_topic and has_question_shape


def _looks_like_directional_short_term(text: str) -> bool:
    has_direction = any(
        keyword in text
        for keyword in (
            "\u4f1a\u6da8",
            "\u4f1a\u8dcc",
            "\u6da8\u5417",
            "\u8dcc\u5417",
            "\u8d70\u52bf",
        )
    )
    has_time_or_trade_context = any(
        keyword in text
        for keyword in (
            "\u4eca\u5929",
            "\u660e\u5929",
            "\u77ed\u7ebf",
            "\u73b0\u5728",
        )
    )
    return has_direction and (has_time_or_trade_context or "\u8d70\u52bf" in text)


def _looks_like_price_window_analysis(text: str) -> bool:
    has_window = bool(re.search(r"(?:近|最近)(?:\d+|[一二三四五六七八九十]+)(?:日|天|个交易日)", text))
    has_price_topic = any(keyword in text for keyword in ("价格分析", "价格走势", "走势分析", "趋势分析", "涨跌", "K线", "k线"))
    return has_window and has_price_topic


def _needs_chart(text: str) -> bool:
    return _contains_any(text, CHART_TRIGGER_KEYWORDS) or _looks_like_directional_short_term(text) or _looks_like_price_window_analysis(text)


def _chart_types(text: str) -> list[str]:
    if not _needs_chart(text):
        return []

    chart_types = ["kline", "volume", "ma5", "ma10", "ma20"]
    if any(keyword in text for keyword in ("MACD", "macd", "今天能不能买", "能不能追", "短线怎么看", "趋势怎么样")):
        chart_types.append("macd")
    if any(keyword in text for keyword in ("RSI", "rsi", "今天能不能买", "短线怎么看", "趋势怎么样")):
        chart_types.append("rsi")
    if any(keyword in text for keyword in ("KDJ", "kdj")):
        chart_types.append("kdj")
    return _dedupe(chart_types)


def _deep_research_chart_types(text: str) -> list[str]:
    if _needs_chart(text):
        return _chart_types(text)
    return ["kline", "volume", "ma5", "ma10", "ma20", "macd", "rsi", "kdj"]


def _directional_short_term_chart_types(text: str) -> list[str]:
    if not _looks_like_directional_short_term(text):
        return _chart_types(text)
    return ["kline", "volume", "ma5", "ma10", "ma20", "macd", "rsi"]


def _price_window_chart_types(text: str) -> list[str]:
    return ["kline", "volume", "ma5", "ma10", "ma20", "macd", "rsi", "kdj"]
