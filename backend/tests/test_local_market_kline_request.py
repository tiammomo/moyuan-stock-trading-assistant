from __future__ import annotations

import json
import urllib.error

from app.services.local_market_skill_client import local_market_skill_client


def test_fetch_daily_kline_uses_stable_eastmoney_query_params(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "data": {
                        "klines": [
                            "2026-04-01,10,10.5,10.8,9.9,100000,1050000",
                            "2026-04-02,10.5,10.6,10.9,10.2,120000,1272000",
                        ]
                    }
                }
            ).encode("utf-8")

    def fake_urlopen(request, timeout=15):
        captured["url"] = request.full_url
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    bars = local_market_skill_client.fetch_daily_kline("000001", limit=30)

    assert len(bars) == 2
    assert "ut=fa5fd1943c7b386f172d6893dbfba10b" in captured["url"]
    assert "beg=0" in captured["url"]
    assert "end=20500101" in captured["url"]


def test_fetch_daily_kline_falls_back_to_tencent_when_eastmoney_fails(monkeypatch):
    captured_urls = []

    class FakeTencentResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "data": {
                        "sh600519": {
                            "qfqday": [
                                ["2026-04-01", "1400", "1410", "1420", "1390", "10000", "14100000"],
                                ["2026-04-02", "1410", "1425", "1430", "1405", "12000", "17100000"],
                            ]
                        }
                    }
                }
            ).encode("utf-8")

    def fake_urlopen(request, timeout=15):
        captured_urls.append(request.full_url)
        if "push2his.eastmoney.com" in request.full_url:
            raise urllib.error.URLError("eastmoney unavailable")
        return FakeTencentResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    bars = local_market_skill_client.fetch_daily_kline("600519", limit=30)

    assert len(bars) == 2
    assert bars[0].time == "2026-04-01"
    assert bars[0].open_price == 1400.0
    assert bars[-1].close_price == 1425.0
    assert any("push2his.eastmoney.com" in url for url in captured_urls)
    assert any("web.ifzq.gtimg.cn" in url and "sh600519" in url for url in captured_urls)
