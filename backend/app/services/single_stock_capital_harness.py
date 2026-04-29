from __future__ import annotations

import re
from typing import Any, Iterable, Optional

from app.schemas import CardType, ResultCard, StructuredResult


CAPITAL_KEYWORDS = (
    "主力",
    "散户",
    "资金",
    "筹码",
    "股东户数",
    "前十大股东",
    "机构持仓",
    "持仓变化",
)


def enhance_single_stock_capital(
    route: Any,
    result: StructuredResult,
    *,
    user_message: str = "",
) -> StructuredResult:
    if not _is_capital_question(route, user_message):
        return result

    subject = str(getattr(route, "subject", "") or "").strip() or "这只股票"
    cards = _ensure_capital_cards(list(result.cards), subject)
    summary = _build_capital_summary(result, subject=subject)
    judgements = _dedupe(
        [
            *result.judgements,
            "主力和散户判断只基于已返回的资金、盘口、换手、股东户数、机构持仓等数据；不会把推测当作事实。",
            "单日主力资金和盘口只能说明短期交易状态，不能直接等同于主力长期加仓或散户集中离场。",
        ]
    )
    follow_ups = _dedupe(
        [
            *result.follow_ups,
            f"看{subject}股东户数变化",
            f"看{subject}机构持仓变化",
            f"看{subject}主力资金连续性",
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


def _is_capital_question(route: Any, user_message: str) -> bool:
    if not getattr(route, "single_security", False):
        return False
    text = _compact_text(user_message)
    return any(keyword in text for keyword in CAPITAL_KEYWORDS)


def _build_capital_summary(result: StructuredResult, *, subject: str) -> str:
    conclusion = _capital_conclusion(result, subject)
    lines = [
        f"一句话结论：{conclusion}",
        "",
        "主力和散户筹码框架：",
        "",
        f"1. 主力资金方向 - {_main_money_line(result)}",
        "",
        f"2. 成交量和换手 - {_volume_turnover_line(result)}",
        "",
        f"3. 盘口和逐笔成交 - {_order_book_line(result)}",
        "",
        f"4. 散户筹码线索 - {_retail_line(result)}",
        "",
        f"5. 股东户数变化 - {_shareholder_count_line(result)}",
        "",
        f"6. 前十大股东 / 机构持仓 - {_institution_line(result)}",
        "",
        f"7. 筹码稳定性判断 - {_chip_stability_line(result)}",
        "",
        f"8. 短期资金风险 - {_capital_risk_line(result)}",
        "",
        f"9. 数据缺口 - {_data_gap_line(result)}",
        "",
        f"10. 小白观察清单 - {_beginner_watch_line(result, subject)}",
    ]
    return "\n".join(lines)


def _capital_conclusion(result: StructuredResult, subject: str) -> str:
    flow = _money_flow_text(_metadata_value(result, "money_flow", "main_money_flow"))
    turnover = _metadata_value(result, "turnover", "turnover_rate")
    order_book = _order_book_signal(result)
    gaps = _missing_capital_data(result)

    bits = []
    if flow:
        bits.append(flow)
    if turnover is not None:
        bits.append(f"换手率约 {_format_percent(turnover)}")
    if order_book:
        bits.append(order_book)
    if not bits:
        bits.append("本次只拿到有限资金线索")

    gap_text = ""
    if gaps:
        gap_text = f"；但本次未返回{ '、'.join(gaps[:3]) }，还不能完整判断散户筹码和机构持仓变化"
    return f"{subject}的主力/散户情报要分开看：{ '，'.join(bits) }{gap_text}。"


def _main_money_line(result: StructuredResult) -> str:
    flow = _money_flow_text(_metadata_value(result, "money_flow", "main_money_flow"))
    if flow:
        return f"{flow}；先看这个方向是否连续，不要只看一天净流入或净流出。"
    line = _line(result, ("主力资金", "净流入", "净流出", "资金流向"))
    return line or "本次返回结果未覆盖主力资金净流入/净流出，不能判断主力资金方向。"


def _volume_turnover_line(result: StructuredResult) -> str:
    turnover = _metadata_value(result, "turnover", "turnover_rate")
    volume_ratio = _metadata_value(result, "volume_ratio")
    amount = _metadata_value(result, "amount", "turnover_amount")
    bits = _join_nonempty(
        [
            f"换手率约 {_format_percent(turnover)}" if turnover is not None else None,
            f"量比 {_format_number(volume_ratio)}" if volume_ratio is not None else None,
            f"成交额约 {_format_money(amount)}" if amount is not None else None,
        ]
    )
    if bits:
        return f"{bits}；换手和量比用来判断筹码活跃度，放量但资金流出时要降低短线信号质量。"
    line = _line(result, ("换手率", "量比", "成交额", "成交量"))
    return line or "本次返回结果未覆盖成交额、量比或换手率，筹码活跃度判断不完整。"


def _order_book_line(result: StructuredResult) -> str:
    line = _line(result, ("盘口", "委比", "逐笔", "买盘", "卖盘", "买一", "卖一"))
    if line:
        return f"{line}；盘口只能反映短时交易强弱，不能直接当成长期主力态度。"
    return "本次返回结果未覆盖五档盘口或逐笔成交，不能判断买卖盘哪边更主动。"


def _retail_line(result: StructuredResult) -> str:
    line = _line(result, ("散户", "筹码集中", "筹码分散", "户均持股"))
    if line:
        return line
    return "散户行为不能从单日涨跌直接反推；本次未返回筹码集中度或户均持股数据，因此只能把散户判断作为待验证项。"


def _shareholder_count_line(result: StructuredResult) -> str:
    value = _metadata_value(result, "shareholder_count", "shareholders", "holder_count")
    if value not in (None, "", []):
        return f"股东户数约 {_format_number(value)}；后续要看环比增加还是减少，增加通常意味着筹码更分散，减少通常意味着筹码更集中。"
    line = _line(result, ("股东户数", "户均持股", "筹码集中"))
    return line or "本次返回结果未覆盖股东户数变化，不能判断散户是否明显增多或减少。"


def _institution_line(result: StructuredResult) -> str:
    line = _line(result, ("前十大股东", "机构持仓", "基金持仓", "北向资金", "股东名单"))
    if line:
        return line
    return "本次返回结果未覆盖前十大股东或机构持仓变化，不能判断机构是否加仓、减仓或持仓稳定。"


def _chip_stability_line(result: StructuredResult) -> str:
    flow_value = _coerce_float(_metadata_value(result, "money_flow", "main_money_flow"))
    turnover = _coerce_float(_metadata_value(result, "turnover", "turnover_rate"))
    if flow_value is not None and turnover is not None:
        if flow_value < 0 and turnover >= 3:
            return "主力资金净流出且换手偏活跃，短期筹码可能在重新分配，需要观察后续是否继续放量转弱。"
        if flow_value > 0 and turnover <= 2:
            return "主力资金净流入且换手不高，说明资金承接线索偏正面，但仍要用连续多日数据确认。"
        return "资金方向和换手没有形成特别极端的组合，筹码稳定性需要继续看连续性。"
    return "筹码稳定性需要同时看主力资金连续性、换手率、股东户数和机构持仓；本次数据还不够完整。"


def _capital_risk_line(result: StructuredResult) -> str:
    risks = []
    flow_value = _coerce_float(_metadata_value(result, "money_flow", "main_money_flow"))
    volume_ratio = _coerce_float(_metadata_value(result, "volume_ratio"))
    if flow_value is not None and flow_value < 0:
        risks.append(f"主力资金净流出 {_format_money(abs(flow_value))}")
    if volume_ratio is not None and volume_ratio < 0.8:
        risks.append(f"量比 {_format_number(volume_ratio)}，短线资金参与度偏低")
    order_book = _order_book_signal(result)
    if order_book:
        risks.append(order_book)
    if risks:
        return "；".join(risks) + "。"
    return "主要风险是把单日盘口或资金流误读成长期趋势；必须结合连续多日资金、股东户数和机构持仓验证。"


def _data_gap_line(result: StructuredResult) -> str:
    gaps = _missing_capital_data(result)
    if not gaps:
        return "主力资金、盘口、换手、股东户数和机构持仓均已有线索，但仍建议用连续数据验证。"
    return f"本次还缺少{ '、'.join(gaps) }，所以不能把这份情报解读成完整筹码结论。"


def _beginner_watch_line(result: StructuredResult, subject: str) -> str:
    return (
        f"看{subject}主力和散户时，先盯三件事：主力资金是连续流入还是一日脉冲，换手率有没有突然放大，"
        "股东户数和机构持仓有没有同步改善；三者没有共振时，不要只凭盘口下结论。"
    )


def _ensure_capital_cards(cards: list[ResultCard], subject: str) -> list[ResultCard]:
    if not any(card.title == "主力和散户筹码 V1" for card in cards):
        cards = [
            ResultCard(
                type=CardType.CUSTOM,
                title="主力和散户筹码 V1",
                content="围绕主力资金、成交量和换手、盘口逐笔、股东户数、前十大股东、机构持仓和筹码稳定性做资金面整理。",
                metadata={"subject": subject, "focus": "capital_structure"},
            ),
            *cards,
        ]
    if not any(_card_type_value(card) == CardType.RISK_WARNING.value for card in cards):
        cards.append(
            ResultCard(
                type=CardType.RISK_WARNING,
                title="资金筹码风险提示",
                content="主力资金、盘口和逐笔成交只代表阶段性交易线索，不构成收益承诺，也不能单独决定买卖。",
                metadata={"subject": subject, "focus": "capital_structure"},
            )
        )
    return cards


def _missing_capital_data(result: StructuredResult) -> list[str]:
    checks = [
        ("主力资金", _metadata_value(result, "money_flow", "main_money_flow") is not None or bool(_line(result, ("主力资金", "净流入", "净流出")))),
        ("盘口逐笔", bool(_line(result, ("盘口", "委比", "逐笔", "买盘", "卖盘")))),
        ("股东户数变化", _metadata_value(result, "shareholder_count", "shareholders", "holder_count") is not None or bool(_line(result, ("股东户数", "户均持股")))),
        ("前十大股东/机构持仓变化", bool(_line(result, ("前十大股东", "机构持仓", "基金持仓", "北向资金")))),
    ]
    return [label for label, ok in checks if not ok]


def _order_book_signal(result: StructuredResult) -> Optional[str]:
    line = _line(result, ("盘口", "委比", "逐笔", "买盘", "卖盘"))
    if not line:
        return None
    if "卖盘更重" in line or "卖盘更主动" in line or "偏弱" in line:
        return "盘口卖压偏重"
    if "买盘更主动" in line or "买盘更重" in line or "偏强" in line:
        return "盘口买盘偏主动"
    return None


def _line(result: StructuredResult, markers: Iterable[str]) -> Optional[str]:
    for item in [*result.facts, *result.judgements, *(f"{card.title} {card.content}" for card in result.cards)]:
        text = _clean_line(item)
        if text and any(marker in text for marker in markers) and not _is_low_value(text):
            return text
    return None


def _metadata_value(result: StructuredResult, *keys: str) -> Any:
    for card in result.cards:
        for key in keys:
            value = card.metadata.get(key)
            if value not in (None, "", []):
                return value
    return None


def _clean_line(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    text = re.sub(r"查询 `[^`]+` 命中 \d+ 条，当前取 \d+ 条。?", "", text)
    text = text.replace("操作建议卡", "").strip()
    return text.strip(" -；;。")


def _is_low_value(text: str) -> bool:
    stripped = text.strip(" -；;。")
    low_value_exact = {"个股行业题材", "个股技术指标", "估值现金流补充", "财报核心指标", "风险点"}
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


def _money_flow_text(value: Any) -> Optional[str]:
    if value in (None, "", []):
        return None
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
        "必涨": "不能保证上涨",
        "无风险": "存在风险",
        "一定上涨": "不确定上涨",
        "直接买入": "需要结合风险承受能力再决策",
        "梭哈": "避免重仓冲动",
        "满仓": "避免满仓",
        "保证收益": "不承诺收益",
    }
    for source, target in replacements.items():
        cleaned = cleaned.replace(source, target)
    return cleaned
