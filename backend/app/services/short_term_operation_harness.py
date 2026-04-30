from __future__ import annotations

import re
from typing import Any, Iterable, Optional

from app.schemas import CardType, ResultCard, StructuredResult


OPERATION_PREFIXES = (
    "现在能不能追：",
    "更好的买点：",
    "失效条件：",
    "止损/观察位：",
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


def enhance_short_term_operation(
    route: Any,
    result: StructuredResult,
    *,
    user_message: str = "",
) -> StructuredResult:
    if not _is_short_term_operation(route):
        return result

    subject = str(getattr(route, "subject", "") or "").strip() or "这只股票"
    cards = _ensure_short_term_cards(list(result.cards), subject)
    staged = StructuredResult(
        summary=result.summary,
        table=result.table,
        cards=cards,
        chart_config=result.chart_config,
        facts=result.facts,
        judgements=result.judgements,
        follow_ups=result.follow_ups,
        sources=result.sources,
    )
    summary = _build_short_term_summary(
        staged,
        subject=subject,
        original_summary=result.summary,
        user_message=user_message,
    )
    judgements = list(result.judgements)
    missing_market_context = _missing_market_context_judgement(staged)
    if missing_market_context and missing_market_context not in "\n".join(judgements):
        judgements.append(missing_market_context)

    return StructuredResult(
        summary=_sanitize_text(summary),
        table=result.table,
        cards=cards,
        chart_config=result.chart_config,
        facts=result.facts,
        judgements=_dedupe(judgements),
        follow_ups=result.follow_ups,
        sources=result.sources,
    )


def _is_short_term_operation(route: Any) -> bool:
    mode = getattr(getattr(route, "mode", None), "value", getattr(route, "mode", ""))
    return bool(
        getattr(route, "single_security", False)
        and getattr(route, "entry_price_focus", False)
        and str(mode) == "short_term"
    )


def _build_short_term_summary(
    result: StructuredResult,
    *,
    subject: str,
    original_summary: str,
    user_message: str = "",
) -> str:
    if _is_price_window_question(user_message):
        return _build_price_window_summary(result, subject=subject, user_message=user_message)

    can_chase = _operation_line(result, "现在能不能追：")
    better_entry = _operation_line(result, "更好的买点：")
    invalidation = _operation_line(result, "失效条件：")
    stop_watch = _operation_line(result, "止损/观察位：")
    conclusion = _short_term_conclusion(
        result,
        subject=subject,
        user_message=user_message,
        can_chase=can_chase,
        better_entry=better_entry,
        invalidation=invalidation,
        stop_watch=stop_watch,
    )

    lines = [
        f"一句话结论：{conclusion}",
        "",
        "短线操作框架：",
        "",
        f"1. 当前短线状态 - {_first_matching_text(result.facts, ('当前价格', '现价', '今日', '涨跌幅')) or '当前只拿到部分行情快照，短线状态需要结合最新价格继续确认。'}",
        "",
        f"2. K线和量能 - {_kline_volume_line(result)}",
        "",
        f"3. 技术指标 - {_technical_line(result)}",
        "",
        f"4. 资金与盘口 - {_capital_line(result)}",
        "",
        f"5. 关键价格位 - {_price_zone_line(result)}",
        "",
        f"6. 现在能不能追 - {_strip_prefix(can_chase, '现在能不能追：') or '当前缺少完整操作信号，先观察，不把单次波动当成买入指令。'}",
        "",
        f"7. 更好的买点 - {_strip_prefix(better_entry, '更好的买点：') or '等待价格、量能和资金重新确认后再看。'}",
        "",
        f"8. 失效条件 - {_strip_prefix(invalidation, '失效条件：') or '跌破关键观察位、资金持续转弱或技术指标继续恶化时，原短线判断失效。'}",
        "",
        f"9. 止损/观察位 - {_strip_prefix(stop_watch, '止损/观察位：') or '当前缺少明确价格位，优先参考前低、短期均线和放量破位。'}",
        "",
        "10. 小白执行清单",
        "- 先看 K 线是否守住关键均线和观察位，不要只看一天涨跌。",
        "- 再看量能和主力资金是否配合，放量但资金转弱要谨慎。",
        "- 最后看失效条件是否触发，触发后先降低主观判断，重新评估。",
    ]
    return "\n".join(lines)


def _build_price_window_summary(result: StructuredResult, *, subject: str, user_message: str) -> str:
    window = _price_window_label(user_message)
    conclusion = _price_window_conclusion(result, subject=subject, window=window)
    lines = [
        f"一句话结论：{conclusion}",
        "",
        f"{window}价格分析框架：",
        "",
        f"1. 价格变化 - {_first_matching_text(result.facts, ('当前价格', '现价', '今日', '涨跌幅', '近5日', '近20日')) or f'本次只拿到{subject}部分行情快照，价格变化需要结合 K 线序列确认。'}",
        "",
        f"2. K线位置 - {_kline_volume_line(result)}",
        "",
        f"3. 量能变化 - {_first_matching_text([*result.facts, *result.judgements], ('量比', '成交量', '成交额', '放量', '缩量', '换手率')) or '当前量能数据不完整，无法判断上涨/下跌是否有成交量配合。'}",
        "",
        f"4. 均线关系 - {_moving_average_line(result)}",
        "",
        f"5. 技术指标 - {_technical_line(result)}",
        "",
        f"6. 资金和盘口 - {_capital_line(result)}",
        "",
        f"7. 强弱判断 - {_strength_line(result)}",
        "",
        f"8. 关键观察位 - {_price_zone_line(result)}",
        "",
        "9. 主要风险 - 近几日价格分析只能说明短期强弱，不能保证下一交易日涨跌；如果 K 线跌破关键观察位、量能放大但资金转弱，短线判断要降置信度。",
        "",
        "10. 小白观察清单",
        "- 先看价格是否站上 MA5/MA10，不要只看一根阳线或阴线。",
        "- 再看成交量是否配合，缩量反弹和放量下跌含义完全不同。",
        "- 最后看 MACD/RSI/KDJ 是否和价格同向修复，指标不共振时先降低判断强度。",
    ]
    return "\n".join(lines)


def _short_term_conclusion(
    result: StructuredResult,
    *,
    subject: str,
    user_message: str,
    can_chase: Optional[str],
    better_entry: Optional[str],
    invalidation: Optional[str],
    stop_watch: Optional[str],
) -> str:
    text = _compact_text(user_message)
    chase = _strip_prefix(can_chase, "现在能不能追：")
    better = _strip_prefix(better_entry, "更好的买点：")
    invalid = _strip_prefix(invalidation, "失效条件：")
    stop = _strip_prefix(stop_watch, "止损/观察位：")
    status = _first_matching_text(result.facts, ("当前价格", "现价", "今日", "涨跌幅")) or ""
    technical = _technical_line(result)

    if any(keyword in text for keyword in ("会跌", "会涨", "明天")):
        return f"{subject}明天涨跌无法保证，短线只能按条件看：{status or technical}；如果{invalid or '跌破关键观察位且资金转弱'}，原短线判断要降低置信度。"
    if any(keyword in text for keyword in ("止损", "要不要止损")):
        return f"{subject}要不要止损先看失效条件和观察位：{stop or '优先参考前低、短期均线和放量破位'}；若{invalid or '资金持续转弱或技术指标继续恶化'}，应重新评估。"
    if any(keyword in text for keyword in ("能不能追", "追")):
        return f"{subject}现在能不能追要看量价和承接，不宜只看单日波动；{chase or '当前更适合先观察'}"
    if any(keyword in text for keyword in ("能不能买", "能买吗", "今天")):
        return f"{subject}今天能不能买要看承接、量能和失效条件；{chase or '当前缺少完整操作信号，先观察'} 更好的买点是{better or '等价格、量能和资金重新确认'}。"
    if any(keyword in text for keyword in ("短线", "怎么看")):
        return f"{subject}短线重点看 K 线位置、量能和资金是否共振；{technical}"
    return f"{subject}短线操作先看量价、资金、关键价格位和失效条件；{chase or '当前先观察，不把单次波动当成买入指令'}"


def _price_window_conclusion(result: StructuredResult, *, subject: str, window: str) -> str:
    status = _first_matching_text(result.facts, ("当前价格", "现价", "今日", "涨跌幅", "近5日", "近20日")) or ""
    technical = _technical_line(result)
    chart_hint = _chart_hint(result)
    return f"{subject}{window}价格分析重点看价格变化、K线位置、量能和均线/指标是否共振；{status or technical}；{chart_hint}。"


def _kline_volume_line(result: StructuredResult) -> str:
    if result.chart_config and result.chart_config.items:
        return "已返回 K 线图表，可结合成交量、MA5/MA10/MA20、MACD、RSI 和 KDJ 一起看。"
    line = _first_matching_text([*result.facts, *result.judgements], ("今日 K 线", "K 线", "量比", "成交量", "成交额"))
    if line:
        return line
    return "当前缺少文字 K 线和可视化 K 线序列，因此短线 K 线判断置信度较低。"


def _technical_line(result: StructuredResult) -> str:
    line = _best_matching_text(_analysis_text_items(result), ("MACD", "RSI", "KDJ", "布林"))
    if line:
        explanation = _technical_indicator_explanation(line)
        return f"{line}。{explanation}" if explanation else line
    bits = _join_nonempty(
        [
            _metric_text(result, ("macd", "MACD"), "MACD"),
            _metric_text(result, ("rsi", "RSI"), "RSI"),
            _metric_text(result, ("kdj", "KDJ", "k"), "KDJ"),
            _metric_text(result, ("boll_mid", "bollinger_mid", "布林中轨"), "布林中轨"),
            _metric_text(result, ("volume_ratio", "量比"), "量比"),
        ]
    )
    if bits:
        explanation = _technical_indicator_explanation(bits)
        return f"{bits}。{explanation}" if explanation else bits
    return "当前缺少 MACD、RSI、KDJ、布林带等指标数据，不能只凭感觉判断强弱。"


def _moving_average_line(result: StructuredResult) -> str:
    line = _best_matching_text(_analysis_text_items(result), ("MA5", "MA10", "MA20", "均线", "站上", "低于"))
    if line:
        return _moving_average_explanation(line)
    bits = _join_nonempty(
        [
            _metric_text(result, ("ma5", "MA5", "5日均线"), "MA5"),
            _metric_text(result, ("ma10", "MA10", "10日均线"), "MA10"),
            _metric_text(result, ("ma20", "MA20", "20日均线"), "MA20"),
        ]
    )
    if bits:
        return _moving_average_explanation(bits)
    return "当前缺少 MA5/MA10/MA20 数据，均线强弱需要等 K 线指标补齐。"


def _capital_line(result: StructuredResult) -> str:
    line = _first_matching_text([*result.facts, *result.judgements], ("主力资金", "盘口", "换手率", "净流入", "净流出", "委比"))
    if line:
        return line
    return "当前资金与盘口信息不完整，短线结论需要降低置信度。"


def _price_zone_line(result: StructuredResult) -> str:
    observe_low = _metadata_value(result, "observe_low")
    observe_high = _metadata_value(result, "observe_high")
    stop_price = _metadata_value(result, "stop_price")
    bits = []
    if observe_low is not None and observe_high is not None:
        bits.append(f"观察区间 {_format_number(observe_low)}-{_format_number(observe_high)} 元")
    if stop_price is not None:
        bits.append(f"失效/止损参考 {_format_number(stop_price)} 元")
    return "，".join(bits) + "。" if bits else "当前缺少明确观察区间，先用前低、短期均线和放量破位做边界。"


def _strength_line(result: StructuredResult) -> str:
    technical = _technical_line(result)
    capital = _capital_line(result)
    if technical and "不完整" not in technical:
        return f"短期强弱先看技术指标是否修复，再结合资金确认；{technical}"
    if capital and "不完整" not in capital:
        return f"短期强弱暂时更多依赖资金和盘口确认；{capital}"
    return "当前短期强弱信号不完整，不能只凭近几日涨跌下结论。"


def _ensure_short_term_cards(cards: list[ResultCard], subject: str) -> list[ResultCard]:
    cards = _ensure_operation_guidance_card(cards, subject)
    if not any(_card_type_value(card) == CardType.RISK_WARNING.value for card in cards):
        cards.append(
            ResultCard(
                type=CardType.RISK_WARNING,
                title="短线风险提示",
                content="短线判断只能做条件分析，不能保证明天涨跌；如果价格跌破关键观察位、资金转弱或消息面出现变化，需要重新评估。",
                metadata={"subject": subject},
            )
        )
    return cards


def _ensure_operation_guidance_card(cards: list[ResultCard], subject: str) -> list[ResultCard]:
    updated: list[ResultCard] = []
    found = False
    for card in cards:
        if _card_type_value(card) != CardType.OPERATION_GUIDANCE.value:
            updated.append(card)
            continue
        found = True
        updated.append(
            ResultCard(
                type=card.type,
                title=card.title,
                content=_ensure_operation_sections(card.content),
                metadata=card.metadata,
            )
        )
    if found:
        return updated
    return [
        ResultCard(
            type=CardType.OPERATION_GUIDANCE,
            title="操作建议卡",
            content=_ensure_operation_sections(
                f"现在能不能追：先观察，不把当前结论理解为买入指令。\n"
                f"更好的买点：等待{subject}回踩后量能、趋势和承接重新确认。\n"
                "失效条件：价格跌破关键观察位、资金持续走弱，或基本面/消息面逻辑被证伪。\n"
                "止损/观察位：缺少明确价格数据时，先以前低、重要均线和放量破位作为观察边界。"
            ),
            metadata={"subject": subject},
        ),
        *updated,
    ]


def _ensure_operation_sections(content: str) -> str:
    lines = [line.strip() for line in str(content or "").splitlines() if line.strip()]
    existing = "\n".join(lines)
    defaults = {
        "现在能不能追：": "现在能不能追：先观察，不把当前结论理解为买入指令。",
        "更好的买点：": "更好的买点：等待量能、趋势和承接重新确认。",
        "失效条件：": "失效条件：价格跌破关键观察位、资金持续走弱，或消息面逻辑被证伪。",
        "止损/观察位：": "止损/观察位：先以前低、重要均线和放量破位作为观察边界。",
    }
    for prefix in OPERATION_PREFIXES:
        if prefix not in existing:
            lines.append(defaults[prefix])
    return "\n".join(lines)


def _operation_line(result: StructuredResult, prefix: str) -> Optional[str]:
    for card in result.cards:
        if _card_type_value(card) != CardType.OPERATION_GUIDANCE.value:
            continue
        for raw_line in str(card.content or "").splitlines():
            line = raw_line.strip()
            if line.startswith(prefix):
                return line
    return None


def _metadata_value(result: StructuredResult, *keys: str) -> Any:
    for card in result.cards:
        for key in keys:
            value = card.metadata.get(key)
            if value not in (None, "", []):
                return value
    if result.table:
        for row in result.table.rows:
            for key in keys:
                value = row.get(key)
                if value not in (None, "", []):
                    return value
    if result.chart_config and result.chart_config.items:
        latest = result.chart_config.items[-1]
        chart_aliases = {
            "ma5": latest.ma5,
            "MA5": latest.ma5,
            "5日均线": latest.ma5,
            "ma10": latest.ma10,
            "MA10": latest.ma10,
            "10日均线": latest.ma10,
            "ma20": latest.ma20,
            "MA20": latest.ma20,
            "20日均线": latest.ma20,
            "macd": latest.macd,
            "MACD": latest.macd,
            "rsi": latest.rsi,
            "RSI": latest.rsi,
            "kdj": latest.k,
            "KDJ": latest.k,
            "k": latest.k,
            "K": latest.k,
            "volume_ratio": None,
            "量比": None,
        }
        for key in keys:
            value = chart_aliases.get(key)
            if value not in (None, "", []):
                return value
    return None


def _metric_text(result: StructuredResult, keys: str | Iterable[str], label: str) -> Optional[str]:
    if isinstance(keys, str):
        lookup_keys = (keys,)
    else:
        lookup_keys = tuple(keys)
    value = _metadata_value(result, *lookup_keys)
    if value in (None, "", []):
        return None
    return f"{label} {_format_number(value)}"


def _analysis_text_items(result: StructuredResult) -> list[str]:
    items = [*result.facts, *result.judgements]
    for card in result.cards:
        if _card_type_value(card) != CardType.OPERATION_GUIDANCE.value:
            items.append(f"{card.title} {card.content}")
        if card.metadata:
            items.append(_metadata_as_indicator_text(card.metadata))
    if result.table:
        for row in result.table.rows:
            items.append(_metadata_as_indicator_text(row))
    if result.chart_config and result.chart_config.items:
        latest = result.chart_config.items[-1]
        items.append(
            _join_nonempty(
                [
                    _formatted_indicator_part("收", latest.close, digits=2),
                    _formatted_indicator_part("MA5", latest.ma5, digits=2),
                    _formatted_indicator_part("MA10", latest.ma10, digits=2),
                    _formatted_indicator_part("MA20", latest.ma20, digits=2),
                    _formatted_indicator_part("MACD", latest.macd, digits=3),
                    _formatted_indicator_part("RSI", latest.rsi, digits=2),
                    _formatted_indicator_part("KDJ", latest.k, digits=2),
                ]
            )
        )
    return [item for item in items if item]


def _metadata_as_indicator_text(values: dict[str, Any]) -> str:
    aliases = (
        ("close", "收"),
        ("收盘价", "收"),
        ("最新价", "收"),
        ("ma5", "MA5"),
        ("MA5", "MA5"),
        ("5日均线", "MA5"),
        ("ma10", "MA10"),
        ("MA10", "MA10"),
        ("10日均线", "MA10"),
        ("ma20", "MA20"),
        ("MA20", "MA20"),
        ("20日均线", "MA20"),
        ("macd", "MACD"),
        ("MACD", "MACD"),
        ("rsi", "RSI"),
        ("RSI", "RSI"),
        ("kdj", "KDJ"),
        ("KDJ", "KDJ"),
        ("k", "KDJ"),
        ("布林中轨", "布林中轨"),
        ("boll_mid", "布林中轨"),
        ("volume_ratio", "量比"),
        ("量比", "量比"),
    )
    parts = []
    for key, label in aliases:
        value = values.get(key)
        if value not in (None, "", []):
            parts.append(_formatted_indicator_part(label, value))
    return "，".join(parts)


def _formatted_indicator_part(label: str, value: Any, *, digits: Optional[int] = None) -> Optional[str]:
    if value in (None, "", []):
        return None
    number = _coerce_float(value)
    if number is None:
        return f"{label} {value}"
    if digits is None:
        if label in {"收", "MA5", "MA10", "MA20", "布林中轨"}:
            digits = 2
        elif label == "MACD":
            digits = 3
        elif label in {"RSI", "KDJ", "量比"}:
            digits = 2
        else:
            digits = 2
    return f"{label} {number:.{digits}f}"


def _best_matching_text(items: Iterable[str], markers: Iterable[str]) -> Optional[str]:
    candidates: list[tuple[int, str]] = []
    marker_tuple = tuple(markers)
    for item in items:
        text = _clean_line(item)
        if not text or not any(marker in text for marker in marker_tuple) or _is_low_value(text):
            continue
        indicator_hits = sum(1 for marker in ("MA5", "MA10", "MA20", "MACD", "RSI", "KDJ", "布林", "量比") if marker in text)
        number_hits = len(re.findall(r"-?\d+(?:\.\d+)?", text))
        candidates.append((indicator_hits * 10 + number_hits, text))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _chart_hint(result: StructuredResult) -> str:
    if result.chart_config and result.chart_config.items:
        return "已返回 K 线和技术指标图表"
    has_text_kline = bool(_first_matching_text([*result.facts, *result.judgements], ("今日 K 线", "K 线")))
    has_text_indicator = bool(_best_matching_text(_analysis_text_items(result), ("MACD", "RSI", "KDJ", "布林", "MA5", "MA10", "MA20")))
    if has_text_kline and has_text_indicator:
        return "本次已有文字 K 线和技术指标，但可视化 K 线图表暂未生成"
    if has_text_kline:
        return "本次已有文字 K 线，但可视化 K 线图表暂未生成"
    if has_text_indicator:
        return "本次已有技术指标文本，但可视化 K 线图表暂未生成"
    return "当前缺少 K 线 / 指标数据，因此短线判断置信度较低"


def _missing_market_context_judgement(result: StructuredResult) -> Optional[str]:
    if result.chart_config and result.chart_config.items:
        return None
    has_text_kline = bool(_first_matching_text([*result.facts, *result.judgements], ("今日 K 线", "K 线")))
    has_text_indicator = bool(_best_matching_text(_analysis_text_items(result), ("MACD", "RSI", "KDJ", "布林", "MA5", "MA10", "MA20")))
    if has_text_kline or has_text_indicator:
        return "当前未生成可视化 K 线图表；文字分析仅基于已返回的行情快照、K 线描述和技术指标。"
    return "当前缺少 K 线 / 指标数据，因此短线判断置信度较低。"


def _first_matching_text(items: Iterable[str], markers: Iterable[str]) -> Optional[str]:
    for item in items:
        text = _clean_line(item)
        if text and any(marker in text for marker in markers) and not _is_low_value(text):
            return text
    return None


def _clean_line(value: str) -> str:
    text = " ".join(str(value or "").split()).strip()
    text = re.sub(r"查询 `[^`]+` 命中 \d+ 条，当前取 \d+ 条。?", "", text)
    return text.strip("，。！？?；:： ")


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
        "深度研究框架",
    )
    return stripped in low_value_exact or any(marker in stripped for marker in low_value_markers)


def _moving_average_explanation(line: str) -> str:
    ma5 = _extract_indicator_value(line, "MA5")
    ma10 = _extract_indicator_value(line, "MA10")
    ma20 = _extract_indicator_value(line, "MA20")
    close = _extract_close_price(line)
    parts = []
    if close is not None and ma5 is not None:
        parts.append(f"价格{'站上' if close >= ma5 else '低于'}MA5")
    if close is not None and ma10 is not None:
        parts.append(f"{'站上' if close >= ma10 else '低于'}MA10")
    if close is not None and ma20 is not None:
        parts.append(f"{'站上' if close >= ma20 else '低于'}MA20")
    if ma5 is not None and ma20 is not None:
        parts.append("短均线强于中期均线" if ma5 >= ma20 else "短均线弱于中期均线")
    if not parts:
        return line
    return f"{line}；小白看法：{ '，'.join(parts) }，用来判断短线是修复、转弱还是震荡。"


def _technical_indicator_explanation(line: str) -> str:
    macd = _extract_indicator_value(line, "MACD")
    rsi = _extract_indicator_value(line, "RSI")
    kdj = _extract_indicator_value(line, "KDJ")
    boll_mid = _extract_indicator_value(line, "布林中轨")
    volume_ratio = _extract_indicator_value(line, "量比")
    parts = []
    if macd is not None:
        parts.append(f"MACD {'在零轴上方或红柱区，偏修复' if macd > 0 else '仍偏弱，需要等绿柱收敛或重新翻红'}")
    if rsi is not None:
        if rsi >= 70:
            parts.append("RSI接近过热，追高要谨慎")
        elif rsi <= 30:
            parts.append("RSI接近超卖，短线可能有修复但仍要看承接")
        else:
            parts.append("RSI处在中性区，暂未极端过热或超卖")
    if kdj is not None:
        parts.append("KDJ偏低，先看是否金叉修复" if kdj < 30 else "KDJ偏高，注意短线钝化或回落" if kdj > 80 else "KDJ处在中间区，方向还要结合价格确认")
    if boll_mid is not None:
        parts.append("布林中轨可作为短线强弱分界")
    if volume_ratio is not None:
        parts.append("量比偏缩量" if volume_ratio < 0.8 else "量比偏放量" if volume_ratio >= 1.2 else "量比大致中性")
    return "；".join(parts)


def _extract_indicator_value(text: str, label: str) -> Optional[float]:
    match = re.search(rf"{re.escape(label)}\s*[:：]?\s*(-?\d+(?:\.\d+)?)", text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _extract_close_price(text: str) -> Optional[float]:
    patterns = (
        r"收\s*(-?\d+(?:\.\d+)?)",
        r"当前价格\s*(-?\d+(?:\.\d+)?)",
        r"现价\s*(-?\d+(?:\.\d+)?)",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
    return None


def _first_sentence(value: str) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return ""
    return re.split(r"(?<=[。！？?])", text, maxsplit=1)[0].strip()


def _compact_text(value: str) -> str:
    return re.sub(r"\s+", "", str(value or ""))


def _is_price_window_question(value: str) -> bool:
    text = _compact_text(value)
    has_window = bool(re.search(r"(?:近|最近)(?:\d+|[一二三四五六七八九十]+)(?:日|天|个交易日)", text))
    has_topic = any(keyword in text for keyword in ("价格分析", "价格走势", "走势分析", "趋势分析", "涨跌", "K线", "k线"))
    return has_window and has_topic


def _price_window_label(value: str) -> str:
    text = _compact_text(value)
    match = re.search(r"((?:近|最近)(?:\d+|[一二三四五六七八九十]+)(?:日|天|个交易日))", text)
    return match.group(1) if match else "短线"


def _strip_prefix(text: Optional[str], prefix: str) -> str:
    value = str(text or "").strip()
    if value.startswith(prefix):
        return value[len(prefix) :].strip()
    return value


def _join_nonempty(parts: Iterable[Optional[str]]) -> str:
    return "，".join(part for part in parts if part)


def _format_number(value: Any) -> str:
    try:
        number = float(str(value).replace(",", "").replace("%", ""))
    except (TypeError, ValueError):
        return str(value)
    return f"{number:.2f}"


def _coerce_float(value: Any) -> Optional[float]:
    try:
        return float(str(value).replace(",", "").replace("%", ""))
    except (TypeError, ValueError):
        return None


def _card_type_value(card: ResultCard) -> str:
    return card.type.value if isinstance(card.type, CardType) else str(card.type)


def _dedupe(items: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
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
