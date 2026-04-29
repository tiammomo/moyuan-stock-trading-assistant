from __future__ import annotations

import json

import pytest

from app.schemas import ChatMode, SkillStrategy, UserProfile
from app.services.chat_engine import RoutePlan, _chart_unavailable_judgement, _execute_plan_core
from app.services.local_market_skill_client import LocalMarketSkillError, local_market_skill_client


def test_execute_plan_core_degrades_when_chart_build_raises_unexpected_error(monkeypatch):
    route = RoutePlan(
        mode=ChatMode.SHORT_TERM,
        strategy=SkillStrategy.SINGLE_SOURCE,
        skills=[],
        subject="\u4e1c\u9633\u5149",
        single_security=True,
        need_chart=True,
        chart_types=["kline", "volume", "ma5", "ma10", "ma20", "macd", "rsi"],
    )

    def boom(route, primary_raw_row):
        raise RuntimeError("unexpected chart error")

    monkeypatch.setattr("app.services.chat_engine._maybe_build_single_security_chart_config", boom)

    result, skills_used, rewritten_query, user_visible_error = _execute_plan_core(
        route,
        UserProfile(gpt_enhancement_enabled=False),
        "\u4e1c\u9633\u5149\u4eca\u5929\u80fd\u4e0d\u80fd\u4e70\uff1f",
    )

    combined = result.summary + "\n" + "\n".join(result.judgements)
    assert result.summary
    assert result.chart_config is None
    assert "K" in combined
    assert skills_used == []
    assert rewritten_query == ""
    assert user_visible_error is None


def test_chart_unavailable_judgement_distinguishes_missing_visual_from_missing_data():
    facts = [
        "宁德时代 今日 K 线：日K开 444.63，高 448.76，低 433.80，收 434.88，收在日内低位。",
        "宁德时代 技术指标：MA5 439.13，MACD 2.346，RSI 55.25。",
    ]

    assert "当前未生成可视化 K 线图表" in _chart_unavailable_judgement(facts, [])
    assert "当前缺少 K 线 / 指标数据" in _chart_unavailable_judgement([], [])


def test_fetch_daily_kline_rejects_when_all_payload_shapes_are_unexpected(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps([]).encode("utf-8")

    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout=15: FakeResponse())

    with pytest.raises(LocalMarketSkillError, match="K line sources failed"):
        local_market_skill_client.fetch_daily_kline("000001", limit=30)


def test_fetch_daily_kline_uses_sina_as_third_fallback(monkeypatch):
    calls = []

    class FakeResponse:
        def __init__(self, body: str):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return self.body.encode("utf-8")

    def fake_urlopen(request, timeout=15):
        url = request.full_url
        calls.append(url)
        if "push2his.eastmoney.com" in url:
            return FakeResponse(json.dumps([]))
        if "web.ifzq.gtimg.cn" in url:
            return FakeResponse(json.dumps({"data": {}}))
        return FakeResponse(
            'var _sz000001_240_30=[{"day":"2026-04-20","open":"10.00","high":"10.30","low":"9.90","close":"10.20","volume":"1000"}];'
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    bars = local_market_skill_client.fetch_daily_kline("000001", limit=30)

    assert len(bars) == 1
    assert bars[0].time == "2026-04-20"
    assert bars[0].close_price == 10.2
    assert any("quotes.sina.cn" in url for url in calls)
