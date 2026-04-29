from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Dict, Iterable, List, Optional

from app.schemas import CardType, ResultCard, SourceRef, StructuredResult


DimensionStatus = str

STATUS_AVAILABLE: DimensionStatus = "available"
STATUS_PARTIAL: DimensionStatus = "partial"
STATUS_MISSING: DimensionStatus = "missing"

OPERATION_SECTIONS = (
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

AMBIGUOUS_STOCK_HINTS = ("这只股票", "这支股票", "这个股票", "这股", "它")
OPERATION_INTENT_KEYWORDS = (
    "今天能不能买",
    "能不能买",
    "能买吗",
    "能不能追",
    "要不要追",
    "多少价格买",
    "什么价格买",
    "怎么操作",
    "如何操作",
    "要不要止损",
    "止损",
    "买点",
)
DEEP_RESEARCH_INTENT_KEYWORDS = (
    "分析",
    "怎么看",
    "小白怎么看",
    "中线价值",
    "值不值得关注",
    "值得关注吗",
    "值得关注",
    "基本面",
    "估值",
    "财报",
    "风险",
    "今天能不能买",
    "能不能买",
    "能买吗",
)
PROFIT_PROMISE_PATTERNS = (
    r"必涨",
    r"稳赚",
    r"无风险",
    r"一定上涨",
    r"保证收益",
)


@dataclass(frozen=True)
class DimensionSpec:
    key: str
    title: str
    missing_subject: str
    keywords: tuple[str, ...]


DIMENSIONS: tuple[DimensionSpec, ...] = (
    DimensionSpec(
        "company_profile",
        "公司画像",
        "公司画像、主营业务、行业概念或赚钱逻辑",
        ("主营", "业务", "行业", "概念", "公司", "上市板块", "赚钱逻辑", "地域"),
    ),
    DimensionSpec(
        "market_snapshot",
        "当前行情状态",
        "最新价、涨跌幅、成交额、成交量、量比或换手率",
        ("最新价", "现价", "涨跌幅", "成交额", "成交量", "量比", "换手率", "过热"),
    ),
    DimensionSpec(
        "technical_signal",
        "技术面信号",
        "均线、MACD、RSI、KDJ、布林带或趋势状态",
        ("均线", "MA5", "MA10", "MA20", "MA60", "MACD", "RSI", "KDJ", "布林", "趋势", "K 线", "K线"),
    ),
    DimensionSpec(
        "fundamental_quality",
        "基本面质量",
        "营收、净利润、毛利率、净利率、ROE、负债率或业绩质量",
        ("营收", "净利润", "归母", "毛利率", "净利率", "ROE", "资产负债率", "业绩", "财报"),
    ),
    DimensionSpec(
        "valuation_cashflow",
        "估值与现金流",
        "PE、PB、PS、经营现金流、行业估值对比或现金流风险",
        ("PE", "PB", "PS", "市盈", "市净", "市销", "现金流", "经营现金", "估值"),
    ),
    DimensionSpec(
        "industry_position",
        "行业位置",
        "行业景气度、板块强弱、竞争地位、龙头属性或政策周期影响",
        ("行业", "板块", "景气", "龙头", "二线", "竞争", "政策", "周期", "概念"),
    ),
    DimensionSpec(
        "capital_structure",
        "资金与筹码",
        "主力资金、换手、股东户数、前十大股东、机构持仓或筹码稳定性",
        ("主力资金", "资金", "换手", "股东户数", "前十大股东", "机构持仓", "筹码", "盘口"),
    ),
    DimensionSpec(
        "news_events",
        "消息事件",
        "近期新闻、公告、研报观点、利好利空或催化事件",
        ("新闻", "公告", "研报", "催化", "利好", "利空", "事件", "标题"),
    ),
    DimensionSpec(
        "risk_factors",
        "主要风险",
        "短线、中线、财务、估值、行业、消息面或数据缺失风险",
        ("风险", "止损", "失效", "回撤", "偏贵", "走弱", "缺少", "不构成投资建议"),
    ),
    DimensionSpec(
        "beginner_conclusion",
        "小白观察清单",
        "小白观察重点、观察/等待/跟踪判断或判断改变信号",
        ("小白", "观察", "等待", "跟踪", "回调", "改变判断", "信号", "清单"),
    ),
)


def extract_deep_research_subject(message: str) -> Optional[str]:
    text = _compact_text(message)
    if not text:
        return None
    if any(hint in text for hint in AMBIGUOUS_STOCK_HINTS):
        return None

    code_match = re.search(r"([0368]\d{5}(?:\.(?:SH|SZ|BJ))?)", text, re.IGNORECASE)
    if code_match:
        return code_match.group(1).upper()

    patterns = (
        r"(?:小白)?(?:怎么看|看一下|分析一下|分析|聊聊)(?P<subject>[A-Za-z0-9\u4e00-\u9fff]{2,12}?)(?:的|现在|今天|中线|短线|基本面|估值|财报|风险|$)",
        r"(?P<subject>[A-Za-z0-9\u4e00-\u9fff]{2,12}?)(?:中线价值|基本面|估值|财报|风险|今天能不能买|现在值不值得关注|值不值得关注|值得关注吗|值得关注|怎么看|能不能买|能买吗|怎么操作)",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        subject = _clean_subject(match.group("subject"))
        if subject:
            return subject
    return None


def preflight_single_stock_research(message: str) -> Optional[StructuredResult]:
    text = _compact_text(message)
    if not text:
        return None

    if any(re.search(pattern, text) for pattern in PROFIT_PROMISE_PATTERNS) and (
        "哪只" in text or "哪支" in text or "明天" in text
    ):
        return _unsafe_profit_promise_result()

    if _is_ambiguous_operation_question(text):
        return StructuredResult(
            summary="请先提供股票名称或股票代码，再判断这只股票是否值得关注或如何操作。",
            cards=[
                ResultCard(
                    type=CardType.RESEARCH_NEXT_STEP,
                    title="需要补充标的",
                    content="请先提供股票名称或股票代码。拿到具体标的后，我会按公司画像、行情、技术面、基本面、估值现金流、行业位置、资金筹码、消息事件、风险和小白观察清单来分析。",
                )
            ],
            judgements=["当前问题缺少股票名称或股票代码，无法做单股分析，也不能给出操作判断。"],
            follow_ups=["补充股票名称或代码", "说明你的持仓成本和周期", "只看基本面还是也看短线操作"],
        )

    return None


def enhance_single_stock_research(
    route: Any,
    result: StructuredResult,
    *,
    user_message: str = "",
) -> StructuredResult:
    subject = str(getattr(route, "subject", "") or extract_deep_research_subject(user_message) or "").strip()
    single_security = bool(getattr(route, "single_security", False) or subject)
    if not single_security or not _is_deep_research_intent(user_message, route):
        return _sanitize_structured_result(result)

    dimension_states = _classify_dimensions(result)
    cards = list(result.cards)
    cards = _ensure_research_overview_card(cards, subject, dimension_states)
    if _is_operation_question(user_message, route):
        cards = _ensure_operation_guidance_card(cards, subject)
    cards = _ensure_risk_warning_card(cards, dimension_states)
    enriched_result = StructuredResult(
        summary=result.summary,
        table=result.table,
        cards=cards,
        chart_config=result.chart_config,
        facts=result.facts,
        judgements=result.judgements,
        follow_ups=result.follow_ups,
        sources=result.sources,
    )
    summary = _build_research_summary(
        original_summary=result.summary,
        subject=subject,
        dimension_states=dimension_states,
        result=enriched_result,
    )

    missing_judgements = [
        f"当前缺少 {spec.missing_subject} 数据，因此该部分判断置信度较低。"
        for spec in DIMENSIONS
        if dimension_states[spec.key]["status"] == STATUS_MISSING
    ]
    judgement_hints = [
        "本报告只基于已返回的 facts、cards、table、judgements 与 sources 做结构化整理；没有把 GPT 或规则层当作新的事实数据源。",
        "若后续补齐财报、公告、研报、股东和行业对比数据，应重新刷新对应维度的判断。",
    ]
    judgements = _dedupe([*result.judgements, *missing_judgements, *judgement_hints])
    follow_ups = _dedupe(
        [
            *result.follow_ups,
            f"补充{subject or '这只股票'}最新公告和研报",
            f"只看{subject or '这只股票'}估值和现金流",
            f"给{subject or '这只股票'}做小白观察清单",
        ],
        limit=3,
    )

    return _sanitize_structured_result(
        StructuredResult(
            summary=summary,
            table=result.table,
            cards=cards,
            chart_config=result.chart_config,
            facts=result.facts,
            judgements=judgements,
            follow_ups=follow_ups,
            sources=result.sources,
        )
    )


def _unsafe_profit_promise_result() -> StructuredResult:
    return StructuredResult(
        summary="无法保证某只股票明天上涨，但可以从资金、趋势、公告、行业催化和风险维度做概率性、条件性分析。",
        cards=[
            ResultCard(
                type=CardType.RISK_WARNING,
                title="收益承诺边界",
                content="无法保证某只股票明天上涨。短线判断只能基于资金、趋势、公告、行业催化、流动性和风险做概率分析，并设置条件和失效信号。",
            ),
            ResultCard(
                type=CardType.RESEARCH_NEXT_STEP,
                title="可分析方向",
                content="可以改问：某只具体股票明天需要观察哪些条件；或给出股票名称/代码后，按资金、趋势、公告、行业催化和风险做条件化分析。",
            ),
        ],
        judgements=["任何单日方向判断都存在风险，不能把概率性信号理解为收益承诺。"],
        follow_ups=["提供一只具体股票", "按资金和趋势做概率分析", "只看公告和行业催化"],
    )


def _classify_dimensions(result: StructuredResult) -> Dict[str, Dict[str, Any]]:
    evidence_pool = _build_evidence_pool(result)
    states: Dict[str, Dict[str, Any]] = {}
    for spec in DIMENSIONS:
        evidence = _dimension_evidence(spec, evidence_pool)
        metadata_hits = _dimension_metadata_hits(spec, result.cards)
        count = len(evidence) + metadata_hits
        if count >= 2:
            status = STATUS_AVAILABLE
        elif count == 1:
            status = STATUS_PARTIAL
        else:
            status = STATUS_MISSING
        states[spec.key] = {
            "title": spec.title,
            "status": status,
            "evidence": evidence[:3],
            "missing_subject": spec.missing_subject,
        }
    return states


def _build_evidence_pool(result: StructuredResult) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    for fact in result.facts:
        items.append({"kind": "fact", "text": _clean_evidence_text(str(fact))})
    for judgement in result.judgements:
        items.append({"kind": "judgement", "text": _clean_evidence_text(str(judgement))})
    for card in result.cards:
        items.append({"kind": "card", "text": _clean_evidence_text(f"{card.title} {card.content}")})
        for key, value in card.metadata.items():
            if value not in (None, "", []):
                items.append({"kind": "metadata", "text": _clean_evidence_text(f"{key}: {value}")})
    if result.table:
        for column in result.table.columns:
            items.append({"kind": "table", "text": _clean_evidence_text(str(column))})
        for row in result.table.rows[:2]:
            for key, value in row.items():
                if value not in (None, "", "-"):
                    items.append({"kind": "table", "text": _clean_evidence_text(f"{key}: {value}")})
    for source in result.sources:
        items.append({"kind": "source", "text": _clean_evidence_text(f"{source.skill} {source.query}")})
    return [item for item in items if item["text"] and not _looks_like_runtime_log(item["text"])]


def _dimension_evidence(spec: DimensionSpec, evidence_pool: List[Dict[str, str]]) -> List[str]:
    evidence: List[str] = []
    for item in evidence_pool:
        text = item["text"]
        if not text:
            continue
        if any(keyword.lower() in text.lower() for keyword in spec.keywords):
            evidence.append(_evidence_snippet(text))
    return _dedupe(evidence, limit=3)


def _dimension_metadata_hits(spec: DimensionSpec, cards: List[ResultCard]) -> int:
    keys = " ".join(
        key
        for card in cards
        for key, value in card.metadata.items()
        if value not in (None, "", [])
    )
    if not keys:
        return 0
    return 1 if any(keyword.lower() in keys.lower() for keyword in spec.keywords) else 0


def _build_research_summary(
    *,
    original_summary: str,
    subject: str,
    dimension_states: Dict[str, Dict[str, Any]],
    result: StructuredResult,
) -> str:
    conclusion = _compact_conclusion(original_summary) or f"{subject or '该股'}需要在数据可追溯的前提下分维度观察，不能只用一句话下结论。"
    lines = [f"一句话结论：{conclusion}", "", "深度研究框架："]
    used_evidence: set[str] = set()
    for index, spec in enumerate(DIMENSIONS, start=1):
        state = dimension_states[spec.key]
        evidence = state["evidence"]
        if state["status"] == STATUS_MISSING:
            lines.extend(
                [
                    "",
                    f"{index}. {spec.title}（missing）",
                    f"- 当前缺少 {spec.missing_subject} 数据，因此该部分判断置信度较低。",
                    "- 后续需要补齐该维度后再更新判断。",
                ]
            )
        else:
            bullets = _dimension_report_bullets(
                spec,
                evidence,
                subject=subject,
                used_evidence=used_evidence,
                result=result,
            )
            lines.extend(["", f"{index}. {spec.title}"])
            lines.extend(f"- {item}" for item in bullets)
            if state["status"] == STATUS_PARTIAL:
                lines.append(f"- 仍需补充：{spec.missing_subject}。")
    return "\n".join(lines)


def _ensure_research_overview_card(
    cards: List[ResultCard],
    subject: str,
    dimension_states: Dict[str, Dict[str, Any]],
) -> List[ResultCard]:
    if any(card.title == "单股深度研究 V1" for card in cards):
        return cards
    content = "\n".join(
        f"- {state['title']}：{state['status']}"
        for state in dimension_states.values()
    )
    metadata = {
        "subject": subject or None,
        "single_stock_research": True,
        "dimensions": {
            key: {
                "status": value["status"],
                "evidence_count": len(value["evidence"]),
            }
            for key, value in dimension_states.items()
        },
    }
    return [
        ResultCard(
            type=CardType.CUSTOM,
            title="单股深度研究 V1",
            content=content,
            metadata={key: value for key, value in metadata.items() if value is not None},
        ),
        *cards,
    ]


def _ensure_operation_guidance_card(cards: List[ResultCard], subject: str) -> List[ResultCard]:
    updated: List[ResultCard] = []
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
                f"更好的买点：等待{subject or '该股'}回调后量能、趋势和承接重新确认。\n"
                "失效条件：价格跌破关键观察位、资金持续走弱，或基本面/消息面逻辑被证伪。\n"
                "止损/观察位：在缺少明确价格数据时，先用前低、重要均线和放量破位作为观察边界。"
            ),
            metadata={"subject": subject} if subject else {},
        ),
        *updated,
    ]


def _ensure_risk_warning_card(
    cards: List[ResultCard],
    dimension_states: Dict[str, Dict[str, Any]],
) -> List[ResultCard]:
    missing = [
        state["title"]
        for state in dimension_states.values()
        if state["status"] == STATUS_MISSING
    ]
    risk_lines = [
        "以上为基于已返回数据的辅助研究整理，不构成投资建议。",
        "缺失数据不会被补写或猜测；缺失越多，结论置信度越低。",
    ]
    if missing:
        risk_lines.append(f"当前缺失维度：{'、'.join(missing)}。")
    risk_content = "\n".join(risk_lines)

    for index, card in enumerate(cards):
        if _card_type_value(card) == CardType.RISK_WARNING.value:
            content = card.content
            if "不构成投资建议" not in content:
                content = f"{content}\n{risk_content}"
            cards[index] = ResultCard(
                type=card.type,
                title=card.title,
                content=content,
                metadata=card.metadata,
            )
            return cards
    return [
        *cards,
        ResultCard(type=CardType.RISK_WARNING, title="风险提示", content=risk_content),
    ]


def _sanitize_structured_result(result: StructuredResult) -> StructuredResult:
    return StructuredResult(
        summary=_sanitize_text(result.summary),
        table=result.table,
        cards=[
            ResultCard(
                type=card.type,
                title=_sanitize_text(card.title),
                content=_sanitize_text(card.content),
                metadata=card.metadata,
            )
            for card in result.cards
        ],
        chart_config=result.chart_config,
        facts=[_sanitize_text(item) for item in result.facts],
        judgements=[_sanitize_text(item) for item in result.judgements],
        follow_ups=[_sanitize_text(item) for item in result.follow_ups],
        sources=result.sources,
    )


def _sanitize_text(text: str) -> str:
    cleaned = str(text or "")
    replacements = {
        "稳赚": "不存在确定收益",
        "必涨": "上涨无法保证",
        "无风险": "风险较低但仍需验证",
        "一定上涨": "上涨需要条件确认",
        "直接买入": "先按条件观察",
        "梭哈": "避免重仓冲动",
        "满仓": "控制仓位",
        "保证收益": "不承诺收益",
    }
    for forbidden, replacement in replacements.items():
        cleaned = cleaned.replace(forbidden, replacement)
    return cleaned


def _is_deep_research_intent(message: str, route: Any) -> bool:
    if bool(getattr(route, "entry_price_focus", False)):
        return True
    text = _compact_text(message)
    subject = _compact_text(str(getattr(route, "subject", "") or ""))
    if not text:
        return bool(getattr(route, "single_security", False))
    if bool(getattr(route, "single_security", False)) and subject:
        if text == subject or text in {f"{subject}股票", f"{subject}个股"}:
            return True
    return any(keyword in text for keyword in DEEP_RESEARCH_INTENT_KEYWORDS)


def _is_operation_question(message: str, route: Any) -> bool:
    if bool(getattr(route, "entry_price_focus", False)):
        return True
    text = _compact_text(message)
    return any(keyword in text for keyword in OPERATION_INTENT_KEYWORDS)


def _is_ambiguous_operation_question(text: str) -> bool:
    return any(hint in text for hint in AMBIGUOUS_STOCK_HINTS) and any(
        keyword in text for keyword in OPERATION_INTENT_KEYWORDS
    )


def _ensure_operation_sections(content: str) -> str:
    lines = [line.strip() for line in str(content or "").splitlines() if line.strip()]
    existing = "\n".join(lines)
    defaults = {
        "现在能不能追：": "现在能不能追：先观察，不把当前结论理解为买入指令。",
        "更好的买点：": "更好的买点：等待量能、趋势和承接重新确认。",
        "失效条件：": "失效条件：价格跌破关键观察位、资金持续走弱，或基本面/消息面逻辑被证伪。",
        "止损/观察位：": "止损/观察位：在缺少明确价格数据时，先用前低、重要均线和放量破位作为观察边界。",
    }
    for section in OPERATION_SECTIONS:
        if section not in existing:
            lines.append(defaults[section])
    return "\n".join(lines)


def _card_type_value(card: ResultCard) -> str:
    return card.type.value if isinstance(card.type, CardType) else str(card.type)


def _compact_text(text: str) -> str:
    return re.sub(r"\s+", "", str(text or "")).strip(" ，。！？?；;：:")


def _clean_subject(subject: str) -> Optional[str]:
    cleaned = str(subject or "").strip(" ，。！？?；;：:")
    cleaned = re.sub(r"^(?:小白|帮我|给我|请|看一下|分析一下|分析)", "", cleaned)
    cleaned = re.sub(r"(?:这只|这支|这个)?(?:股票|个股)$", "", cleaned)
    if not 2 <= len(cleaned) <= 12:
        return None
    if cleaned in {"这只", "这支", "这个", "股票", "个股", "大盘", "板块", "行业"}:
        return None
    return cleaned


def _evidence_snippet(text: str, limit: int = 140) -> str:
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit]}..."


def _clean_evidence_text(text: str) -> str:
    normalized = " ".join(str(text or "").split()).strip()
    normalized = re.sub(r"查询 `[^`]+` 命中 \d+ 条，当前取 \d+ 条。?", "", normalized)
    normalized = re.sub(r"查询 `[^`]+` 命中 \d+ 条。?", "", normalized)
    normalized = re.sub(r"`[^`]{16,}`", "相关查询", normalized)
    normalized = normalized.replace("  ", " ").strip(" ；;。")
    return normalized


def _looks_like_runtime_log(text: str) -> bool:
    if not text:
        return True
    runtime_markers = (
        "命中",
        "当前取",
        "查询  命中",
        "数据来源：",
        "已补充",
        "来自同花顺公开行情页",
    )
    return any(marker in text for marker in runtime_markers) and len(text) < 80


def _humanize_evidence(text: str, limit: Optional[int] = 180) -> str:
    cleaned = _clean_evidence_text(text)
    cleaned = re.sub(r"^(操作建议卡|三周期分析|财报与基本面|使用边界)\s*", "", cleaned)
    cleaned = cleaned.strip(" -；;。")
    if not cleaned:
        return "已有结构化数据提供了可追溯线索。"
    if limit is not None and len(cleaned) > limit:
        cleaned = f"{cleaned[:limit]}..."
    return cleaned


def _dimension_report_bullets(
    spec: DimensionSpec,
    evidence: List[str],
    *,
    subject: str,
    used_evidence: set[str],
    result: StructuredResult,
) -> List[str]:
    max_bullets = 4 if spec.key == "risk_factors" else 3
    specialized = _specialized_dimension_bullets(spec.key, result, subject)
    bullets: List[str] = []
    for item in specialized:
        normalized = _humanize_evidence(item)
        if normalized and normalized not in used_evidence and not _is_low_value_report_line(normalized):
            bullets.append(normalized)
            used_evidence.add(normalized)
        if len(bullets) >= max_bullets:
            return bullets

    if spec.key in {"risk_factors", "beginner_conclusion"} and bullets:
        return bullets

    candidates = [_humanize_evidence(item) for item in evidence]
    candidates = [
        item
        for item in candidates
        if item
        and item not in used_evidence
        and not _is_low_value_report_line(item)
    ]

    preferred = _prefer_dimension_lines(spec.key, candidates)
    for item in preferred:
        if item in bullets:
            continue
        bullets.append(item)
        used_evidence.add(item)
        if len(bullets) >= max_bullets:
            break

    if bullets:
        return bullets
    return [_fallback_dimension_line(spec.key, subject)]


def _prefer_dimension_lines(dimension_key: str, candidates: List[str]) -> List[str]:
    priority: Dict[str, tuple[str, ...]] = {
        "company_profile": ("主营", "业务", "行业", "概念", "上市板块", "公司"),
        "market_snapshot": ("当前价格", "最新价", "涨跌幅", "成交额", "量比", "换手率", "主力资金"),
        "technical_signal": ("K 线", "K线", "MA", "MACD", "RSI", "KDJ", "布林", "趋势"),
        "fundamental_quality": ("财报期", "营收", "净利润", "毛利率", "净利率", "ROE", "资产负债率"),
        "valuation_cashflow": ("PE", "PB", "PS", "估值", "现金流", "市盈", "市净", "市销"),
        "industry_position": ("行业", "板块", "龙头", "景气", "竞争", "政策", "周期"),
        "capital_structure": ("主力资金", "净流入", "净流出", "换手", "股东", "机构", "筹码", "盘口"),
        "news_events": ("新闻", "公告", "研报", "催化", "回购", "担保", "中标", "事件"),
        "risk_factors": ("风险", "失效", "止损", "不构成投资建议", "回撤", "偏弱", "追"),
        "beginner_conclusion": ("小白", "观察", "等待", "跟踪", "回调", "信号", "清单"),
    }
    keywords = priority.get(dimension_key, ())
    scored = sorted(
        enumerate(candidates),
        key=lambda item: (
            -sum(1 for keyword in keywords if keyword.lower() in item[1].lower()),
            len(item[1]),
            item[0],
        ),
    )
    return [item for _, item in scored]


def _specialized_dimension_bullets(
    dimension_key: str,
    result: StructuredResult,
    subject: str,
) -> List[str]:
    if dimension_key == "market_snapshot":
        return _market_snapshot_bullets(result, subject)
    if dimension_key == "technical_signal":
        return _technical_signal_bullets(result, subject)
    if dimension_key == "fundamental_quality":
        return _fundamental_quality_bullets(result, subject)
    if dimension_key == "valuation_cashflow":
        return _valuation_cashflow_bullets(result, subject)
    if dimension_key == "industry_position":
        return _industry_position_bullets(result, subject)
    if dimension_key == "capital_structure":
        return _capital_structure_bullets(result, subject)
    if dimension_key == "news_events":
        return _news_event_bullets(result, subject)
    if dimension_key == "risk_factors":
        return _risk_factor_bullets(result, subject)
    if dimension_key == "beginner_conclusion":
        return _beginner_conclusion_bullets(result, subject)
    return []


def _market_snapshot_bullets(result: StructuredResult, subject: str) -> List[str]:
    close = _metadata_value(result, "close", "latest_price", "price")
    change = _metadata_value(result, "change", "change_pct", "pct_change")
    amount = _metadata_value(result, "amount", "turnover_amount")
    turnover = _metadata_value(result, "turnover", "turnover_rate")
    volume_ratio = _metadata_value(result, "volume_ratio", "vr")
    money_flow = _metadata_value(result, "money_flow", "main_money_flow")
    amplitude = _metadata_value(result, "amplitude")

    bullets: List[str] = []

    if close is not None or change is not None:
        parts = _join_nonempty(
            [
                f"{subject or '该股'} 当前价格 {_format_ratio_value(close)}" if close is not None else None,
                f"今日涨跌幅 {_format_percent_value(change)}" if change is not None else None,
            ]
        )
        if parts:
            bullets.append(f"{parts}。")
    else:
        snapshot_line = _first_matching_text_excluding(
            result.facts,
            ("当前价格", "最新价", "涨跌幅", "成交额", "换手率", "量比"),
            ("MA", "MACD", "RSI", "KDJ", "布林", "K 线", "K线"),
        )
        if snapshot_line:
            bullets.append(snapshot_line)

    flow_bits = _join_nonempty(
        [
            f"成交额 {_format_money_amount(amount)}" if amount is not None else None,
            f"换手率 {_format_percent_value(turnover)}" if turnover is not None else None,
            f"量比 {_format_ratio_value(volume_ratio)}" if volume_ratio is not None else None,
            f"振幅 {_format_percent_value(amplitude)}" if amplitude is not None else None,
        ]
    )
    money_flow_value = _coerce_float(money_flow)
    if money_flow_value is not None:
        direction = "净流入" if money_flow_value >= 0 else "净流出"
        flow_bits = _join_nonempty(
            [
                flow_bits if flow_bits else None,
                f"主力资金{direction} {_format_money_amount(abs(money_flow_value))}",
            ]
        )
    elif money_flow not in (None, "", []):
        flow_bits = _join_nonempty([flow_bits if flow_bits else None, f"主力资金 {money_flow}"])

    if flow_bits:
        bullets.append(f"{flow_bits}。")
    else:
        flow_line = _first_matching_text_excluding(
            result.facts,
            ("成交额", "量比", "换手率", "主力资金"),
            ("MA", "MACD", "RSI", "KDJ", "布林", "K 线", "K线"),
        )
        if flow_line:
            bullets.append(flow_line)

    turnover_value = _coerce_float(turnover)
    volume_ratio_value = _coerce_float(volume_ratio)
    change_value = _coerce_float(change)
    hot_signals = sum(
        [
            1 if turnover_value is not None and turnover_value >= 8 else 0,
            1 if volume_ratio_value is not None and volume_ratio_value >= 2 else 0,
            1 if change_value is not None and abs(change_value) >= 5 else 0,
        ]
    )
    cold_signals = sum(
        [
            1 if turnover_value is not None and turnover_value < 2 else 0,
            1 if volume_ratio_value is not None and volume_ratio_value < 0.8 else 0,
            1 if money_flow_value is not None and money_flow_value < 0 else 0,
        ]
    )
    if hot_signals >= 2:
        bullets.append("短期交易热度偏高，后续要重点防范放量冲高后的回撤。")
    elif cold_signals >= 2:
        bullets.append("短期热度偏弱，更多是存量博弈，现阶段不属于明显过热状态。")
    else:
        bullets.append("短期热度中性，暂未看到明显过热，但还要继续观察量价是否同步。")

    return bullets[:3]


def _technical_signal_bullets(result: StructuredResult, subject: str) -> List[str]:
    close = _metadata_value(result, "close", "latest_price", "price")
    ma5 = _metadata_value(result, "ma5")
    ma10 = _metadata_value(result, "ma10")
    ma20 = _metadata_value(result, "ma20")
    ma60 = _metadata_value(result, "ma60")
    macd = _metadata_value(result, "macd")
    diff = _metadata_value(result, "diff", "dif")
    dea = _metadata_value(result, "dea")
    rsi = _metadata_value(result, "rsi")
    kdj = _metadata_value(result, "kdj", "k")
    boll_mid = _metadata_value(result, "boll_mid")

    bullets: List[str] = []
    ma_bits = _join_nonempty(
        [
            f"MA5 {_format_ratio_value(ma5)}" if ma5 is not None else None,
            f"MA10 {_format_ratio_value(ma10)}" if ma10 is not None else None,
            f"MA20 {_format_ratio_value(ma20)}" if ma20 is not None else None,
            f"MA60 {_format_ratio_value(ma60)}" if ma60 is not None else None,
        ]
    )
    if ma_bits:
        bullets.append(f"{subject or '该股'} 技术锚点包括 {ma_bits}。")

    signal_bits = _join_nonempty(
        [
            f"MACD {_format_ratio_value(macd)}" if macd is not None else None,
            f"DIF {_format_ratio_value(diff)} / DEA {_format_ratio_value(dea)}" if diff is not None and dea is not None else None,
            f"RSI {_format_ratio_value(rsi)}" if rsi is not None else None,
            f"KDJ {_format_ratio_value(kdj)}" if kdj is not None else None,
            f"布林中轨 {_format_ratio_value(boll_mid)}" if boll_mid is not None else None,
        ]
    )
    if signal_bits:
        bullets.append(f"当前技术指标显示 {signal_bits}。")

    close_value = _coerce_float(close)
    ma5_value = _coerce_float(ma5)
    ma20_value = _coerce_float(ma20)
    if close_value is not None and ma5_value is not None and ma20_value is not None:
        if close_value < ma5_value and close_value >= ma20_value:
            bullets.append("短线仍在修复区，强度还不够，暂时更像震荡中的观察阶段。")
        elif close_value >= ma5_value and close_value >= ma20_value:
            bullets.append("价格站在短中期均线之上，趋势偏强，后续重点看量能能否跟上。")
        else:
            bullets.append("价格仍弱于短期均线，趋势判断不能只看单日反弹，先等均线关系改善。")

    trend_line = _first_matching_text(result.facts, ("近期趋势表现", "今日 K 线", "技术指标"))
    if trend_line and not bullets:
        bullets.append(trend_line)
    return bullets[:3]


def _industry_position_bullets(result: StructuredResult, subject: str) -> List[str]:
    industry = _metadata_value(result, "industry")
    concept = _metadata_value(result, "concept")
    listing_board = _metadata_value(result, "listing_board")
    listing_place = _metadata_value(result, "listing_place")

    bullets: List[str] = []
    if industry or concept:
        parts = _join_nonempty(
            [
                f"所属行业 {industry}" if industry else None,
                f"核心题材 {concept}" if concept else None,
            ]
        )
        if parts:
            bullets.append(f"{subject or '该股'} 当前更受 {parts} 这条产业线影响。")
    if listing_board or listing_place:
        board_bits = _join_nonempty(
            [
                f"上市板块 {listing_board}" if listing_board else None,
                f"上市地点 {listing_place}" if listing_place else None,
            ]
        )
        if board_bits:
            bullets.append(f"{board_bits}，后续要结合板块强弱和政策周期一起看。")

    industry_line = _first_matching_text([*result.facts, *result.judgements], ("行业", "板块", "题材", "政策", "景气"))
    if industry_line and industry_line not in bullets:
        bullets.append(industry_line)
    if not bullets:
        bullets.append("行业位置这部分暂时只有板块归属线索，还缺少景气度、竞争格局和同行对比。")
    return bullets[:3]


def _capital_structure_bullets(result: StructuredResult, subject: str) -> List[str]:
    money_flow = _metadata_value(result, "money_flow", "main_money_flow")
    turnover = _metadata_value(result, "turnover", "turnover_rate")
    observe_line = _first_matching_text(result.facts, ("盘口补充", "主力资金", "换手率"))

    bullets: List[str] = []
    money_flow_value = _coerce_float(money_flow)
    if money_flow_value is not None:
        direction = "净流入" if money_flow_value >= 0 else "净流出"
        bullets.append(f"主力资金当前为 {direction} {_format_money_amount(abs(money_flow_value))}。")
    if turnover is not None:
        bullets.append(f"换手率约 {_format_percent_value(turnover)}，可作为短线筹码活跃度的一个观察锚点。")
    if observe_line:
        bullets.append(observe_line)
    if not bullets:
        bullets.append(f"{subject or '该股'} 当前缺少更完整的股东户数、机构持仓和前十大股东变化数据。")
    return bullets[:3]


def _news_event_bullets(result: StructuredResult, subject: str) -> List[str]:
    news_line = _first_matching_text(result.facts, ("近期可跟踪的催化线索",))
    announcement_line = _first_matching_text(result.facts, ("公告侧最近的重点是",))

    bullets: List[str] = []
    if news_line:
        bullets.append(news_line)
    if announcement_line:
        bullets.append(announcement_line)
    if news_line or announcement_line:
        bullets.append("消息和公告更适合拿来验证逻辑有没有变化，不适合只看标题就直接下结论。")
    else:
        bullets.append(f"{subject or '该股'} 当前还缺少足够明确的近期新闻、公告和研报增量信息。")
    return bullets[:3]


def _beginner_conclusion_bullets(result: StructuredResult, subject: str) -> List[str]:
    can_chase = _operation_guidance_line(result, "现在能不能追：")
    better_entry = _operation_guidance_line(result, "更好的买点：")
    invalidation = _operation_guidance_line(result, "失效条件：")
    stop_watch = _operation_guidance_line(result, "止损/观察位：")

    bullets: List[str] = []
    if can_chase:
        bullets.append(f"先看结论：{_strip_prefix(can_chase, '现在能不能追：')}")
    bullets.append("小白优先盯三件事：趋势有没有重新站稳短期均线、财报里的利润和现金流有没有继续背离、公告和主力资金有没有出现新的变化。")

    change_bits = _join_nonempty(
        [
            _strip_prefix(better_entry, "更好的买点：") if better_entry else None,
            _strip_prefix(invalidation, "失效条件：") if invalidation else None,
            _strip_prefix(stop_watch, "止损/观察位：") if stop_watch else None,
        ]
    )
    if change_bits:
        bullets.append(f"这些信号出现后要及时调整判断：{change_bits}")
    else:
        bullets.append(f"{subject or '该股'} 后续一旦趋势、资金或公告逻辑发生变化，就要重新刷新判断。")
    return bullets[:3]


def _fundamental_quality_bullets(result: StructuredResult, subject: str) -> List[str]:
    report_period = _metadata_value(result, "report_period")
    revenue = _metadata_value(result, "revenue")
    revenue_growth = _metadata_value(result, "revenue_growth")
    net_profit = _metadata_value(result, "net_profit")
    profit_growth = _metadata_value(result, "profit_growth")
    roe = _metadata_value(result, "roe")
    gross_margin = _metadata_value(result, "gross_margin")
    debt_ratio = _metadata_value(result, "debt_ratio")
    operating_cash_flow = _metadata_value(result, "operating_cash_flow")

    bullets: List[str] = []
    growth_bits = _join_nonempty(
        [
            f"营收 {_format_money_amount(revenue)}" if revenue is not None else None,
            f"营收同比 {_format_percent_value(revenue_growth)}" if revenue_growth is not None else None,
            f"归母净利润 {_format_money_amount(net_profit)}" if net_profit is not None else None,
            f"归母同比 {_format_percent_value(profit_growth)}" if profit_growth is not None else None,
        ]
    )
    if growth_bits:
        prefix = f"{subject or '该股'} 最新财报期 {report_period}：" if report_period else f"{subject or '该股'} 最新财报："
        bullets.append(f"{prefix}{growth_bits}。")
    else:
        growth_line = _first_matching_text(result.facts, ("最新财报期", "营收", "归母净利润"))
        if growth_line:
            bullets.append(growth_line)

    quality_bits = _join_nonempty(
        [
            f"ROE {_format_percent_value(roe)}" if roe is not None else None,
            f"毛利率 {_format_percent_value(gross_margin)}" if gross_margin is not None else None,
            f"资产负债率 {_format_percent_value(debt_ratio)}" if debt_ratio is not None else None,
        ]
    )
    if quality_bits:
        bullets.append(f"盈利质量锚点包括 {quality_bits}。")
    else:
        quality_line = _first_matching_text(result.facts, ("ROE", "毛利率", "资产负债率", "基本面指标"))
        if quality_line:
            bullets.append(quality_line)

    if operating_cash_flow is not None:
        if _coerce_float(operating_cash_flow) is not None and _coerce_float(operating_cash_flow) > 0:
            bullets.append(f"经营现金流为 {_format_money_amount(operating_cash_flow)}，利润兑现能力目前看没有明显失真。")
        else:
            bullets.append(f"经营现金流为 {_format_money_amount(operating_cash_flow)}，需要警惕利润好看但现金流承压。")
    else:
        cashflow_line = _first_matching_text(result.facts, ("经营现金流", "现金流"))
        if cashflow_line:
            bullets.append(cashflow_line)
    if not bullets:
        bullets.append("当前只拿到部分财报锚点，仍需补齐营收、净利润、利润率和现金流后再判断业绩质量。")
    return bullets


def _valuation_cashflow_bullets(result: StructuredResult, subject: str) -> List[str]:
    pe = _metadata_value(result, "pe")
    pb = _metadata_value(result, "pb")
    ps = _metadata_value(result, "ps")
    operating_cash_flow = _metadata_value(result, "operating_cash_flow")
    report_period = _metadata_value(result, "report_period")

    bullets: List[str] = []
    valuation_bits = _join_nonempty(
        [
            f"PE(TTM) {_format_ratio_value(pe)}" if pe is not None else None,
            f"PB {_format_ratio_value(pb)}" if pb is not None else None,
            f"PS {_format_ratio_value(ps)}" if ps is not None else None,
        ]
    )
    if valuation_bits:
        bullets.append(f"{subject or '该股'} 当前可追踪的估值锚点包括 {valuation_bits}。")
    else:
        valuation_line = _first_matching_text(result.facts, ("PE", "PB", "PS", "市盈率", "市净率", "估值"))
        if valuation_line:
            bullets.append(valuation_line)
        else:
            bullets.append("当前估值维度缺少完整的 PE / PB / PS 锚点，只能做非常有限的判断。")

    if operating_cash_flow is not None:
        cashflow_prefix = f"最新财报期 {report_period}" if report_period else "最新财报"
        if _coerce_float(operating_cash_flow) is not None and _coerce_float(operating_cash_flow) > 0:
            bullets.append(f"{cashflow_prefix}经营现金流为 {_format_money_amount(operating_cash_flow)}，现金流和利润暂时没有明显背离。")
        else:
            bullets.append(f"{cashflow_prefix}经营现金流为 {_format_money_amount(operating_cash_flow)}，需要重点核对利润和现金流是否背离。")
    else:
        cashflow_line = _first_matching_text(result.facts, ("经营现金流", "现金流"))
        if cashflow_line:
            bullets.append(cashflow_line)
        else:
            bullets.append("当前缺少经营现金流锚点，因此“利润好看但现金流差”的风险还不能排除。")

    bullets.append("当前还缺少同行估值对比，因此暂时不能下结论说它相对行业偏贵还是偏便宜。")
    return bullets


def _risk_factor_bullets(result: StructuredResult, subject: str) -> List[str]:
    invalidation = _operation_guidance_line(result, "失效条件：")
    stop_watch = _operation_guidance_line(result, "止损/观察位：")
    close = _metadata_value(result, "close", "latest_price", "price")
    ma5 = _metadata_value(result, "ma5")
    money_flow = _metadata_value(result, "money_flow", "main_money_flow")
    volume_ratio = _metadata_value(result, "volume_ratio", "vr")
    debt_ratio = _metadata_value(result, "debt_ratio")
    operating_cash_flow = _metadata_value(result, "operating_cash_flow")
    pe = _metadata_value(result, "pe")
    pb = _metadata_value(result, "pb")

    money_flow_value = _coerce_float(money_flow)
    volume_ratio_value = _coerce_float(volume_ratio)
    debt_ratio_value = _coerce_float(debt_ratio)
    operating_cash_flow_value = _coerce_float(operating_cash_flow)
    close_value = _coerce_float(close)
    ma5_value = _coerce_float(ma5)
    pe_value = _coerce_float(pe)
    pb_value = _coerce_float(pb)

    bullets: List[str] = []
    short_term_risks: List[str] = []
    if close_value is not None and ma5_value is not None and close_value < ma5_value:
        gap = (ma5_value - close_value) / ma5_value * 100 if ma5_value else 0
        short_term_risks.append(f"股价仍在 MA5 下方约 {gap:.1f}%")
    if money_flow_value is not None and money_flow_value < 0:
        short_term_risks.append(f"主力资金仍是净流出 {_format_money_amount(abs(money_flow_value))}")
    if volume_ratio_value is not None and volume_ratio_value < 0.8:
        short_term_risks.append(f"量比 {_format_ratio_value(volume_ratio_value)}，追涨资金不算积极")
    if short_term_risks:
        bullets.append(f"短线风险：{_join_nonempty(short_term_risks)}。")
    else:
        short_term_line = _first_matching_text_excluding(
            result.judgements,
            ("风险", "追高", "走弱", "回撤", "失效"),
            ("现在能不能追",),
        )
        if short_term_line:
            bullets.append(f"短线风险：{short_term_line}。")

    medium_term_risks: List[str] = []
    if operating_cash_flow_value is not None and operating_cash_flow_value <= 0:
        medium_term_risks.append("经营现金流偏弱，需警惕利润和现金流背离")
    elif operating_cash_flow is None:
        medium_term_risks.append("当前缺少经营现金流细项，财务风险判断仍不完整")
    if debt_ratio_value is not None and debt_ratio_value >= 60:
        medium_term_risks.append(f"资产负债率 {_format_percent_value(debt_ratio_value)}，财务杠杆偏高")
    if pe_value is None and pb_value is None:
        medium_term_risks.append("估值锚点还不完整，暂时无法判断是否偏贵")
    else:
        medium_term_risks.append("还缺少同行估值对比，无法确认当前估值相对行业是偏贵还是偏便宜")

    industry_or_news_line = _first_matching_text(
        [*result.judgements, *result.facts],
        ("行业", "景气", "政策", "周期", "公告", "新闻", "催化", "研报"),
    )
    if industry_or_news_line:
        medium_term_risks.append(f"行业和消息面还要持续跟踪，尤其是 {industry_or_news_line}")
    else:
        medium_term_risks.append("行业景气、政策节奏和公告催化变化，都会影响中线判断")

    bullets.append(f"中线风险：{_join_nonempty(medium_term_risks[:3])}。")
    if invalidation:
        bullets.append(f"失效条件：{_strip_prefix(invalidation, '失效条件：')}。")
    if stop_watch:
        bullets.append(f"止损/观察位：{_strip_prefix(stop_watch, '止损/观察位：')}。")
    else:
        bullets.append("数据风险：若后续财报、行业对比或公告信息继续缺失，风险判断的置信度会下降。")
    if not bullets:
        bullets.append(f"{subject or '该股'} 当前至少要同时防范趋势走弱、资金回落和消息扰动带来的判断失效。")
    return bullets[:4]


def _is_low_value_report_line(text: str) -> bool:
    low_value_markers = (
        "覆盖状态",
        "已覆盖",
        "已补充",
        "查询",
        "命中",
        "数据来源",
        "使用边界",
        "辅助整理",
        "当前取",
        "来自同花顺公开行情页",
    )
    return any(marker in text for marker in low_value_markers)


def _fallback_dimension_line(dimension_key: str, subject: str) -> str:
    name = subject or "该股"
    fallback: Dict[str, str] = {
        "company_profile": f"{name} 的公司画像已有部分线索，重点看主营业务、行业归属和赚钱逻辑是否清晰。",
        "market_snapshot": "行情维度重点看最新价、涨跌幅、成交额、量比和换手率，判断是否短期过热。",
        "technical_signal": "技术维度重点看均线位置、MACD、RSI、KDJ 和布林带，判断趋势是强势、弱势还是震荡。",
        "fundamental_quality": "基本面维度重点看营收、净利润、利润率、ROE 和负债率，判断增长质量。",
        "valuation_cashflow": "估值现金流维度重点看 PE、PB、PS 与经营现金流是否匹配。",
        "industry_position": "行业维度重点看板块强弱、景气度、竞争位置和政策周期影响。",
        "capital_structure": "资金筹码维度重点看主力资金、换手、股东户数、机构持仓和筹码稳定性。",
        "news_events": "消息维度重点看近期新闻、公告、研报和催化事件是否改变短中期逻辑。",
        "risk_factors": "风险维度重点看短线追高、趋势失效、估值、财务、行业和消息面风险。",
        "beginner_conclusion": "小白重点看三件事：趋势有没有走坏、基本面有没有恶化、估值和现金流是否匹配。",
    }
    return fallback.get(dimension_key, f"{name} 该维度已有部分结构化线索，建议继续跟踪。")


def _compact_conclusion(text: str, limit: int = 120) -> str:
    conclusion = _first_sentence(text)
    if len(conclusion) <= limit:
        return conclusion
    for separator in (" 风险：", " 操作建议：", "。", "；", ";"):
        if separator in conclusion:
            head = conclusion.split(separator, 1)[0].strip()
            if 20 <= len(head) <= limit:
                return head
    return f"{conclusion[:limit]}..."


def _metadata_value(result: StructuredResult, *keys: str) -> Any:
    for card in result.cards:
        for key in keys:
            if key in card.metadata and card.metadata[key] not in (None, "", []):
                return card.metadata[key]
    return None


def _operation_guidance_line(result: StructuredResult, prefix: str) -> Optional[str]:
    for card in result.cards:
        if _card_type_value(card) != CardType.OPERATION_GUIDANCE.value:
            continue
        for raw_line in str(card.content or "").splitlines():
            line = raw_line.strip()
            if line.startswith(prefix):
                return line
    return None


def _first_card_text(result: StructuredResult, card_type: CardType) -> Optional[str]:
    for card in result.cards:
        if _card_type_value(card) == card_type.value:
            return _humanize_evidence(card.content)
    return None


def _first_matching_text(items: Iterable[str], markers: Iterable[str]) -> Optional[str]:
    for item in items:
        text = _humanize_evidence(item)
        if any(marker in text for marker in markers):
            return text
    return None


def _first_matching_text_excluding(
    items: Iterable[str],
    markers: Iterable[str],
    excluded_markers: Iterable[str],
) -> Optional[str]:
    for item in items:
        text = _humanize_evidence(item)
        if any(marker in text for marker in markers) and not any(marker in text for marker in excluded_markers):
            return text
    return None


def _strip_prefix(text: str, prefix: str) -> str:
    value = str(text or "").strip()
    if value.startswith(prefix):
        value = value[len(prefix) :].strip()
    return value


def _join_nonempty(parts: Iterable[Optional[str]]) -> str:
    return "，".join(part for part in parts if part)


def _coerce_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "").replace("%", ""))
    except (TypeError, ValueError):
        return None


def _format_ratio_value(value: Any) -> str:
    numeric = _coerce_float(value)
    if numeric is None:
        return str(value)
    return f"{numeric:.2f}"


def _format_percent_value(value: Any) -> str:
    numeric = _coerce_float(value)
    if numeric is None:
        return str(value)
    return f"{numeric:.2f}%"


def _format_money_amount(value: Any) -> str:
    numeric = _coerce_float(value)
    if numeric is None:
        return str(value)
    abs_numeric = abs(numeric)
    if abs_numeric >= 1e8:
        return f"{numeric / 1e8:.2f}亿"
    if abs_numeric >= 1e4:
        return f"{numeric / 1e4:.2f}万"
    return f"{numeric:.2f}"


def _join_evidence(evidence: List[str]) -> str:
    if not evidence:
        return "已有结构化结果提供了部分线索。"
    return "；".join(evidence)


def _first_sentence(text: str) -> str:
    normalized = " ".join(str(text or "").split()).strip()
    if not normalized:
        return ""
    parts = re.split(r"(?<=[。！？!?])", normalized, maxsplit=1)
    return parts[0].strip()


def _dedupe(items: Iterable[str], *, limit: Optional[int] = None) -> List[str]:
    result: List[str] = []
    seen: set[str] = set()
    for item in items:
        text = " ".join(str(item or "").split()).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
        if limit is not None and len(result) >= limit:
            break
    return result
