from __future__ import annotations

import asyncio
import logging
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, time
from typing import Dict, List, Optional
from uuid import uuid4

from app.schemas import (
    ScheduledReportJobRecord,
    ScheduledReportRunRecord,
    ScheduledReportType,
)
from app.schemas.portfolio import PortfolioPositionView, PortfolioSummary

from .llm_manager import LLMProviderError
from .local_market_skill_client import local_market_skill_client
from .monitor_notifier import monitor_notifier
from .portfolio_store import portfolio_store
from .repository import repository
from .scheduled_report_llm import scheduled_report_llm_enhancer
from .scheduled_report_store import ScheduledReportStoreError, scheduled_report_store
from .skill_adapters import WencaiSearchAdapterResult, get_skill_adapter
from .skill_registry import SKILL_SEARCH_NEWS, skill_registry
from .trading_calendar import CN_TZ, trading_calendar
from .watch_monitor import watch_monitor_service
from .watch_rule_store import watch_rule_store
from .wencai_client import wencai_client


logger = logging.getLogger(__name__)

REPORT_LABELS: Dict[ScheduledReportType, str] = {
    "pre_market_watchlist": "盘前观察清单",
    "post_market_review": "盘后复盘",
    "portfolio_daily": "持仓日报",
    "news_digest": "新闻摘要",
}

BUCKET_LABELS = {
    "short_term": "短线",
    "swing": "波段",
    "mid_term_value": "中线价值",
    "observe": "观察",
    "discard": "丢弃",
}
BUCKET_PRIORITY = {
    "short_term": 0,
    "swing": 1,
    "mid_term_value": 2,
    "observe": 3,
    "discard": 4,
}


@dataclass(frozen=True)
class GeneratedReport:
    title: str
    summary: str
    body: str
    trading_date: Optional[str]
    payload: Dict[str, object]


def _now_cn() -> datetime:
    return datetime.now(CN_TZ)


def _parse_clock(value: str) -> time:
    hour_text, minute_text = value.split(":", 1)
    return time(hour=int(hour_text), minute=int(minute_text))


def _quote_code(symbol: str) -> str:
    return str(symbol or "").split(".", 1)[0]


def _signed_pct(value: Optional[float]) -> str:
    if value is None:
        return "--"
    prefix = "+" if value >= 0 else ""
    return f"{prefix}{value:.2f}%"


def _signed_money(value: Optional[float]) -> str:
    if value is None:
        return "--"
    prefix = "+" if value >= 0 else ""
    return f"{prefix}{value:.2f}"


def _clean_sentence(value: str) -> str:
    return " ".join(str(value or "").split()).strip().rstrip("。；")


def _compose_section(title: str, parts: List[str], *, fallback: str) -> str:
    cleaned = [_clean_sentence(part) for part in parts if _clean_sentence(part)]
    sentence = "；".join(cleaned) if cleaned else _clean_sentence(fallback)
    return f"{title}：{sentence}。"


def _unique_keep_order(items: List[str]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for item in items:
        text = _clean_sentence(item)
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


class ScheduledReportService:
    def __init__(self) -> None:
        self._task: Optional[asyncio.Task[None]] = None
        self._stop_event = asyncio.Event()
        self._run_lock = asyncio.Lock()

    def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run_loop(), name="scheduled-report-service")

    async def shutdown(self) -> None:
        self._stop_event.set()
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    def list_jobs(self) -> List[ScheduledReportJobRecord]:
        return scheduled_report_store.list_jobs()

    def list_runs(self, limit: int = 20) -> List[ScheduledReportRunRecord]:
        return scheduled_report_store.list_runs(limit=limit)

    def update_job(
        self,
        report_type: ScheduledReportType,
        enabled: Optional[bool] = None,
        schedule_time: Optional[str] = None,
        channel_ids: Optional[List[str]] = None,
    ) -> Optional[ScheduledReportJobRecord]:
        from app.schemas import ScheduledReportJobUpdate

        return scheduled_report_store.update_job(
            report_type,
            ScheduledReportJobUpdate(
                enabled=enabled,
                schedule_time=schedule_time,
                channel_ids=channel_ids,
            ),
        )

    async def trigger(self, report_type: ScheduledReportType, *, trigger: str = "manual") -> ScheduledReportRunRecord:
        async with self._run_lock:
            job = scheduled_report_store.get_job(report_type)
            if job is None:
                raise ScheduledReportStoreError("日报任务不存在")
            return self._run_job(job, trigger=trigger)

    async def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self._run_due_jobs()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Scheduled report loop failed")
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=30.0)
            except asyncio.TimeoutError:
                continue

    async def _run_due_jobs(self) -> None:
        now = _now_cn()
        if not trading_calendar.is_trading_day(now):
            return
        async with self._run_lock:
            trading_date = now.date().isoformat()
            for job in scheduled_report_store.list_jobs():
                if not job.enabled:
                    continue
                if scheduled_report_store.was_scheduled_for_date(job.report_type, trading_date):
                    continue
                if now.time() < _parse_clock(job.schedule_time):
                    continue
                record = self._run_job(job, trigger="scheduled")
                scheduled_report_store.mark_scheduled_for_date(
                    job.report_type,
                    trading_date,
                    run_id=record.id,
                )

    def _run_job(
        self,
        job: ScheduledReportJobRecord,
        *,
        trigger: str,
    ) -> ScheduledReportRunRecord:
        now = _now_cn()
        channel_ids = list(job.channel_ids)
        try:
            generated = self._generate_report(job.report_type, now=now)
            ai_enhanced = False
            ai_provider: Optional[str] = None
            enhancement = None
            try:
                enhancement = scheduled_report_llm_enhancer.enhance_report(
                    report_type=job.report_type,
                    title=generated.title,
                    summary=generated.summary,
                    body=generated.body,
                    payload=generated.payload,
                )
            except (LLMProviderError, ValueError) as exc:
                logger.warning("Scheduled report AI enhancement skipped: type=%s error=%s", job.report_type, exc)
            if enhancement is not None:
                generated = GeneratedReport(
                    title=enhancement.title,
                    summary=enhancement.summary,
                    body=enhancement.body,
                    trading_date=generated.trading_date,
                    payload={
                        **generated.payload,
                        "ai_enhanced": True,
                        "ai_provider": enhancement.provider,
                    },
                )
                ai_enhanced = True
                ai_provider = enhancement.provider
            fingerprint = (
                f"scheduled_report|{job.report_type}|{generated.trading_date}"
                if trigger == "scheduled"
                else f"scheduled_report|{job.report_type}|manual|{uuid4().hex[:8]}"
            )
            deliveries = monitor_notifier.dispatch_message(
                channel_ids=channel_ids,
                fingerprint=fingerprint,
                title=generated.title,
                body=generated.body,
                payload={
                    "source": "scheduled_report",
                    "report_type": job.report_type,
                    "title": generated.title,
                    "summary": generated.summary,
                    "body": generated.body,
                    "trading_date": generated.trading_date,
                    **generated.payload,
                },
                created_at=now,
            )
            delivered_count = sum(1 for item in deliveries if item.status == "success")
            if channel_ids or deliveries:
                if delivered_count > 0:
                    status = "success"
                    reason = None
                elif deliveries and all(item.status == "skipped" for item in deliveries):
                    status = "skipped"
                    reason = deliveries[0].reason
                elif deliveries and all(item.status == "failed" for item in deliveries):
                    status = "failed"
                    reason = deliveries[0].reason
                else:
                    status = "skipped"
                    reason = "通知未发送"
            else:
                status = "skipped"
                reason = "未配置日报通知渠道，将沿用盯盘默认渠道；若默认渠道为空则不会推送"
            record = ScheduledReportRunRecord(
                id=f"sr_{uuid4().hex[:12]}",
                report_type=job.report_type,
                title=generated.title,
                summary=generated.summary,
                body=generated.body,
                status=status,
                trigger=trigger,
                channel_ids=channel_ids,
                delivered_count=delivered_count,
                ai_enhanced=ai_enhanced,
                ai_provider=ai_provider,
                reason=reason,
                trading_date=generated.trading_date,
                created_at=now,
            )
        except Exception as exc:
            record = ScheduledReportRunRecord(
                id=f"sr_{uuid4().hex[:12]}",
                report_type=job.report_type,
                title=REPORT_LABELS[job.report_type],
                summary="日报生成失败",
                body="",
                status="failed",
                trigger=trigger,
                channel_ids=channel_ids,
                delivered_count=0,
                ai_enhanced=False,
                ai_provider=None,
                reason=str(exc),
                trading_date=now.date().isoformat() if trading_calendar.is_trading_day(now) else None,
                created_at=now,
            )
            logger.exception("Scheduled report generation failed: type=%s", job.report_type)
        scheduled_report_store.append_run(record)
        return record

    def _generate_report(self, report_type: ScheduledReportType, *, now: datetime) -> GeneratedReport:
        if report_type == "pre_market_watchlist":
            return self._generate_pre_market_watchlist(now=now)
        if report_type == "post_market_review":
            return self._generate_post_market_review(now=now)
        if report_type == "portfolio_daily":
            return self._generate_portfolio_daily(now=now)
        if report_type == "news_digest":
            return self._generate_news_digest(now=now)
        raise ScheduledReportStoreError("未知日报类型")

    def _generate_pre_market_watchlist(self, *, now: datetime) -> GeneratedReport:
        items = [
            item for item in repository.list_watchlist()
            if item.bucket.value != "discard"
        ]
        if not items:
            return GeneratedReport(
                title="盘前观察清单",
                summary="候选池为空，今天没有可发送的盘前观察清单。",
                body="\n\n".join(
                    [
                        _compose_section("今天怎么看", [], fallback="候选池为空，今天没有可执行的盘前观察清单"),
                        _compose_section("先盯谁", [], fallback="暂无优先观察标的"),
                        _compose_section("哪些风险", [], fallback="没有候选池意味着开盘前缺少准备，容易临盘追单"),
                        _compose_section("开盘怎么做", [], fallback="先补观察池，再决定是否启用盘前简报"),
                    ]
                ),
                trading_date=now.date().isoformat() if trading_calendar.is_trading_day(now) else None,
                payload={"source_items": 0},
            )

        items.sort(key=lambda item: (BUCKET_PRIORITY.get(item.bucket.value, 99), item.name))
        rules = watch_rule_store.list_rules()
        rules_by_item = Counter(rule.item_id for rule in rules if rule.enabled)
        bucket_counts = Counter(item.bucket.value for item in items)
        focus_lines: List[str] = []
        short_term_focus: List[str] = []
        swing_focus: List[str] = []
        quote_success = 0
        for item in items[:6]:
            latest_price = None
            change_pct = None
            try:
                snapshot = local_market_skill_client.fetch_realhead(_quote_code(item.symbol))
                latest_price = snapshot.latest_price
                change_pct = snapshot.change_pct
                quote_success += 1
            except Exception:
                pass
            segments = [
                f"{item.name} {item.symbol}",
                BUCKET_LABELS.get(item.bucket.value, item.bucket.value),
                f"规则 {rules_by_item.get(item.id, 0)} 条",
            ]
            if latest_price is not None:
                segments.append(f"现价 {latest_price:.2f}")
            if change_pct is not None:
                segments.append(f"涨跌 {_signed_pct(change_pct)}")
            line = "｜".join(segments)
            focus_lines.append(line)
            if item.bucket.value == "short_term":
                short_term_focus.append(line)
            if item.bucket.value == "swing":
                swing_focus.append(line)

        summary = (
            f"候选池共 {len(items)} 只，短线 {bucket_counts.get('short_term', 0)} / "
            f"波段 {bucket_counts.get('swing', 0)} / 中线价值 {bucket_counts.get('mid_term_value', 0)}。"
        )
        missing_quotes = max(0, min(len(items), 6) - quote_success)
        no_rule_count = sum(1 for item in items[:6] if rules_by_item.get(item.id, 0) == 0)
        today_view = _compose_section(
            "今天怎么看",
            [
                summary,
                f"今晨已补到 {quote_success} 只行情快照",
                (
                    "短线桶是今天的开盘观察主轴"
                    if bucket_counts.get("short_term", 0) > 0
                    else "短线桶为空，今天更适合先看波段延续而不是盲目追强"
                ),
            ],
            fallback=summary,
        )
        watch_targets = _compose_section(
            "先盯谁",
            short_term_focus[:3] or swing_focus[:3] or focus_lines[:3],
            fallback="当前没有明确的优先观察标的",
        )
        risk_parts: List[str] = []
        if missing_quotes > 0:
            risk_parts.append(f"有 {missing_quotes} 只优先标的今晨还没补到行情，开盘前要先核价格和涨跌幅")
        if no_rule_count > 0:
            risk_parts.append(f"有 {no_rule_count} 只优先标的还没有启用规则覆盖，盘中异动提醒会偏弱")
        if bucket_counts.get("observe", 0) >= max(2, bucket_counts.get("short_term", 0) + bucket_counts.get("swing", 0)):
            risk_parts.append("观察桶数量偏多，说明当前高确定性机会不多，别把所有观察票都当成开盘动作")
        if len(items) >= 6:
            risk_parts.append("候选池数量偏多，开盘先做排序，不要同时分散处理所有标的")
        risks = _compose_section(
            "哪些风险",
            risk_parts,
            fallback="当前没有额外的结构性风险提示，但开盘前仍要先核行情和规则覆盖",
        )
        opening_action_parts: List[str] = []
        if short_term_focus:
            opening_action_parts.append("9:30 后先看短线桶前两只的量价承接，再决定是否进入交易观察")
        elif swing_focus:
            opening_action_parts.append("开盘先看波段桶的趋势延续和回踩承接，不急着做追强动作")
        else:
            opening_action_parts.append("开盘先核候选池里现价和涨跌幅，再决定是否有继续观察价值")
        if missing_quotes > 0:
            opening_action_parts.append("未补到行情的标的先不动作，等快照补齐后再判断")
        if no_rule_count > 0:
            opening_action_parts.append("优先把有规则覆盖的标的放到前排，没有规则的先手动盯一下")
        opening_actions = _compose_section(
            "开盘怎么做",
            opening_action_parts,
            fallback="开盘先核行情，再只处理最靠前的 1 到 2 只标的",
        )
        return GeneratedReport(
            title="盘前观察清单",
            summary=summary,
            body="\n\n".join([today_view, watch_targets, risks, opening_actions]),
            trading_date=now.date().isoformat() if trading_calendar.is_trading_day(now) else None,
            payload={
                "source_items": len(items),
                "bucket_counts": dict(bucket_counts),
            },
        )

    def _generate_post_market_review(self, *, now: datetime) -> GeneratedReport:
        trading_date = now.date().isoformat() if trading_calendar.is_trading_day(now) else None
        events = [
            event
            for event in watch_monitor_service.list_events(limit=100)
            if event.created_at.astimezone(CN_TZ).date().isoformat() == trading_date
        ] if trading_date else []
        event_types = Counter(event.event_type for event in events)
        warning_count = sum(1 for event in events if event.severity == "warning")
        focus_events = events[:5]
        watch_items = [
            item for item in repository.list_watchlist()
            if item.bucket.value != "discard"
        ]
        snapshots: List[tuple[str, str, Optional[float]]] = []
        for item in watch_items[:8]:
            try:
                snapshot = local_market_skill_client.fetch_realhead(_quote_code(item.symbol))
                snapshots.append((item.name, item.symbol, snapshot.change_pct))
            except Exception:
                continue
        snapshots.sort(key=lambda item: abs(item[2] or 0), reverse=True)
        performance_lines = [
            f"{name} {symbol}｜涨跌 {_signed_pct(change_pct)}"
            for name, symbol, change_pct in snapshots[:5]
        ]
        negative_lines = [
            f"{name} {symbol}｜涨跌 {_signed_pct(change_pct)}"
            for name, symbol, change_pct in sorted(
                [item for item in snapshots if (item[2] or 0) < 0],
                key=lambda item: item[2] or 0,
            )[:3]
        ]
        summary = (
            f"今日监控事件 {len(events)} 条，warning {warning_count} 条，"
            f"主要集中在 {', '.join(f'{k}:{v}' for k, v in event_types.most_common(3)) or '无明显异动'}。"
        )
        happened = _compose_section(
            "今天发生了什么",
            [
                summary,
                f"候选池收盘后还能回溯到 {len(snapshots)} 只行情快照",
            ],
            fallback=summary,
        )
        key_points = _compose_section(
            "哪些最关键",
            [f"{event.name} {event.symbol}｜{event.summary}" for event in focus_events[:3]] or performance_lines[:3],
            fallback="今天没有新的关键异动可复盘",
        )
        tomorrow_watch_candidates = _unique_keep_order(
            [f"{event.name} {event.symbol}" for event in focus_events[:3]]
            + [f"{name} {symbol}" for name, symbol, _ in snapshots[:3]]
        )
        tomorrow_watch = _compose_section(
            "明天看什么",
            tomorrow_watch_candidates[:4],
            fallback="明天先从候选池里重新筛一遍最强方向，再决定继续跟踪谁",
        )
        avoid_parts = []
        if negative_lines:
            avoid_parts.extend(negative_lines)
        if warning_count > 0 and focus_events:
            avoid_parts.append("warning 事件较多的标的明天不要在没有修复信号前抢反弹")
        avoid = _compose_section(
            "哪些先回避",
            avoid_parts[:4],
            fallback="今天没有形成新的明确回避名单，但弱势且无承接的标的先别急着抄底",
        )
        return GeneratedReport(
            title="盘后复盘",
            summary=summary,
            body="\n\n".join([happened, key_points, tomorrow_watch, avoid]),
            trading_date=trading_date,
            payload={
                "event_count": len(events),
                "warning_count": warning_count,
                "event_types": dict(event_types),
            },
        )

    def _generate_portfolio_daily(self, *, now: datetime) -> GeneratedReport:
        summary_data = portfolio_store.summary()
        trading_date = now.date().isoformat() if trading_calendar.is_trading_day(now) else None
        positions = self._flatten_positions(summary_data)
        top_daily = sorted(
            [position for position in positions if position.daily_pnl is not None],
            key=lambda item: abs(item.daily_pnl or 0),
            reverse=True,
        )[:5]
        top_total = sorted(
            [position for position in positions if position.pnl is not None],
            key=lambda item: abs(item.pnl or 0),
            reverse=True,
        )[:5]
        summary = (
            f"总成本 {summary_data.total_cost:.2f}，总市值 {summary_data.total_market_value:.2f}，"
            f"累计盈亏 {_signed_money(summary_data.total_pnl)}，日内 {_signed_money(summary_data.total_daily_pnl)}。"
        )
        body_lines = [
            f"交易日：{trading_date or now.date().isoformat()}",
            summary,
            f"账户数 {len(summary_data.accounts)}，持仓数 {len(positions)}，报价异常 {summary_data.quote_error_count} 条。",
            "日内波动最大的持仓：",
        ]
        if top_daily:
            body_lines.extend(
                [
                    f"{index + 1}. {position.name} {position.symbol}｜日内 {_signed_money(position.daily_pnl)}｜"
                    f"涨跌 {_signed_pct(position.change_pct)}｜账户 {position.account_name}"
                    for index, position in enumerate(top_daily)
                ]
            )
        else:
            body_lines.append("1. 当前没有可计算日内盈亏的持仓。")
        body_lines.append("累计盈亏关注：")
        if top_total:
            body_lines.extend(
                [
                    f"{index + 1}. {position.name} {position.symbol}｜累计 {_signed_money(position.pnl)}｜"
                    f"收益 {_signed_pct(position.pnl_pct)}｜账户 {position.account_name}"
                    for index, position in enumerate(top_total)
                ]
            )
        else:
            body_lines.append("1. 当前没有可计算累计盈亏的持仓。")
        return GeneratedReport(
            title="持仓日报",
            summary=summary,
            body="\n".join(body_lines),
            trading_date=trading_date,
            payload={
                "account_count": len(summary_data.accounts),
                "position_count": len(positions),
                "total_pnl": summary_data.total_pnl,
                "total_daily_pnl": summary_data.total_daily_pnl,
            },
        )

    def _generate_news_digest(self, *, now: datetime) -> GeneratedReport:
        subjects = self._news_subjects()
        if not subjects:
            return GeneratedReport(
                title="新闻摘要",
                summary="候选池和持仓都为空，暂时没有可汇总的新闻主题。",
                body="候选池和持仓均为空。\n建议先维护观察池或持仓账户，再启用新闻摘要。",
                trading_date=now.date().isoformat() if trading_calendar.is_trading_day(now) else None,
                payload={"subject_count": 0},
            )
        if not wencai_client.has_api_key:
            return GeneratedReport(
                title="新闻摘要",
                summary="未配置 IWENCAI_API_KEY，新闻摘要暂时无法调用问财搜索。",
                body=(
                    "新闻摘要未执行。\n"
                    "原因：当前环境未配置 IWENCAI_API_KEY，无法调用问财综合搜索接口。"
                ),
                trading_date=now.date().isoformat() if trading_calendar.is_trading_day(now) else None,
                payload={"subject_count": min(len(subjects), 5), "title_count": 0, "error_count": 1},
            )
        spec = skill_registry.require(SKILL_SEARCH_NEWS)
        adapter = get_skill_adapter(spec.adapter_kind)
        sections: List[str] = []
        title_count = 0
        error_messages: List[str] = []
        for subject in subjects[:5]:
            try:
                result = adapter.execute(spec, query=f"{subject} 新闻", limit=2)
                titles = result.titles if isinstance(result, WencaiSearchAdapterResult) else []
                if titles:
                    title_count += len(titles)
                    sections.append(
                        "\n".join(
                            [f"{subject}：", *[f"- {title}" for title in titles]]
                        )
                    )
                else:
                    sections.append(f"{subject}：\n- 暂无新增新闻标题")
            except Exception as exc:
                error_messages.append(f"{subject}: {exc}")
        if not sections and error_messages:
            return GeneratedReport(
                title="新闻摘要",
                summary="新闻搜索接口本次全部失败，未能生成有效摘要。",
                body="\n".join(
                    [
                        "本次新闻摘要未抓到可用标题。",
                        "抓取异常：",
                        *[f"- {message}" for message in error_messages[:5]],
                    ]
                ),
                trading_date=now.date().isoformat() if trading_calendar.is_trading_day(now) else None,
                payload={"subject_count": min(len(subjects), 5), "title_count": 0, "error_count": len(error_messages)},
            )
        summary = (
            f"已扫描 {min(len(subjects), 5)} 个主题，抓到 {title_count} 条新闻标题。"
            if title_count > 0
            else f"已扫描 {min(len(subjects), 5)} 个主题，暂未抓到新的新闻标题。"
        )
        body_lines = [
            f"交易日：{now.date().isoformat() if trading_calendar.is_trading_day(now) else now.date().isoformat()}",
            summary,
            *sections,
        ]
        if error_messages:
            body_lines.append("抓取异常：")
            body_lines.extend([f"- {message}" for message in error_messages[:3]])
        return GeneratedReport(
            title="新闻摘要",
            summary=summary,
            body="\n".join(body_lines),
            trading_date=now.date().isoformat() if trading_calendar.is_trading_day(now) else None,
            payload={
                "subject_count": min(len(subjects), 5),
                "title_count": title_count,
                "error_count": len(error_messages),
            },
        )

    def _flatten_positions(self, summary: PortfolioSummary) -> List[PortfolioPositionView]:
        positions: List[PortfolioPositionView] = []
        for account in summary.accounts:
            positions.extend(account.positions)
        return positions

    def _news_subjects(self) -> List[str]:
        subjects: List[str] = []
        seen: set[str] = set()
        watch_items = [
            item for item in repository.list_watchlist()
            if item.bucket.value in {"short_term", "swing", "mid_term_value", "observe"}
        ]
        watch_items.sort(key=lambda item: (BUCKET_PRIORITY.get(item.bucket.value, 99), item.name))
        for item in watch_items:
            if item.name in seen:
                continue
            seen.add(item.name)
            subjects.append(item.name)
        positions = self._flatten_positions(portfolio_store.summary())
        positions.sort(key=lambda item: item.cost_value, reverse=True)
        for position in positions:
            if position.name in seen:
                continue
            seen.add(position.name)
            subjects.append(position.name)
        return subjects


scheduled_report_service = ScheduledReportService()
