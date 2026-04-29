from __future__ import annotations

from types import SimpleNamespace

from app.schemas import CardType, ChatMode, ResultCard, SourceRef, StructuredResult
from app.services.single_stock_capital_harness import enhance_single_stock_capital
from app.services.single_stock_value_harness import enhance_single_stock_value


def _route(subject: str = "宁德时代"):
    return SimpleNamespace(
        subject=subject,
        single_security=True,
        entry_price_focus=False,
        mode=ChatMode.MID_TERM_VALUE,
    )


def _base_result(subject: str = "宁德时代") -> StructuredResult:
    return StructuredResult(
        summary="短线：现价 434.88；今日 -2.25%。\n\n波段：中线先看趋势确认。\n\n操作建议：中线更适合分批跟踪。",
        cards=[
            ResultCard(
                type=CardType.MULTI_HORIZON_ANALYSIS,
                title="三周期分析",
                content="短线偏中性，中线继续跟踪。",
                metadata={
                    "subject": subject,
                    "money_flow": -259000000,
                    "turnover": 0.78,
                    "volume_ratio": 0.71,
                },
            )
        ],
        facts=[
            f"{subject} 当前价格 434.88，今日涨跌幅 -2.25%。",
            "当前换手率约 0.78%，说明市场交易活跃度已被纳入观察。",
            "盘口补充：盘口委比 -58.04% 偏弱，最近逐笔卖盘更重（卖 38.95万股，买 1.28万股）。",
        ],
        judgements=["主力资金当前为 净流出 2.59亿。"],
        sources=[SourceRef(skill="测试资金", query=f"{subject} 主力 散户 筹码")],
    )


def test_capital_harness_answers_main_vs_retail_question():
    result = enhance_single_stock_capital(_route(), _base_result(), user_message="宁德时代主力和散户的情报")

    assert "主力和散户筹码框架" in result.summary
    assert "1. 主力资金方向" in result.summary
    assert "4. 散户筹码线索" in result.summary
    assert "5. 股东户数变化" in result.summary
    assert "6. 前十大股东 / 机构持仓" in result.summary
    assert "9. 数据缺口" in result.summary
    assert "主力资金净流出" in result.summary
    assert "盘口卖压偏重" in result.summary
    assert "本次返回结果未覆盖股东户数变化" in result.summary
    assert "中线价值框架" not in result.summary
    assert "操作建议：" not in result.summary
    assert any(card.title == "主力和散户筹码 V1" for card in result.cards)
    assert any(card.type == CardType.RISK_WARNING for card in result.cards)


def test_capital_harness_keeps_contract_layers_unchanged():
    base = _base_result()
    result = enhance_single_stock_capital(_route(), base, user_message="宁德时代主力和散户的情况")

    assert result.facts == base.facts
    assert result.sources == base.sources
    assert result.table == base.table


def test_value_harness_does_not_override_capital_question():
    base = enhance_single_stock_capital(_route(), _base_result(), user_message="宁德时代资金值得关注吗")
    result = enhance_single_stock_value(_route(), base, user_message="宁德时代资金值得关注吗")

    assert result.summary == base.summary
    assert "主力和散户筹码框架" in result.summary
    assert "中线价值框架" not in result.summary
