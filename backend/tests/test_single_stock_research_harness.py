from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from app.schemas import CardType, ChatMode, ResultCard, ResultTable, SourceRef, StructuredResult
from app.services.single_stock_research_harness import (
    DIMENSIONS,
    OPERATION_SECTIONS,
    enhance_single_stock_research,
    extract_deep_research_subject,
    preflight_single_stock_research,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "single_stock_research_cases.json"


def _load_cases():
    return {case["id"]: case for case in json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))}


def _route(subject: str = "贵州茅台", *, operation: bool = False):
    return SimpleNamespace(
        subject=subject,
        single_security=True,
        entry_price_focus=operation,
        mode=ChatMode.MID_TERM_VALUE,
    )


def _sample_result(subject: str = "贵州茅台") -> StructuredResult:
    return StructuredResult(
        summary=f"{subject}需要同时看品牌护城河、估值现金流和行业景气，当前更适合跟踪而不是冲动操作。",
        table=ResultTable(
            columns=["名称", "最新价", "涨跌幅", "成交额", "量比", "换手率", "PE", "PB"],
            rows=[
                {
                    "名称": subject,
                    "最新价": 1688.0,
                    "涨跌幅": "1.2%",
                    "成交额": "85亿元",
                    "量比": 1.1,
                    "换手率": "0.4%",
                    "PE": 26.5,
                    "PB": 8.2,
                }
            ],
        ),
        cards=[
            ResultCard(
                type=CardType.MULTI_HORIZON_ANALYSIS,
                title="三周期分析",
                content="短线：MA20上方震荡，MACD修复。中线：ROE和现金流仍需跟踪。长线：行业龙头属性明显。",
                metadata={
                    "subject": subject,
                    "ma20": 1600,
                    "macd": 0.3,
                    "rsi": 55,
                    "roe": 30,
                    "operating_cash_flow": 1000000000,
                    "industry": "白酒",
                    "concept": "高端消费",
                },
            ),
            ResultCard(
                type=CardType.RESEARCH_NEXT_STEP,
                title="新闻搜索补充",
                content="- 近期公告显示公司披露分红方案\n- 研报观点关注渠道库存和批价",
            ),
        ],
        facts=[
            f"{subject}主营高端白酒，所属行业为白酒，所属概念包括高端消费。",
            f"{subject}最新价1688元，涨跌幅1.2%，成交额85亿元，成交量和量比处于正常区间。",
            f"{subject}技术指标：MA5、MA20、MACD、RSI、KDJ、布林带均已返回。",
            f"{subject}最新财报：营收同比增长，净利润同比增长，毛利率、净利率、ROE较高，资产负债率较低。",
            f"{subject}估值指标包括PE、PB、PS，经营现金流为正。",
            f"{subject}主力资金小幅净流入，换手率较低，股东户数和前十大股东需要继续跟踪。",
            f"{subject}近期新闻、公告和研报均提示行业景气度和渠道批价是催化事件。",
        ],
        judgements=[
            "公司赚钱逻辑主要来自品牌、渠道和产品结构。",
            "估值相对行业不便宜，需要结合现金流验证是否存在利润好看但现金流差的风险。",
            "行业位置偏龙头，仍受政策、周期和消费景气影响。",
            "短线风险是追高和量能衰减，中线风险是估值、财务和行业景气变化。",
            "小白重点看三件事：业绩质量、现金流、批价和渠道库存信号。",
        ],
        follow_ups=["补充最新公告", "只看估值现金流", "生成小白观察清单"],
        sources=[SourceRef(skill="问财个股快照", query=f"{subject} 最新价 基本面 估值 现金流")],
    )


def _research_card(result: StructuredResult) -> ResultCard:
    return next(card for card in result.cards if card.title == "单股深度研究 V1")


def _summary_section(summary: str, number: int) -> str:
    import re

    pattern = rf"\n{number}\. .*?(?=\n\d+\. |\Z)"
    match = re.search(pattern, summary, flags=re.S)
    return match.group(0) if match else ""


def test_deep_research_covers_all_dimensions_and_keeps_contract_layers():
    result = enhance_single_stock_research(
        _route("贵州茅台"),
        _sample_result("贵州茅台"),
        user_message="小白怎么看贵州茅台？",
    )

    card = _research_card(result)
    dimensions = card.metadata["dimensions"]
    assert set(dimensions) == {spec.key for spec in DIMENSIONS}
    assert all(state["status"] in {"available", "partial", "missing"} for state in dimensions.values())
    assert "一句话结论" in result.summary
    assert "1. 公司画像" in result.summary
    assert "10. 小白观察清单" in result.summary
    assert result.facts == _sample_result("贵州茅台").facts
    assert result.sources == _sample_result("贵州茅台").sources
    assert any(card.type == CardType.RISK_WARNING for card in result.cards)


def test_fixture_must_have_dimensions_are_present():
    case = _load_cases()["beginner_maotai"]
    result = enhance_single_stock_research(
        _route("贵州茅台"),
        _sample_result("贵州茅台"),
        user_message=case["query"],
    )
    dimensions = _research_card(result).metadata["dimensions"]
    for dimension in case["must_have_dimensions"]:
        assert dimension in dimensions
        assert dimensions[dimension]["status"] in {"available", "partial"}
    combined = json.dumps(result.model_dump(mode="json"), ensure_ascii=False)
    for phrase in case["forbidden_phrases"]:
        assert phrase not in combined


def test_missing_data_is_explicit_and_not_added_to_facts():
    base = StructuredResult(
        summary="只拿到很少信息。",
        facts=["当前仅确认该标的是贵州茅台。"],
        sources=[SourceRef(skill="测试快照", query="贵州茅台")],
    )
    result = enhance_single_stock_research(
        _route("贵州茅台"),
        base,
        user_message="小白怎么看贵州茅台？",
    )

    assert "当前缺少" in result.summary
    assert any("当前缺少" in judgement for judgement in result.judgements)
    assert result.facts == base.facts
    assert result.sources == base.sources


def test_report_summary_filters_runtime_query_logs():
    base = _sample_result("上海电气")
    base.facts.insert(0, "个股价格量能 查询 `上海电气 最新价 涨跌幅 近5日涨跌幅 开盘价 最高价 最低价 振幅 量比 换手率 成交额 主力资金净流入` 命中 1 条，当前取 1 条。")
    result = enhance_single_stock_research(
        _route("上海电气"),
        base,
        user_message="上海电气今天能不能买？",
    )

    assert "查询 `" not in result.summary
    assert "命中 1 条" not in result.summary
    assert "覆盖状态" not in result.summary
    assert "已覆盖" not in result.summary
    assert "深度研究框架" in result.summary
    assert "\n1. " in result.summary
    assert "\n2. " in result.summary


def test_bare_stock_name_also_gets_deep_research_report():
    result = enhance_single_stock_research(
        _route("胜宏科技"),
        _sample_result("胜宏科技"),
        user_message="胜宏科技",
    )

    assert "一句话结论" in result.summary
    assert "深度研究框架" in result.summary
    assert "1. " in result.summary
    assert any(card.title == "单股深度研究 V1" for card in result.cards)


def test_fundamental_valuation_and_risk_sections_are_fully_explained():
    result = enhance_single_stock_research(
        _route("汇川技术", operation=True),
        _sample_result("汇川技术"),
        user_message="汇川技术短线怎么看？",
    )

    assert "4. 基本面质量" in result.summary
    assert "营收" in result.summary
    assert ("净利润" in result.summary) or ("最新财报" in result.summary)
    assert "ROE" in result.summary
    assert "5. 估值与现金流" in result.summary
    assert "经营现金流" in result.summary
    assert "相对行业偏贵还是偏便宜" in result.summary
    assert "9. 主要风险" in result.summary
    assert "失效条件" in result.summary
    assert "止损/观察位" in result.summary


def test_market_snapshot_and_risk_sections_use_cleaner_report_logic():
    result = enhance_single_stock_research(
        _route("汇川技术", operation=True),
        _sample_result("汇川技术"),
        user_message="汇川技术今天能不能买？",
    )

    market_section = _summary_section(result.summary, 2)
    assert market_section
    assert "MA" not in market_section
    assert "MACD" not in market_section
    assert "RSI" not in market_section
    assert "KDJ" not in market_section

    risk_section = _summary_section(result.summary, 9)
    assert risk_section
    assert "中线风险" in risk_section
    assert "失效条件" in risk_section
    assert "止损/观察位" in risk_section
    assert "现在能不能追" not in risk_section


def test_operation_question_has_guidance_card_and_four_sections():
    case = _load_cases()["short_term_dongyangguang"]
    result = enhance_single_stock_research(
        _route("东阳光", operation=True),
        _sample_result("东阳光"),
        user_message=case["query"],
    )

    card_types = [card.type.value if isinstance(card.type, CardType) else card.type for card in result.cards]
    for card_type in case["must_have_cards"]:
        assert card_type in card_types
    operation_card = next(card for card in result.cards if card.type == CardType.OPERATION_GUIDANCE)
    for section in OPERATION_SECTIONS:
        assert section in operation_card.content


def test_ambiguous_stock_question_asks_for_name_or_code():
    case = _load_cases()["ambiguous_stock"]
    result = preflight_single_stock_research(case["query"])
    assert result is not None
    combined = json.dumps(result.model_dump(mode="json"), ensure_ascii=False)
    for expected in case["must_ask_for"]:
        assert expected in combined


def test_unsafe_profit_promise_refuses_guarantee_without_forbidden_promise():
    case = _load_cases()["unsafe_profit_promise"]
    result = preflight_single_stock_research(case["query"])
    assert result is not None
    combined = json.dumps(result.model_dump(mode="json"), ensure_ascii=False)
    for expected in case["must_have"]:
        assert expected in combined
    for forbidden in ("稳赚", "必涨", "无风险", "一定上涨", "直接买入", "梭哈", "满仓", "保证收益"):
        assert forbidden not in combined


def test_subject_extraction_for_acceptance_queries():
    assert extract_deep_research_subject("小白怎么看贵州茅台？") == "贵州茅台"
    assert extract_deep_research_subject("宁德时代中线价值如何？") == "宁德时代"
    assert extract_deep_research_subject("分析一下比亚迪的基本面和估值") == "比亚迪"
    assert extract_deep_research_subject("通富微电现在值不值得关注？") == "通富微电"
    assert extract_deep_research_subject("东阳光今天能不能买？") == "东阳光"
