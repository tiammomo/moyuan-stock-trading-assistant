from __future__ import annotations

from datetime import datetime, timezone
from math import ceil
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.core.config import get_settings
from app.schemas import (
    MonitorRuleCondition,
    MonitorRuleConditionGroup,
    MonitorRuleCreate,
    MonitorRuleRecord,
    MonitorRuleUpdate,
    WatchItemRecord,
)

from .json_store import JsonFileStore
from .repository import repository


DEFAULT_RULE_NAME = "默认异动提醒"


class WatchRuleStoreError(RuntimeError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def _default_condition_group() -> MonitorRuleConditionGroup:
    return MonitorRuleConditionGroup(
        op="or",
        items=[
            MonitorRuleCondition(type="change_pct", op=">=", value=3),
            MonitorRuleCondition(type="change_pct", op="<=", value=-3),
            MonitorRuleCondition(type="volume_ratio", op=">=", value=1.8),
            MonitorRuleCondition(type="weibi", op=">=", value=20),
            MonitorRuleCondition(type="weibi", op="<=", value=-20),
        ],
    )


class WatchRuleStore:
    def __init__(self) -> None:
        settings = get_settings()
        self.default_cooldown_minutes = max(
            0,
            ceil(max(0, int(settings.watch_monitor_event_cooldown_seconds)) / 60),
        )
        self.store = JsonFileStore(settings.data_dir / "watch_rules.json", lambda: [])

    def list_rules(self, *, item_id: Optional[str] = None) -> List[MonitorRuleRecord]:
        rows = self.store.read()
        items = [MonitorRuleRecord(**row) for row in rows]
        if item_id:
            items = [rule for rule in items if rule.item_id == item_id]
        items.sort(key=lambda rule: rule.updated_at, reverse=True)
        return items

    def get_rule(self, rule_id: str) -> Optional[MonitorRuleRecord]:
        for row in self.store.read():
            if row.get("id") == rule_id:
                return MonitorRuleRecord(**row)
        return None

    def get_rules_for_item(self, item_id: str, *, enabled_only: bool = False) -> List[MonitorRuleRecord]:
        rules = self.list_rules(item_id=item_id)
        if enabled_only:
            rules = [rule for rule in rules if rule.enabled]
        return rules

    def ensure_default_rules(self, items: List[WatchItemRecord]) -> List[MonitorRuleRecord]:
        created: List[MonitorRuleRecord] = []
        known_item_ids = {item.id for item in items}

        def mutate(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            existing_item_ids = {str(row.get("item_id") or "") for row in rows}
            for item in items:
                if item.id in existing_item_ids:
                    continue
                now = _utc_now_iso()
                payload = {
                    "id": f"wr_{uuid4().hex[:12]}",
                    "item_id": item.id,
                    "symbol": item.symbol,
                    "name": item.name,
                    "bucket": item.bucket.value,
                    "rule_name": DEFAULT_RULE_NAME,
                    "enabled": True,
                    "severity": "info",
                    "condition_group": _default_condition_group().model_dump(mode="json"),
                    "market_hours_mode": "trading_only",
                    "repeat_mode": "repeat",
                    "expire_at": None,
                    "cooldown_minutes": self.default_cooldown_minutes,
                    "max_triggers_per_day": 5,
                    "created_at": now,
                    "updated_at": now,
                }
                rows.append(payload)
                existing_item_ids.add(item.id)
                created.append(MonitorRuleRecord(**payload))

            rows[:] = [
                row
                for row in rows
                if not row.get("item_id") or str(row.get("item_id")) in known_item_ids
            ]
            return rows

        self.store.update(mutate)
        return created

    def ensure_default_rule_for_item(self, item: WatchItemRecord) -> MonitorRuleRecord:
        existing = self.get_rules_for_item(item.id)
        if existing:
            return existing[0]
        created = self.ensure_default_rules([item])
        return created[0] if created else self.get_rules_for_item(item.id)[0]

    def sync_item_metadata(self, item: WatchItemRecord) -> None:
        def mutate(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            for row in rows:
                if row.get("item_id") != item.id:
                    continue
                row["symbol"] = item.symbol
                row["name"] = item.name
                row["bucket"] = item.bucket.value
                row["updated_at"] = _utc_now_iso()
            return rows

        self.store.update(mutate)

    def create_rule(self, data: MonitorRuleCreate) -> MonitorRuleRecord:
        item = self._require_watch_item(data.item_id)
        now = _utc_now_iso()
        payload = {
            "id": f"wr_{uuid4().hex[:12]}",
            "item_id": item.id,
            "symbol": item.symbol,
            "name": item.name,
            "bucket": item.bucket.value,
            "rule_name": data.rule_name.strip() or DEFAULT_RULE_NAME,
            "enabled": data.enabled,
            "severity": data.severity,
            "condition_group": data.condition_group.model_dump(mode="json"),
            "market_hours_mode": data.market_hours_mode,
            "repeat_mode": data.repeat_mode,
            "expire_at": data.expire_at.isoformat() if data.expire_at is not None else None,
            "cooldown_minutes": data.cooldown_minutes,
            "max_triggers_per_day": data.max_triggers_per_day,
            "created_at": now,
            "updated_at": now,
        }

        def mutate(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            rows.append(payload)
            return rows

        self.store.update(mutate)
        return MonitorRuleRecord(**payload)

    def update_rule(self, rule_id: str, update: MonitorRuleUpdate) -> Optional[MonitorRuleRecord]:
        patch = update.model_dump(exclude_unset=True)
        updated: Optional[Dict[str, Any]] = None

        def mutate(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            nonlocal updated
            for row in rows:
                if row.get("id") != rule_id:
                    continue
                if "rule_name" in patch and isinstance(patch["rule_name"], str):
                    row["rule_name"] = patch["rule_name"].strip() or row["rule_name"]
                if "enabled" in patch:
                    row["enabled"] = patch["enabled"]
                if "severity" in patch and patch["severity"]:
                    row["severity"] = patch["severity"]
                if "condition_group" in patch and patch["condition_group"] is not None:
                    row["condition_group"] = patch["condition_group"].model_dump(mode="json")
                if "market_hours_mode" in patch and patch["market_hours_mode"]:
                    row["market_hours_mode"] = patch["market_hours_mode"]
                if "repeat_mode" in patch and patch["repeat_mode"]:
                    row["repeat_mode"] = patch["repeat_mode"]
                if "expire_at" in patch:
                    expire_at = patch["expire_at"]
                    row["expire_at"] = expire_at.isoformat() if expire_at is not None else None
                if "cooldown_minutes" in patch and patch["cooldown_minutes"] is not None:
                    row["cooldown_minutes"] = patch["cooldown_minutes"]
                if "max_triggers_per_day" in patch and patch["max_triggers_per_day"] is not None:
                    row["max_triggers_per_day"] = patch["max_triggers_per_day"]
                row["updated_at"] = _utc_now_iso()
                updated = dict(row)
                break
            return rows

        self.store.update(mutate)
        return MonitorRuleRecord(**updated) if updated else None

    def delete_rule(self, rule_id: str) -> bool:
        before = len(self.store.read())
        self.store.write([row for row in self.store.read() if row.get("id") != rule_id])
        return len(self.store.read()) < before

    def delete_rules_for_item(self, item_id: str) -> int:
        rows = self.store.read()
        remaining = [row for row in rows if row.get("item_id") != item_id]
        removed = len(rows) - len(remaining)
        if removed > 0:
            self.store.write(remaining)
        return removed

    def _require_watch_item(self, item_id: str) -> WatchItemRecord:
        for item in repository.list_watchlist():
            if item.id == item_id:
                return item
        raise WatchRuleStoreError("候选池里未找到对应股票，无法创建提醒规则")


watch_rule_store = WatchRuleStore()
