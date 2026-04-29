from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Iterable, Optional
from zoneinfo import ZoneInfo


CN_TZ = ZoneInfo("Asia/Shanghai")
CN_TRADING_WINDOWS = (
    (time(hour=9, minute=30), time(hour=11, minute=30)),
    (time(hour=13, minute=0), time(hour=15, minute=0)),
)
CALENDAR_SOURCE = "上交所节假日休市安排（2024-2026）"
OPEN_MARKET_REFRESH_INTERVAL_MS = 10_000
OFFICIAL_HOLIDAY_RANGES = (
    ("2024-01-01", "2024-01-01"),
    ("2024-02-09", "2024-02-18"),
    ("2024-04-04", "2024-04-07"),
    ("2024-05-01", "2024-05-05"),
    ("2024-06-10", "2024-06-10"),
    ("2024-09-15", "2024-09-17"),
    ("2024-10-01", "2024-10-07"),
    ("2025-01-01", "2025-01-01"),
    ("2025-01-28", "2025-02-04"),
    ("2025-04-04", "2025-04-06"),
    ("2025-05-01", "2025-05-05"),
    ("2025-05-31", "2025-06-02"),
    ("2025-10-01", "2025-10-08"),
    ("2026-01-01", "2026-01-03"),
    ("2026-02-15", "2026-02-23"),
    ("2026-04-04", "2026-04-06"),
    ("2026-05-01", "2026-05-05"),
    ("2026-06-19", "2026-06-21"),
    ("2026-09-25", "2026-09-27"),
    ("2026-10-01", "2026-10-07"),
)


def _expand_holiday_ranges(ranges: Iterable[tuple[str, str]]) -> frozenset[date]:
    dates: set[date] = set()
    for start_raw, end_raw in ranges:
        start = date.fromisoformat(start_raw)
        end = date.fromisoformat(end_raw)
        current = start
        while current <= end:
            dates.add(current)
            current += timedelta(days=1)
    return frozenset(dates)


OFFICIAL_CLOSED_DATES = _expand_holiday_ranges(OFFICIAL_HOLIDAY_RANGES)


@dataclass(frozen=True)
class TradingCalendarSnapshot:
    calendar_source: str
    market_phase: str
    is_trading_day: bool
    next_open_at: Optional[datetime]
    next_refresh_in_ms: int


class ChinaTradingCalendar:
    def _to_cn_datetime(self, value: Optional[datetime] = None) -> datetime:
        dt = value or datetime.now(CN_TZ)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=CN_TZ)
        return dt.astimezone(CN_TZ)

    def is_trading_day(self, value: date | datetime) -> bool:
        current_date = value.date() if isinstance(value, datetime) else value
        return current_date.weekday() < 5 and current_date not in OFFICIAL_CLOSED_DATES

    def market_phase(self, value: Optional[datetime] = None) -> str:
        dt = self._to_cn_datetime(value)
        if not self.is_trading_day(dt):
            return "closed"
        current = dt.time()
        for start, end in CN_TRADING_WINDOWS:
            if start <= current <= end:
                return "open"
        return "closed"

    def next_open_at(self, value: Optional[datetime] = None) -> Optional[datetime]:
        dt = self._to_cn_datetime(value)
        if self.is_trading_day(dt):
            morning_open, morning_close = CN_TRADING_WINDOWS[0]
            afternoon_open, _ = CN_TRADING_WINDOWS[1]
            if dt.time() < morning_open:
                return datetime.combine(dt.date(), morning_open, tzinfo=CN_TZ)
            if morning_close < dt.time() < afternoon_open:
                return datetime.combine(dt.date(), afternoon_open, tzinfo=CN_TZ)

        for offset in range(0, 370):
            candidate_date = dt.date() + timedelta(days=offset)
            if not self.is_trading_day(candidate_date):
                continue
            morning_open, _ = CN_TRADING_WINDOWS[0]
            candidate_open = datetime.combine(candidate_date, morning_open, tzinfo=CN_TZ)
            if candidate_open > dt:
                return candidate_open
        return None

    def next_refresh_in_ms(self, value: Optional[datetime] = None) -> int:
        dt = self._to_cn_datetime(value)
        if self.market_phase(dt) == "open":
            return OPEN_MARKET_REFRESH_INTERVAL_MS
        next_open = self.next_open_at(dt)
        if next_open is None:
            return OPEN_MARKET_REFRESH_INTERVAL_MS
        delta_ms = int((next_open - dt).total_seconds() * 1000)
        return max(delta_ms, OPEN_MARKET_REFRESH_INTERVAL_MS)

    def snapshot(self, value: Optional[datetime] = None) -> TradingCalendarSnapshot:
        dt = self._to_cn_datetime(value)
        return TradingCalendarSnapshot(
            calendar_source=CALENDAR_SOURCE,
            market_phase=self.market_phase(dt),
            is_trading_day=self.is_trading_day(dt),
            next_open_at=self.next_open_at(dt),
            next_refresh_in_ms=self.next_refresh_in_ms(dt),
        )


trading_calendar = ChinaTradingCalendar()
