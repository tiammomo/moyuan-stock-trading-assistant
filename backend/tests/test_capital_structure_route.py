from app.schemas import UserProfile
from app.services.chat_engine import plan_chat_route
from app.services.skill_registry import (
    SKILL_LOCAL_ORDERBOOK,
    SKILL_LOCAL_REALHEAD,
    SKILL_SEARCH_ANNOUNCEMENT,
    SKILL_SEARCH_REPORT,
    SKILL_WENCAI_SHAREHOLDER_QUERY,
    SKILL_WENCAI_SINGLE_SECURITY_FUNDAMENTAL,
    SKILL_WENCAI_SINGLE_SECURITY_SNAPSHOT,
)


def test_capital_structure_question_uses_lightweight_route():
    detection, route, rewritten_query, plan, direct_result = plan_chat_route(
        "宁德时代主力和散户的情报",
        profile=UserProfile(gpt_enhancement_enabled=False),
    )

    assert direct_result is None
    assert route is not None
    assert route.single_security is True
    assert route.subject == "宁德时代"
    assert route.need_chart is False
    assert plan.intent == "single_stock_deep_research"
    assert detection.mode.value == "mid_term_value"
    assert rewritten_query == "宁德时代主力和散户的情报"

    skill_ids = [skill.skill_id for skill in route.skills]
    assert skill_ids == [
        SKILL_WENCAI_SINGLE_SECURITY_SNAPSHOT,
        SKILL_LOCAL_REALHEAD,
        SKILL_LOCAL_ORDERBOOK,
        SKILL_WENCAI_SHAREHOLDER_QUERY,
    ]
    assert SKILL_WENCAI_SINGLE_SECURITY_FUNDAMENTAL not in skill_ids
    assert SKILL_SEARCH_REPORT not in skill_ids
    assert SKILL_SEARCH_ANNOUNCEMENT not in skill_ids
