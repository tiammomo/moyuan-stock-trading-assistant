from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Dict, List, Optional, Protocol, Union

from .local_market_skill_client import (
    LocalOrderBookSnapshot,
    LocalRealheadSnapshot,
    LocalThemeSnapshot,
    local_market_skill_client,
)
from .skill_registry import SkillAdapterKind, SkillSpec
from .wencai_client import wencai_client


@dataclass(frozen=True)
class WencaiQueryAdapterResult:
    rows: List[Dict[str, Any]]
    code_count: int
    latency_ms: int


@dataclass(frozen=True)
class WencaiSearchAdapterResult:
    titles: List[str]
    latency_ms: int


@dataclass(frozen=True)
class LocalRealheadAdapterResult:
    snapshot: LocalRealheadSnapshot
    latency_ms: int


@dataclass(frozen=True)
class LocalOrderBookAdapterResult:
    order_book: LocalOrderBookSnapshot
    trades: List[Any]
    latency_ms: int


@dataclass(frozen=True)
class LocalThemeAdapterResult:
    snapshot: LocalThemeSnapshot
    latency_ms: int


SkillAdapterResult = Union[
    WencaiQueryAdapterResult,
    WencaiSearchAdapterResult,
    LocalRealheadAdapterResult,
    LocalOrderBookAdapterResult,
    LocalThemeAdapterResult,
]


class SkillAdapter(Protocol):
    def execute(self, spec: SkillSpec, **kwargs: Any) -> SkillAdapterResult:
        ...


def _result_titles(items: List[Dict[str, Any]], limit: int = 3) -> List[str]:
    titles: List[str] = []
    for item in items[:limit]:
        title = item.get("title") or item.get("summary")
        if title:
            titles.append(str(title))
    return titles


class WencaiQueryAdapter:
    def execute(self, spec: SkillSpec, **kwargs: Any) -> WencaiQueryAdapterResult:
        query = str(kwargs["query"])
        limit = int(kwargs.get("limit", 10))
        result = wencai_client.query2data(query, limit=limit)
        datas = result.get("datas") or []
        return WencaiQueryAdapterResult(
            rows=datas if isinstance(datas, list) else [],
            code_count=int(result.get("code_count", len(datas))),
            latency_ms=int(result.get("_latency_ms", 0)),
        )


class WencaiSearchAdapter:
    def execute(self, spec: SkillSpec, **kwargs: Any) -> WencaiSearchAdapterResult:
        query = str(kwargs["query"])
        limit = int(kwargs.get("limit", 3))
        channel = spec.default_channel
        if not channel:
            raise ValueError(f"Skill {spec.skill_id} missing default_channel")
        result = wencai_client.comprehensive_search(channel, query, limit=limit)
        data = result.get("data") or []
        items = data if isinstance(data, list) else []
        return WencaiSearchAdapterResult(
            titles=_result_titles(items, limit=limit),
            latency_ms=int(result.get("_latency_ms", 0)),
        )


class LocalRealheadAdapter:
    def execute(self, spec: SkillSpec, **kwargs: Any) -> LocalRealheadAdapterResult:
        code = str(kwargs["code"])
        started = perf_counter()
        snapshot = local_market_skill_client.fetch_realhead(code)
        return LocalRealheadAdapterResult(
            snapshot=snapshot,
            latency_ms=int((perf_counter() - started) * 1000),
        )


class LocalOrderBookAdapter:
    def execute(self, spec: SkillSpec, **kwargs: Any) -> LocalOrderBookAdapterResult:
        code = str(kwargs["code"])
        realhead = kwargs.get("realhead")
        started = perf_counter()
        order_book = local_market_skill_client.fetch_order_book(code, realhead=realhead)
        trades = local_market_skill_client.fetch_trade_details(code, limit=12)
        return LocalOrderBookAdapterResult(
            order_book=order_book,
            trades=trades,
            latency_ms=int((perf_counter() - started) * 1000),
        )


class LocalThemeAdapter:
    def execute(self, spec: SkillSpec, **kwargs: Any) -> LocalThemeAdapterResult:
        code = str(kwargs["code"])
        started = perf_counter()
        snapshot = local_market_skill_client.fetch_theme_snapshot(code)
        return LocalThemeAdapterResult(
            snapshot=snapshot,
            latency_ms=int((perf_counter() - started) * 1000),
        )


_ADAPTERS: Dict[SkillAdapterKind, SkillAdapter] = {
    SkillAdapterKind.WENCAI_QUERY: WencaiQueryAdapter(),
    SkillAdapterKind.WENCAI_SEARCH: WencaiSearchAdapter(),
    SkillAdapterKind.LOCAL_REALHEAD: LocalRealheadAdapter(),
    SkillAdapterKind.LOCAL_ORDERBOOK: LocalOrderBookAdapter(),
    SkillAdapterKind.LOCAL_THEME: LocalThemeAdapter(),
}


def get_skill_adapter(kind: SkillAdapterKind) -> SkillAdapter:
    return _ADAPTERS[kind]


__all__ = [
    "LocalOrderBookAdapterResult",
    "LocalRealheadAdapterResult",
    "LocalThemeAdapterResult",
    "SkillAdapter",
    "SkillAdapterResult",
    "WencaiQueryAdapterResult",
    "WencaiSearchAdapterResult",
    "get_skill_adapter",
]
