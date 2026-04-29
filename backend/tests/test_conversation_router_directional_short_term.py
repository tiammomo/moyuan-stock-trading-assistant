from app.services.conversation_router import route_message


def test_directional_short_term_query_routes_to_operation_with_chart():
    plan = route_message("\u8d35\u5dde\u8305\u53f0\u660e\u5929\u4f1a\u8dcc\u5417")

    assert plan.intent == "short_term_operation"
    assert plan.workflow == "short_term_operation"
    assert plan.stock_names == ["\u8d35\u5dde\u8305\u53f0"]
    assert plan.time_horizon == "short_term"
    assert plan.need_chart is True
    assert plan.chart_types == ["kline", "volume", "ma5", "ma10", "ma20", "macd", "rsi"]


def test_directional_trend_query_also_requests_chart():
    plan = route_message("\u8d35\u5dde\u8305\u53f0\u8d70\u52bf\u600e\u4e48\u6837")

    assert plan.intent == "short_term_operation"
    assert plan.workflow == "short_term_operation"
    assert plan.stock_names == ["\u8d35\u5dde\u8305\u53f0"]
    assert plan.need_chart is True
    assert "kline" in plan.chart_types
    assert "macd" in plan.chart_types
    assert "rsi" in plan.chart_types
