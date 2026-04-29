from app.services.local_market_skill_client import LocalKlineBar
from app.services.technical_chart_service import build_chart_config


def test_build_chart_config_generates_core_indicators():
    bars = []
    base = 20.0
    for index in range(40):
        close = base + index * 0.3 + (0.5 if index % 2 == 0 else -0.2)
        open_price = close - 0.15
        high = close + 0.4
        low = close - 0.45
        bars.append(
            LocalKlineBar(
                time=f"2026-03-{index + 1:02d}",
                open_price=open_price,
                close_price=close,
                high_price=high,
                low_price=low,
                volume=1000000 + index * 5000,
                amount=(1000000 + index * 5000) * close,
            )
        )

    chart_config = build_chart_config(
        subject="宁德时代",
        bars=bars,
        chart_types=["kline", "volume", "ma5", "ma10", "ma20", "macd", "rsi", "kdj"],
    )

    assert chart_config is not None
    assert chart_config.subject == "宁德时代"
    assert len(chart_config.items) == len(bars)
    assert chart_config.items[-1].ma5 is not None
    assert chart_config.items[-1].ma10 is not None
    assert chart_config.items[-1].ma20 is not None
    assert chart_config.items[-1].macd is not None
    assert chart_config.items[-1].dif is not None
    assert chart_config.items[-1].dea is not None
    assert chart_config.items[-1].rsi is not None
    assert chart_config.items[-1].k is not None
    assert chart_config.items[-1].d is not None
    assert chart_config.items[-1].j is not None
