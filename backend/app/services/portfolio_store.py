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
    PortfolioIndustryExposure,
    PortfolioMarketSchedule,
    PortfolioPositionAdvice,
    PortfolioPositionCreate,
    PortfolioPositionLot,
    PortfolioPositionRecord,
    PortfolioPositionUpdate,
    PortfolioPositionView,
    PortfolioSummary,
)

from .json_store import JsonFileStore
from .local_market_skill_client import LocalMarketSkillError, local_market_skill_client
from .trading_calendar import trading_calendar


VALID_TRADING_STYLES = {"short", "swing", "long"}


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


def _as_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    return None


def _as_int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if not text:
            return None
        try:
            return int(float(text))
        except ValueError:
            return None
    return None


def _parse_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


class PortfolioStore:
    def __init__(self) -> None:
        settings = get_settings()
        self.accounts_store = JsonFileStore(settings.data_dir / "portfolio_accounts.json", lambda: [])
        self.positions_store = JsonFileStore(settings.data_dir / "portfolio_positions.json", lambda: [])
        self.migrate_legacy_positions()

    def migrate_legacy_positions(self) -> int:
        migrated_count = 0

        def mutate(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            nonlocal migrated_count
            for row in rows:
                _, changed = self._normalize_position_payload(row, strict=False, hydrate_name=False)
                if changed:
                    migrated_count += 1
            return rows

        self.positions_store.update(mutate)
        return migrated_count

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
        now = _now_iso()
        payload = {
            "id": f"pp_{uuid4().hex[:12]}",
            **data.model_dump(mode="json"),
            "created_at": now,
            "updated_at": now,
        }
        normalized, _ = self._normalize_position_payload(payload, strict=True, hydrate_name=True)

        def mutate(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            rows.append(normalized)
            return rows

        self.positions_store.update(mutate)
        return PortfolioPositionRecord(**normalized)

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
                available_quantity=data.available_quantity,
                frozen_quantity=data.frozen_quantity,
                invested_amount=data.invested_amount,
                trading_style=data.trading_style,
                industry=data.industry,
                note=next_note,
                lots=data.lots,
            ),
        )
        if updated is None:
            raise ValueError("更新持仓失败")
        return updated, True

    def update_position(self, position_id: str, update: PortfolioPositionUpdate) -> Optional[PortfolioPositionRecord]:
        patch = update.model_dump(exclude_unset=True, mode="json")
        updated: Optional[Dict[str, Any]] = None
        if patch.get("account_id") and self.get_account(str(patch["account_id"])) is None:
            raise ValueError("账户不存在")

        def mutate(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            nonlocal updated
            for row in rows:
                if row.get("id") != position_id:
                    continue
                merged = dict(row)
                for key, value in patch.items():
                    merged[key] = value
                merged["updated_at"] = _now_iso()
                normalized, _ = self._normalize_position_payload(merged, strict=True, hydrate_name=True)
                row.clear()
                row.update(normalized)
                updated = dict(normalized)
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
        account_map = {account.id: account for account in accounts}
        positions_by_account: Dict[str, List[PortfolioPositionView]] = {account.id: [] for account in accounts}
        quote_error_count = 0

        raw_views: List[PortfolioPositionView] = []
        for position in positions:
            account = account_map.get(position.account_id)
            if account is None:
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

            raw_views.append(
                PortfolioPositionView(
                    **position.model_dump(mode="json"),
                    account_name=account.name,
                    latest_price=latest_price,
                    change_pct=change_pct,
                    market_value=market_value,
                    cost_value=cost_value,
                    pnl=pnl,
                    pnl_pct=pnl_pct,
                    daily_pnl=daily_pnl,
                    weight_pct=0,
                    available_ratio_pct=(position.available_quantity / position.quantity * 100) if position.quantity else 0,
                    quote_error=quote_error,
                    advice=None,
                )
            )

        account_views: List[PortfolioAccountView] = []
        total_cost = 0.0
        total_market_value = 0.0
        total_pnl = 0.0
        total_daily_pnl = 0.0
        available_funds_total = sum(account.available_funds for account in accounts)

        for account in accounts:
            account_positions = [item for item in raw_views if item.account_id == account.id]
            account_cost = sum(item.cost_value for item in account_positions)
            account_market_value = sum(item.market_value or item.cost_value for item in account_positions)
            account_pnl = sum(item.pnl or 0 for item in account_positions)
            account_daily_pnl = sum(item.daily_pnl or 0 for item in account_positions)
            account_total_assets = account_market_value + account.available_funds
            account_pnl_pct = account_pnl / account_cost * 100 if account_cost else 0
            account_position_ratio_pct = account_market_value / account_total_assets * 100 if account_total_assets else 0

            enriched_positions: List[PortfolioPositionView] = []
            for position in account_positions:
                exposure_value = position.market_value or position.cost_value
                weight_pct = exposure_value / account_total_assets * 100 if account_total_assets else 0
                advice = self._build_position_advice(
                    position=position,
                    account_total_assets=account_total_assets,
                    weight_pct=weight_pct,
                )
                enriched_positions.append(
                    position.model_copy(
                        update={
                            "weight_pct": weight_pct,
                            "advice": advice,
                        }
                    )
                )

            enriched_positions.sort(key=lambda item: ((item.market_value or item.cost_value), item.updated_at), reverse=True)
            industry_exposures = self._build_industry_exposures(enriched_positions, basis_total=account_market_value)

            total_cost += account_cost
            total_market_value += account_market_value
            total_pnl += account_pnl
            total_daily_pnl += account_daily_pnl
            positions_by_account[account.id] = enriched_positions
            account_views.append(
                PortfolioAccountView(
                    **account.model_dump(mode="json"),
                    positions=enriched_positions,
                    total_cost=account_cost,
                    total_market_value=account_market_value,
                    total_pnl=account_pnl,
                    total_pnl_pct=account_pnl_pct,
                    total_daily_pnl=account_daily_pnl,
                    total_assets=account_total_assets,
                    position_ratio_pct=account_position_ratio_pct,
                    industry_exposures=industry_exposures,
                )
            )

        total_assets = total_market_value + available_funds_total
        total_position_ratio_pct = total_market_value / total_assets * 100 if total_assets else 0
        industry_exposures = self._build_industry_exposures(
            [item for account in account_views for item in account.positions],
            basis_total=total_market_value,
        )

        return PortfolioSummary(
            accounts=account_views,
            available_funds_total=available_funds_total,
            total_cost=total_cost,
            total_market_value=total_market_value,
            total_assets=total_assets,
            total_position_ratio_pct=total_position_ratio_pct,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl / total_cost * 100 if total_cost else 0,
            total_daily_pnl=total_daily_pnl,
            quote_error_count=quote_error_count,
            industry_exposures=industry_exposures,
            market_schedule=PortfolioMarketSchedule(
                calendar_source=market_schedule_snapshot.calendar_source,
                market_phase=market_schedule_snapshot.market_phase,
                is_trading_day=market_schedule_snapshot.is_trading_day,
                next_open_at=market_schedule_snapshot.next_open_at,
                next_refresh_in_ms=market_schedule_snapshot.next_refresh_in_ms,
            ),
        )

    def _normalize_position_payload(
        self,
        payload: Dict[str, Any],
        *,
        strict: bool,
        hydrate_name: bool,
    ) -> tuple[Dict[str, Any], bool]:
        changed = False
        row = dict(payload)

        symbol = _normalize_symbol(str(row.get("symbol") or ""))
        if strict and not symbol:
            raise ValueError("股票代码不能为空")
        if symbol != row.get("symbol"):
            row["symbol"] = symbol
            changed = True

        name = _clean_text(row.get("name")) or ""
        if not name and hydrate_name and symbol:
            name = self._resolve_position_name(symbol)
        if not name:
            name = symbol
        if name != row.get("name"):
            row["name"] = name
            changed = True

        lots = self._normalize_lots(row.get("lots"), strict=strict)
        if row.get("lots") != lots:
            row["lots"] = lots
            changed = True

        quantity = _as_int(row.get("quantity"))
        cost_price = _as_float(row.get("cost_price"))
        invested_amount = _as_float(row.get("invested_amount"))
        if lots:
            derived_quantity = sum(item.quantity for item in lots)
            derived_invested = sum(item.quantity * item.cost_price for item in lots)
            derived_cost = derived_invested / derived_quantity if derived_quantity else 0
            quantity = derived_quantity
            cost_price = derived_cost
            invested_amount = derived_invested

        if quantity is None or quantity <= 0:
            if strict:
                raise ValueError("持仓数量需要大于 0")
            quantity = max(quantity or 0, 1)
            changed = True
        if cost_price is None or cost_price <= 0:
            if strict:
                raise ValueError("成本价需要大于 0")
            cost_price = max(cost_price or 0, 0.01)
            changed = True
        if invested_amount is None:
            invested_amount = cost_price * quantity
            changed = True

        available_quantity = _as_int(row.get("available_quantity"))
        frozen_quantity = _as_int(row.get("frozen_quantity"))
        if available_quantity is None and frozen_quantity is None:
            available_quantity = quantity
            frozen_quantity = 0
            changed = True
        elif available_quantity is None:
            frozen_quantity = max(frozen_quantity or 0, 0)
            available_quantity = max(quantity - frozen_quantity, 0)
            changed = True
        elif frozen_quantity is None:
            available_quantity = max(available_quantity, 0)
            frozen_quantity = max(quantity - available_quantity, 0)
            changed = True
        else:
            available_quantity = max(available_quantity, 0)
            frozen_quantity = max(frozen_quantity, 0)

        if available_quantity + frozen_quantity > quantity:
            if strict:
                raise ValueError("可用数量与冻结数量之和不能大于总持仓数量")
            overflow = available_quantity + frozen_quantity - quantity
            if frozen_quantity >= overflow:
                frozen_quantity -= overflow
            else:
                available_quantity = max(quantity - frozen_quantity, 0)
            changed = True

        industry = _clean_text(row.get("industry")) or None
        if industry != row.get("industry"):
            row["industry"] = industry
            changed = True

        note = _clean_text(row.get("note")) or None
        if note != row.get("note"):
            row["note"] = note
            changed = True

        trading_style = str(row.get("trading_style") or "swing")
        if trading_style not in VALID_TRADING_STYLES:
            trading_style = "swing"
            changed = True

        row.update(
            {
                "quantity": quantity,
                "cost_price": round(cost_price, 4),
                "available_quantity": available_quantity,
                "frozen_quantity": frozen_quantity,
                "invested_amount": round(invested_amount, 2),
                "trading_style": trading_style,
                "industry": industry,
                "note": note,
                "lots": [item.model_dump(mode="json") for item in lots],
            }
        )
        return row, changed

    def _normalize_lots(self, lots: Any, *, strict: bool) -> List[PortfolioPositionLot]:
        if lots in (None, ""):
            return []
        if not isinstance(lots, list):
            if strict:
                raise ValueError("分批买入记录格式不正确")
            return []

        normalized: List[PortfolioPositionLot] = []
        for item in lots:
            if not isinstance(item, dict):
                if strict:
                    raise ValueError("分批买入记录格式不正确")
                continue
            quantity = _as_int(item.get("quantity"))
            cost_price = _as_float(item.get("cost_price"))
            if quantity is None or quantity <= 0 or cost_price is None or cost_price <= 0:
                if strict:
                    raise ValueError("分批买入记录里的数量和成本价都需要大于 0")
                continue
            acquired_at = _parse_datetime(item.get("acquired_at"))
            normalized.append(
                PortfolioPositionLot(
                    acquired_at=acquired_at,
                    quantity=quantity,
                    cost_price=cost_price,
                    note=_clean_text(item.get("note")) or None,
                )
            )
        return normalized

    def _resolve_position_name(self, symbol: str) -> str:
        try:
            snapshot = local_market_skill_client.fetch_realhead(_quote_code(symbol))
            return snapshot.name or symbol
        except Exception:
            return symbol

    def _build_industry_exposures(
        self,
        positions: List[PortfolioPositionView],
        *,
        basis_total: float,
    ) -> List[PortfolioIndustryExposure]:
        buckets: Dict[str, Dict[str, Any]] = {}
        for position in positions:
            industry = position.industry or "未分类"
            bucket = buckets.setdefault(
                industry,
                {"market_value": 0.0, "position_count": 0, "symbols": []},
            )
            exposure_value = position.market_value or position.cost_value
            bucket["market_value"] += exposure_value
            bucket["position_count"] += 1
            if position.symbol not in bucket["symbols"]:
                bucket["symbols"].append(position.symbol)

        exposures = [
            PortfolioIndustryExposure(
                industry=industry,
                market_value=payload["market_value"],
                weight_pct=payload["market_value"] / basis_total * 100 if basis_total else 0,
                position_count=payload["position_count"],
                symbols=payload["symbols"][:8],
            )
            for industry, payload in buckets.items()
        ]
        exposures.sort(key=lambda item: item.market_value, reverse=True)
        return exposures[:8]

    def _build_position_advice(
        self,
        *,
        position: PortfolioPositionView,
        account_total_assets: float,
        weight_pct: float,
    ) -> PortfolioPositionAdvice:
        if position.quote_error:
            headline = "行情未更新，先核实价格后再决策"
            risk = "当前快照失败，任何盈亏和仓位判断都可能失真。"
            action = "先刷新行情，再决定是否调仓。"
        else:
            pnl_pct = position.pnl_pct or 0
            change_pct = position.change_pct or 0
            if pnl_pct >= 15:
                headline = "浮盈较厚，已有较强安全垫"
            elif pnl_pct >= 5:
                headline = "处于正收益区间，可继续跟踪强弱"
            elif pnl_pct <= -8:
                headline = "浮亏偏深，需要先看风险控制"
            else:
                headline = "仓位靠近成本区，重点看下一步方向选择"

            risk_bits: List[str] = []
            if weight_pct >= 25:
                risk_bits.append("单仓权重偏高")
            if position.frozen_quantity > 0:
                risk_bits.append("有冻结仓位")
            if change_pct <= -5:
                risk_bits.append("当日回撤较大")
            if position.available_quantity < position.quantity:
                risk_bits.append("可卖仓位不足")
            risk = "；".join(risk_bits) if risk_bits else "当前没有额外的仓位结构风险。"

            if position.trading_style == "short":
                if pnl_pct >= 8:
                    action = "短线已有利润，优先分批锁盈，不把盈利单拖成长线。"
                elif pnl_pct <= -5:
                    action = "短线浮亏扩大时先收缩仓位，别等情绪继续转弱。"
                else:
                    action = "短线仓位以快进快出为主，盘中只处理最关键的一两个价位。"
            elif position.trading_style == "long":
                if weight_pct >= 25:
                    action = "长线逻辑仍在也别把单仓做得过重，优先平衡组合权重。"
                else:
                    action = "长线仓位更看基本面和节奏，不需要被日内波动反复干扰。"
            else:
                if pnl_pct >= 10:
                    action = "波段仓位可沿趋势做移动保护，强势时留底仓观察。"
                elif pnl_pct <= -8:
                    action = "波段失守时先减仓降风险，再等下一次修复确认。"
                else:
                    action = "波段仓位先看趋势是否延续，不急着在成本线附近来回折腾。"

        template = "\n".join(
            [
                f"当前状态：{headline}",
                f"风险点：{risk}",
                f"仓位动作：{action}",
                (
                    f"处理模板：总仓 {position.quantity} 股，可用 {position.available_quantity} 股，冻结 {position.frozen_quantity} 股，"
                    f"当前仓位占账户资产约 {weight_pct:.2f}%。"
                ),
            ]
        )
        return PortfolioPositionAdvice(
            headline=headline,
            risk=risk,
            action=action,
            template=template,
        )


portfolio_store = PortfolioStore()
