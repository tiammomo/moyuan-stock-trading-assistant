from __future__ import annotations

import re
from typing import Any, Iterable, Optional

from app.schemas import CardType, ResultCard, StructuredResult


LONG_TERM_KEYWORDS = (
    "长线",
    "长期",
    "长期价值",
    "能不能长期拿",
    "拿三年",
    "拿五年",
    "拿十年",
    "十年",
    "护城河",
    "分红",
    "股东回报",
)


def enhance_single_stock_long_term(
    route: Any,
    result: StructuredResult,
    *,
    user_message: str = "",
) -> StructuredResult:
    if not _is_long_term_research(route, user_message):
        return result

    subject = str(getattr(route, "subject", "") or "").strip() or "这只股票"
    cards = _ensure_long_term_cards(list(result.cards), subject)
    summary = _build_long_term_summary(result, subject=subject, user_message=user_message)
    judgements = _dedupe(
        [
            *result.judgements,
            "长期质量判断只基于已返回数据；缺少分红、回购、长期ROE、行业空间或竞争格局时，结论需要降置信度。",
            "长期持有问题不能只看短期涨跌，应持续验证商业模式、现金流、资本开支和估值是否匹配。",
        ]
    )
    follow_ups = _dedupe(
        [
            *result.follow_ups,
            f"看{subject}护城河和竞争格局",
            f"看{subject}分红和股东回报",
            f"看{subject}长期ROE和现金流稳定性",
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


def _is_long_term_research(route: Any, user_message: str) -> bool:
    if not getattr(route, "single_security", False):
        return False
    if getattr(route, "entry_price_focus", False):
        return False
    text = _compact_text(user_message)
    return any(keyword in text for keyword in LONG_TERM_KEYWORDS)


def _build_long_term_summary(result: StructuredResult, *, subject: str, user_message: str = "") -> str:
    conclusion = _long_term_conclusion(result, subject, user_message=user_message)
    lines = [
        f"一句话结论：{conclusion}",
        "",
        "长期质量框架：",
        "",
        f"1. 商业模式是不是好生意 - {_business_line(result, subject)}",
        "",
        f"2. 护城河是否稳定 - {_moat_line(result)}",
        "",
        f"3. 行业空间和周期位置 - {_industry_line(result)}",
        "",
        f"4. 公司竞争地位 - {_position_line(result, subject)}",
        "",
        f"5. ROE 和现金流长期稳定性 - {_roe_cashflow_line(result)}",
        "",
        f"6. 负债和资本开支压力 - {_debt_line(result)}",
        "",
        f"7. 分红 / 回购 / 股东回报 - {_shareholder_return_line(result)}",
        "",
        f"8. 估值是否透支长期预期 - {_valuation_expectation_line(result)}",
        "",
        f"9. 长期风险 - {_long_term_risk_line(result)}",
        "",
        f"10. 长期跟踪清单 - {_tracking_line(subject)}",
    ]
    return "\n".join(lines)


def _long_term_conclusion(result: StructuredResult, subject: str, *, user_message: str = "") -> str:
    focus = _long_term_focus(user_message, result)
    roe = _coerce_float(_metadata_value(result, "roe"))
    gross_margin = _coerce_float(_metadata_value(result, "gross_margin"))
    cashflow = _coerce_float(_metadata_value(result, "operating_cash_flow"))
    debt_ratio = _coerce_float(_metadata_value(result, "debt_ratio"))
    pe = _coerce_float(_metadata_value(result, "pe"))
    pb = _coerce_float(_metadata_value(result, "pb"))
    shareholder_events = _shareholder_return_events(result)
    industry = _clean_taxonomy(_metadata_value(result, "industry"))
    concept = _clean_taxonomy(_metadata_value(result, "concept"))

    quality_signals = sum(
        [
            1 if roe is not None and roe >= 10 else 0,
            1 if gross_margin is not None and gross_margin >= 30 else 0,
            1 if cashflow is not None and cashflow > 0 else 0,
            1 if debt_ratio is not None and debt_ratio < 60 else 0,
        ]
    )
    known_quality_metrics = sum(
        1
        for value in (roe, gross_margin, cashflow, debt_ratio, pe, pb)
        if value is not None
    )
    valuation_known = pe is not None or pb is not None
    quality_text = _join_nonempty(
        [
            f"ROE约 {roe:.2f}%" if roe is not None else None,
            f"毛利率约 {gross_margin:.2f}%" if gross_margin is not None else None,
            "经营现金流为正" if cashflow is not None and cashflow > 0 else None,
            f"资产负债率约 {debt_ratio:.2f}%" if debt_ratio is not None else None,
        ]
    )
    valuation_text = _join_nonempty(
        [
            f"PE约 {pe:.2f}" if pe is not None else None,
            f"PB约 {pb:.2f}" if pb is not None else None,
        ]
    )

    if focus == "moat":
        return (
            f"{subject}护城河不能只看概念，重点看主营壁垒、成本优势、品牌/渠道和市占率；"
            f"当前可见质量线索是{quality_text or '质量数据不完整'}，行业/题材线索是{industry or '行业缺失'}、{concept or '概念缺失'}，还需要同行份额和利润率对比来验证强弱。"
        )
    if focus == "shareholder_return":
        return (
            f"{subject}分红和回购要区分“有动作”和“回报稳定”；当前可确认{('有' + '、'.join(shareholder_events) + '相关动作') if shareholder_events else '本次返回未覆盖明确股东回报动作'}，"
            f"但还需要分红率、股息率、回购金额占市值比例和多年连续性，才能判断长期股东回报质量。"
        )
    if focus == "hold_years":
        return (
            f"{subject}适不适合拿三年，要看质量指标能否跨周期稳定；当前可见质量线索是{quality_text or '质量数据不完整'}，"
            f"估值线索是{valuation_text or '估值数据不完整'}，还要持续验证行业地位和现金流连续性。"
        )
    if focus == "long_value":
        return (
            f"{subject}长线价值要看商业模式、行业空间、ROE现金流和估值是否匹配；当前可见质量线索是{quality_text or '质量数据不完整'}，"
            f"估值线索是{valuation_text or '估值数据不完整'}，缺少同行对比时更适合继续跟踪验证。"
        )
    if quality_signals >= 3 and valuation_known:
        return (
            f"从已返回数据看，{subject}具备长期跟踪价值，质量锚点主要在盈利能力、现金流和较可控的负债；"
            "但长期能不能拿，关键还要看增长是否延续、估值有没有透支，以及行业竞争地位有没有被削弱。"
        )
    if quality_signals >= 2:
        incomplete_parts = []
        if not industry and not concept:
            incomplete_parts.append("行业空间")
        if pe is None and pb is None:
            incomplete_parts.append("估值")
        if not incomplete_parts:
            incomplete_parts.extend(["同行对比", "多期连续数据"])
        incomplete_text = "、".join(incomplete_parts)
        return (
            f"{subject}已有部分长期质量线索：{quality_text or '质量指标有返回'}，估值线索是{valuation_text or '估值数据不完整'}；"
            f"但{incomplete_text}还需要补充验证，更适合继续跟踪，不适合只凭短期涨跌决定长期持有。"
        )
    if known_quality_metrics >= 4:
        weak_reasons = _join_nonempty(
            [
                f"ROE约 {roe:.2f}% 偏弱" if roe is not None and roe < 10 else None,
                f"毛利率约 {gross_margin:.2f}% 偏低" if gross_margin is not None and gross_margin < 15 else None,
                "经营现金流为负" if cashflow is not None and cashflow <= 0 else None,
                f"PE约 {pe:.2f} 需要增长来消化" if pe is not None and pe >= 25 else None,
            ]
        )
        return (
            f"{subject}不是数据缺口多，而是已返回的长期质量信号偏弱：{weak_reasons or '盈利效率、现金流或估值支撑仍需验证'}；"
            "更适合作为周期股跟踪，重点看商品价格周期、成本控制、现金流修复和估值消化。"
        )
    return (
        f"{subject}当前长期判断的数据缺口较多，先把商业模式、ROE现金流、负债、估值和股东回报补齐，"
        "再判断是否适合长期持有。"
    )


def _long_term_focus(user_message: str, result: StructuredResult) -> str:
    query_text = " ".join(source.query for source in result.sources)
    text = _compact_text(f"{user_message}{query_text}")
    if any(keyword in text for keyword in ("护城河", "壁垒", "强不强")):
        return "moat"
    if any(keyword in text for keyword in ("分红", "回购", "股东回报", "派息", "股息")):
        return "shareholder_return"
    if any(keyword in text for keyword in ("拿三年", "拿五年", "拿十年", "适合拿")):
        return "hold_years"
    if any(keyword in text for keyword in ("长线价值", "长期价值", "长线")):
        return "long_value"
    return "hold"


def _business_line(result: StructuredResult, subject: str) -> str:
    business = _business_text(result)
    industry = _clean_taxonomy(_metadata_value(result, "industry"))
    concept = _clean_taxonomy(_metadata_value(result, "concept"))
    gross_margin = _metadata_value(result, "gross_margin")
    if business:
        business = _summarize_business_text(business)
        margin_hint = f"毛利率约 {_format_percent(gross_margin)}，" if gross_margin is not None else ""
        if _is_resource_or_metal(industry, concept):
            return f"{subject}主营线索是{business}；{margin_hint}长期要看资源禀赋、冶炼加工成本、铜价/金属价格周期和资本开支效率。"
        if _is_semiconductor_packaging(industry, concept):
            return f"{subject}主营线索是{business}；{margin_hint}长期要看先进封装能力、客户结构、产能利用率、良率和资本开支效率。"
        return f"{subject}主营线索是{business}；{margin_hint}长期要看产品力、定价能力和渠道效率能否持续。"
    if industry or concept:
        return f"{subject}当前归属 {industry or '行业信息缺失'}，相关概念包括 {concept or '概念信息缺失'}；长期赚钱逻辑仍需回到主营产品、定价权和现金流。"
    return f"当前缺少{subject}主营业务和长期赚钱逻辑数据，因此商业模式判断置信度较低。"


def _moat_line(result: StructuredResult) -> str:
    industry = _clean_taxonomy(_metadata_value(result, "industry"))
    concept = _clean_taxonomy(_metadata_value(result, "concept"))
    gross_margin = _coerce_float(_metadata_value(result, "gross_margin"))
    cashflow = _coerce_float(_metadata_value(result, "operating_cash_flow"))
    industry_text = f"{industry or ''}{concept or ''}"
    if any(keyword in f"{industry}{concept}" for keyword in ("白酒", "超级品牌", "品牌")):
        return "行业和概念里已经出现品牌属性线索，护城河重点看品牌定价权、渠道库存、批价稳定性和高端需求是否保持。"
    if any(keyword in industry_text for keyword in ("汽车", "新能源车", "新能源汽车", "乘用车", "电池")):
        quality_bits = _join_nonempty(
            [
                f"毛利率约 {gross_margin:.2f}%" if gross_margin is not None else None,
                "经营现金流为正" if cashflow is not None and cashflow > 0 else None,
            ]
        )
        prefix = f"已有{quality_bits}这类经营质量线索，" if quality_bits else ""
        return f"{prefix}护城河重点看三件事：电池/整车垂直整合能力、规模制造带来的成本优势、车型迭代和渠道效率能否持续；当前还缺少市占率和同行毛利率对比，不能只凭题材断言很强。"
    if _is_resource_or_metal(industry, concept):
        return "资源/有色金属公司的护城河不主要看品牌，而要看矿山资源储量、自给率、冶炼成本、加工费议价能力和周期低点现金流韧性；当前还缺少这些细项，所以护城河只能先降置信度。"
    if _is_semiconductor_packaging(industry, concept):
        quality_bits = _join_nonempty(
            [
                f"毛利率约 {gross_margin:.2f}%" if gross_margin is not None else None,
                "经营现金流为正" if cashflow is not None and cashflow > 0 else None,
            ]
        )
        prefix = f"已有{quality_bits}这类经营质量线索，" if quality_bits else ""
        return f"{prefix}封测公司的护城河重点看先进封装能力、客户结构、产能利用率、制程良率和资本开支效率；当前还缺少客户份额、先进封装收入占比和同行毛利率对比，不能只凭研报标题判断护城河很强。"
    moat_line = _line(result, ("龙头", "品牌", "壁垒", "护城河", "市占率", "竞争"), exclude=("主营业务", "主营业务摘要"))
    if moat_line:
        return f"{_truncate_text(moat_line, 90)}；长期还要用市占率、价格体系和渠道稳定性继续验证。"
    return "当前缺少品牌壁垒、市占率、客户黏性或成本优势数据，因此护城河判断还不完整。"


def _industry_line(result: StructuredResult) -> str:
    industry = _clean_taxonomy(_metadata_value(result, "industry"))
    concept = _clean_taxonomy(_metadata_value(result, "concept"))
    if industry or concept:
        generic_note = "行业归类偏泛，" if _is_generic_taxonomy(industry) else ""
        return f"{generic_note}当前可确认的行业/题材是 {industry or '行业缺失'}、{concept or '概念缺失'}；长期重点不是题材热度，而是行业空间、周期位置和需求稳定性。"
    return _line(result, ("行业", "板块", "景气", "周期", "政策", "空间", "赛道")) or "当前缺少行业空间、景气度和周期位置数据，长期行业判断需要继续补齐。"


def _position_line(result: StructuredResult, subject: str) -> str:
    industry = _clean_taxonomy(_metadata_value(result, "industry"))
    concept = _clean_taxonomy(_metadata_value(result, "concept"))
    roe = _coerce_float(_metadata_value(result, "roe"))
    gross_margin = _coerce_float(_metadata_value(result, "gross_margin"))
    cashflow = _coerce_float(_metadata_value(result, "operating_cash_flow"))
    listing_board = _metadata_value(result, "listing_board")
    listing_place = _metadata_value(result, "listing_place")
    industry_text = f"{industry or ''}{concept or ''}"
    if any(keyword in industry_text for keyword in ("汽车", "新能源车", "新能源汽车", "乘用车", "电池")):
        quality_bits = _join_nonempty(
            [
                f"ROE约 {roe:.2f}%" if roe is not None else None,
                f"毛利率约 {gross_margin:.2f}%" if gross_margin is not None else None,
                "经营现金流为正" if cashflow is not None and cashflow > 0 else None,
            ]
        )
        return f"{subject}处在汽车/新能源车产业链，{quality_bits or '已返回数据还不足以量化竞争地位'}；竞争地位应重点用销量份额、电池自供比例、单车盈利、海外销量和同行毛利率对比来验证。"
    if _is_resource_or_metal(industry, concept):
        quality_bits = _join_nonempty(
            [
                f"ROE约 {roe:.2f}%" if roe is not None else None,
                f"毛利率约 {gross_margin:.2f}%" if gross_margin is not None else None,
                "经营现金流为正" if cashflow is not None and cashflow > 0 else "经营现金流为负" if cashflow is not None else None,
            ]
        )
        return f"{subject}处在有色/工业金属链条，{quality_bits or '已返回数据还不足以量化竞争地位'}；竞争地位应重点用铜资源储量、矿山自给率、冶炼产能、加工成本和同行现金流对比来验证。"
    if _is_semiconductor_packaging(industry, concept):
        quality_bits = _join_nonempty(
            [
                f"ROE约 {roe:.2f}%" if roe is not None else None,
                f"毛利率约 {gross_margin:.2f}%" if gross_margin is not None else None,
                "经营现金流为正" if cashflow is not None and cashflow > 0 else None,
            ]
        )
        return f"{subject}处在半导体封测链条，{quality_bits or '已返回数据还不足以量化竞争地位'}；竞争地位应重点用全球/国内封测份额、先进封装产能、客户结构和同行盈利能力对比来验证。"
    position_line = _line(result, ("龙头", "市占率", "份额", "竞争地位", "领先"), exclude=("上市板块", "上市地点", "主营业务"))
    if position_line:
        return f"{_truncate_text(position_line, 90)}；长期还要持续比较同行份额、利润率和渠道质量。"
    listing_bits = _join_nonempty(
        [
            f"上市板块 {listing_board}" if listing_board else None,
            f"上市地点 {listing_place}" if listing_place else None,
        ]
    )
    if listing_bits:
        return f"{listing_bits}只能说明上市属性，不能直接证明竞争地位；还需要同行市占率、品牌份额和盈利能力对比。"
    return f"{subject}当前只拿到部分行业归属线索，还不能明确判断是龙头、二线还是边缘公司。"


def _roe_cashflow_line(result: StructuredResult) -> str:
    bits = _join_nonempty(
        [
            _metric(result, "roe", "ROE", percent=True),
            _metric(result, "gross_margin", "毛利率", percent=True),
            _metric(result, "operating_cash_flow", "经营现金流", money=True),
        ]
    )
    if bits:
        return f"长期质量锚点包括 {bits}；但还需要多期连续数据确认稳定性。"
    return _line(result, ("ROE", "经营现金流", "现金流", "毛利率")) or "当前缺少多期 ROE 和经营现金流数据，因此无法判断长期稳定性。"


def _debt_line(result: StructuredResult) -> str:
    debt_ratio = _metadata_value(result, "debt_ratio")
    if debt_ratio is not None:
        value = _coerce_float(debt_ratio)
        if value is not None and value >= 60:
            return f"资产负债率约 {value:.2f}%，长期跟踪时要重点看财务杠杆和资本开支压力。"
        return f"资产负债率约 {_format_percent(debt_ratio)}，仍需结合行业属性和资本开支判断压力。"
    return _line(result, ("资产负债率", "负债", "资本开支")) or "当前缺少资产负债率和资本开支数据，长期财务压力判断不完整。"


def _shareholder_return_line(result: StructuredResult) -> str:
    events = _shareholder_return_events(result)
    payout_ratio = _metadata_value(result, "payout_ratio", "dividend_payout_ratio")
    dividend_yield = _metadata_value(result, "dividend_yield", "股息率")
    buyback_amount = _metadata_value(result, "buyback_amount", "回购金额")
    details = _join_nonempty(
        [
            f"分红率 {_format_percent(payout_ratio)}" if payout_ratio is not None else None,
            f"股息率 {_format_percent(dividend_yield)}" if dividend_yield is not None else None,
            f"回购金额 {_format_money(buyback_amount)}" if buyback_amount is not None else None,
        ]
    )
    if events:
        action_text = "、".join(events)
        detail_text = f"本次还返回了{details}；" if details else ""
        missing_text = "" if details else "本次还未覆盖分红率、股息率和回购金额占市值比例；"
        return f"近期可确认有{action_text}相关动作，{detail_text}{missing_text}说明公司有股东回报安排；但还要结合多年连续性，才能判断“回报是否足够稳定”。"
    if details:
        return f"本次返回了{details}，但没有同步覆盖最近分红/回购公告和多年连续性；只能把股东回报作为待验证项，不能直接判断长期回报稳定。"
    return "本次返回结果未覆盖分红率、股息率、回购规模或连续派息记录；这一项只能标记为待补充，不能据此判断公司没有股东回报。"


def _valuation_expectation_line(result: StructuredResult) -> str:
    bits = _join_nonempty(
        [
            _metric(result, "pe", "PE(TTM)"),
            _metric(result, "pb", "PB"),
            _metric(result, "ps", "PS"),
        ]
    )
    if bits:
        return f"当前估值锚点包括 {bits}；长期判断要看估值是否已经提前透支未来增长。"
    return _line(result, ("PE", "PB", "PS", "估值")) or "当前缺少估值锚点和同行对比，无法判断长期预期是否已被透支。"


def _long_term_risk_line(result: StructuredResult) -> str:
    risks = []
    industry = _clean_taxonomy(_metadata_value(result, "industry"))
    concept = _clean_taxonomy(_metadata_value(result, "concept"))
    roe = _coerce_float(_metadata_value(result, "roe"))
    gross_margin = _coerce_float(_metadata_value(result, "gross_margin"))
    debt_ratio = _coerce_float(_metadata_value(result, "debt_ratio"))
    pe = _coerce_float(_metadata_value(result, "pe"))
    pb = _coerce_float(_metadata_value(result, "pb"))
    cashflow = _coerce_float(_metadata_value(result, "operating_cash_flow"))

    if debt_ratio is not None and debt_ratio >= 65:
        risks.append(f"资产负债率约 {debt_ratio:.2f}%，长期要防财务杠杆和资本开支压力")
    if gross_margin is not None and gross_margin < 25:
        risks.append(f"毛利率约 {gross_margin:.2f}%，若行业价格战加剧，盈利弹性可能被压缩")
    if roe is not None and roe < 10:
        risks.append(f"ROE约 {roe:.2f}%，长期回报效率还不算突出")
    if cashflow is None:
        risks.append("现金流稳定性缺失")
    elif cashflow <= 0:
        risks.append("经营现金流为负，利润兑现质量需要重点核对")
    if roe is None:
        risks.append("长期ROE稳定性缺失")
    if pe is None and pb is None:
        risks.append("估值锚点缺失")
    elif pe is not None and pe >= 25:
        risks.append(f"PE约 {pe:.2f}，如果增长放缓，估值消化压力会上升")
    elif pb is not None and pb >= 4:
        risks.append(f"PB约 {pb:.2f}，需要看资产回报率能否支撑估值")

    industry_text = f"{industry or ''}{concept or ''}"
    if any(keyword in industry_text for keyword in ("汽车", "新能源车", "新能源汽车", "乘用车")):
        risks.append("汽车行业受价格竞争、补贴政策、销量周期和技术迭代影响较大")
    elif _is_resource_or_metal(industry, concept):
        risks.append("有色金属行业受商品价格周期、矿山供给、冶炼加工费和资本开支影响较大")
    elif _is_semiconductor_packaging(industry, concept):
        risks.append("半导体封测行业受下游需求周期、先进封装资本开支、产能利用率和客户集中度影响较大")
    elif industry or concept:
        risks.append("行业景气、竞争格局和政策变化可能改变长期逻辑")

    if not risks:
        risks.append("当前风险数据不足，仍需补齐行业周期、竞争格局、估值和现金流连续性")
    return "；".join(_dedupe(risks, limit=4)) + "。"


def _tracking_line(subject: str) -> str:
    return f"长期跟踪{subject}时，优先看三件事：ROE和现金流能否跨周期稳定、行业地位有没有被削弱、估值有没有明显透支长期增长。"


def _ensure_long_term_cards(cards: list[ResultCard], subject: str) -> list[ResultCard]:
    if not any(card.title == "单股长期质量 V1" for card in cards):
        cards = [
            ResultCard(
                type=CardType.CUSTOM,
                title="单股长期质量 V1",
                content="围绕商业模式、护城河、行业空间、ROE现金流、负债资本开支、股东回报和长期风险做质量整理。",
                metadata={"subject": subject, "horizon": "long_term"},
            ),
            *cards,
        ]
    if not any(_card_type_value(card) == CardType.RISK_WARNING.value for card in cards):
        cards.append(
            ResultCard(
                type=CardType.RISK_WARNING,
                title="长期风险提示",
                content="长期质量分析不等于长期收益承诺；商业模式、竞争格局、现金流、估值和行业周期都可能变化。",
                metadata={"subject": subject, "horizon": "long_term"},
            )
        )
    return cards


def _line(
    result: StructuredResult,
    markers: Iterable[str],
    *,
    exclude: Iterable[str] = (),
) -> Optional[str]:
    for item in [*result.facts, *result.judgements, *(f"{card.title} {card.content}" for card in result.cards)]:
        text = _clean_line(item)
        if (
            text
            and any(marker in text for marker in markers)
            and not any(marker in text for marker in exclude)
            and not _is_low_value(text)
        ):
            return text
    return None


def _metric(result: StructuredResult, key: str, label: str, *, percent: bool = False, money: bool = False) -> Optional[str]:
    value = _metadata_value(result, key)
    if value in (None, "", []):
        return None
    if money:
        return f"{label} {_format_money(value)}"
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


def _truncate_text(text: str, limit: int = 120) -> str:
    cleaned = _clean_line(text)
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit]}..."


def _summarize_business_text(text: str) -> str:
    cleaned = _clean_line(text)
    if len(cleaned) <= 90:
        return cleaned
    keywords = []
    keyword_groups = (
        ("选矿", "选矿"),
        ("矿物洗选", "矿物洗选"),
        ("金属矿石", "金属矿石"),
        ("铜", "铜"),
        ("有色金属冶炼", "有色金属冶炼"),
        ("贵金属冶炼", "贵金属冶炼"),
        ("压延加工", "压延加工"),
        ("电池", "电池"),
        ("乘用车", "乘用车"),
        ("电动车", "电动车"),
        ("汽车", "汽车"),
        ("零部件", "零部件"),
        ("集成电路封测", "集成电路封测"),
        ("先进封装", "先进封装"),
        ("封装", "封装"),
        ("测试", "测试"),
        ("半导体", "半导体"),
        ("芯片", "芯片"),
        ("电子产品", "电子产品"),
        ("出口", "出口"),
        ("售后服务", "售后服务"),
    )
    for marker, label in keyword_groups:
        if marker in cleaned and label not in keywords:
            keywords.append(label)
    if keywords:
        return "、".join(keywords[:6])
    return f"{cleaned[:90]}..."


def _is_resource_or_metal(industry: Optional[str], concept: Optional[str]) -> bool:
    text = f"{industry or ''}{concept or ''}"
    return any(
        keyword in text
        for keyword in ("有色", "工业金属", "铜", "黄金", "金属", "矿", "小金属", "镍", "铝", "锌")
    )


def _is_semiconductor_packaging(industry: Optional[str], concept: Optional[str]) -> bool:
    text = f"{industry or ''}{concept or ''}"
    return any(keyword in text for keyword in ("半导体", "集成电路", "封测", "先进封装", "芯片", "电子"))


def _is_low_value(text: str) -> bool:
    stripped = text.strip(" -；;。")
    low_value_exact = {"个股行业题材", "估值现金流补充", "财报核心指标", "风险点"}
    low_value_markers = (
        "覆盖状态",
        "已覆盖",
        "查询",
        "命中",
        "使用边界",
        "同花顺题材补充 已补充",
        "已补充地域、概念和主营业务",
        "单股实时补充来自",
        "研报搜索补充",
        "新闻搜索补充",
        "公告搜索补充",
    )
    return stripped in low_value_exact or any(marker in stripped for marker in low_value_markers)


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


def _shareholder_return_events(result: StructuredResult) -> list[str]:
    texts: list[str] = []
    for fact in result.facts:
        texts.append(_clean_line(fact))
    for judgement in result.judgements:
        texts.append(_clean_line(judgement))
    for card in result.cards:
        texts.extend(_announcement_like_lines(card.title, card.content))

    profit_distribution: list[str] = []
    buyback: list[str] = []
    dividend: list[str] = []
    for text in texts:
        if not text or _is_low_value(text):
            continue
        cleaned = _clean_announcement_text(text)
        if not cleaned:
            continue
        if any(keyword in cleaned for keyword in ("利润分配", "分配方案", "中期利润分配")):
            profit_distribution.append(cleaned)
        elif any(keyword in cleaned for keyword in ("回购", "股份回购")):
            buyback.append(cleaned)
        elif any(keyword in cleaned for keyword in ("分红", "派息", "股息", "股东回报")):
            dividend.append(cleaned)

    events: list[str] = []
    if profit_distribution:
        events.append("利润分配")
    if buyback:
        events.append("回购")
    if dividend:
        events.append("分红/派息")
    return _dedupe(events, limit=3)


def _announcement_like_lines(title: str, content: str) -> list[str]:
    title_text = _clean_line(title)
    content_text = str(content or "")
    lines = [_clean_line(line) for line in content_text.splitlines()]
    if "公告" in title_text and content_text:
        expanded: list[str] = []
        for line in lines:
            expanded.extend(_split_announcement_line(line))
        return [line for line in expanded if line]
    return [line for line in lines if line]


def _split_announcement_line(text: str) -> list[str]:
    cleaned = _clean_announcement_text(text)
    if not cleaned:
        return []
    parts = re.split(r"\s+-\s+|；|;", cleaned)
    return [_clean_announcement_text(part) for part in parts if _clean_announcement_text(part)]


def _clean_announcement_text(text: str) -> str:
    cleaned = _clean_line(text)
    cleaned = re.sub(r"^(公告搜索补充|新闻搜索补充|研报搜索补充)\s*[-：:]\s*", "", cleaned)
    cleaned = re.sub(r"^[^-：:]{2,12}\s*[-：:]\s*", "", cleaned)
    cleaned = cleaned.strip(" -；;。")
    if not cleaned or cleaned in {"公告搜索补充", "新闻搜索补充", "研报搜索补充"}:
        return ""
    return cleaned


def _short_title(text: str, limit: int = 36) -> str:
    cleaned = _clean_announcement_text(text)
    if len(cleaned) <= limit:
        return f"「{cleaned}」"
    return f"「{cleaned[:limit]}...」"


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


def _first_sentence(value: str) -> str:
    text = " ".join(str(value or "").split()).strip()
    return re.split(r"(?<=[。！？?])", text, maxsplit=1)[0].strip() if text else ""


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
