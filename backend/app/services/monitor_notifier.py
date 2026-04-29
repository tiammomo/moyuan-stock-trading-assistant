from __future__ import annotations

import json
import logging
import time
import urllib.parse
import urllib.request
from datetime import datetime, time as dtime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.core.config import get_settings
from app.schemas import (
    MonitorNotificationChannelRecord,
    MonitorNotificationDeliveryRecord,
    MonitorRuleRecord,
    WatchMonitorEvent,
)

from .json_store import JsonFileStore
from .monitor_notification_store import monitor_notification_store
from .trading_calendar import CN_TZ


logger = logging.getLogger(__name__)


class MonitorNotifier:
    def __init__(self) -> None:
        settings = get_settings()
        self.timeout_seconds = max(3, int(getattr(settings, "watch_notification_timeout_seconds", 10)))
        self.state_store = JsonFileStore(
            settings.data_dir / "monitor_notification_state.json",
            lambda: {"dedupe": {}},
        )

    def list_recent_deliveries(self, limit: int = 30) -> List[MonitorNotificationDeliveryRecord]:
        return monitor_notification_store.list_deliveries(limit=limit)

    def send_test(self, channel_id: str) -> MonitorNotificationDeliveryRecord:
        channel = monitor_notification_store.get_channel(channel_id)
        if channel is None:
            raise ValueError("通知渠道不存在")
        if not channel.enabled:
            raise ValueError("通知渠道已停用，无法发送测试消息")
        title = "盯盘通知测试"
        body = (
            "这是一条测试消息，用于验证当前通知渠道可用。"
            f"\n渠道：{channel.name}"
            f"\n发送时间：{datetime.now(CN_TZ).strftime('%Y-%m-%d %H:%M:%S')}"
        )
        attempts, error = self._send_with_retry(
            channel,
            {
                "title": title,
                "body": body,
                "payload": {
                    "source": "watch_monitor_test",
                    "channel_id": channel.id,
                    "channel_name": channel.name,
                    "sent_at": datetime.now(CN_TZ).isoformat(),
                },
            },
            max_attempts=1,
        )
        delivery = MonitorNotificationDeliveryRecord(
            id=f"nd_{uuid4().hex[:12]}",
            channel_id=channel.id,
            channel_name=channel.name,
            channel_type=channel.type,
            status="success" if error is None else "failed",
            title=title,
            reason=error,
            attempts=attempts,
            created_at=datetime.now(CN_TZ),
        )
        monitor_notification_store.append_delivery(delivery)
        return delivery

    def dispatch_rule_event(
        self,
        event: WatchMonitorEvent,
        rule: MonitorRuleRecord,
        *,
        fingerprint: str,
    ) -> List[MonitorNotificationDeliveryRecord]:
        return self.dispatch_message(
            channel_ids=rule.notify_channel_ids,
            fingerprint=fingerprint,
            title=event.title,
            body=self._event_body(event, rule),
            payload=self._event_payload(event, rule),
            created_at=event.created_at,
            event=event,
            rule=rule,
        )

    def dispatch_message(
        self,
        *,
        channel_ids: List[str],
        fingerprint: str,
        title: str,
        body: str,
        payload: Dict[str, Any],
        created_at: Optional[datetime] = None,
        event: Optional[WatchMonitorEvent] = None,
        rule: Optional[MonitorRuleRecord] = None,
    ) -> List[MonitorNotificationDeliveryRecord]:
        settings = monitor_notification_store.get_settings()
        effective_channel_ids = channel_ids or settings.default_channel_ids
        channels = self._resolve_channels(effective_channel_ids)
        if not channels:
            return []

        now = created_at or datetime.now(CN_TZ)
        if now.tzinfo is None:
            now = now.replace(tzinfo=CN_TZ)
        else:
            now = now.astimezone(CN_TZ)
        quiet_hours = settings.quiet_hours_enabled and self._in_quiet_hours(
            now,
            settings.quiet_hours_start,
            settings.quiet_hours_end,
        )
        deliveries: List[MonitorNotificationDeliveryRecord] = []
        for channel in channels:
            dedupe_key = f"{channel.id}|{fingerprint}"
            if quiet_hours:
                deliveries.append(
                    self._record_delivery(
                        event=event,
                        rule=rule,
                        channel=channel,
                        status="skipped",
                        title=title,
                        reason="当前处于静默时段，已跳过发送",
                        attempts=1,
                        dedupe_key=dedupe_key,
                    )
                )
                continue
            if settings.delivery_dedupe_minutes > 0 and self._is_duplicate(
                dedupe_key,
                now=now,
                dedupe_minutes=settings.delivery_dedupe_minutes,
            ):
                deliveries.append(
                    self._record_delivery(
                        event=event,
                        rule=rule,
                        channel=channel,
                        status="skipped",
                        title=title,
                        reason=f"{settings.delivery_dedupe_minutes} 分钟去重窗口内已发送",
                        attempts=1,
                        dedupe_key=dedupe_key,
                    )
                )
                continue

            attempts, error = self._send_with_retry(
                channel,
                {
                    "title": title,
                    "body": body,
                    "payload": payload,
                },
                max_attempts=settings.delivery_retry_attempts,
            )
            if error is None:
                self._mark_delivery_success(dedupe_key, now)
                deliveries.append(
                    self._record_delivery(
                        event=event,
                        rule=rule,
                        channel=channel,
                        status="success",
                        title=title,
                        reason=None,
                        attempts=attempts,
                        dedupe_key=dedupe_key,
                    )
                )
            else:
                deliveries.append(
                    self._record_delivery(
                        event=event,
                        rule=rule,
                        channel=channel,
                        status="failed",
                        title=title,
                        reason=error,
                        attempts=attempts,
                        dedupe_key=dedupe_key,
                    )
                )
        return deliveries

    def _resolve_channels(self, channel_ids: List[str]) -> List[MonitorNotificationChannelRecord]:
        channels: List[MonitorNotificationChannelRecord] = []
        seen: set[str] = set()
        for channel_id in channel_ids:
            if channel_id in seen:
                continue
            seen.add(channel_id)
            channel = monitor_notification_store.get_channel(channel_id)
            if channel is None or not channel.enabled:
                continue
            channels.append(channel)
        return channels

    def _record_delivery(
        self,
        *,
        event: Optional[WatchMonitorEvent],
        rule: Optional[MonitorRuleRecord],
        channel: MonitorNotificationChannelRecord,
        status: str,
        title: str,
        reason: Optional[str],
        attempts: int,
        dedupe_key: Optional[str],
    ) -> MonitorNotificationDeliveryRecord:
        delivery = MonitorNotificationDeliveryRecord(
            id=f"nd_{uuid4().hex[:12]}",
            event_id=event.id if event is not None else None,
            rule_id=rule.id if rule is not None else None,
            rule_name=rule.rule_name if rule is not None else None,
            symbol=event.symbol if event is not None else None,
            name=event.name if event is not None else None,
            channel_id=channel.id,
            channel_name=channel.name,
            channel_type=channel.type,
            status=status,
            title=title,
            reason=reason,
            attempts=attempts,
            dedupe_key=dedupe_key,
            created_at=datetime.now(CN_TZ),
        )
        monitor_notification_store.append_delivery(delivery)
        return delivery

    def _event_body(self, event: WatchMonitorEvent, rule: MonitorRuleRecord) -> str:
        parts = [
            event.summary,
            f"股票：{event.name} {event.symbol}",
            f"规则：{rule.rule_name}",
            f"时间：{event.created_at.astimezone(CN_TZ).strftime('%Y-%m-%d %H:%M:%S')}",
        ]
        return "\n".join(parts)

    def _event_payload(self, event: WatchMonitorEvent, rule: MonitorRuleRecord) -> Dict[str, Any]:
        return {
            "source": "watch_monitor",
            "event": event.model_dump(mode="json"),
            "rule": {
                "id": rule.id,
                "name": rule.rule_name,
                "severity": rule.severity,
            },
        }

    def _send_with_retry(
        self,
        channel: MonitorNotificationChannelRecord,
        message: Dict[str, Any],
        *,
        max_attempts: int,
    ) -> tuple[int, Optional[str]]:
        attempts = 0
        last_error: Optional[str] = None
        safe_attempts = max(1, int(max_attempts))
        for attempt in range(1, safe_attempts + 1):
            attempts = attempt
            try:
                if channel.type == "bark":
                    self._send_bark(channel, title=str(message["title"]), body=str(message["body"]))
                elif channel.type == "webhook":
                    self._send_webhook(channel, payload=message["payload"])
                elif channel.type == "pushplus":
                    self._send_pushplus(channel, title=str(message["title"]), body=str(message["body"]))
                elif channel.type == "wecom_bot":
                    self._send_wecom_bot(channel, title=str(message["title"]), body=str(message["body"]))
                elif channel.type == "dingtalk_bot":
                    self._send_dingtalk_bot(channel, title=str(message["title"]), body=str(message["body"]))
                elif channel.type == "telegram_bot":
                    self._send_telegram_bot(channel, title=str(message["title"]), body=str(message["body"]))
                else:
                    raise ValueError(f"暂不支持的通知渠道类型：{channel.type}")
                return attempts, None
            except Exception as exc:  # pragma: no cover - defensive
                last_error = str(exc)
                logger.warning(
                    "Monitor notification failed: channel=%s attempt=%s error=%s",
                    channel.id,
                    attempt,
                    exc,
                )
                if attempt < safe_attempts:
                    time.sleep(min(1.0 * attempt, 2.0))
        return attempts, last_error

    def _send_bark(
        self,
        channel: MonitorNotificationChannelRecord,
        *,
        title: str,
        body: str,
    ) -> None:
        if not channel.bark_server_url or not channel.bark_device_key:
            raise ValueError("Bark 通知配置不完整")
        encoded_title = urllib.parse.quote(title, safe="")
        encoded_body = urllib.parse.quote(body, safe="")
        params = {}
        if channel.bark_group:
            params["group"] = channel.bark_group
        if channel.bark_sound:
            params["sound"] = channel.bark_sound
        query = f"?{urllib.parse.urlencode(params)}" if params else ""
        url = (
            f"{channel.bark_server_url}/{channel.bark_device_key}/"
            f"{encoded_title}/{encoded_body}{query}"
        )
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            status = getattr(response, "status", 200)
            if status >= 400:
                raise ValueError(f"Bark 返回 HTTP {status}")

    def _send_webhook(
        self,
        channel: MonitorNotificationChannelRecord,
        *,
        payload: Dict[str, Any],
    ) -> None:
        if not channel.webhook_url:
            raise ValueError("Webhook 地址未配置")
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            channel.webhook_url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            status = getattr(response, "status", 200)
            if status >= 400:
                raise ValueError(f"Webhook 返回 HTTP {status}")

    def _send_pushplus(
        self,
        channel: MonitorNotificationChannelRecord,
        *,
        title: str,
        body: str,
    ) -> None:
        if not channel.pushplus_token:
            raise ValueError("PushPlus Token 未配置")
        payload = {
            "token": channel.pushplus_token,
            "title": title,
            "content": body.replace("\n", "<br>"),
            "template": "html",
        }
        self._post_json("https://www.pushplus.plus/send", payload, service_name="PushPlus")

    def _send_wecom_bot(
        self,
        channel: MonitorNotificationChannelRecord,
        *,
        title: str,
        body: str,
    ) -> None:
        if not channel.wecom_webhook_url:
            raise ValueError("企业微信机器人 Webhook 未配置")
        self._post_json(
            channel.wecom_webhook_url,
            {
                "msgtype": "markdown",
                "markdown": {"content": f"**{title}**\n\n{body}"},
            },
            service_name="企业微信机器人",
        )

    def _send_dingtalk_bot(
        self,
        channel: MonitorNotificationChannelRecord,
        *,
        title: str,
        body: str,
    ) -> None:
        if not channel.dingtalk_webhook_url:
            raise ValueError("钉钉机器人 Webhook 未配置")
        self._post_json(
            channel.dingtalk_webhook_url,
            {
                "msgtype": "markdown",
                "markdown": {"title": title, "text": f"### {title}\n\n{body}"},
            },
            service_name="钉钉机器人",
        )

    def _send_telegram_bot(
        self,
        channel: MonitorNotificationChannelRecord,
        *,
        title: str,
        body: str,
    ) -> None:
        if not channel.telegram_bot_token or not channel.telegram_chat_id:
            raise ValueError("Telegram Bot Token 或 Chat ID 未配置")
        token = urllib.parse.quote(channel.telegram_bot_token, safe=":")
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        self._post_json(
            url,
            {
                "chat_id": channel.telegram_chat_id,
                "text": f"{title}\n\n{body}",
                "disable_web_page_preview": True,
            },
            service_name="Telegram",
        )

    def _post_json(self, url: str, payload: Dict[str, Any], *, service_name: str) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            status = getattr(response, "status", 200)
            if status >= 400:
                raise ValueError(f"{service_name} 返回 HTTP {status}")

    def _in_quiet_hours(self, now: datetime, start_text: str, end_text: str) -> bool:
        current = now.astimezone(CN_TZ).time()
        start = self._parse_clock(start_text)
        end = self._parse_clock(end_text)
        if start == end:
            return True
        if start < end:
            return start <= current < end
        return current >= start or current < end

    def _parse_clock(self, value: str) -> dtime:
        hour_text, minute_text = value.split(":", 1)
        return dtime(hour=int(hour_text), minute=int(minute_text))

    def _is_duplicate(self, dedupe_key: str, *, now: datetime, dedupe_minutes: int) -> bool:
        state = self.state_store.read()
        dedupe = state.get("dedupe") or {}
        last_sent_at = dedupe.get(dedupe_key)
        if not last_sent_at:
            return False
        try:
            last_dt = datetime.fromisoformat(str(last_sent_at))
        except ValueError:
            return False
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=CN_TZ)
        return (now - last_dt).total_seconds() < dedupe_minutes * 60

    def _mark_delivery_success(self, dedupe_key: str, now: datetime) -> None:
        def mutate(payload: Dict[str, Any]) -> Dict[str, Any]:
            next_payload = dict(payload or {"dedupe": {}})
            dedupe = next_payload.setdefault("dedupe", {})
            dedupe[dedupe_key] = now.isoformat()
            if len(dedupe) > 500:
                keys = sorted(dedupe.keys(), key=lambda item: dedupe[item], reverse=True)[:500]
                next_payload["dedupe"] = {key: dedupe[key] for key in keys}
            return next_payload

        self.state_store.update(mutate)


monitor_notifier = MonitorNotifier()
