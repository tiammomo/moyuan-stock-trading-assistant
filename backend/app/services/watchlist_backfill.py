from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

from app.schemas import (
    ChatMessageRecord,
    ChatMode,
    WatchBucket,
    WatchItemUpdate,
    WatchlistBackfillItemResult,
    WatchlistBackfillResponse,
)

from .repository import Repository
from .watchlist_resolver import (
    WatchlistResolveError,
    normalize_stock_symbol,
    normalize_tags,
    resolve_watch_stock,
)


MODE_LABELS = {
    ChatMode.SHORT_TERM: "短线",
    ChatMode.SWING: "波段",
    ChatMode.MID_TERM_VALUE: "中线价值",
    ChatMode.GENERIC_DATA_QUERY: "通用",
}

BUCKET_LABELS = {
    WatchBucket.SHORT_TERM: "短线",
    WatchBucket.SWING: "波段",
    WatchBucket.MID_TERM_VALUE: "中线价值",
    WatchBucket.OBSERVE: "观察",
    WatchBucket.DISCARD: "丢弃",
}


def _split_tag_parts(value: Optional[str], limit: int) -> List[str]:
    text = str(value or "").strip()
    if not text:
        return []
    return [part.strip() for part in re.split(r"[、,，/]", text) if part.strip()][:limit]


def _dedupe_tags(tags: Iterable[Optional[str]]) -> List[str]:
    return normalize_tags([str(tag or "").strip() for tag in tags if str(tag or "").strip()])


def _row_value(row: Optional[Dict[str, Any]], exact: Iterable[str], contains: Iterable[str]) -> Optional[str]:
    if not row:
        return None

    for key in exact:
        if key in row and str(row.get(key) or "").strip():
            return str(row.get(key)).strip()

    lowered_contains = [part.lower() for part in contains]
    for raw_key, value in row.items():
        lowered_key = raw_key.lower()
        if any(part in lowered_key for part in lowered_contains):
            text = str(value or "").strip()
            if text:
                return text
    return None


def _extract_first_sentence(value: Optional[str]) -> Optional[str]:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return None
    sentence = re.split(r"[。！？；;\n]", text, maxsplit=1)[0].strip() or text
    if len(sentence) <= 88:
        return sentence
    return sentence[:88].rstrip() + "..."


def _matching_row(message: Optional[ChatMessageRecord], symbol: str, name: str) -> Optional[Dict[str, Any]]:
    snapshot = message.result_snapshot if message else None
    table = snapshot.table if snapshot else None
    if table is None:
        return None

    normalized_symbol = normalize_stock_symbol(symbol)
    for row in table.rows:
        row_symbol = normalize_stock_symbol(str(row.get("代码") or ""))
        row_name = str(row.get("名称") or "").strip()
        if normalized_symbol and row_symbol == normalized_symbol:
            return row
        if name and row_name == name:
            return row
    return None


def _resolve_mode_tag(
    *,
    bucket: WatchBucket,
    latest_assistant: Optional[ChatMessageRecord],
    session_mode: Optional[ChatMode],
) -> str:
    mode = latest_assistant.mode if latest_assistant and latest_assistant.mode else session_mode
    if mode in MODE_LABELS:
        return MODE_LABELS[mode]
    return BUCKET_LABELS[bucket]


def _build_auto_tags(
    *,
    symbol: str,
    name: str,
    bucket: WatchBucket,
    latest_assistant: Optional[ChatMessageRecord],
    session_mode: Optional[ChatMode],
) -> tuple[List[str], Optional[str]]:
    try:
        candidate = resolve_watch_stock(symbol or name)
    except WatchlistResolveError as exc:
        return [_resolve_mode_tag(bucket=bucket, latest_assistant=latest_assistant, session_mode=session_mode)], str(exc)

    industry_tags = _split_tag_parts(candidate.industry, 2)
    concept_tags = list(candidate.concepts[:3])
    mode_tag = _resolve_mode_tag(bucket=bucket, latest_assistant=latest_assistant, session_mode=session_mode)
    return _dedupe_tags([*industry_tags, *concept_tags, mode_tag]), None


def _build_auto_note(
    *,
    symbol: str,
    name: str,
    latest_assistant: Optional[ChatMessageRecord],
) -> Optional[str]:
    row = _matching_row(latest_assistant, symbol=symbol, name=name)
    row_note = _extract_first_sentence(
        _row_value(row, ("核心逻辑", "基本面", "风险点"), ("核心逻辑", "基本面", "风险点"))
    )
    if row_note:
        return row_note

    snapshot = latest_assistant.result_snapshot if latest_assistant else None
    first_judgement = snapshot.judgements[0] if snapshot and snapshot.judgements else None
    judgement_note = _extract_first_sentence(first_judgement)
    if judgement_note:
        return judgement_note if name in judgement_note else f"{name}：{judgement_note}"

    summary_note = _extract_first_sentence(
        snapshot.summary if snapshot and snapshot.summary else latest_assistant.content if latest_assistant else None
    )
    if summary_note:
        return summary_note if name in summary_note else f"{name}：{summary_note}"

    return None


def backfill_watchlist(repository: Repository) -> WatchlistBackfillResponse:
    items = repository.list_watchlist()
    results: List[WatchlistBackfillItemResult] = []
    updated_count = 0

    for item in items:
        session_summary = (
            repository.get_session_summary(item.source_session_id)
            if item.source_session_id
            else None
        )
        latest_assistant = (
            repository.latest_assistant_message(item.source_session_id)
            if item.source_session_id
            else None
        )
        session_mode = session_summary.mode if session_summary else None

        auto_tags, tag_warning = _build_auto_tags(
            symbol=item.symbol,
            name=item.name,
            bucket=item.bucket,
            latest_assistant=latest_assistant,
            session_mode=session_mode,
        )
        merged_tags = _dedupe_tags([*item.tags, *auto_tags])
        existing_tag_set = set(item.tags)
        tags_added = [tag for tag in merged_tags if tag not in existing_tag_set]

        note_added = None
        if not item.note:
            note_added = _build_auto_note(
                symbol=item.symbol,
                name=item.name,
                latest_assistant=latest_assistant,
            )

        patch_data: Dict[str, Any] = {}
        if tags_added:
            patch_data["tags"] = merged_tags
        if note_added:
            patch_data["note"] = note_added

        updated = False
        final_tags = item.tags
        final_note = item.note
        if patch_data:
            updated_record = repository.update_watch_item(item.id, WatchItemUpdate(**patch_data))
            if updated_record is not None:
                updated = True
                updated_count += 1
                final_tags = updated_record.tags
                final_note = updated_record.note

        skipped_reason = None
        if not updated:
            if item.tags and item.note:
                skipped_reason = "已有标签和备注，无需回填"
            elif tag_warning and not note_added:
                skipped_reason = tag_warning
            else:
                skipped_reason = "没有可新增的标签或备注"

        results.append(
            WatchlistBackfillItemResult(
                item_id=item.id,
                symbol=item.symbol,
                name=item.name,
                updated=updated,
                tags_added=tags_added,
                note_added=note_added,
                tags=final_tags,
                note=final_note,
                skipped_reason=skipped_reason,
            )
        )

    return WatchlistBackfillResponse(
        scanned_count=len(items),
        updated_count=updated_count,
        unchanged_count=len(items) - updated_count,
        items=results,
    )
