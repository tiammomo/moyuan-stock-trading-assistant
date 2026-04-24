from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.core.config import get_settings
from app.schemas.portfolio import (
    PortfolioAccountCreate,
    PortfolioAccountRecord,
    PortfolioAccountUpdate,
    PortfolioAccountView,
    PortfolioMarketSchedule,
    PortfolioPositionCreate,
    PortfolioPositionRecord,
    PortfolioPositionUpdate,
    PortfolioPositionView,
    PortfolioSummary,
)

from .json_store import JsonFileStore
from .local_market_skill_client import LocalMarketSkillError, local_market_skill_client
from .trading_calendar import trading_calendar


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_text(value: Optional[str]) -> str:
    return " ".join(str(value or "").strip().split())


def _normalize_symbol(symbol: str) -> str:
    text = _clean_text(symbol).upper()
    if "." in text:
        code, exchange = text.split(".", 1)
        return f"{code}.{exchange}"
    if len(text) == 6 and text.isdigit():
        if text.startswith(("60", "68", "90")):
            return f"{text}.SH"
        if text.startswith(("00", "20", "30")):
            return f"{text}.SZ"
        if text.startswith(("43", "83", "87", "88", "92")) or text.startswith("8"):
            return f"{text}.BJ"
    return text


def _quote_code(symbol: str) -> str:
    return _normalize_symbol(symbol).split(".", 1)[0]


class PortfolioStore:
    def __init__(self) -> None:
        settings = get_settings()
        self.accounts_store = JsonFileStore(settings.data_dir / "portfolio_accounts.json", lambda: [])
        self.positions_store = JsonFileStore(settings.data_dir / "portfolio_positions.json", lambda: [])

    def list_accounts(self) -> List[PortfolioAccountRecord]:
        rows = sorted(self.accounts_store.read(), key=lambda item: item.get("created_at", ""))
        return [PortfolioAccountRecord(**row) for row in rows]

    def get_account(self, account_id: str) -> Optional[PortfolioAccountRecord]:
        for row in self.accounts_store.read():
            if row.get("id") == account_id:
                return PortfolioAccountRecord(**row)
        return None

    def create_account(self, data: PortfolioAccountCreate) -> PortfolioAccountRecord:
        now = _now_iso()
        payload = {
            "id": f"pa_{uuid4().hex[:12]}",
            "name": _clean_text(data.name),
            "available_funds": float(data.available_funds or 0),
            "enabled": data.enabled,
            "created_at": now,
            "updated_at": now,
        }

        def mutate(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            rows.append(payload)
            return rows

        self.accounts_store.update(mutate)
        return PortfolioAccountRecord(**payload)

    def update_account(self, account_id: str, update: PortfolioAccountUpdate) -> Optional[PortfolioAccountRecord]:
        patch = update.model_dump(exclude_unset=True)
        updated: Optional[Dict[str, Any]] = None

        def mutate(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            nonlocal updated
            for row in rows:
                if row.get("id") != account_id:
                    continue
                if "name" in patch and patch["name"] is not None:
                    row["name"] = _clean_text(patch["name"])
                if "available_funds" in patch and patch["available_funds"] is not None:
                    row["available_funds"] = float(patch["available_funds"])
                if "enabled" in patch and patch["enabled"] is not None:
                    row["enabled"] = bool(patch["enabled"])
                row["updated_at"] = _now_iso()
                updated = dict(row)
                break
            return rows

        self.accounts_store.update(mutate)
        return PortfolioAccountRecord(**updated) if updated else None

    def delete_account(self, account_id: str) -> bool:
        rows = self.accounts_store.read()
        remaining = [row for row in rows if row.get("id") != account_id]
        deleted = len(remaining) < len(rows)
        if deleted:
            self.accounts_store.write(remaining)
            self.positions_store.write([
                row for row in self.positions_store.read() if row.get("account_id") != account_id
            ])
        return deleted

    def list_positions(self, *, account_id: Optional[str] = None) -> List[PortfolioPositionRecord]:
        rows = self.positions_store.read()
        if account_id:
            rows = [row for row in rows if row.get("account_id") == account_id]
        rows = sorted(rows, key=lambda item: item.get("updated_at", ""), reverse=True)
        return [PortfolioPositionRecord(**row) for row in rows]

    def find_position(self, account_id: str, symbol: str) -> Optional[PortfolioPositionRecord]:
        normalized_symbol = _normalize_symbol(symbol)
        for row in self.positions_store.read():
            if row.get("account_id") != account_id:
                continue
            if _normalize_symbol(str(row.get("symbol") or "")) == normalized_symbol:
                return PortfolioPositionRecord(**row)
        return None

    def create_position(self, data: PortfolioPositionCreate) -> PortfolioPositionRecord:
        account = self.get_account(data.account_id)
        if account is None:
            raise ValueError("账户不存在")
        symbol = _normalize_symbol(data.symbol)
        name = _clean_text(data.name)
        if not name:
            try:
                snapshot = local_market_skill_client.fetch_realhead(_quote_code(symbol))
                name = snapshot.name or symbol
            except Exception:
                name = symbol
        now = _now_iso()
        payload = {
            "id": f"pp_{uuid4().hex[:12]}",
            "account_id": data.account_id,
            "symbol": symbol,
            "name": name,
            "cost_price": float(data.cost_price),
            "quantity": int(data.quantity),
            "invested_amount": data.invested_amount,
            "trading_style": data.trading_style,
            "note": _clean_text(data.note) or None,
            "created_at": now,
            "updated_at": now,
        }

        def mutate(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            rows.append(payload)
            return rows

        self.positions_store.update(mutate)
        return PortfolioPositionRecord(**payload)

    def upsert_position(
        self,
        data: PortfolioPositionCreate,
        *,
        preserve_existing_note: bool = False,
    ) -> tuple[PortfolioPositionRecord, bool]:
        existing = self.find_position(data.account_id, data.symbol)
        if existing is None:
            return self.create_position(data), False

        next_note = existing.note if preserve_existing_note else data.note
        updated = self.update_position(
            existing.id,
            PortfolioPositionUpdate(
                symbol=data.symbol,
                name=data.name,
                cost_price=data.cost_price,
                quantity=data.quantity,
                invested_amount=data.invested_amount,
                trading_style=data.trading_style,
                note=next_note,
            ),
        )
        if updated is None:
            raise ValueError("更新持仓失败")
        return updated, True

    def update_position(self, position_id: str, update: PortfolioPositionUpdate) -> Optional[PortfolioPositionRecord]:
        patch = update.model_dump(exclude_unset=True)
        updated: Optional[Dict[str, Any]] = None
        if patch.get("account_id") and self.get_account(str(patch["account_id"])) is None:
            raise ValueError("账户不存在")

        def mutate(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            nonlocal updated
            for row in rows:
                if row.get("id") != position_id:
                    continue
                for key in ("account_id", "cost_price", "quantity", "invested_amount", "trading_style"):
                    if key in patch and patch[key] is not None:
                        row[key] = patch[key]
                if "symbol" in patch and patch["symbol"]:
                    row["symbol"] = _normalize_symbol(str(patch["symbol"]))
                if "name" in patch and patch["name"] is not None:
                    row["name"] = _clean_text(patch["name"]) or row.get("name")
                if "note" in patch:
                    row["note"] = _clean_text(patch["note"]) or None
                row["updated_at"] = _now_iso()
                updated = dict(row)
                break
            return rows

        self.positions_store.update(mutate)
        return PortfolioPositionRecord(**updated) if updated else None

    def delete_position(self, position_id: str) -> bool:
        rows = self.positions_store.read()
        remaining = [row for row in rows if row.get("id") != position_id]
        self.positions_store.write(remaining)
        return len(remaining) < len(rows)

    def summary(self) -> PortfolioSummary:
        market_schedule_snapshot = trading_calendar.snapshot()
        accounts = self.list_accounts()
        positions = self.list_positions()
        account_names = {account.id: account.name for account in accounts}
        positions_by_account: Dict[str, List[PortfolioPositionView]] = {account.id: [] for account in accounts}
        quote_error_count = 0

        for position in positions:
            if position.account_id not in positions_by_account:
                continue
            latest_price: Optional[float] = None
            change_pct: Optional[float] = None
            quote_error: Optional[str] = None
            try:
                snapshot = local_market_skill_client.fetch_realhead(_quote_code(position.symbol))
                latest_price = snapshot.latest_price
                change_pct = snapshot.change_pct
            except LocalMarketSkillError as exc:
                quote_error = str(exc)
                quote_error_count += 1
            except Exception as exc:
                quote_error = str(exc)
                quote_error_count += 1

            cost_value = position.cost_price * position.quantity
            market_value = latest_price * position.quantity if latest_price is not None else None
            pnl = market_value - cost_value if market_value is not None else None
            pnl_pct = (pnl / cost_value * 100) if pnl is not None and cost_value else None
            daily_pnl = None
            if latest_price is not None and change_pct is not None and change_pct != -100:
                prev_price = latest_price / (1 + change_pct / 100)
                daily_pnl = (latest_price - prev_price) * position.quantity

            positions_by_account[position.account_id].append(
                PortfolioPositionView(
                    **position.model_dump(mode="json"),
                    account_name=account_names.get(position.account_id, ""),
                    latest_price=latest_price,
                    change_pct=change_pct,
                    market_value=market_value,
                    cost_value=cost_value,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    daily_pnl=daily_pnl,
                    quote_error=quote_error,
                )
            )

        account_views: List[PortfolioAccountView] = []
        total_cost = 0.0
        total_market_value = 0.0
        total_pnl = 0.0
        total_daily_pnl = 0.0
        for account in accounts:
            account_positions = positions_by_account.get(account.id, [])
            account_cost = sum(item.cost_value for item in account_positions)
            account_market_value = sum(item.market_value or 0 for item in account_positions)
            account_pnl = sum(item.pnl or 0 for item in account_positions)
            account_daily_pnl = sum(item.daily_pnl or 0 for item in account_positions)
            account_pnl_pct = account_pnl / account_cost * 100 if account_cost else 0
            total_cost += account_cost
            total_market_value += account_market_value
            total_pnl += account_pnl
            total_daily_pnl += account_daily_pnl
            account_views.append(
                PortfolioAccountView(
                    **account.model_dump(mode="json"),
                    positions=account_positions,
                    total_cost=account_cost,
                    total_market_value=account_market_value,
                    total_pnl=account_pnl,
                    total_pnl_pct=account_pnl_pct,
                    total_daily_pnl=account_daily_pnl,
                )
            )

        return PortfolioSummary(
            accounts=account_views,
            total_cost=total_cost,
            total_market_value=total_market_value,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl / total_cost * 100 if total_cost else 0,
            total_daily_pnl=total_daily_pnl,
            quote_error_count=quote_error_count,
            market_schedule=PortfolioMarketSchedule(
                calendar_source=market_schedule_snapshot.calendar_source,
                market_phase=market_schedule_snapshot.market_phase,
                is_trading_day=market_schedule_snapshot.is_trading_day,
                next_open_at=market_schedule_snapshot.next_open_at,
                next_refresh_in_ms=market_schedule_snapshot.next_refresh_in_ms,
            ),
        )


portfolio_store = PortfolioStore()
