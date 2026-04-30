from __future__ import annotations

from types import SimpleNamespace

from app.schemas import CardType, ChatMode, ResultCard, SourceRef, StructuredResult
from app.services.single_stock_long_term_harness import enhance_single_stock_long_term
from app.services.single_stock_value_harness import enhance_single_stock_value


def _route(subject: str = "比亚迪"):
    return SimpleNamespace(
        subject=subject,
        single_security=True,
        entry_price_focus=False,
        mode=ChatMode.MID_TERM_VALUE,
    )


def _base_result(subject: str = "比亚迪") -> StructuredResult:
    return StructuredResult(
        summary=f"{subject}需要同时看业绩、估值、现金流和行业景气。",
        cards=[
            ResultCard(
                type=CardType.MULTI_HORIZON_ANALYSIS,
                title="三周期分析",
                content="中线：财报和估值需要继续验证。长线：行业空间和竞争格局仍是关键。",
                metadata={
                    "subject": subject,
                    "roe": 13.5,
                    "gross_margin": 22.1,
                    "debt_ratio": 58.2,
                    "pe": 24.5,
                    "pb": 4.1,
                    "operating_cash_flow": 35000000000,
                    "industry": "汽车",
                },
            )
        ],
        facts=[
            f"{subject}主营新能源汽车和相关业务，所属行业为汽车。",
            f"{subject}最新财报：营收同比增长，归母净利润同比增长。",
            f"{subject}近期公告和行业催化需要继续跟踪。",
        ],
        judgements=["行业景气、竞争格局和估值消化速度会影响判断。"],
        sources=[SourceRef(skill="测试财报", query=subject)],
    )


def test_mid_term_value_harness_uses_value_frame_and_keeps_contract_layers():
    base = _base_result("比亚迪")
    result = enhance_single_stock_value(_route("比亚迪"), base, user_message="比亚迪中线价值如何？")

    assert "中线价值框架" in result.summary
    assert "2. 业绩增长质量" in result.summary
    assert "4. 估值位置" in result.summary
    assert "5. 现金流验证" in result.summary
    assert "10. 是否值得继续跟踪" in result.summary
    assert any(card.title == "单股中线价值 V1" for card in result.cards)
    assert result.facts == base.facts
    assert result.sources == base.sources


def test_mid_term_value_harness_rebuilds_conclusion_and_filters_runtime_fragments():
    base = StructuredResult(
        summary=(
            "一句话结论：短线：现价 1405.0；今日 -3.67%。\n\n"
            "深度研究框架：\n1. 公司画像 - 个股行业题材\n2. 当前行情状态 - 贵州茅台 当前价格 1405.00"
        ),
        cards=[
            ResultCard(
                type=CardType.CUSTOM,
                title="同花顺题材补充",
                content="主营业务：茅台酒及系列酒的生产与销售",
                metadata={"subject": "贵州茅台", "business": "茅台酒及系列酒的生产与销售"},
            ),
            ResultCard(
                type=CardType.MULTI_HORIZON_ANALYSIS,
                title="三周期分析",
                content="短线：偏弱。中线：需要看财报和估值。",
                metadata={
                    "subject": "贵州茅台",
                    "industry": "食品饮料、白酒Ⅲ",
                    "concept": "超级品牌、白酒概念",
                    "roe": 10.57,
                    "gross_margin": 89.76,
                    "debt_ratio": 12.12,
                    "pe": 16.15,
                    "pb": 6.49,
                    "revenue_growth": 6.54,
                    "profit_growth": 1.47,
                    "operating_cash_flow": 26910000000,
                    "money_flow": -1242000000,
                    "turnover": 0.36,
                },
            ),
        ],
        facts=[
            "个股行业题材",
            "单股实时补充来自同花顺公开行情页、盘口接口和题材页。",
            "贵州茅台 最新财报期 2026-03-31：营收 539.09亿，营收同比 6.54%，归母净利润 272.43亿，归母同比 1.47%，经营现金流 269.10亿。",
        ],
        sources=[SourceRef(skill="测试估值", query="贵州茅台估值贵不贵")],
    )

    result = enhance_single_stock_value(_route("贵州茅台"), base, user_message="贵州茅台估值贵不贵？")

    assert result.summary.count("一句话结论：") == 1
    assert "中线价值框架" in result.summary
    assert "深度研究框架" not in result.summary
    assert "短线：现价" not in result.summary
    assert "个股行业题材" not in result.summary
    assert "单股实时补充来自" not in result.summary
    assert "估值贵不贵不能只看价格" in result.summary
    assert "PE约 16.15" in result.summary
    assert "PB约 6.49" in result.summary
    assert "茅台酒及系列酒的生产与销售" in result.summary
    assert result.facts == base.facts
    assert result.sources == base.sources


def test_mid_term_value_question_set_uses_clean_mid_term_frame():
    cases = [
        ("比亚迪", "比亚迪中线价值如何？", "中线价值要看"),
        ("宁德时代", "宁德时代值不值得关注？", "是否值得关注"),
        ("通富微电", "通富微电基本面怎么样？", "基本面要重点看"),
        ("贵州茅台", "贵州茅台估值贵不贵？", "估值贵不贵不能只看价格"),
        ("汇川技术", "汇川技术现金流和财报质量怎么样？", "现金流和财报质量要看"),
    ]
    forbidden = ["深度研究框架", "短线操作框架", "长期质量框架", "个股行业题材", "单股实时补充来自", "覆盖状态", "已覆盖"]

    for subject, query, expected in cases:
        base = StructuredResult(
            summary="一句话结论：短线：现价 100；今日 -1%。\n\n深度研究框架：\n1. 公司画像 - 个股行业题材",
            cards=[
                ResultCard(
                    type=CardType.CUSTOM,
                    title="同花顺题材补充",
                    content=f"主营业务：{subject}主营业务测试",
                    metadata={"subject": subject, "business": f"{subject}主营业务测试"},
                ),
                ResultCard(
                    type=CardType.MULTI_HORIZON_ANALYSIS,
                    title="三周期分析",
                    content="中线：财报和估值需要继续验证。",
                    metadata={
                        "subject": subject,
                        "industry": "测试行业",
                        "concept": "测试概念",
                        "roe": 12.3,
                        "gross_margin": 30.1,
                        "debt_ratio": 45.6,
                        "pe": 18.2,
                        "pb": 3.4,
                        "revenue_growth": 8.9,
                        "profit_growth": 6.7,
                        "operating_cash_flow": 12300000000,
                        "money_flow": -120000000,
                        "turnover": 1.2,
                    },
                ),
            ],
            facts=[
                "个股行业题材",
                "单股实时补充来自同花顺公开行情页、盘口接口和题材页。",
                f"{subject} 最新财报期 2026-03-31：营收同比 8.90%，归母同比 6.70%，经营现金流 123.00亿。",
            ],
            sources=[SourceRef(skill="测试中线", query=query)],
        )

        result = enhance_single_stock_value(_route(subject), base, user_message=query)

        assert result.summary.count("一句话结论：") == 1
        assert "中线价值框架" in result.summary
        assert expected in result.summary
        assert "4. 估值位置" in result.summary
        assert "5. 现金流验证" in result.summary
        assert "9. 中线风险" in result.summary
        for phrase in forbidden:
            assert phrase not in result.summary
        assert result.facts == base.facts
        assert result.sources == base.sources


def test_long_term_harness_uses_quality_frame_and_keeps_contract_layers():
    base = _base_result("贵州茅台")
    result = enhance_single_stock_long_term(_route("贵州茅台"), base, user_message="贵州茅台长期能不能拿？")

    assert "长期质量框架" in result.summary
    assert "1. 商业模式是不是好生意" in result.summary
    assert "2. 护城河是否稳定" in result.summary
    assert "7. 分红 / 回购 / 股东回报" in result.summary
    assert "10. 长期跟踪清单" in result.summary
    assert any(card.title == "单股长期质量 V1" for card in result.cards)
    assert result.facts == base.facts
    assert result.sources == base.sources


def test_long_term_question_set_uses_clean_long_term_frame_and_focused_conclusion():
    cases = [
        ("贵州茅台", "贵州茅台长期能不能拿？", "具备长期跟踪价值"),
        ("宁德时代", "宁德时代长线价值怎么样？", "长线价值要看"),
        ("比亚迪", "比亚迪护城河强不强？", "护城河不能只看概念"),
        ("贵州茅台", "贵州茅台分红和回购怎么样？", "分红和回购要区分"),
        ("汇川技术", "汇川技术适合拿三年吗？", "适不适合拿三年"),
    ]
    forbidden = ["深度研究框架", "短线操作框架", "中线价值框架", "个股行业题材", "单股实时补充来自", "覆盖状态", "已覆盖"]

    for subject, query, expected in cases:
        base = StructuredResult(
            summary="一句话结论：短线：现价 100；今日 -1%。\n\n深度研究框架：\n1. 公司画像 - 个股行业题材",
            cards=[
                ResultCard(
                    type=CardType.CUSTOM,
                    title="公告搜索补充",
                    content=f"- {subject}：{subject}关于2025年度利润分配方案的公告\n- {subject}：{subject}关于回购股份实施进展的公告",
                ),
                ResultCard(
                    type=CardType.MULTI_HORIZON_ANALYSIS,
                    title="三周期分析",
                    content="长线：质量稳定性需要继续验证。",
                    metadata={
                        "subject": subject,
                        "industry": "测试行业",
                        "concept": "测试概念",
                        "listing_board": "主板",
                        "listing_place": "上海",
                        "roe": 12.3,
                        "gross_margin": 35.0,
                        "debt_ratio": 45.6,
                        "pe": 18.2,
                        "pb": 3.4,
                        "operating_cash_flow": 12300000000,
                    },
                ),
            ],
            facts=[
                "个股行业题材",
                "单股实时补充来自同花顺公开行情页、盘口接口和题材页。",
            ],
            sources=[SourceRef(skill="测试长期", query=query)],
        )

        result = enhance_single_stock_long_term(_route(subject), base, user_message=query)

        assert result.summary.count("一句话结论：") == 1
        assert "长期质量框架" in result.summary
        assert expected in result.summary
        assert "7. 分红 / 回购 / 股东回报" in result.summary
        assert "9. 长期风险" in result.summary
        for phrase in forbidden:
            assert phrase not in result.summary
        assert result.facts == base.facts
        assert result.sources == base.sources


def test_horizon_harnesses_do_not_apply_to_short_term_operation_route():
    base = _base_result("东阳光")
    route = SimpleNamespace(
        subject="东阳光",
        single_security=True,
        entry_price_focus=True,
        mode=ChatMode.SHORT_TERM,
    )

    assert enhance_single_stock_value(route, base, user_message="东阳光今天能不能买？") == base
    assert enhance_single_stock_long_term(route, base, user_message="东阳光今天能不能买？") == base


def test_long_term_harness_filters_runtime_fragments_and_answers_hold_question():
    base = StructuredResult(
        summary="短线：现价 1458.49；今日 2.78%；短线可继续跟踪。",
        cards=[
            ResultCard(
                type=CardType.CUSTOM,
                title="同花顺题材补充",
                content="所属地域：贵州\n涉及概念：超级品牌、白酒概念\n主营业务：茅台酒及系列酒的生产与销售",
                metadata={
                    "subject": "贵州茅台",
                    "business": "茅台酒及系列酒的生产与销售",
                    "themes": ["超级品牌", "白酒概念"],
                },
            ),
            ResultCard(
                type=CardType.MULTI_HORIZON_ANALYSIS,
                title="三周期分析",
                content="长线：行业/题材上主要看 食品饮料、白酒Ⅲ。",
                metadata={
                    "subject": "贵州茅台",
                    "industry": "食品饮料、白酒Ⅲ",
                    "concept": "超级品牌、白酒概念、同花顺漂亮100",
                    "listing_board": "主板",
                    "listing_place": "上海",
                    "roe": 10.57,
                    "gross_margin": 89.76,
                    "debt_ratio": 12.12,
                    "pe": 16.76,
                    "pb": 6.74,
                    "operating_cash_flow": 26910000000,
                },
            ),
        ],
        facts=[
            "同花顺题材补充 已补充地域、概念和主营业务。",
            "个股行业题材",
            "贵州茅台 上市板块 主板，上市地点 上海。",
            "贵州茅台 所属行业 食品饮料、白酒Ⅲ；所属概念 超级品牌、白酒概念、同花顺漂亮100、证金持股。",
        ],
        sources=[SourceRef(skill="测试题材", query="贵州茅台")],
    )

    result = enhance_single_stock_long_term(_route("贵州茅台"), base, user_message="贵州茅台长期能不能拿？")

    assert "长期能不能拿" in result.summary
    assert "茅台酒及系列酒的生产与销售" in result.summary
    assert "品牌定价权" in result.summary
    assert "只能说明上市属性，不能直接证明竞争地位" in result.summary
    assert "同花顺题材补充 已补充" not in result.summary
    assert "\n3. 行业空间和周期位置 - 个股行业题材" not in result.summary
    assert result.facts == base.facts
    assert result.sources == base.sources


def test_long_term_shareholder_return_section_summarizes_announcements_cleanly():
    base = StructuredResult(
        summary="贵州茅台需要看长期质量。",
        cards=[
            ResultCard(
                type=CardType.CUSTOM,
                title="公告搜索补充",
                content=(
                    "- 贵州茅台：贵州茅台关于续聘会计师事务所的公告\n"
                    "- 贵州茅台：贵州茅台关于2025年年度利润分配方案及2026年中期利润分配安排的公告\n"
                    "- 贵州茅台：贵州茅台关于回购股份实施进展的公告"
                ),
            ),
            ResultCard(
                type=CardType.MULTI_HORIZON_ANALYSIS,
                title="三周期分析",
                content="长线：质量稳定性需要继续验证。",
                metadata={
                    "subject": "贵州茅台",
                    "roe": 10.57,
                    "gross_margin": 89.76,
                    "debt_ratio": 12.12,
                    "pe": 16.76,
                    "pb": 6.74,
                    "operating_cash_flow": 26910000000,
                },
            ),
        ],
    )

    result = enhance_single_stock_long_term(_route("贵州茅台"), base, user_message="贵州茅台长期能不能拿？")
    shareholder_section = result.summary.split("7. 分红 / 回购 / 股东回报 - ", 1)[1].split("\n\n8.", 1)[0]

    assert "利润分配" in shareholder_section
    assert "回购" in shareholder_section
    assert "有股东回报安排" in shareholder_section
    assert "分红率" in shareholder_section
    assert "股息率" in shareholder_section
    assert "回购金额占市值比例" in shareholder_section
    assert "公告搜索补充" not in shareholder_section
    assert "关于2025年年度利润分配方案" not in shareholder_section
    assert "续聘会计师事务所" not in shareholder_section


def test_long_term_risk_section_is_stock_specific_for_auto_company():
    base = StructuredResult(
        summary="比亚迪护城河需要看长期质量。",
        cards=[
            ResultCard(
                type=CardType.MULTI_HORIZON_ANALYSIS,
                title="三周期分析",
                content="长线：行业空间和竞争格局仍是关键。",
                metadata={
                    "subject": "比亚迪",
                    "industry": "汽车整车、乘用车",
                    "concept": "新能源汽车、无人驾驶",
                    "roe": 15.12,
                    "gross_margin": 17.74,
                    "debt_ratio": 70.74,
                    "pe": 28.68,
                    "pb": 4.11,
                    "operating_cash_flow": 59136000000,
                },
            )
        ],
    )

    result = enhance_single_stock_long_term(_route("比亚迪"), base, user_message="比亚迪护城河强不强？")
    risk_section = result.summary.split("9. 长期风险 - ", 1)[1].split("\n\n10.", 1)[0]

    assert "资产负债率约 70.74%" in risk_section
    assert "毛利率约 17.74%" in risk_section
    assert "价格战" in risk_section
    assert "PE约 28.68" in risk_section
    assert "行业周期、竞争格局、政策变化和管理层资本配置都可能改变长期逻辑" not in risk_section


def test_long_term_moat_and_position_are_not_business_blob_or_listing_template():
    base = StructuredResult(
        summary="比亚迪护城河需要看长期质量。",
        cards=[
            ResultCard(
                type=CardType.CUSTOM,
                title="同花顺题材补充",
                content=(
                    "主营业务：锂离子电池以及其他电池、充电器、电子产品、仪器仪表、柔性线路板、"
                    "五金制品、手机零配件、模具、塑胶制品及其相关附件的生产、销售；货物及技术进出口；"
                    "作为比亚迪汽车有限公司比亚迪品牌乘用车、电动车的总经销商，从事上述品牌的乘用车、"
                    "电动车及其零部件的营销、批发和出口，提供售后服务；电池管理系统的研发。"
                ),
                metadata={
                    "subject": "比亚迪",
                    "business": (
                        "锂离子电池以及其他电池、充电器、电子产品、仪器仪表、柔性线路板、"
                        "五金制品、手机零配件、模具、塑胶制品及其相关附件的生产、销售；货物及技术进出口；"
                        "作为比亚迪汽车有限公司比亚迪品牌乘用车、电动车的总经销商，从事上述品牌的乘用车、"
                        "电动车及其零部件的营销、批发和出口，提供售后服务；电池管理系统的研发。"
                    ),
                },
            ),
            ResultCard(
                type=CardType.MULTI_HORIZON_ANALYSIS,
                title="三周期分析",
                content="长线：行业空间和竞争格局仍是关键。",
                metadata={
                    "subject": "比亚迪",
                    "industry": "汽车整车、乘用车",
                    "concept": "盐湖提锂、无人驾驶、新能源汽车",
                    "listing_board": "主板",
                    "listing_place": "深圳",
                    "roe": 15.12,
                    "gross_margin": 17.74,
                    "debt_ratio": 70.74,
                    "pe": 28.68,
                    "pb": 4.11,
                    "operating_cash_flow": 59136000000,
                },
            ),
        ],
    )

    result = enhance_single_stock_long_term(_route("比亚迪"), base, user_message="比亚迪护城河强不强？")
    moat_section = result.summary.split("2. 护城河是否稳定 - ", 1)[1].split("\n\n3.", 1)[0]
    position_section = result.summary.split("4. 公司竞争地位 - ", 1)[1].split("\n\n5.", 1)[0]

    assert "..." not in moat_section
    assert "主营业务摘要" not in moat_section
    assert "锂离子电池以及其他电池、充电器、电子产品" not in moat_section
    assert "垂直整合能力" in moat_section
    assert "规模制造" in moat_section
    assert "市占率" in moat_section

    assert "上市板块" not in position_section
    assert "只能说明上市属性" not in position_section
    assert "销量份额" in position_section
    assert "单车盈利" in position_section
    assert "海外销量" in position_section


def test_long_term_weak_quality_signals_are_not_reported_as_missing_data():
    base = StructuredResult(
        summary="铜陵有色长期能不能拿需要看周期和现金流。",
        cards=[
            ResultCard(
                type=CardType.CUSTOM,
                title="同花顺题材补充",
                content="主营业务：选矿；矿物洗选加工；金属矿石销售；常用有色金属冶炼；贵金属冶炼；有色金属压延加工。",
                metadata={
                    "subject": "铜陵有色",
                    "business": "选矿；矿物洗选加工；金属矿石销售；常用有色金属冶炼；贵金属冶炼；有色金属压延加工。",
                },
            ),
            ResultCard(
                type=CardType.MULTI_HORIZON_ANALYSIS,
                title="三周期分析",
                content="长线：周期属性较强。",
                metadata={
                    "subject": "铜陵有色",
                    "industry": "有色金属、工业金属、铜",
                    "concept": "黄金概念、金属铜、金属镍、小金属概念",
                    "listing_board": "主板",
                    "listing_place": "深圳",
                    "roe": 6.82,
                    "gross_margin": 7.86,
                    "debt_ratio": 53.60,
                    "pe": 34.93,
                    "pb": 2.28,
                    "operating_cash_flow": -227000000,
                },
            ),
        ],
        sources=[SourceRef(skill="测试长期", query="铜陵有色长期能不能拿？")],
    )

    result = enhance_single_stock_long_term(_route("铜陵有色"), base, user_message="铜陵有色长期能不能拿？")

    assert "不是数据缺口多" in result.summary
    assert "长期质量信号偏弱" in result.summary
    assert "当前长期判断的数据缺口较多" not in result.summary
    assert "资源禀赋" in result.summary
    assert "矿山资源储量" in result.summary
    assert "商品价格周期" in result.summary
    assert "铜资源储量" in result.summary


def test_long_term_semiconductor_packaging_filters_report_titles_and_uses_industry_logic():
    base = StructuredResult(
        summary="长电科技长期能不能拿需要看先进封装和周期。",
        cards=[
            ResultCard(
                type=CardType.CUSTOM,
                title="研报搜索补充",
                content="- 长电科技（600584）：深度研究报告：国内封测龙头，全面布局先进封装加速成长...",
            ),
            ResultCard(
                type=CardType.MULTI_HORIZON_ANALYSIS,
                title="三周期分析",
                content="长线：半导体封测周期和竞争格局仍是关键。",
                metadata={
                    "subject": "长电科技",
                    "industry": "电子、半导体、集成电路封测",
                    "concept": "绿色电力、无人驾驶、人工智能、机器人概念、毫米波雷达",
                    "listing_board": "主板",
                    "listing_place": "上海",
                    "roe": 5.56,
                    "gross_margin": 14.15,
                    "debt_ratio": 43.64,
                    "pe": 52.95,
                    "pb": 2.89,
                    "operating_cash_flow": 4652000000,
                },
            ),
        ],
        sources=[SourceRef(skill="测试长期", query="长电科技长期能不能拿？")],
    )

    result = enhance_single_stock_long_term(_route("长电科技"), base, user_message="长电科技长期能不能拿？")
    moat_section = result.summary.split("2. 护城河是否稳定 - ", 1)[1].split("\n\n3.", 1)[0]
    position_section = result.summary.split("4. 公司竞争地位 - ", 1)[1].split("\n\n5.", 1)[0]
    risk_section = result.summary.split("9. 长期风险 - ", 1)[1].split("\n\n10.", 1)[0]

    assert "研报搜索补充" not in result.summary
    assert "深度研究报告" not in result.summary
    assert "..." not in result.summary
    assert "估值、行业空间或股东回报数据还不够完整" not in result.summary
    assert "但股东回报还需要补充验证" not in result.summary.split("\n", 1)[0]
    assert "封测公司的护城河" in moat_section
    assert "先进封装能力" in moat_section
    assert "客户结构" in moat_section
    assert "半导体封测链条" in position_section
    assert "先进封装产能" in position_section
    assert "同行盈利能力" in position_section
    assert "半导体封测行业" in risk_section
    assert "下游需求周期" in risk_section
    assert "当前缺少分红、回购和股东回报数据" not in result.summary
    assert "本次返回结果未覆盖分红率、股息率、回购规模或连续派息记录" in result.summary


def test_long_term_shareholder_return_missing_data_is_described_as_data_boundary():
    base = StructuredResult(
        summary="长电科技长期能不能拿需要看质量。",
        cards=[
            ResultCard(
                type=CardType.MULTI_HORIZON_ANALYSIS,
                title="三周期分析",
                content="长线：质量稳定性需要继续验证。",
                metadata={
                    "subject": "长电科技",
                    "industry": "电子、半导体、集成电路封测",
                    "roe": 5.56,
                    "gross_margin": 14.15,
                    "debt_ratio": 43.64,
                    "pe": 52.95,
                    "pb": 2.89,
                    "operating_cash_flow": 4652000000,
                },
            )
        ],
    )

    result = enhance_single_stock_long_term(_route("长电科技"), base, user_message="长电科技长期能不能拿？")
    shareholder_section = result.summary.split("7. 分红 / 回购 / 股东回报 - ", 1)[1].split("\n\n8.", 1)[0]

    assert "当前缺少分红、回购和股东回报数据" not in shareholder_section
    assert "长期持有吸引力需要继续验证" not in shareholder_section
    assert "本次返回结果未覆盖" in shareholder_section
    assert "不能据此判断公司没有股东回报" in shareholder_section
