from app.schemas import ChatMode, UserProfile
from app.services.chat_engine import build_route


def test_bare_stock_query_requests_chart_in_single_security_route():
    route = build_route(
        "\u8d35\u5dde\u8305\u53f0",
        ChatMode.SHORT_TERM,
        UserProfile(gpt_enhancement_enabled=False),
    )

    assert route.single_security is True
    assert route.subject == "\u8d35\u5dde\u8305\u53f0"
    assert route.need_chart is True
    assert route.chart_types == ["kline", "volume", "ma5", "ma10", "ma20", "macd", "rsi", "kdj"]
