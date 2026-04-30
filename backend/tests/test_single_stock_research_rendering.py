from __future__ import annotations

from types import SimpleNamespace

from app.schemas import ChatMode, ResultCard, StructuredResult
from app.services.single_stock_research_harness import enhance_single_stock_research


def test_beginner_conclusion_section_does_not_use_truncated_ellipsis():
    base = StructuredResult(
        summary="东阳光需要结合趋势、资金和公告一起看，当前更适合先观察。",
        cards=[
            ResultCard(
                type="operation_guidance",
                title="操作建议卡",
                content=(
                    "现在能不能追：先观察更稳，别急着下手。 当前 K 线 低于MA5 2.6%。 盘口上买一到买三大致在 32.71-32.73 元，"
                    "最近逐笔卖盘更重（卖 48.27万股，买 11.28万股）。\n"
                    "更好的买点：等重新走强或回踩 32.71 元附近出现放量承接。\n"
                    "失效条件：跌破 31.10 元，或主力资金转弱并出现冲高回落，且 MACD 没有修复。\n"
                    "止损/观察位：观察 32.73 元附近承接，止损参考 31.10 元。"
                ),
                metadata={"subject": "东阳光"},
            )
        ],
        facts=[
            "东阳光 当前价格 32.74，今日涨跌幅 -4.10%。",
            "东阳光 技术指标：MA5 33.60，MA20 32.32，MA60 31.76，MACD 0.191，RSI 44.81，KDJ 27.18。",
            "东阳光 最新财报期 2025-12-31：营收 149.35亿，营收同比 22.42%，归母净利润 2.75亿，归母同比 -26.54%，经营现金流 13.09亿。",
            "近期可跟踪的催化线索：东阳光(600673):东阳光关于2026年度日常关联交易预计。",
        ],
        judgements=["东阳光 还要结合公告和主力资金变化继续跟踪。"],
    )
    route = SimpleNamespace(
        subject="东阳光",
        single_security=True,
        entry_price_focus=True,
        mode=ChatMode.SHORT_TERM,
    )

    result = enhance_single_stock_research(
        route,
        base,
        user_message="东阳光今天能不能买？",
    )

    beginner_section = result.summary.split("10. 小白观察清单", 1)[-1]
    assert beginner_section
    assert "..." not in beginner_section
    assert "小白优先盯三件事" in beginner_section
