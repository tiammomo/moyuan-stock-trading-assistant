from __future__ import annotations

import math
import re
from typing import Any, Dict, Iterable, List, Optional

from app.schemas import WatchItemCreate, WatchStockCandidate

from .wencai_client import WencaiClientError, wencai_client


class WatchlistResolveError(RuntimeError):
    pass


def normalize_stock_symbol(value: Optional[str]) -> str:
    text = str(value or "").strip().upper().replace(" ", "")
    if not text:
        return ""
    if re.fullmatch(r"\d{6}\.(SH|SZ|BJ)", text):
        return text
    if not re.fullmatch(r"\d{6}", text):
        return text
    if text.startswith(("60", "68", "90")):
        return f"{text}.SH"
    if text.startswith(("00", "20", "30")):
        return f"{text}.SZ"
    if text.startswith(("43", "83", "87", "88", "92")) or text.startswith("8"):
        return f"{text}.BJ"
    return text


def _find_value(row: Dict[str, Any], exact: Iterable[str], contains: Iterable[str]) -> Any:
    for key in exact:
        if key in row:
            return row.get(key)
        lowered = key.lower()
        for row_key, value in row.items():
            if row_key.lower() == lowered:
                return value
    for key, value in row.items():
        lowered_key = key.lower()
        if any(part in key or part.lower() in lowered_key for part in contains):
            return value
    return None


def _safe_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and math.isfinite(value):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace("%", "").replace(",", ""))
        except ValueError:
            return None
    return None


def _text_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, list):
        parts = [str(item).strip() for item in value if str(item).strip()]
        return "、".join(parts[:4]) if parts else None
    text = str(value).strip()
    return text or None


def _concepts(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()][:6]
    text = str(value).strip()
    if not text:
        return []
    return [part.strip() for part in re.split(r"[、,，/]", text) if part.strip()][:6]


def _row_to_candidate(row: Dict[str, Any], *, source_query: str) -> Optional[WatchStockCandidate]:
    symbol = normalize_stock_symbol(_find_value(row, ("股票代码", "代码"), ("代码",)))
    name = _text_or_none(_find_value(row, ("股票简称", "名称", "股票名称"), ("简称", "名称")))
    if not symbol or not name:
        return None

    return WatchStockCandidate(
        symbol=symbol,
        name=name,
        latest_price=_safe_float(_find_value(row, ("最新价",), ("最新价", "收盘价"))),
        change_pct=_safe_float(_find_value(row, ("最新涨跌幅",), ("涨跌幅",))),
        industry=_text_or_none(_find_value(row, ("所属同花顺行业", "所属行业"), ("所属行业",))),
        concepts=_concepts(_find_value(row, ("所属概念",), ("所属概念", "概念"))),
        source_query=source_query,
    )


def _select_best_row(query: str, rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    normalized_query = normalize_stock_symbol(query)
    query_text = query.strip()
    for row in rows:
        row_symbol = normalize_stock_symbol(_find_value(row, ("股票代码", "代码"), ("代码",)))
        if normalized_query and row_symbol == normalized_query:
            return row
    for row in rows:
        name = _text_or_none(_find_value(row, ("股票简称", "名称", "股票名称"), ("简称", "名称")))
        if name and name == query_text:
            return row
    return rows[0] if rows else None


def resolve_watch_stock(query: str) -> WatchStockCandidate:
    keyword = query.strip()
    if not keyword:
        raise WatchlistResolveError("请输入股票名称或代码")

    source_query = f"{keyword} 最新价 涨跌幅 所属行业 所属概念"
    try:
        result = wencai_client.query2data(source_query, limit=5)
    except WencaiClientError as exc:
        raise WatchlistResolveError(str(exc)) from exc

    rows = result.get("datas") or []
    if not rows:
        raise WatchlistResolveError(f"未识别到股票：{keyword}")

    row = _select_best_row(keyword, rows)
    candidate = _row_to_candidate(row or {}, source_query=source_query)
    if candidate is None:
        raise WatchlistResolveError(f"未能从问财结果中解析股票代码和名称：{keyword}")
    return candidate


def normalize_tags(tags: List[str]) -> List[str]:
    normalized: List[str] = []
    seen: set[str] = set()
    for raw_tag in tags:
        tag = str(raw_tag).strip()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        normalized.append(tag)
    return normalized[:8]


def prepare_watch_item_create(data: WatchItemCreate) -> WatchItemCreate:
    query = (data.query or "").strip()
    symbol = normalize_stock_symbol(data.symbol)
    name = str(data.name or "").strip()

    if not (symbol and name):
        lookup_key = query or symbol or name
        if not lookup_key:
            raise WatchlistResolveError("请输入股票名称或代码")
        candidate = resolve_watch_stock(lookup_key)
        symbol = candidate.symbol
        name = candidate.name

    note = data.note.strip() if isinstance(data.note, str) and data.note.strip() else None
    return WatchItemCreate(
        query=query or None,
        symbol=symbol,
        name=name,
        bucket=data.bucket,
        tags=normalize_tags(data.tags),
        note=note,
        source_session_id=data.source_session_id,
    )
