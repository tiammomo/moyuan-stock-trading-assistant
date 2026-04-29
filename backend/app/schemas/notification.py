from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import Field

from .common import ContractModel


MonitorNotificationChannelType = Literal[
    "bark",
    "webhook",
    "pushplus",
    "wecom_bot",
    "dingtalk_bot",
    "telegram_bot",
]
MonitorNotificationDeliveryStatus = Literal["success", "failed", "skipped"]


class MonitorNotificationChannelCreate(ContractModel):
    name: str = Field(..., min_length=1)
    type: MonitorNotificationChannelType
    enabled: bool = True
    bark_server_url: Optional[str] = None
    bark_device_key: Optional[str] = None
    bark_group: Optional[str] = None
    bark_sound: Optional[str] = None
    webhook_url: Optional[str] = None
    pushplus_token: Optional[str] = None
    wecom_webhook_url: Optional[str] = None
    dingtalk_webhook_url: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None


class MonitorNotificationChannelUpdate(ContractModel):
    name: Optional[str] = None
    type: Optional[MonitorNotificationChannelType] = None
    enabled: Optional[bool] = None
    bark_server_url: Optional[str] = None
    bark_device_key: Optional[str] = None
    bark_group: Optional[str] = None
    bark_sound: Optional[str] = None
    webhook_url: Optional[str] = None
    pushplus_token: Optional[str] = None
    wecom_webhook_url: Optional[str] = None
    dingtalk_webhook_url: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None


class MonitorNotificationChannelRecord(ContractModel):
    id: str
    name: str
    type: MonitorNotificationChannelType
    enabled: bool = True
    bark_server_url: Optional[str] = None
    bark_device_key: Optional[str] = None
    bark_group: Optional[str] = None
    bark_sound: Optional[str] = None
    webhook_url: Optional[str] = None
    pushplus_token: Optional[str] = None
    wecom_webhook_url: Optional[str] = None
    dingtalk_webhook_url: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class MonitorNotificationSettings(ContractModel):
    default_channel_ids: List[str] = Field(default_factory=list)
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = "22:30"
    quiet_hours_end: str = "08:30"
    delivery_retry_attempts: int = Field(default=2, ge=1, le=5)
    delivery_dedupe_minutes: int = Field(default=30, ge=0, le=1440)
    updated_at: datetime


class MonitorNotificationSettingsUpdate(ContractModel):
    default_channel_ids: Optional[List[str]] = None
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    delivery_retry_attempts: Optional[int] = Field(default=None, ge=1, le=5)
    delivery_dedupe_minutes: Optional[int] = Field(default=None, ge=0, le=1440)


class MonitorNotificationDeliveryRecord(ContractModel):
    id: str
    event_id: Optional[str] = None
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    symbol: Optional[str] = None
    name: Optional[str] = None
    channel_id: str
    channel_name: str
    channel_type: MonitorNotificationChannelType
    status: MonitorNotificationDeliveryStatus
    title: str
    reason: Optional[str] = None
    attempts: int = Field(default=1, ge=1)
    dedupe_key: Optional[str] = None
    created_at: datetime
