from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.schemas import (
    ScheduledReportJobRecord,
    ScheduledReportJobUpdate,
    ScheduledReportRunRecord,
    ScheduledReportType,
)

from .json_store import JsonFileStore
from .monitor_notification_store import monitor_notification_store


DEFAULT_SCHEDULED_REPORT_JOBS: tuple[tuple[ScheduledReportType, str], ...] = (
    ("news_digest", "08:50"),
    ("pre_market_watchlist", "09:05"),
    ("portfolio_daily", "15:10"),
    ("post_market_review", "15:20"),
)


class ScheduledReportStoreError(RuntimeError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def _default_jobs_payload() -> List[Dict[str, Any]]:
    now = _utc_now_iso()
    return [
        {
            "report_type": report_type,
            "enabled": False,
            "schedule_time": schedule_time,
            "channel_ids": [],
            "updated_at": now,
        }
        for report_type, schedule_time in DEFAULT_SCHEDULED_REPORT_JOBS
    ]


class ScheduledReportStore:
    def __init__(self) -> None:
        settings = get_settings()
        self.jobs_store = JsonFileStore(
            settings.data_dir / "scheduled_report_jobs.json",
            _default_jobs_payload,
        )
        self.runs_store = JsonFileStore(
            settings.data_dir / "scheduled_report_runs.json",
            lambda: [],
        )
        self.state_store = JsonFileStore(
            settings.data_dir / "scheduled_report_state.json",
            lambda: {"scheduled_dates": {}},
        )
        self.migrate_legacy_jobs()

    def migrate_legacy_jobs(self) -> int:
        migrated_count = 0

        def mutate(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            nonlocal migrated_count
            known = {str(row.get("report_type") or "") for row in rows}
            defaults_by_type = dict(DEFAULT_SCHEDULED_REPORT_JOBS)
            for row in rows:
                if self._normalize_job_row(row, defaults_by_type.get(str(row.get("report_type") or ""))):
                    migrated_count += 1
            for report_type, schedule_time in DEFAULT_SCHEDULED_REPORT_JOBS:
                if report_type in known:
                    continue
                rows.append(
                    {
                        "report_type": report_type,
                        "enabled": False,
                        "schedule_time": schedule_time,
                        "channel_ids": [],
                        "updated_at": _utc_now_iso(),
                    }
                )
                migrated_count += 1
            rows.sort(
                key=lambda item: list(dict(DEFAULT_SCHEDULED_REPORT_JOBS).keys()).index(
                    str(item.get("report_type") or "")
                )
                if str(item.get("report_type") or "") in dict(DEFAULT_SCHEDULED_REPORT_JOBS)
                else 999
            )
            return rows

        self.jobs_store.update(mutate)
        return migrated_count

    def list_jobs(self) -> List[ScheduledReportJobRecord]:
        rows = self.jobs_store.read()
        return [ScheduledReportJobRecord(**row) for row in rows]

    def get_job(self, report_type: ScheduledReportType) -> Optional[ScheduledReportJobRecord]:
        for row in self.jobs_store.read():
            if row.get("report_type") == report_type:
                return ScheduledReportJobRecord(**row)
        return None

    def update_job(
        self,
        report_type: ScheduledReportType,
        update: ScheduledReportJobUpdate,
    ) -> Optional[ScheduledReportJobRecord]:
        patch = update.model_dump(exclude_unset=True)
        known_channel_ids = {channel.id for channel in monitor_notification_store.list_channels()}
        updated_record: Optional[Dict[str, Any]] = None

        def mutate(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            nonlocal updated_record
            for row in rows:
                if row.get("report_type") != report_type:
                    continue
                if "enabled" in patch and patch["enabled"] is not None:
                    row["enabled"] = bool(patch["enabled"])
                if "schedule_time" in patch and patch["schedule_time"] is not None:
                    row["schedule_time"] = self._validate_time_text(patch["schedule_time"])
                if "channel_ids" in patch and patch["channel_ids"] is not None:
                    deduped = list(dict.fromkeys(str(item) for item in patch["channel_ids"]))
                    row["channel_ids"] = [
                        channel_id for channel_id in deduped if channel_id in known_channel_ids
                    ]
                row["updated_at"] = _utc_now_iso()
                updated_record = dict(row)
                break
            return rows

        self.jobs_store.update(mutate)
        return ScheduledReportJobRecord(**updated_record) if updated_record else None

    def remove_notification_channel_references(self, channel_id: str) -> int:
        updated_count = 0

        def mutate(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            nonlocal updated_count
            for row in rows:
                channel_ids = [str(item) for item in (row.get("channel_ids") or [])]
                filtered = [item for item in channel_ids if item != channel_id]
                if filtered == channel_ids:
                    continue
                row["channel_ids"] = filtered
                row["updated_at"] = _utc_now_iso()
                updated_count += 1
            return rows

        self.jobs_store.update(mutate)
        return updated_count

    def list_runs(self, limit: int = 20) -> List[ScheduledReportRunRecord]:
        safe_limit = max(1, min(int(limit), 200))
        return [ScheduledReportRunRecord(**row) for row in self.runs_store.read()[:safe_limit]]

    def append_run(self, record: ScheduledReportRunRecord) -> None:
        def mutate(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            next_rows = [record.model_dump(mode="json"), *rows]
            return next_rows[:200]

        self.runs_store.update(mutate)

    def was_scheduled_for_date(self, report_type: ScheduledReportType, trading_date: str) -> bool:
        payload = self.state_store.read()
        scheduled_dates = payload.get("scheduled_dates") or {}
        return str((scheduled_dates.get(report_type) or {}).get("trading_date") or "") == trading_date

    def mark_scheduled_for_date(
        self,
        report_type: ScheduledReportType,
        trading_date: str,
        *,
        run_id: Optional[str] = None,
    ) -> None:
        def mutate(payload: Dict[str, Any]) -> Dict[str, Any]:
            next_payload = dict(payload or {"scheduled_dates": {}})
            scheduled_dates = next_payload.setdefault("scheduled_dates", {})
            scheduled_dates[report_type] = {
                "trading_date": trading_date,
                "run_id": run_id,
                "updated_at": _utc_now_iso(),
            }
            return next_payload

        self.state_store.update(mutate)

    def _normalize_job_row(self, row: Dict[str, Any], default_schedule_time: Optional[str]) -> bool:
        changed = False
        report_type = str(row.get("report_type") or "")
        if report_type not in {item[0] for item in DEFAULT_SCHEDULED_REPORT_JOBS}:
            return changed

        if not isinstance(row.get("enabled"), bool):
            row["enabled"] = bool(row.get("enabled", False))
            changed = True

        schedule_time = str(row.get("schedule_time") or "").strip()
        if not schedule_time:
            row["schedule_time"] = default_schedule_time or "09:00"
            changed = True
        else:
            normalized = self._validate_time_text(schedule_time)
            if normalized != schedule_time:
                row["schedule_time"] = normalized
                changed = True

        channel_ids = row.get("channel_ids")
        if isinstance(channel_ids, list):
            normalized_channel_ids = list(dict.fromkeys(str(item) for item in channel_ids if str(item).strip()))
        else:
            normalized_channel_ids = []
        if channel_ids != normalized_channel_ids:
            row["channel_ids"] = normalized_channel_ids
            changed = True

        if "updated_at" not in row or not row.get("updated_at"):
            row["updated_at"] = _utc_now_iso()
            changed = True

        return changed

    def _validate_time_text(self, value: str) -> str:
        text = str(value or "").strip()
        if len(text) != 5 or text[2] != ":":
            raise ScheduledReportStoreError("时间格式必须是 HH:MM")
        hour_text, minute_text = text.split(":", 1)
        try:
            hour = int(hour_text)
            minute = int(minute_text)
        except ValueError as exc:
            raise ScheduledReportStoreError("时间格式必须是 HH:MM") from exc
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ScheduledReportStoreError("时间必须落在 00:00 到 23:59")
        return f"{hour:02d}:{minute:02d}"


scheduled_report_store = ScheduledReportStore()
