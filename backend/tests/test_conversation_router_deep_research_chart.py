from app.services.conversation_router import route_message


def test_deep_research_queries_also_request_chart_for_single_stock():
    for query, expected_name in [
        ("小白怎么看宁德时代？", "宁德时代"),
        ("分析一下贵州茅台", "贵州茅台"),
        ("比亚迪中线价值如何？", "比亚迪"),
        ("通富微电值得关注吗？", "通富微电"),
    ]:
        plan = route_message(query)
        assert plan.intent == "single_stock_deep_research"
        assert plan.workflow == "single_stock_deep_research"
        assert plan.stock_names == [expected_name]
        assert plan.need_chart is True
        assert "kline" in plan.chart_types
        assert "macd" in plan.chart_types
        assert "rsi" in plan.chart_types
