from __future__ import annotations

import re
from typing import Any, Iterable, Optional

from app.schemas import CardType, ResultCard, StructuredResult


VALUE_KEYWORDS = (
    "中线",
    "中期",
    "价值",
    "值不值得关注",
    "值得关注吗",
    "值得关注",
    "基本面",
    "估值",
    "财报",
    "现金流",
)

FORBIDDEN_PHRASES = (
    "稳赚",
    "必涨",
    "无风险",
    "一定上涨",
    "直接买入",
    "梭哈",
    "满仓",
    "保证收益",
)


def enhance_single_stock_value(
    route: Any,
    result: StructuredResult,
    *,
    user_message: str = "",
) -> StructuredResult:
    if not _is_value_research(route, user_message):
        return result

    subject = str(getattr(route, "subject", "") or "").strip() or "这只股票"
    cards = _ensure_value_cards(list(result.cards), subject)
    summary = _build_value_summary(result, subject=subject, user_message=user_message)
    judgements = _dedupe(
        [
            *result.judgements,
            "中线价值判断只基于已返回 facts、cards、table、judgements 与 sources；不会补写或猜测缺失数据。",
            "若后续补齐同行估值、行业景气和公告研报数据，应重新刷新中线判断。",
        ]
    )
    follow_ups = _dedupe(
        [
            *result.follow_ups,
            f"只看{subject}估值和现金流",
            f"补充{subject}同行估值对比",
            f"跟踪{subject}未来1-3个季度观察点",
        ],
        limit=3,
    )
    return StructuredResult(
        summary=_sanitize_text(summary),
        table=result.table,
        cards=cards,
        chart_config=result.chart_config,
        facts=result.facts,
        judgements=judgements,
        follow_ups=follow_ups,
        sources=result.sources,
    )


def _is_value_research(route: Any, user_message: str) -> bool:
    if not getattr(route, "single_security", False):
        return False
    if getattr(route, "entry_price_focus", False):
        return False
    text = _compact_text(user_message)
    if _is_capital_structure_question(text):
        return False
    if any(keyword in text for keyword in ("长线", "长期", "十年", "三年", "五年", "护城河", "分红")):
        return False
    return any(keyword in text for keyword in VALUE_KEYWORDS)


def _is_capital_structure_question(text: str) -> bool:
    capital_keywords = ("主力", "散户", "资金", "筹码", "股东户数", "前十大股东", "机构持仓", "持仓变化")
    return any(keyword in text for keyword in capital_keywords)


def _build_value_summary(result: StructuredResult, *, subject: str, user_message: str = "") -> str:
    conclusion = _value_conclusion(result, subject, user_message=user_message)
    lines = [
        f"一句话结论：{conclusion}",
        "",
        "中线价值框架：",
        "",
        f"1. 公司赚钱逻辑 - {_business_model_line(result, subject)}",
        "",
        f"2. 业绩增长质量 - {_fundamental_line(result)}",
        "",
        f"3. 盈利能力 - {_profitability_line(result)}",
        "",
        f"4. 估值位置 - {_valuation_line(result)}",
        "",
        f"5. 现金流验证 - {_cashflow_line(result)}",
        "",
        f"6. 行业景气和竞争位置 - {_industry_line(result)}",
        "",
        f"7. 资金和机构态度 - {_capital_line(result)}",
        "",
        f"8. 未来1-3个季度观察点 - {_quarter_watch_line(result, subject)}",
        "",
        f"9. 中线风险 - {_value_risk_line(result)}",
        "",
        f"10. 是否值得继续跟踪 - {_tracking_line(result, subject)}",
    ]
    return "\n".join(lines)


def _fundamental_line(result: StructuredResult) -> str:
    line = _line(result, ("最新财报期", "营收", "归母净利润", "净利润", "业绩"))
    if line:
        return line
    return "当前缺少营收、净利润和同比增速数据，因此业绩增长质量判断置信度较低。"


def _value_conclusion(result: StructuredResult, subject: str, *, user_message: str = "") -> str:
    intent = _value_question_intent(subject, result, user_message=user_message)
    pe = _coerce_float(_metadata_value(result, "pe"))
    pb = _coerce_float(_metadata_value(result, "pb"))
    roe = _coerce_float(_metadata_value(result, "roe"))
    gross_margin = _coerce_float(_metadata_value(result, "gross_margin"))
    cashflow = _coerce_float(_metadata_value(result, "operating_cash_flow"))
    profit_growth = _coerce_float(_metadata_value(result, "profit_growth"))
    revenue_growth = _coerce_float(_metadata_value(result, "revenue_growth"))

    quality_bits = []
    if roe is not None:
        quality_bits.append(f"ROE约 {roe:.2f}%")
    if gross_margin is not None:
        quality_bits.append(f"毛利率约 {gross_margin:.2f}%")
    if cashflow is not None and cashflow > 0:
        quality_bits.append("经营现金流为正")
    valuation_bits = []
    if pe is not None:
        valuation_bits.append(f"PE约 {pe:.2f}")
    if pb is not None:
        valuation_bits.append(f"PB约 {pb:.2f}")
    growth_bits = []
    if revenue_growth is not None:
        growth_bits.append(f"营收同比约 {revenue_growth:.2f}%")
    if profit_growth is not None:
        growth_bits.append(f"净利润同比约 {profit_growth:.2f}%")

    valuation_text = "、".join(valuation_bits) if valuation_bits else "估值数据不完整"
    quality_text = "、".join(quality_bits) if quality_bits else "质量数据不完整"
    growth_text = "、".join(growth_bits) if growth_bits else "还需要补充增速"

    if intent == "fundamental":
        return (
            f"{subject}基本面要重点看增长、盈利能力和现金流三条线；当前质量锚点是{quality_text}，"
            f"增长端{growth_text}，估值端{valuation_text}。若现金流和利润同步，基本面可信度更高；若增速放缓但估值不低，中线吸引力会下降。"
        )
    if intent == "cashflow":
        return (
            f"{subject}现金流和财报质量要看利润有没有现金流支撑；当前质量锚点是{quality_text}，"
            f"增长端{growth_text}，估值端{valuation_text}。重点继续核对经营现金流、净利润增速和负债率是否匹配。"
        )
    if intent == "watch":
        return (
            f"{subject}是否值得关注，关键看质量、估值和行业催化是否同时成立；当前质量锚点是{quality_text}，"
            f"估值端{valuation_text}，增长端{growth_text}。数据不完整时更适合放入观察池，而不是直接下结论。"
        )
    if intent == "valuation":
        return (
            f"{subject}估值贵不贵不能只看价格；当前可见估值锚点是{valuation_text}，"
            f"质量锚点是{quality_text}，增长端{growth_text}；缺少同行估值对比前，只能判断是否值得继续跟踪，不能直接断言便宜或昂贵。"
        )
    if valuation_bits or quality_bits:
        return (
            f"{subject}中线价值要看业绩质量、估值现金流和行业景气是否匹配；当前质量锚点是{quality_text}，"
            f"估值端{valuation_text}，增长端{growth_text}。缺少同行对比前，更适合继续跟踪验证。"
        )
    return f"{subject}的中线价值需要先补齐 PE/PB/PS、ROE、利润增速、经营现金流和同行估值对比，再判断是否值得关注。"


def _value_question_intent(subject: str, result: StructuredResult, *, user_message: str = "") -> str:
    query_text = " ".join(source.query for source in result.sources)
    combined = _compact_text(f"{subject}{user_message}{query_text}")
    if any(keyword in combined for keyword in ("现金流", "财报质量", "财报")):
        return "cashflow"
    if any(keyword in combined for keyword in ("基本面",)):
        return "fundamental"
    if any(keyword in combined for keyword in ("估值", "贵不贵", "便宜", "贵吗")):
        return "valuation"
    if any(keyword in combined for keyword in ("值不值得关注", "值得关注", "关注吗")):
        return "watch"
    return "value"


def _business_model_line(result: StructuredResult, subject: str) -> str:
    business = _business_text(result)
    industry = _clean_taxonomy(_metadata_value(result, "industry"))
    concept = _clean_taxonomy(_metadata_value(result, "concept"))
    if business:
        return f"{subject}主营线索是{business}；中线看点是主营能否继续带来营收、利润和现金流的同步增长。"
    if industry or concept:
        return f"{subject}当前行业/题材线索是 {industry or '行业缺失'}、{concept or '概念缺失'}；中线仍要回到主营收入、利润率和现金流验证。"
    return f"{subject} 当前缺少完整主营业务和赚钱逻辑数据，因此公司画像置信度较低。"


def _profitability_line(result: StructuredResult) -> str:
    bits = _join_nonempty(
        [
            _metric(result, "roe", "ROE", percent=True),
            _metric(result, "gross_margin", "毛利率", percent=True),
            _metric(result, "net_margin", "净利率", percent=True),
            _metric(result, "debt_ratio", "资产负债率", percent=True),
        ]
    )
    if bits:
        return f"盈利能力锚点包括 {bits}，后续重点看这些指标是否稳定。"
    line = _line(result, ("ROE", "毛利率", "净利率", "资产负债率", "基本面指标"))
    return line or "当前缺少 ROE、利润率和负债率数据，因此盈利质量判断不完整。"


def _valuation_line(result: StructuredResult) -> str:
    bits = _join_nonempty(
        [
            _metric(result, "pe", "PE(TTM)"),
            _metric(result, "pb", "PB"),
            _metric(result, "ps", "PS"),
        ]
    )
    if bits:
        return f"当前可追踪估值锚点包括 {bits}；若缺少同行对比，暂时不能直接判断相对行业偏贵或偏便宜。"
    line = _line(result, ("PE", "PB", "PS", "估值", "市盈", "市净", "市销"))
    return line or "当前缺少 PE / PB / PS 和同行估值对比，因此估值位置判断置信度较低。"


def _cashflow_line(result: StructuredResult) -> str:
    cashflow = _metadata_value(result, "operating_cash_flow")
    if cashflow is not None:
        numeric = _coerce_float(cashflow)
        if numeric is not None and numeric > 0:
            return f"经营现金流为 {_format_money(cashflow)}，目前更像有现金流支撑，但仍要继续和净利润同步验证。"
        return f"经营现金流为 {_format_money(cashflow)}，需要警惕利润好看但现金流承压。"
    line = _line(result, ("经营现金流", "现金流"))
    return line or "当前缺少经营现金流数据，因此无法排除利润好看但现金流较弱的风险。"


def _industry_line(result: StructuredResult) -> str:
    industry = _clean_taxonomy(_metadata_value(result, "industry"))
    concept = _clean_taxonomy(_metadata_value(result, "concept"))
    if industry or concept:
        generic_note = "行业归类偏泛，" if _is_generic_taxonomy(industry) else ""
        return f"{generic_note}当前行业/题材是 {industry or '行业缺失'}、{concept or '概念缺失'}；中线要继续看板块景气、需求变化和同行估值对比。"
    line = _line(result, ("景气", "竞争", "龙头", "政策", "周期"))
    return line or "当前缺少行业景气、竞争格局和政策周期数据，中线行业判断仍不完整。"


def _capital_line(result: StructuredResult) -> str:
    money_flow = _metadata_value(result, "money_flow", "main_money_flow")
    turnover = _metadata_value(result, "turnover", "turnover_rate")
    bits = _join_nonempty(
        [
            _money_flow_text(money_flow) if money_flow is not None else None,
            f"换手率约 {_format_percent(turnover)}" if turnover is not None else None,
        ]
    )
    if bits:
        return f"{bits}；这只能说明阶段性资金和筹码活跃度，中线还需要机构持仓、股东户数和前十大股东变化来验证。"
    line = _line(result, ("机构", "股东", "股东户数", "前十大股东", "筹码"))
    return line or "当前缺少机构持仓、股东户数和筹码稳定性数据，资金态度只能作为弱参考。"


def _quarter_watch_line(result: StructuredResult, subject: str) -> str:
    return (
        f"重点看{subject}后续财报里的营收/净利润增速、经营现金流、行业景气和公告催化是否继续匹配；"
        "如果增长放缓且估值没有同步消化，中线吸引力会下降。"
    )


def _value_risk_line(result: StructuredResult) -> str:
    risks = []
    debt_ratio = _coerce_float(_metadata_value(result, "debt_ratio"))
    if debt_ratio is not None and debt_ratio >= 60:
        risks.append(f"资产负债率约 {debt_ratio:.2f}%，财务杠杆偏高")
    if _metadata_value(result, "operating_cash_flow") is None:
        risks.append("经营现金流缺失，利润质量仍需验证")
    if _metadata_value(result, "pe") is None and _metadata_value(result, "pb") is None:
        risks.append("估值锚点不完整")
    risks.append("行业景气、政策节奏和公告事件可能改变中线逻辑")
    return "；".join(risks) + "。"


def _tracking_line(result: StructuredResult, subject: str) -> str:
    if _metadata_value(result, "operating_cash_flow") is not None and (
        _metadata_value(result, "pe") is not None or _metadata_value(result, "pb") is not None
    ):
        return f"{subject}可以继续放入观察池，但更适合按财报、估值和行业催化逐步验证，不适合只靠单日涨跌做判断。"
    return f"{subject}当前仍有关键数据缺口，适合先观察和补数据，等财报、估值现金流和行业对比更完整后再提高判断置信度。"


def _ensure_value_cards(cards: list[ResultCard], subject: str) -> list[ResultCard]:
    if not any(card.title == "单股中线价值 V1" for card in cards):
        cards = [
            ResultCard(
                type=CardType.CUSTOM,
                title="单股中线价值 V1",
                content="围绕业绩增长、盈利能力、估值现金流、行业景气、资金筹码和未来1-3个季度观察点做中线价值整理。",
                metadata={"subject": subject, "horizon": "mid_term"},
            ),
            *cards,
        ]
    if not any(_card_type_value(card) == CardType.RISK_WARNING.value for card in cards):
        cards.append(
            ResultCard(
                type=CardType.RISK_WARNING,
                title="中线风险提示",
                content="中线价值分析不等于收益承诺；财报、估值、行业景气、公告事件和市场流动性变化都可能改变判断。",
                metadata={"subject": subject, "horizon": "mid_term"},
            )
        )
    return cards


def _line(result: StructuredResult, markers: Iterable[str]) -> Optional[str]:
    for item in [*result.facts, *result.judgements, *(f"{card.title} {card.content}" for card in result.cards)]:
        text = _clean_line(item)
        if text and any(marker in text for marker in markers) and not _is_low_value(text):
            return text
    return None


def _metric(result: StructuredResult, key: str, label: str, *, percent: bool = False) -> Optional[str]:
    value = _metadata_value(result, key)
    if value in (None, "", []):
        return None
    return f"{label} {_format_percent(value) if percent else _format_number(value)}"


def _metadata_value(result: StructuredResult, *keys: str) -> Any:
    for card in result.cards:
        for key in keys:
            value = card.metadata.get(key)
            if value not in (None, "", []):
                return value
    return None


def _clean_line(value: str) -> str:
    text = " ".join(str(value or "").split()).strip()
    text = re.sub(r"查询 `[^`]+` 命中 \d+ 条，当前取 \d+ 条。?", "", text)
    return text.strip(" -；;。")


def _is_low_value(text: str) -> bool:
    stripped = text.strip(" -；;。")
    low_value_exact = {"个股行业题材", "估值现金流补充", "财报核心指标", "风险点"}
    low_value_markers = (
        "覆盖状态",
        "已覆盖",
        "查询",
        "命中",
        "使用边界",
        "单股实时补充来自",
        "同花顺题材补充 已补充",
        "已补充地域、概念和主营业务",
    )
    return stripped in low_value_exact or any(marker in stripped for marker in low_value_markers)


def _first_sentence(value: str) -> str:
    text = " ".join(str(value or "").split()).strip()
    return re.split(r"(?<=[。！？?])", text, maxsplit=1)[0].strip() if text else ""


def _business_text(result: StructuredResult) -> Optional[str]:
    metadata_business = _metadata_value(result, "business", "main_business")
    if metadata_business not in (None, "", []):
        return _clean_line(str(metadata_business))
    for item in result.facts:
        text = _clean_line(item)
        match = re.search(r"主营业务摘要[:：](?P<business>.+)", text)
        if match:
            return match.group("business").strip("。；; ")
        match = re.search(r"主营业务[:：](?P<business>.+)", text)
        if match:
            return match.group("business").strip("。；; ")
    return None


def _clean_taxonomy(value: Any) -> Optional[str]:
    if value in (None, "", []):
        return None
    if isinstance(value, list):
        parts = [str(item).strip() for item in value]
    else:
        parts = re.split(r"[、,，;；/]+", str(value))
    cleaned: list[str] = []
    seen: set[str] = set()
    for part in parts:
        item = part.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        cleaned.append(item)
    return "、".join(cleaned[:6]) if cleaned else None


def _is_generic_taxonomy(value: Optional[str]) -> bool:
    if not value:
        return False
    generic_parts = {"综合", "综合Ⅲ", "其它", "其他", "未分类"}
    parts = set(re.split(r"[、,，;；/]+", value))
    return bool(parts) and parts.issubset(generic_parts)


def _money_flow_text(value: Any) -> str:
    numeric = _coerce_float(value)
    if numeric is None:
        return f"主力资金 {value}"
    direction = "净流入" if numeric >= 0 else "净流出"
    return f"主力资金{direction} {_format_money(abs(numeric))}"


def _compact_text(value: str) -> str:
    return re.sub(r"\s+", "", str(value or ""))


def _join_nonempty(parts: Iterable[Optional[str]]) -> str:
    return "，".join(part for part in parts if part)


def _coerce_float(value: Any) -> Optional[float]:
    try:
        return float(str(value).replace(",", "").replace("%", ""))
    except (TypeError, ValueError):
        return None


def _format_number(value: Any) -> str:
    number = _coerce_float(value)
    return str(value) if number is None else f"{number:.2f}"


def _format_percent(value: Any) -> str:
    number = _coerce_float(value)
    return str(value) if number is None else f"{number:.2f}%"


def _format_money(value: Any) -> str:
    number = _coerce_float(value)
    if number is None:
        return str(value)
    if abs(number) >= 1e8:
        return f"{number / 1e8:.2f}亿"
    if abs(number) >= 1e4:
        return f"{number / 1e4:.2f}万"
    return f"{number:.2f}"


def _card_type_value(card: ResultCard) -> str:
    return card.type.value if isinstance(card.type, CardType) else str(card.type)


def _dedupe(items: Iterable[str], *, limit: Optional[int] = None) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
        if limit is not None and len(result) >= limit:
            break
    return result


def _sanitize_text(text: str) -> str:
    cleaned = str(text or "")
    replacements = {
        "稳赚": "不承诺收益",
        "必涨": "无法保证上涨",
        "无风险": "需要关注风险",
        "一定上涨": "存在不确定性",
        "直接买入": "按条件观察",
        "梭哈": "避免重仓冲动",
        "满仓": "控制仓位",
        "保证收益": "不承诺收益",
    }
    for forbidden, replacement in replacements.items():
        cleaned = cleaned.replace(forbidden, replacement)
    return cleaned
