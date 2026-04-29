from __future__ import annotations

from types import SimpleNamespace

from app.schemas import ChatMode, ResultCard, StructuredResult
from app.services.single_stock_research_harness import enhance_single_stock_research


def test_risk_section_does_not_fall_back_to_truncated_operation_guidance():
    base = StructuredResult(
        summary="贵州茅台短线可以继续跟踪，但更适合轻仓试错，不适合重仓追价。",
        cards=[
            ResultCard(
                type="operation_guidance",
                title="操作建议卡",
                content=(
                    "现在能不能追：可以轻仓跟踪，但不适合重仓追价。当前 K 线站上MA5 2.6%。盘口上盘口委比 46.47% 偏强，最近逐笔买盘更主动（买 7.84万股，卖 8500股）。\n"
                    "更好的买点：等重新走强或回踩 1458.46 元附近出现放量承接。\n"
                    "失效条件：跌破 1385.57 元，或主力资金转弱并出现冲高回落，且 MACD 没有修复。\n"
                    "止损/观察位：观察 1458.48 元附近承接，止损参考 1385.57 元。"
                ),
                metadata={"subject": "贵州茅台"},
            )
        ],
        facts=[
            "贵州茅台 当前价格 1458.49，今日涨跌幅 2.78%。",
            "贵州茅台 技术指标：MA5 1421.98，MA10 1433.77，MA20 1441.13，MACD -3.38，RSI 65.66，KDJ 53.34。",
            "贵州茅台 最新财报期 2026-03-31：营收 539.09亿，营收同比 6.54%，归母净利润 272.43亿，归母同比 1.47%，经营现金流 269.10亿。",
            "近期可跟踪的催化线索：贵州茅台(600519)2026年一季报点评：市场化成效显著 I茅台放量增长。",
        ],
        judgements=["贵州茅台 还缺少同行估值对比，行业和消息面还要持续跟踪。"],
    )
    route = SimpleNamespace(
        subject="贵州茅台",
        single_security=True,
        entry_price_focus=True,
        mode=ChatMode.SHORT_TERM,
    )

    result = enhance_single_stock_research(
        route,
        base,
        user_message="贵州茅台明天会跌吗？",
    )

    risk_section = result.summary.split("9. 主要风险", 1)[-1].split("10. 小白观察清单", 1)[0]
    assert risk_section
    assert "..." not in risk_section
    assert "现在能不能追" not in risk_section
