from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.core.config import get_settings
from app.schemas import MonitorRuleRecord, WatchMonitorEvent, WatchMonitorScanResponse, WatchMonitorStatus
from app.schemas.watchlist import WatchItemRecord

from .json_store import JsonFileStore
from .local_market_skill_client import LocalMarketSkillError, local_market_skill_client
from .repository import repository
from .trading_calendar import trading_calendar
from .watch_rule_store import watch_rule_store


logger = logging.getLogger(__name__)
def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _utc_now().isoformat()


def _safe_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace("%", "").replace(",", "").strip()
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _as_iso_or_none(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value is not None else None


def _parse_datetime(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _is_expired(value: Optional[datetime], now: datetime) -> bool:
    if value is None:
        return False
    expires_at = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return now >= expires_at


def _market_phase(now: Optional[datetime] = None) -> str:
    return trading_calendar.market_phase(now)


def _condition_label(condition_type: str) -> str:
    mapping = {
        "latest_price": "现价",
        "change_pct": "涨跌幅",
        "volume_ratio": "量比",
        "weibi": "委比",
        "amount": "成交额",
        "volume": "成交量",
        "turnover_pct": "换手率",
        "amplitude_pct": "振幅",
        "waipan": "外盘",
        "neipan": "内盘",
        "weicha": "委差",
        "pb": "市净率",
        "pe_dynamic": "动态市盈率",
        "total_market_value": "总市值",
        "float_market_value": "流通市值",
    }
    return mapping.get(condition_type, condition_type)


def _format_target(condition_type: str, op: str, value: Any) -> str:
    suffix = "%" if condition_type in {"change_pct", "weibi", "turnover_pct", "amplitude_pct"} else ""
    if op == "between":
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            return "介于无效区间"
        low = _safe_float(value[0])
        high = _safe_float(value[1])
        if low is None or high is None:
            return "介于无效区间"
        return f"介于 {low:g}{suffix} 到 {high:g}{suffix}"
    numeric = _safe_float(value)
    if numeric is None:
        return f"{op} 无效值"
    return f"{op} {numeric:g}{suffix}"


def _event_type_for_condition_types(condition_types: List[str]) -> str:
    if "latest_price" in condition_types or "change_pct" in condition_types:
        return "price_move"
    if any(item in condition_types for item in ("volume_ratio", "amount", "volume", "turnover_pct")):
        return "volume_spike"
    if any(item in condition_types for item in ("weibi", "weicha", "waipan", "neipan")):
        return "orderbook_bias"
    if "amplitude_pct" in condition_types:
        return "volatility"
    if any(item in condition_types for item in ("pb", "pe_dynamic", "total_market_value", "float_market_value")):
        return "valuation_watch"
    return "watch_update"


def _severity_for_rule(
    rule_severity: str,
    change_pct: Optional[float],
    weibi: Optional[float],
) -> str:
    if rule_severity == "warning":
        return "warning"
    if change_pct is not None and abs(change_pct) >= 5.0:
        return "warning"
    if weibi is not None and weibi <= -35.0:
        return "warning"
    return "info"


def _build_rule_summary(
    rule: MonitorRuleRecord,
    *,
    metrics: Dict[str, Optional[float]],
    matched_conditions: List[Dict[str, Any]],
) -> str:
    bits: List[str] = []
    latest_price = metrics.get("latest_price")
    if latest_price is not None:
        bits.append(f"现价 {latest_price:.2f}")
    change_pct = metrics.get("change_pct")
    if change_pct is not None:
        prefix = "+" if change_pct >= 0 else ""
        bits.append(f"涨跌幅 {prefix}{change_pct:.2f}%")
    volume_ratio = metrics.get("volume_ratio")
    if volume_ratio is not None:
        bits.append(f"量比 {volume_ratio:.2f}")
    weibi = metrics.get("weibi")
    if weibi is not None:
        bits.append(f"委比 {weibi:.2f}%")
    turnover_pct = metrics.get("turnover_pct")
    if turnover_pct is not None:
        bits.append(f"换手率 {turnover_pct:.2f}%")
    amount = metrics.get("amount")
    if amount is not None:
        bits.append(f"成交额 {amount:g}")
    amplitude_pct = metrics.get("amplitude_pct")
    if amplitude_pct is not None:
        bits.append(f"振幅 {amplitude_pct:.2f}%")

    trigger_bits: List[str] = []
    for detail in matched_conditions:
        trigger_bits.append(
            f"{_condition_label(str(detail.get('type') or ''))} "
            f"{_format_target(str(detail.get('type') or ''), str(detail.get('op') or ''), detail.get('target'))}"
        )
    reason_text = "、".join(trigger_bits) or "满足条件"
    metrics = "，".join(bits)
    if metrics:
        return f"命中规则「{rule.rule_name}」：{reason_text}；{metrics}。"
    return f"命中规则「{rule.rule_name}」：{reason_text}。"


class WatchMonitorService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.events_store = JsonFileStore(
            self.settings.data_dir / "watch_monitor_events.json",
            lambda: [],
        )
        self.state_store = JsonFileStore(
            self.settings.data_dir / "watch_monitor_state.json",
            lambda: {
                "runtime": {
                    "watchlist_count": 0,
                    "event_count": 0,
                    "last_scan_at": None,
                    "last_event_at": None,
                    "last_scan_duration_ms": None,
                    "last_error": None,
                },
                "rules": {},
                "symbols": {},
            },
        )
        self._task: Optional[asyncio.Task[None]] = None
        self._stop_event = asyncio.Event()
        self._scan_lock = asyncio.Lock()

    def get_status(self) -> WatchMonitorStatus:
        state = self.state_store.read()
        runtime = state.get("runtime") or {}
        return WatchMonitorStatus(
            enabled=self.settings.watch_monitor_enabled,
            running=self._task is not None and not self._task.done(),
            market_phase=_market_phase(),
            interval_seconds=max(15, int(self.settings.watch_monitor_interval_seconds)),
            watchlist_count=int(runtime.get("watchlist_count") or 0),
            event_count=len(self.events_store.read()),
            last_scan_at=_parse_datetime(runtime.get("last_scan_at")),
            last_event_at=_parse_datetime(runtime.get("last_event_at")),
            last_scan_duration_ms=runtime.get("last_scan_duration_ms"),
            last_error=runtime.get("last_error"),
        )

    def list_events(self, limit: int = 20) -> List[WatchMonitorEvent]:
        safe_limit = max(1, min(int(limit), 100))
        rows = self.events_store.read()[:safe_limit]
        return [WatchMonitorEvent(**row) for row in rows]

    def _update_runtime(self, patch: Dict[str, Any]) -> None:
        def mutate(data: Dict[str, Any]) -> Dict[str, Any]:
            runtime = data.setdefault("runtime", {})
            runtime.update(patch)
            return data

        self.state_store.update(mutate)

    def _get_symbol_state(self, symbol: str) -> Dict[str, Any]:
        data = self.state_store.read()
        symbols = data.get("symbols") or {}
        record = symbols.get(symbol) or {}
        return record if isinstance(record, dict) else {}

    def _get_rule_state(self, rule_id: str) -> Dict[str, Any]:
        data = self.state_store.read()
        rules = data.get("rules") or {}
        record = rules.get(rule_id) or {}
        return record if isinstance(record, dict) else {}

    def _update_symbol_state(self, symbol: str, patch: Dict[str, Any]) -> None:
        def mutate(data: Dict[str, Any]) -> Dict[str, Any]:
            symbols = data.setdefault("symbols", {})
            record = symbols.setdefault(symbol, {})
            record.update(patch)
            return data

        self.state_store.update(mutate)

    def _update_rule_state(self, rule_id: str, patch: Dict[str, Any]) -> None:
        def mutate(data: Dict[str, Any]) -> Dict[str, Any]:
            rules = data.setdefault("rules", {})
            record = rules.setdefault(rule_id, {})
            record.update(patch)
            return data

        self.state_store.update(mutate)

    def _append_event(self, event: Dict[str, Any]) -> None:
        def mutate(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            next_items = [event, *items]
            return next_items[: max(20, int(self.settings.watch_monitor_max_events))]

        self.events_store.update(mutate)

    def _eval_rule_condition(
        self,
        condition: Dict[str, Any],
        metrics: Dict[str, Optional[float]],
    ) -> Dict[str, Any]:
        condition_type = str(condition.get("type") or "")
        op = str(condition.get("op") or "")
        target = condition.get("value")
        actual = metrics.get(condition_type)
        matched = False

        if actual is not None:
            if op == "between":
                if isinstance(target, (list, tuple)) and len(target) == 2:
                    low = _safe_float(target[0])
                    high = _safe_float(target[1])
                    if low is not None and high is not None:
                        matched = low <= actual <= high
            else:
                target_value = _safe_float(target)
                if target_value is not None:
                    if op == ">":
                        matched = actual > target_value
                    elif op == ">=":
                        matched = actual >= target_value
                    elif op == "<":
                        matched = actual < target_value
                    elif op == "<=":
                        matched = actual <= target_value

        return {
            "type": condition_type,
            "op": op,
            "target": target,
            "actual": actual,
            "matched": matched,
        }

    def _evaluate_rule(
        self,
        item: WatchItemRecord,
        rule: MonitorRuleRecord,
        *,
        metrics: Dict[str, Optional[float]],
    ) -> Dict[str, Any]:
        details = [
            self._eval_rule_condition(condition.model_dump(mode="json"), metrics)
            for condition in rule.condition_group.items
        ]
        bools = [bool(detail.get("matched")) for detail in details]
        if not bools:
            matched = False
        elif rule.condition_group.op == "and":
            matched = all(bools)
        else:
            matched = any(bools)

        matched_details = [detail for detail in details if detail.get("matched")]
        matched_types = list(dict.fromkeys(str(detail.get("type") or "") for detail in matched_details))
        event_type = _event_type_for_condition_types(matched_types)
        fingerprint = "|".join(
            [
                rule.id,
                event_type,
                *[
                    f"{detail.get('type')}:{detail.get('op')}:{detail.get('target')}"
                    for detail in matched_details
                ],
            ]
        )

        return {
            "matched": matched,
            "matched_conditions": matched_details,
            "matched_types": matched_types,
            "event_type": event_type,
            "fingerprint": fingerprint,
            "severity": _severity_for_rule(rule.severity, metrics.get("change_pct"), metrics.get("weibi")),
            "summary": _build_rule_summary(
                rule,
                metrics=metrics,
                matched_conditions=matched_details,
            ),
            "metrics": metrics,
            "title": f"{item.name} 命中规则：{rule.rule_name}",
        }

    def _can_emit_rule_event(
        self,
        rule: MonitorRuleRecord,
        *,
        fingerprint: str,
        now: datetime,
    ) -> bool:
        state = self._get_rule_state(rule.id)
        if _is_expired(rule.expire_at, now):
            return False

        today = now.astimezone(CN_TZ).strftime("%Y-%m-%d")
        trigger_date = str(state.get("trigger_date") or "")
        trigger_count_today = int(state.get("trigger_count_today") or 0)
        if trigger_date != today:
            trigger_count_today = 0

        if rule.repeat_mode == "once" and state.get("has_triggered"):
            return False

        if rule.max_triggers_per_day > 0 and trigger_count_today >= rule.max_triggers_per_day:
            return False

        last_trigger_at = _parse_datetime(state.get("last_trigger_at"))
        cooldown_seconds = max(0, int(rule.cooldown_minutes or 0)) * 60
        if last_trigger_at is not None and cooldown_seconds > 0:
            if (now - last_trigger_at).total_seconds() < cooldown_seconds:
                return False

        last_fingerprint = str(state.get("last_event_fingerprint") or "")
        if (
            cooldown_seconds > 0
            and last_fingerprint
            and last_fingerprint == fingerprint
            and last_trigger_at is not None
        ):
            if (now - last_trigger_at).total_seconds() < cooldown_seconds:
                return False
        return True

    def _mark_rule_event(
        self,
        rule: MonitorRuleRecord,
        *,
        fingerprint: str,
        now: datetime,
    ) -> None:
        state = self._get_rule_state(rule.id)
        today = now.astimezone(CN_TZ).strftime("%Y-%m-%d")
        trigger_count_today = int(state.get("trigger_count_today") or 0)
        trigger_date = str(state.get("trigger_date") or "")
        if trigger_date != today:
            trigger_count_today = 0

        self._update_rule_state(
            rule.id,
            {
                "last_trigger_at": _as_iso_or_none(now),
                "trigger_date": today,
                "trigger_count_today": trigger_count_today + 1,
                "last_event_fingerprint": fingerprint,
                "has_triggered": True,
            },
        )

    def _scan_item(
        self,
        item: WatchItemRecord,
        *,
        manual: bool,
        now: datetime,
    ) -> List[WatchMonitorEvent]:
        code = item.symbol.split(".", 1)[0]
        previous = self._get_symbol_state(item.symbol)
        snapshot = local_market_skill_client.fetch_realhead(code)
        metrics = {
            "latest_price": snapshot.latest_price,
            "change_pct": snapshot.change_pct,
            "volume_ratio": snapshot.volume_ratio,
            "weibi": snapshot.weibi,
            "amount": snapshot.amount,
            "volume": snapshot.volume,
            "turnover_pct": snapshot.turnover_pct,
            "amplitude_pct": snapshot.amplitude_pct,
            "waipan": snapshot.waipan,
            "neipan": snapshot.neipan,
            "weicha": snapshot.weicha,
            "pb": snapshot.pb,
            "pe_dynamic": snapshot.pe_dynamic,
            "total_market_value": snapshot.total_market_value,
            "float_market_value": snapshot.float_market_value,
        }
        next_state = {
            "last_seen_at": _as_iso_or_none(now),
            **metrics,
        }
        emitted_events: List[WatchMonitorEvent] = []
        rules = watch_rule_store.get_rules_for_item(item.id, enabled_only=True)
        if not rules:
            self._update_symbol_state(item.symbol, next_state)
            return emitted_events

        for rule in rules:
            if not manual and rule.market_hours_mode == "trading_only" and _market_phase(now) != "open":
                continue
            evaluation = self._evaluate_rule(
                item,
                rule,
                metrics=metrics,
            )
            if not evaluation["matched"]:
                continue
            fingerprint = str(evaluation["fingerprint"])
            if not self._can_emit_rule_event(rule, fingerprint=fingerprint, now=now):
                continue

            event = WatchMonitorEvent(
                id=f"me_{uuid4().hex[:12]}",
                symbol=item.symbol,
                name=item.name,
                bucket=item.bucket,
                rule_id=rule.id,
                rule_name=rule.rule_name,
                event_type=str(evaluation["event_type"]),
                severity=str(evaluation["severity"]),
                title=str(evaluation["title"]),
                summary=str(evaluation["summary"]),
                reasons=[str(reason) for reason in evaluation["matched_types"]],
                metrics={
                    **evaluation["metrics"],
                    "bucket": item.bucket.value,
                },
                created_at=now,
            )
            self._append_event(event.model_dump(mode="json"))
            self._mark_rule_event(rule, fingerprint=fingerprint, now=now)
            emitted_events.append(event)

        self._update_symbol_state(
            item.symbol,
            {
                **next_state,
                "last_event_at": _as_iso_or_none(now) if emitted_events else previous.get("last_event_at"),
                "last_event_type": emitted_events[0].event_type if emitted_events else previous.get("last_event_type"),
            },
        )
        return emitted_events

    async def scan_once(self, *, manual: bool = False) -> WatchMonitorScanResponse:
        async with self._scan_lock:
            started_at = _utc_now()
            watchlist = repository.list_watchlist()
            watch_rule_store.ensure_default_rules(watchlist)
            event_count_before = len(self.events_store.read())
            triggered_events: List[WatchMonitorEvent] = []
            skipped_count = 0
            last_error: Optional[str] = None

            market_open = _market_phase(started_at) == "open"
            if not manual and not market_open:
                active_always_item_ids = {
                    rule.item_id
                    for rule in watch_rule_store.list_rules()
                    if rule.enabled
                    and rule.market_hours_mode == "always"
                    and not _is_expired(rule.expire_at, started_at)
                }
                if active_always_item_ids:
                    watchlist = [item for item in watchlist if item.id in active_always_item_ids]
                else:
                    skipped_count = len(watchlist)
                    duration_ms = int((_utc_now() - started_at).total_seconds() * 1000)
                    self._update_runtime(
                        {
                            "watchlist_count": len(watchlist),
                            "event_count": event_count_before,
                            "last_scan_at": _as_iso_or_none(_utc_now()),
                            "last_scan_duration_ms": duration_ms,
                        }
                    )
                    return WatchMonitorScanResponse(
                        scanned_count=0,
                        triggered_count=0,
                        skipped_count=skipped_count,
                        events=[],
                        status=self.get_status(),
                    )

            if not manual and not market_open and len(watchlist) == 0:
                skipped_count = len(watchlist)
                duration_ms = int((_utc_now() - started_at).total_seconds() * 1000)
                self._update_runtime(
                    {
                        "watchlist_count": len(watchlist),
                        "event_count": event_count_before,
                        "last_scan_at": _as_iso_or_none(_utc_now()),
                        "last_scan_duration_ms": duration_ms,
                    }
                )
                return WatchMonitorScanResponse(
                    scanned_count=0,
                    triggered_count=0,
                    skipped_count=skipped_count,
                    events=[],
                    status=self.get_status(),
                )

            for item in watchlist:
                try:
                    events = await asyncio.to_thread(
                        self._scan_item,
                        item,
                        manual=manual,
                        now=started_at,
                    )
                    if events:
                        triggered_events.extend(events)
                except LocalMarketSkillError as exc:
                    last_error = f"{item.name}：{exc}"
                    logger.warning("Watch monitor scan failed for %s: %s", item.symbol, exc)
                except Exception as exc:  # pragma: no cover - defensive
                    last_error = f"{item.name}：{exc}"
                    logger.exception("Watch monitor scan crashed for %s", item.symbol)

            finished_at = _utc_now()
            duration_ms = int((finished_at - started_at).total_seconds() * 1000)
            runtime_patch = {
                "watchlist_count": len(watchlist),
                "event_count": len(self.events_store.read()),
                "last_scan_at": _as_iso_or_none(finished_at),
                "last_scan_duration_ms": duration_ms,
            }
            if triggered_events:
                runtime_patch["last_event_at"] = _as_iso_or_none(triggered_events[0].created_at)
            if last_error:
                runtime_patch["last_error"] = last_error
            elif manual or event_count_before != len(self.events_store.read()):
                runtime_patch["last_error"] = None
            self._update_runtime(runtime_patch)

            return WatchMonitorScanResponse(
                scanned_count=len(watchlist),
                triggered_count=len(triggered_events),
                skipped_count=skipped_count,
                events=triggered_events,
                status=self.get_status(),
            )

    async def _run_loop(self) -> None:
        interval = max(15, int(self.settings.watch_monitor_interval_seconds))
        while not self._stop_event.is_set():
            try:
                await self.scan_once(manual=False)
            except Exception:
                logger.exception("Watch monitor loop failed")
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                continue

    def start(self) -> None:
        if not self.settings.watch_monitor_enabled:
            logger.info("Watch monitor disabled by config")
            return
        if self._task is not None and not self._task.done():
            return
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run_loop(), name="watch-monitor-loop")
        logger.info(
            "Watch monitor started: interval=%ss cooldown=%ss",
            max(15, int(self.settings.watch_monitor_interval_seconds)),
            max(0, int(self.settings.watch_monitor_event_cooldown_seconds)),
        )

    async def shutdown(self) -> None:
        if self._task is None:
            return
        self._stop_event.set()
        try:
            await self._task
        except Exception:
            logger.exception("Watch monitor shutdown failed")
        finally:
            self._task = None


watch_monitor_service = WatchMonitorService()
