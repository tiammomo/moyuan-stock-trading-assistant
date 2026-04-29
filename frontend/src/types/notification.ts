export type MonitorNotificationChannelType =
  | "bark"
  | "webhook"
  | "pushplus"
  | "wecom_bot"
  | "dingtalk_bot"
  | "telegram_bot";
export type MonitorNotificationDeliveryStatus = "success" | "failed" | "skipped";

export interface MonitorNotificationChannelCreate {
  name: string;
  type: MonitorNotificationChannelType;
  enabled: boolean;
  bark_server_url?: string | null;
  bark_device_key?: string | null;
  bark_group?: string | null;
  bark_sound?: string | null;
  webhook_url?: string | null;
  pushplus_token?: string | null;
  wecom_webhook_url?: string | null;
  dingtalk_webhook_url?: string | null;
  telegram_bot_token?: string | null;
  telegram_chat_id?: string | null;
}

export interface MonitorNotificationChannelUpdate {
  name?: string | null;
  type?: MonitorNotificationChannelType | null;
  enabled?: boolean | null;
  bark_server_url?: string | null;
  bark_device_key?: string | null;
  bark_group?: string | null;
  bark_sound?: string | null;
  webhook_url?: string | null;
  pushplus_token?: string | null;
  wecom_webhook_url?: string | null;
  dingtalk_webhook_url?: string | null;
  telegram_bot_token?: string | null;
  telegram_chat_id?: string | null;
}

export interface MonitorNotificationChannelRecord {
  id: string;
  name: string;
  type: MonitorNotificationChannelType;
  enabled: boolean;
  bark_server_url?: string | null;
  bark_device_key?: string | null;
  bark_group?: string | null;
  bark_sound?: string | null;
  webhook_url?: string | null;
  pushplus_token?: string | null;
  wecom_webhook_url?: string | null;
  dingtalk_webhook_url?: string | null;
  telegram_bot_token?: string | null;
  telegram_chat_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface MonitorNotificationSettings {
  default_channel_ids: string[];
  quiet_hours_enabled: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
  delivery_retry_attempts: number;
  delivery_dedupe_minutes: number;
  updated_at: string;
}

export interface MonitorNotificationSettingsUpdate {
  default_channel_ids?: string[] | null;
  quiet_hours_enabled?: boolean | null;
  quiet_hours_start?: string | null;
  quiet_hours_end?: string | null;
  delivery_retry_attempts?: number | null;
  delivery_dedupe_minutes?: number | null;
}

export interface MonitorNotificationDeliveryRecord {
  id: string;
  event_id?: string | null;
  rule_id?: string | null;
  rule_name?: string | null;
  symbol?: string | null;
  name?: string | null;
  channel_id: string;
  channel_name: string;
  channel_type: MonitorNotificationChannelType;
  status: MonitorNotificationDeliveryStatus;
  title: string;
  reason?: string | null;
  attempts: number;
  dedupe_key?: string | null;
  created_at: string;
}
