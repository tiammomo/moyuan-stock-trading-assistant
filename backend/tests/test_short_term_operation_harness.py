from __future__ import annotations

from types import SimpleNamespace

from app.schemas import CardType, ChatMode, ChartConfig, ChartDataPoint, ResultCard, ResultTable, SourceRef, StructuredResult
from app.services.short_term_operation_harness import enhance_short_term_operation


def _route():
    return SimpleNamespace(
        subject="贵州茅台",
        single_security=True,
        entry_price_focus=True,
        mode=ChatMode.SHORT_TERM,
    )


def _base_result(*, with_chart: bool = False) -> StructuredResult:
    chart_config = None
    if with_chart:
        chart_config = ChartConfig(
            subject="贵州茅台",
            chart_types=["kline", "volume", "ma5", "ma10", "ma20", "macd", "rsi", "kdj"],
            items=[
                ChartDataPoint(
                    time="2026-04-24",
                    open=1450,
                    high=1460,
                    low=1440,
                    close=1458,
                    volume=100000,
                    ma5=1420,
                    ma10=1430,
                    ma20=1440,
                    macd=-3.1,
                    rsi=65,
                    k=52,
                    d=48,
                    j=60,
                )
            ],
        )
    return StructuredResult(
        summary="短线：现价 1458.49；今日 2.78%；量比 1.26，放量，净流入9.29亿。",
        cards=[
            ResultCard(
                type=CardType.OPERATION_GUIDANCE,
                title="操作建议卡",
                content=(
                    "现在能不能追：可以轻仓跟踪，但不适合重仓追价。\n"
                    "更好的买点：回踩 1450 元附近承接稳定时再看。\n"
                    "失效条件：跌破 1385 元，或主力资金转弱。\n"
                    "止损/观察位：观察 1450 元附近承接，止损参考 1385 元。"
                ),
                metadata={"observe_low": 1450, "observe_high": 1458.49, "stop_price": 1385},
            )
        ],
        chart_config=chart_config,
        facts=[
            "贵州茅台 当前价格 1458.49，今日涨跌幅 2.78%。",
            "贵州茅台 技术指标：MA5 1421.98，MA10 1433.77，MACD -3.38，RSI 65.66，KDJ 53.34。",
            "主力资金当前为 净流入 9.29亿。",
        ],
        judgements=["短线需要看量价和资金是否继续配合。"],
        sources=[SourceRef(skill="测试行情", query="贵州茅台")],
    )


def test_short_term_operation_summary_replaces_deep_research_frame():
    base = _base_result(with_chart=True)
    result = enhance_short_term_operation(_route(), base, user_message="贵州茅台明天会跌吗")

    assert "短线操作框架" in result.summary
    assert "深度研究框架" not in result.summary
    assert "2. K线和量能" in result.summary
    assert "9. 止损/观察位" in result.summary
    assert "10. 小白执行清单" in result.summary
    assert "已返回 K 线图表" in result.summary


def test_short_term_operation_rebuilds_conclusion_and_filters_runtime_fragments():
    base = StructuredResult(
        summary="一句话结论：中线价值。\n\n深度研究框架：\n1. 公司画像 - 个股行业题材",
        cards=[
            ResultCard(
                type=CardType.OPERATION_GUIDANCE,
                title="操作建议卡",
                content=(
                    "现在能不能追：先观察更稳，别急着追。\n"
                    "更好的买点：等回踩后量能和承接重新确认。\n"
                    "失效条件：跌破关键观察位且资金持续转弱。\n"
                    "止损/观察位：先看 10.00 元附近承接。"
                ),
                metadata={"observe_low": 9.8, "observe_high": 10.0, "stop_price": 9.5},
            )
        ],
        facts=[
            "个股行业题材",
            "单股实时补充来自同花顺公开行情页、盘口接口和题材页。",
            "东阳光 当前价格 10.20，今日涨跌幅 -1.20%。",
            "东阳光 技术指标：MA5 10.50，MACD -0.12，RSI 42.00。",
        ],
        sources=[SourceRef(skill="测试行情", query="东阳光今天能不能买？")],
    )
    route = SimpleNamespace(
        subject="东阳光",
        single_security=True,
        entry_price_focus=True,
        mode=ChatMode.SHORT_TERM,
    )

    result = enhance_short_term_operation(route, base, user_message="东阳光今天能不能买？")

    assert result.summary.count("一句话结论：") == 1
    assert "短线操作框架" in result.summary
    assert "深度研究框架" not in result.summary
    assert "中线价值" not in result.summary
    assert "个股行业题材" not in result.summary
    assert "单股实时补充来自" not in result.summary
    assert "今天能不能买要看承接、量能和失效条件" in result.summary
    assert result.facts == base.facts
    assert result.sources == base.sources


def test_short_term_operation_keeps_contract_layers_and_cards():
    base = _base_result()
    result = enhance_short_term_operation(_route(), base, user_message="贵州茅台今天能不能买？")

    assert result.facts == base.facts
    assert result.sources == base.sources
    assert any(card.type == CardType.RISK_WARNING for card in result.cards)

    operation_card = next(card for card in result.cards if card.type == CardType.OPERATION_GUIDANCE)
    for section in ["现在能不能追", "更好的买点", "失效条件", "止损/观察位"]:
        assert section in operation_card.content
        assert section in result.summary

    combined = result.summary + "\n" + "\n".join(card.content for card in result.cards)
    for forbidden in ["稳赚", "必涨", "无风险", "直接买入", "梭哈", "满仓", "保证收益"]:
        assert forbidden not in combined


def test_short_term_operation_explicitly_mentions_missing_chart_data():
    result = enhance_short_term_operation(_route(), _base_result(), user_message="贵州茅台短线怎么看？")

    combined = result.summary + "\n" + "\n".join(result.judgements)
    assert result.chart_config is None
    assert "当前未生成可视化 K 线图表" in combined


def test_recent_price_analysis_uses_price_analysis_frame_not_operation_frame():
    base = _base_result(with_chart=True)
    result = enhance_short_term_operation(_route(), base, user_message="贵州茅台的近5日价格分析")

    assert "近5日价格分析框架" in result.summary
    assert "短线操作框架" not in result.summary
    assert "1. 价格变化" in result.summary
    assert "2. K线位置" in result.summary
    assert "3. 量能变化" in result.summary
    assert "4. 均线关系" in result.summary
    assert "5. 技术指标" in result.summary
    assert "10. 小白观察清单" in result.summary
    assert "已返回 K 线图表" in result.summary


def test_recent_price_analysis_technical_section_prefers_numeric_indicators():
    base = StructuredResult(
        summary="短线查询完成。",
        cards=[
            ResultCard(
                type=CardType.OPERATION_GUIDANCE,
                title="操作建议卡",
                content=(
                    "现在能不能追：先观察。\n"
                    "更好的买点：等回踩承接。\n"
                    "失效条件：跌破观察位。\n"
                    "止损/观察位：看 430 元。"
                ),
            )
        ],
        facts=[
            "个股技术指标",
            "宁德时代 当前价格 434.88，今日涨跌幅 -2.25%。",
            "宁德时代 技术指标：MA5 439.13，MA20 415.04，MA60 380.46，MACD 2.346，RSI 55.25，KDJ 55.95，布林中轨 415.04，量比 0.71。",
        ],
    )

    result = enhance_short_term_operation(_route(), base, user_message="宁德时代的近5日价格分析")
    technical_section = result.summary.split("5. 技术指标 - ", 1)[1].split("\n\n6.", 1)[0]

    assert "个股技术指标" not in technical_section
    assert "MACD 2.346" in technical_section
    assert "RSI 55.25" in technical_section
    assert "KDJ 55.95" in technical_section
    assert "MACD 在零轴上方或红柱区，偏修复" in technical_section
    assert "RSI处在中性区" in technical_section
    assert "量比偏缩量" in technical_section


def test_recent_price_analysis_reads_indicators_from_table_when_facts_are_sparse():
    base = StructuredResult(
        summary="短线查询完成。",
        table=ResultTable(
            columns=["股票简称", "最新价", "MA5", "MA10", "MA20", "MACD", "RSI", "KDJ", "量比"],
            rows=[
                {
                    "股票简称": "宁德时代",
                    "最新价": 434.88,
                    "MA5": 439.13,
                    "MA10": 441.20,
                    "MA20": 415.04,
                    "MACD": 2.346,
                    "RSI": 55.25,
                    "KDJ": 55.95,
                    "量比": 0.71,
                }
            ],
        ),
        cards=[
            ResultCard(
                type=CardType.OPERATION_GUIDANCE,
                title="操作建议卡",
                content=(
                    "现在能不能追：先观察。\n"
                    "更好的买点：等回踩承接。\n"
                    "失效条件：跌破观察位。\n"
                    "止损/观察位：看 430 元。"
                ),
            )
        ],
        facts=[
            "宁德时代 当前价格 434.88，今日涨跌幅 -2.25%。",
            "宁德时代 今日 K 线：日K开 444.63，高 448.76，低 433.80，收 434.88，收在日内低位。",
        ],
    )

    result = enhance_short_term_operation(_route(), base, user_message="宁德时代的近5日价格分析")

    assert "当前缺少 MA5/MA10/MA20 数据" not in result.summary
    assert "当前缺少 MACD、RSI、KDJ、布林带" not in result.summary
    assert "MA5 439.13" in result.summary
    assert "MACD 2.346" in result.summary
    assert "价格低于MA5" in result.summary
    assert "RSI处在中性区" in result.summary


def test_recent_price_analysis_formats_chart_indicator_numbers():
    base = StructuredResult(
        summary="短线查询完成。",
        chart_config=ChartConfig(
            subject="宁德时代",
            chart_types=["kline", "volume", "ma5", "ma10", "ma20", "macd", "rsi", "kdj"],
            items=[
                ChartDataPoint(
                    time="2026-04-24",
                    close=434.88,
                    volume=1000,
                    ma5=439.14399999999995,
                    ma10=435.36400000000003,
                    ma20=415.0795,
                    macd=2.1819406951936173,
                    rsi=71.7490494296578,
                    k=67.14257388399783,
                )
            ],
        ),
        cards=[
            ResultCard(
                type=CardType.OPERATION_GUIDANCE,
                title="操作建议卡",
                content=(
                    "现在能不能追：先观察。\n"
                    "更好的买点：等回踩承接。\n"
                    "失效条件：跌破观察位。\n"
                    "止损/观察位：看 430 元。"
                ),
            )
        ],
        facts=["宁德时代 当前价格 434.88，今日涨跌幅 -2.25%。"],
    )

    result = enhance_short_term_operation(_route(), base, user_message="宁德时代的近5日价格分析")

    assert "439.14399999999995" not in result.summary
    assert "435.36400000000003" not in result.summary
    assert "2.1819406951936173" not in result.summary
    assert "MA5 439.14" in result.summary
    assert "MA10 435.36" in result.summary
    assert "MACD 2.182" in result.summary
    assert "RSI 71.75" in result.summary
    assert "KDJ 67.14" in result.summary


def test_recent_price_analysis_does_not_claim_kline_missing_when_text_kline_exists():
    base = StructuredResult(
        summary="短线查询完成。",
        cards=[
            ResultCard(
                type=CardType.OPERATION_GUIDANCE,
                title="操作建议卡",
                content=(
                    "现在能不能追：先观察更稳，别急着下手。盘口上盘口委比 -58.04% 偏弱。"
                    "\n更好的买点：等重新走强或回踩 434.86 元附近出现放量承接。"
                    "\n失效条件：跌破 413.14 元，或主力资金转弱并出现冲高回落，且 MACD 没有修复。"
                    "\n止损/观察位：观察 434.88 元附近承接，止损参考 413.14 元。"
                ),
            )
        ],
        facts=[
            "宁德时代 当前价格 434.88，今日涨跌幅 -2.25%。",
            "宁德时代 今日 K 线：日K开 444.63，高 448.76，低 433.80，收 434.88，收在日内低位。",
        ],
    )

    result = enhance_short_term_operation(_route(), base, user_message="宁德时代的近5日价格分析")
    combined = result.summary + "\n" + "\n".join(result.judgements)
    technical_section = result.summary.split("5. 技术指标 - ", 1)[1].split("\n\n6.", 1)[0]

    assert "当前缺少 K 线 / 指标数据，因此短线判断置信度较低" not in combined
    assert "本次已有文字 K 线，但可视化 K 线图表暂未生成" in result.summary
    assert "操作建议卡" not in technical_section
    assert "现在能不能追" not in technical_section


def test_non_short_term_route_is_not_changed():
    base = _base_result()
    route = SimpleNamespace(
        subject="贵州茅台",
        single_security=True,
        entry_price_focus=False,
        mode=ChatMode.MID_TERM_VALUE,
    )

    result = enhance_short_term_operation(route, base, user_message="小白怎么看贵州茅台？")

    assert result == base
