from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, List, Optional

from app.schemas import (
    CardType,
    ChatMessageRecord,
    ChatMode,
    ResultCard,
    ResultTable,
    SourceRef,
    StructuredResult,
    WatchBucket,
    WatchItemCreate,
)

from .repository import Repository
from .watchlist_resolver import WatchStockCandidate, WatchlistResolveError, resolve_watch_stock


POOL_KEYWORDS = ("候选池", "观察池", "观察列表", "自选")
ADD_KEYWORDS = ("加入", "加到", "添加", "放入", "放进", "收进", "收藏")
MULTI_CONTEXT_KEYWORDS = ("这几只", "这些", "上面这几只", "上面的这些", "都加入")
SINGLE_CONTEXT_KEYWORDS = ("这只", "它", "这个", "上面这只", "上一只")


@dataclass
class WatchlistAddIntent:
    bucket: WatchBucket
    subject: Optional[str]
    use_context_single: bool = False
    use_context_multi: bool = False


def detect_watchlist_add_intent(
    message: str,
    *,
    mode_hint: Optional[ChatMode] = None,
    session_mode: Optional[ChatMode] = None,
) -> Optional[WatchlistAddIntent]:
    if not any(keyword in message for keyword in POOL_KEYWORDS):
        return None
    if not any(keyword in message for keyword in ADD_KEYWORDS):
        return None

    bucket = _infer_bucket(message, mode_hint=mode_hint, session_mode=session_mode)
    if any(keyword in message for keyword in MULTI_CONTEXT_KEYWORDS):
        return WatchlistAddIntent(bucket=bucket, subject=None, use_context_multi=True)
    if any(keyword in message for keyword in SINGLE_CONTEXT_KEYWORDS):
        return WatchlistAddIntent(bucket=bucket, subject=None, use_context_single=True)

    subject = _extract_subject(message)
    return WatchlistAddIntent(bucket=bucket, subject=subject, use_context_single=subject is None)


def execute_watchlist_add_intent(
    *,
    repository: Repository,
    intent: WatchlistAddIntent,
    session_id: str,
    message: str,
    latest_assistant: Optional[ChatMessageRecord],
) -> StructuredResult:
    sources: List[SourceRef] = []
    added: List[WatchStockCandidate] = []
    existing: List[WatchStockCandidate] = []
    unresolved_error: Optional[str] = None

    if intent.use_context_single or intent.use_context_multi:
        context_candidates = _context_candidates(latest_assistant, multi=intent.use_context_multi)
        if not context_candidates:
            unresolved_error = "当前上下文里没有可加入候选池的股票，请直接说股票名称或代码。"
        else:
            sources.extend(_context_sources(latest_assistant))
            for candidate in context_candidates:
                if _maybe_add_candidate(
                    repository=repository,
                    candidate=candidate,
                    bucket=intent.bucket,
                    session_id=session_id,
                ):
                    added.append(candidate)
                else:
                    existing.append(candidate)
    else:
        try:
            candidate = resolve_watch_stock(intent.subject or message)
            sources.append(SourceRef(skill="候选池解析", query=candidate.source_query))
            if _maybe_add_candidate(
                repository=repository,
                candidate=candidate,
                bucket=intent.bucket,
                session_id=session_id,
            ):
                added.append(candidate)
            else:
                existing.append(candidate)
        except WatchlistResolveError as exc:
            unresolved_error = str(exc)

    cards: List[ResultCard] = []
    facts: List[str] = []
    judgements: List[str] = []
    follow_ups: List[str] = []

    if unresolved_error:
        summary = unresolved_error
        cards.append(
            ResultCard(
                type=CardType.CUSTOM,
                title="候选池操作失败",
                content=unresolved_error,
            )
        )
        follow_ups = ["把股票名称说完整一点", "直接用 6 位代码再试", "先分析一只股票再决定是否入池"]
        return StructuredResult(
            summary=summary,
            table=None,
            cards=cards,
            facts=facts,
            judgements=judgements,
            follow_ups=follow_ups,
            sources=sources,
        )

    card_lines: List[str] = []
    if added:
        added_lines = [f"- 已加入：{candidate.name}（{candidate.symbol}）" for candidate in added]
        card_lines.extend(added_lines)
        facts.extend(
            [
                f"{candidate.name}（{candidate.symbol}）已加入候选池，分类 { _bucket_label(intent.bucket) }。"
                for candidate in added
            ]
        )
    if existing:
        existing_lines = [f"- 已存在：{candidate.name}（{candidate.symbol}）" for candidate in existing]
        card_lines.extend(existing_lines)
        judgements.append("重复股票不会再次写入候选池，候选池按标准化代码去重。")

    title = "候选池更新"
    cards.append(
        ResultCard(
            type=CardType.CANDIDATE_SUMMARY,
            title=title,
            content="\n".join(card_lines) if card_lines else "没有新增股票。",
            metadata={
                "bucket": intent.bucket.value,
                "added_count": len(added),
                "existing_count": len(existing),
            },
        )
    )

    if added and not existing:
        if len(added) == 1:
            summary = f"已把 {added[0].name}（{added[0].symbol}）加入候选池，分类为{_bucket_label(intent.bucket)}。"
        else:
            summary = f"已把 {len(added)} 只股票加入候选池，分类为{_bucket_label(intent.bucket)}。"
    elif added and existing:
        summary = f"已新增 {len(added)} 只股票到候选池，另有 {len(existing)} 只原本已在池中。"
    elif existing:
        if len(existing) == 1:
            summary = f"{existing[0].name}（{existing[0].symbol}）已经在候选池中。"
        else:
            summary = f"这批股票已经在候选池中，没有重复写入。"
    else:
        summary = "没有识别到可加入候选池的股票。"

    if added:
        preview_rows = [
            {
                "代码": candidate.symbol,
                "名称": candidate.name,
                "最新价": candidate.latest_price if candidate.latest_price is not None else "-",
                "涨跌幅": f"{candidate.change_pct:.2f}%" if candidate.change_pct is not None else "-",
                "分类": _bucket_label(intent.bucket),
            }
            for candidate in added[:10]
        ]
        table = ResultTable(columns=["代码", "名称", "最新价", "涨跌幅", "分类"], rows=preview_rows)
    else:
        table = None

    if added:
        focus_name = added[0].name
        follow_ups = [
            f"分析{focus_name}今天能不能买",
            "把候选池里的股票按短线优先级排一下",
            f"把{focus_name}改到短线或波段桶里",
        ]
    else:
        follow_ups = [
            "查看候选池当前有哪些股票",
            "把候选池里的股票按模式分桶",
            "分析候选池里最值得先看的股票",
        ]

    return StructuredResult(
        summary=summary,
        table=table,
        cards=cards,
        facts=facts,
        judgements=judgements,
        follow_ups=follow_ups,
        sources=sources,
    )


def _infer_bucket(
    message: str,
    *,
    mode_hint: Optional[ChatMode],
    session_mode: Optional[ChatMode],
) -> WatchBucket:
    if "短线" in message:
        return WatchBucket.SHORT_TERM
    if "波段" in message:
        return WatchBucket.SWING
    if "中线" in message or "价值" in message:
        return WatchBucket.MID_TERM_VALUE
    if "丢弃" in message:
        return WatchBucket.DISCARD
    if "观察" in message:
        return WatchBucket.OBSERVE
    if mode_hint == ChatMode.SHORT_TERM or session_mode == ChatMode.SHORT_TERM:
        return WatchBucket.SHORT_TERM
    if mode_hint == ChatMode.SWING or session_mode == ChatMode.SWING:
        return WatchBucket.SWING
    if mode_hint == ChatMode.MID_TERM_VALUE or session_mode == ChatMode.MID_TERM_VALUE:
        return WatchBucket.MID_TERM_VALUE
    return WatchBucket.OBSERVE


def _extract_subject(message: str) -> Optional[str]:
    patterns = (
        r"(?:把|将|请把|帮我把)?(?P<subject>[A-Za-z0-9\u4e00-\u9fff\.]{2,20}?)(?:加入|加到|添加到|放入|放进|收进|收藏到)(?:我的)?(?:短线|波段|中线|价值|观察)?(?:候选池|观察池|观察列表|自选)",
        r"(?:加入|加到|添加|放入|放进|收进|收藏)(?:我的)?(?:短线|波段|中线|价值|观察)?(?:候选池|观察池|观察列表|自选)(?P<subject>[A-Za-z0-9\u4e00-\u9fff\.]{2,20})",
    )
    for pattern in patterns:
        matched = re.search(pattern, message)
        if not matched:
            continue
        subject = matched.group("subject").strip(" ，。！？?？:")
        subject = re.sub(r"^(股票|个股)", "", subject)
        subject = re.sub(r"(股票|个股)$", "", subject)
        subject = subject.strip()
        if subject:
            return subject
    return None


def _context_candidates(
    latest_assistant: Optional[ChatMessageRecord],
    *,
    multi: bool,
) -> List[WatchStockCandidate]:
    snapshot = latest_assistant.result_snapshot if latest_assistant else None
    if snapshot is None:
        return []

    candidates: List[WatchStockCandidate] = []
    if snapshot.table and snapshot.table.rows:
        rows = snapshot.table.rows if multi else snapshot.table.rows[:1]
        for row in rows:
            symbol = str(row.get("代码") or "").strip()
            name = str(row.get("名称") or "").strip()
            if not symbol or not name or symbol == "-" or name == "-":
                continue
            change_raw = str(row.get("涨跌幅") or "").replace("%", "").strip()
            latest_raw = row.get("最新价")
            latest_price = float(latest_raw) if isinstance(latest_raw, (int, float)) else None
            try:
                change_pct = float(change_raw) if change_raw else None
            except ValueError:
                change_pct = None
            candidates.append(
                WatchStockCandidate(
                    symbol=symbol,
                    name=name,
                    latest_price=latest_price,
                    change_pct=change_pct,
                    industry=None,
                    concepts=[],
                    source_query=name,
                )
            )
        if candidates:
            return candidates

    for card in snapshot.cards:
        subject = card.metadata.get("subject") if isinstance(card.metadata, dict) else None
        if not subject:
            continue
        text = str(subject).strip()
        if not text:
            continue
        try:
            candidate = resolve_watch_stock(text)
        except WatchlistResolveError:
            continue
        return [candidate]

    return []


def _maybe_add_candidate(
    *,
    repository: Repository,
    candidate: WatchStockCandidate,
    bucket: WatchBucket,
    session_id: str,
) -> bool:
    if repository.find_watch_item_by_symbol(candidate.symbol):
        return False
    repository.create_watch_item(
        WatchItemCreate(
            symbol=candidate.symbol,
            name=candidate.name,
            bucket=bucket,
            tags=[],
            note=None,
            source_session_id=session_id,
        )
    )
    return True


def _context_sources(latest_assistant: Optional[ChatMessageRecord]) -> List[SourceRef]:
    snapshot = latest_assistant.result_snapshot if latest_assistant else None
    if snapshot is None:
        return []
    return snapshot.sources[:4]


def _bucket_label(bucket: WatchBucket) -> str:
    mapping = {
        WatchBucket.SHORT_TERM: "短线",
        WatchBucket.SWING: "波段",
        WatchBucket.MID_TERM_VALUE: "中线价值",
        WatchBucket.OBSERVE: "观察",
        WatchBucket.DISCARD: "丢弃",
    }
    return mapping.get(bucket, bucket.value)
