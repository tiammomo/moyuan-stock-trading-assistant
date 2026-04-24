from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.core.config import get_settings
from app.schemas import (
    MonitorNotificationChannelCreate,
    MonitorNotificationChannelRecord,
    MonitorNotificationChannelUpdate,
    MonitorNotificationDeliveryRecord,
    MonitorNotificationSettings,
    MonitorNotificationSettingsUpdate,
)

from .json_store import JsonFileStore


DEFAULT_BARK_SERVER_URL = "https://api.day.app"


class MonitorNotificationStoreError(RuntimeError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def _clean_text(value: Optional[str]) -> Optional[str]:
    text = " ".join(str(value or "").strip().split())
    return text or None


def _normalize_url(value: Optional[str], *, strip_trailing_slash: bool = False) -> Optional[str]:
    text = _clean_text(value)
    if text is None:
        return None
    normalized = text.rstrip("/") if strip_trailing_slash else text
    if not normalized.startswith(("http://", "https://")):
        raise MonitorNotificationStoreError("通知地址必须以 http:// 或 https:// 开头")
    return normalized


def _default_settings_payload() -> Dict[str, Any]:
    now = _utc_now_iso()
    return {
        "default_channel_ids": [],
        "quiet_hours_enabled": False,
        "quiet_hours_start": "22:30",
        "quiet_hours_end": "08:30",
        "delivery_retry_attempts": 2,
        "delivery_dedupe_minutes": 30,
        "updated_at": now,
    }


class MonitorNotificationStore:
    def __init__(self) -> None:
        settings = get_settings()
        self.channels_store = JsonFileStore(
            settings.data_dir / "monitor_notification_channels.json",
            lambda: [],
        )
        self.settings_store = JsonFileStore(
            settings.data_dir / "monitor_notification_settings.json",
            _default_settings_payload,
        )
        self.deliveries_store = JsonFileStore(
            settings.data_dir / "monitor_notification_deliveries.json",
            lambda: [],
        )

    def list_channels(self) -> List[MonitorNotificationChannelRecord]:
        rows = sorted(self.channels_store.read(), key=lambda item: item.get("updated_at", ""), reverse=True)
        return [MonitorNotificationChannelRecord(**row) for row in rows]

    def get_channel(self, channel_id: str) -> Optional[MonitorNotificationChannelRecord]:
        for row in self.channels_store.read():
            if row.get("id") == channel_id:
                return MonitorNotificationChannelRecord(**row)
        return None

    def create_channel(self, data: MonitorNotificationChannelCreate) -> MonitorNotificationChannelRecord:
        payload = self._normalized_channel_payload(data.model_dump())
        now = _utc_now_iso()
        record = {
            "id": f"nc_{uuid4().hex[:12]}",
            **payload,
            "created_at": now,
            "updated_at": now,
        }

        def mutate(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            rows.append(record)
            return rows

        self.channels_store.update(mutate)
        return MonitorNotificationChannelRecord(**record)

    def update_channel(
        self,
        channel_id: str,
        update: MonitorNotificationChannelUpdate,
    ) -> Optional[MonitorNotificationChannelRecord]:
        existing = self.get_channel(channel_id)
        if existing is None:
            return None
        patch = update.model_dump(exclude_unset=True)
        merged = {
            **existing.model_dump(mode="json"),
            **patch,
        }
        payload = self._normalized_channel_payload(merged)
        updated_record: Optional[Dict[str, Any]] = None

        def mutate(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            nonlocal updated_record
            for row in rows:
                if row.get("id") != channel_id:
                    continue
                row.update(payload)
                row["updated_at"] = _utc_now_iso()
                updated_record = dict(row)
                break
            return rows

        self.channels_store.update(mutate)
        return MonitorNotificationChannelRecord(**updated_record) if updated_record else None

    def delete_channel(self, channel_id: str) -> bool:
        rows = self.channels_store.read()
        remaining = [row for row in rows if row.get("id") != channel_id]
        deleted = len(remaining) < len(rows)
        if deleted:
            self.channels_store.write(remaining)
            settings = self.get_settings()
            filtered = [item for item in settings.default_channel_ids if item != channel_id]
            if filtered != settings.default_channel_ids:
                self.update_settings(
                    MonitorNotificationSettingsUpdate(default_channel_ids=filtered)
                )
        return deleted

    def get_settings(self) -> MonitorNotificationSettings:
        payload = self.settings_store.read()
        if not payload:
            payload = _default_settings_payload()
            self.settings_store.write(payload)
        return MonitorNotificationSettings(**payload)

    def update_settings(
        self,
        update: MonitorNotificationSettingsUpdate,
    ) -> MonitorNotificationSettings:
        patch = update.model_dump(exclude_unset=True)
        known_channel_ids = {channel.id for channel in self.list_channels()}
        updated_payload: Optional[Dict[str, Any]] = None

        def mutate(payload: Dict[str, Any]) -> Dict[str, Any]:
            nonlocal updated_payload
            next_payload = dict(payload or _default_settings_payload())
            if "default_channel_ids" in patch and patch["default_channel_ids"] is not None:
                deduped = list(dict.fromkeys(str(item) for item in patch["default_channel_ids"]))
                next_payload["default_channel_ids"] = [
                    channel_id for channel_id in deduped if channel_id in known_channel_ids
                ]
            if "quiet_hours_enabled" in patch and patch["quiet_hours_enabled"] is not None:
                next_payload["quiet_hours_enabled"] = bool(patch["quiet_hours_enabled"])
            if "quiet_hours_start" in patch and patch["quiet_hours_start"] is not None:
                next_payload["quiet_hours_start"] = self._validate_time_text(patch["quiet_hours_start"])
            if "quiet_hours_end" in patch and patch["quiet_hours_end"] is not None:
                next_payload["quiet_hours_end"] = self._validate_time_text(patch["quiet_hours_end"])
            if "delivery_retry_attempts" in patch and patch["delivery_retry_attempts"] is not None:
                next_payload["delivery_retry_attempts"] = int(patch["delivery_retry_attempts"])
            if "delivery_dedupe_minutes" in patch and patch["delivery_dedupe_minutes"] is not None:
                next_payload["delivery_dedupe_minutes"] = int(patch["delivery_dedupe_minutes"])
            next_payload["updated_at"] = _utc_now_iso()
            updated_payload = next_payload
            return next_payload

        self.settings_store.update(mutate)
        return MonitorNotificationSettings(**updated_payload)

    def list_deliveries(self, limit: int = 30) -> List[MonitorNotificationDeliveryRecord]:
        safe_limit = max(1, min(int(limit), 200))
        rows = self.deliveries_store.read()[:safe_limit]
        return [MonitorNotificationDeliveryRecord(**row) for row in rows]

    def append_delivery(self, delivery: MonitorNotificationDeliveryRecord) -> None:
        def mutate(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            next_rows = [delivery.model_dump(mode="json"), *rows]
            return next_rows[:200]

        self.deliveries_store.update(mutate)

    def _normalized_channel_payload(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        name = _clean_text(raw.get("name"))
        channel_type = str(raw.get("type") or "").strip()
        if not name:
            raise MonitorNotificationStoreError("通知渠道名称不能为空")
        if channel_type not in {"bark", "webhook"}:
            raise MonitorNotificationStoreError("通知渠道类型只支持 bark 或 webhook")

        payload: Dict[str, Any] = {
            "name": name,
            "type": channel_type,
            "enabled": bool(raw.get("enabled", True)),
            "bark_server_url": None,
            "bark_device_key": None,
            "bark_group": None,
            "bark_sound": None,
            "webhook_url": None,
        }

        if channel_type == "bark":
            device_key = _clean_text(raw.get("bark_device_key"))
            if not device_key:
                raise MonitorNotificationStoreError("Bark 渠道必须填写设备 key")
            payload["bark_server_url"] = _normalize_url(
                raw.get("bark_server_url") or DEFAULT_BARK_SERVER_URL,
                strip_trailing_slash=True,
            )
            payload["bark_device_key"] = device_key
            payload["bark_group"] = _clean_text(raw.get("bark_group"))
            payload["bark_sound"] = _clean_text(raw.get("bark_sound"))
        elif channel_type == "webhook":
            webhook_url = _normalize_url(raw.get("webhook_url"))
            if not webhook_url:
                raise MonitorNotificationStoreError("Webhook 渠道必须填写回调地址")
            payload["webhook_url"] = webhook_url

        return payload

    def _validate_time_text(self, value: str) -> str:
        text = str(value or "").strip()
        if len(text) != 5 or text[2] != ":":
            raise MonitorNotificationStoreError("静默时段时间格式必须是 HH:MM")
        hour_text, minute_text = text.split(":", 1)
        try:
            hour = int(hour_text)
            minute = int(minute_text)
        except ValueError as exc:
            raise MonitorNotificationStoreError("静默时段时间格式必须是 HH:MM") from exc
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise MonitorNotificationStoreError("静默时段时间必须落在 00:00 到 23:59")
        return f"{hour:02d}:{minute:02d}"


monitor_notification_store = MonitorNotificationStore()
