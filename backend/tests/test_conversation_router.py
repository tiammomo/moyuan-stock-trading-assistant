from app.services.conversation_router import direct_response_for_plan, route_message


def test_single_stock_deep_research_intent():
    plan = route_message("小白怎么看宁德时代？")
    assert plan.intent == "single_stock_deep_research"
    assert plan.workflow == "single_stock_deep_research"
    assert plan.stock_names == ["宁德时代"]


def test_short_term_operation_intent():
    plan = route_message("东阳光今天能不能买？")
    assert plan.intent == "short_term_operation"
    assert plan.workflow == "short_term_operation"
    assert plan.stock_names == ["东阳光"]
    assert plan.time_horizon == "short_term"
    assert plan.need_chart is True
    assert "kline" in plan.chart_types
    assert "macd" in plan.chart_types
    assert "rsi" in plan.chart_types


def test_stock_compare_intent():
    plan = route_message("贵州茅台和五粮液哪个好？")
    assert plan.intent == "stock_compare"
    assert plan.workflow == "stock_compare"
    assert plan.stock_names == ["贵州茅台", "五粮液"]


def test_capital_structure_connector_is_not_stock_compare():
    plan = route_message("宁德时代主力和散户的情况")
    assert plan.intent == "single_stock_deep_research"
    assert plan.workflow == "single_stock_deep_research"
    assert plan.stock_names == ["宁德时代"]
    assert plan.time_horizon == "mid_term"


def test_capital_structure_intelligence_routes_to_single_stock_research():
    plan = route_message("宁德时代主力和散户的情报")
    assert plan.intent == "single_stock_deep_research"
    assert plan.workflow == "single_stock_deep_research"
    assert plan.stock_names == ["宁德时代"]


def test_capital_structure_question_without_stock_asks_clarification():
    plan = route_message("主力和散户的情况")
    assert plan.intent == "ask_clarification"
    assert plan.workflow == "ask_clarification"
    assert plan.need_clarification is True
    assert "股票名称" in (plan.clarification_question or "")


def test_market_or_sector_analysis_intent():
    plan = route_message("新能源板块怎么样？")
    assert plan.intent == "market_or_sector_analysis"
    assert plan.workflow == "market_or_sector_analysis"


def test_beginner_education_intent():
    plan = route_message("PE 是什么意思？")
    assert plan.intent == "beginner_education"
    assert plan.workflow == "beginner_education"
    assert plan.need_chart is False
    assert plan.chart_types == []


def test_ask_clarification_without_stock_context():
    plan = route_message("这只股票能买吗？")
    assert plan.intent == "ask_clarification"
    assert plan.workflow == "ask_clarification"
    assert plan.need_clarification is True
    assert "股票名称" in (plan.clarification_question or "")


def test_safety_response_for_profit_promise():
    plan = route_message("明天哪只股票必涨？")
    assert plan.intent == "safety_response"
    assert plan.workflow == "safety_response"
    assert plan.risk_level == "high"
    assert plan.need_chart is False

    result = direct_response_for_plan(plan)
    assert result is not None
    assert "无法保证" in result.summary
    assert any(card.type == "risk_warning" or getattr(card.type, "value", "") == "risk_warning" for card in result.cards)


def test_inherit_context_stock_when_follow_up_is_ambiguous():
    plan = route_message("现在能买吗？", context_stock_names=["宁德时代"])
    assert plan.intent == "short_term_operation"
    assert plan.workflow == "short_term_operation"
    assert plan.stock_names == ["宁德时代"]
    assert plan.need_chart is True


def test_short_term_view_question_requires_chart():
    plan = route_message("宁德时代短线怎么看？")
    assert plan.intent == "short_term_operation"
    assert plan.workflow == "short_term_operation"
    assert plan.stock_names == ["宁德时代"]
    assert plan.need_chart is True
    assert "kline" in plan.chart_types


def test_recent_price_analysis_routes_to_short_term_chart_frame():
    plan = route_message("宁德时代的近5日价格分析")
    assert plan.intent == "short_term_operation"
    assert plan.workflow == "short_term_operation"
    assert plan.stock_names[0] == "宁德时代"
    assert plan.time_horizon == "short_term"
    assert plan.need_chart is True
    assert plan.chart_types == ["kline", "volume", "ma5", "ma10", "ma20", "macd", "rsi", "kdj"]


def test_short_term_operation_question_set_routes_to_short_term_with_chart():
    cases = [
        ("东阳光今天能不能买？", "东阳光"),
        ("贵州茅台明天会跌吗？", "贵州茅台"),
        ("宁德时代短线怎么看？", "宁德时代"),
        ("比亚迪现在能不能追？", "比亚迪"),
        ("通富微电要不要止损？", "通富微电"),
    ]
    for query, stock_name in cases:
        plan = route_message(query)
        assert plan.intent == "short_term_operation"
        assert plan.workflow == "short_term_operation"
        assert plan.stock_names == [stock_name]
        assert plan.time_horizon == "short_term"
        assert plan.need_chart is True
        assert "kline" in plan.chart_types


def test_long_term_single_stock_question_is_deep_research_with_long_horizon():
    plan = route_message("贵州茅台长期能不能拿？")
    assert plan.intent == "single_stock_deep_research"
    assert plan.workflow == "single_stock_deep_research"
    assert plan.stock_names == ["贵州茅台"]
    assert plan.time_horizon == "long_term"


def test_long_term_quality_question_set_routes_to_long_horizon():
    cases = [
        ("贵州茅台长期能不能拿？", "贵州茅台"),
        ("宁德时代长线价值怎么样？", "宁德时代"),
        ("比亚迪护城河强不强？", "比亚迪"),
        ("贵州茅台分红和回购怎么样？", "贵州茅台"),
        ("汇川技术适合拿三年吗？", "汇川技术"),
    ]
    for query, stock_name in cases:
        plan = route_message(query)
        assert plan.intent == "single_stock_deep_research"
        assert plan.workflow == "single_stock_deep_research"
        assert plan.stock_names == [stock_name]
        assert plan.time_horizon == "long_term"


def test_mid_term_value_question_set_routes_to_single_stock_research():
    cases = [
        ("比亚迪中线价值如何？", "比亚迪"),
        ("宁德时代值不值得关注？", "宁德时代"),
        ("通富微电基本面怎么样？", "通富微电"),
        ("贵州茅台估值贵不贵？", "贵州茅台"),
        ("汇川技术现金流和财报质量怎么样？", "汇川技术"),
    ]
    for query, stock_name in cases:
        plan = route_message(query)
        assert plan.intent == "single_stock_deep_research"
        assert plan.workflow == "single_stock_deep_research"
        assert plan.stock_names == [stock_name]
        assert plan.time_horizon == "mid_term"


def test_non_single_stock_question_set_does_not_enter_single_stock_analysis():
    cases = [
        ("PE 是什么意思？", "beginner_education"),
        ("新能源板块怎么样？", "market_or_sector_analysis"),
        ("贵州茅台和五粮液哪个好？", "stock_compare"),
        ("这只股票能买吗？", "ask_clarification"),
        ("明天哪只股票必涨？", "safety_response"),
    ]
    for query, intent in cases:
        plan = route_message(query)
        assert plan.intent == intent
        assert plan.workflow == intent
        assert plan.intent != "single_stock_deep_research"
        assert plan.workflow != "single_stock_deep_research"
